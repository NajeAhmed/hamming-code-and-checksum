"""
================================================================================
Comprehensive Unit Test Suite for ECC & Integrity Studio
================================================================================
Tests:
1. Parity count calculation for standard word sizes.
2. Pristine encoding & zero-error verification.
3. 100% Single-bit error correction across ALL bit positions.
4. Single-bit error in overall parity bit P0.
5. 100% Double-bit error detection across all bit pairs (SEC-DED guarantee).
6. Checksum-assisted 2-bit error resolution.
7. RFC 1071 Checksum 1's complement addition & verification.
================================================================================
"""

import unittest
from ecc_core import BitManipulator, ExtendedHammingCode, InternetChecksum


class TestExtendedHamming(unittest.TestCase):

    def test_parity_bit_counts(self):
        """Test standard block configurations."""
        self.assertEqual(ExtendedHammingCode.calc_parity_bits(4), 3)   # Hamming (7,4) -> (8,4) with P0
        self.assertEqual(ExtendedHammingCode.calc_parity_bits(8), 4)   # Hamming (12,8) -> (13,8) with P0
        self.assertEqual(ExtendedHammingCode.calc_parity_bits(11), 4)  # Hamming (15,11) -> (16,11) with P0
        self.assertEqual(ExtendedHammingCode.calc_parity_bits(16), 5)  # Hamming (21,16) -> (22,16) with P0

    def test_pristine_codeword(self):
        """Test that uncorrupted codewords analyze as VALID."""
        for pattern in ["1011", "01000001", "10110010110", "1111000011110000"]:
            data_bits = BitManipulator.binary_string_to_bits(pattern)
            enc = ExtendedHammingCode.encode(data_bits)
            cw = enc["raw_codeword"]
            analysis = ExtendedHammingCode.analyze(cw)

            self.assertEqual(analysis["classification"], "VALID")
            self.assertEqual(analysis["syndrome_value"], 0)
            self.assertEqual(analysis["p_check"], 0)

    def test_all_single_bit_errors(self):
        """Test that flipping ANY single bit in the codeword is correctly pinpointed and corrected."""
        test_inputs = [
            "1011",               # 4-bit data
            "01000001",           # 8-bit data ('A')
            "10110010110"         # 11-bit data
        ]

        for inp in test_inputs:
            data_bits = BitManipulator.binary_string_to_bits(inp)
            enc = ExtendedHammingCode.encode(data_bits)
            orig_cw = enc["raw_codeword"]
            total_bits = len(orig_cw)

            # Flip each bit position 1..total_bits-1 (standard bits)
            for err_pos in range(1, total_bits):
                corrupted = list(orig_cw)
                corrupted[err_pos] ^= 1

                analysis = ExtendedHammingCode.analyze(corrupted)
                self.assertEqual(
                    analysis["classification"],
                    "SINGLE_BIT_CORRECTABLE",
                    f"Failed classification for err_pos={err_pos} on input={inp}"
                )
                self.assertEqual(
                    analysis["error_pos"],
                    err_pos,
                    f"Wrong error position pinpointed: expected {err_pos}, got {analysis['error_pos']}"
                )

                # Test auto-correction
                fixed = ExtendedHammingCode.correct_single_bit(corrupted, analysis["error_pos"])
                self.assertEqual(fixed, orig_cw, f"Auto-correction failed for bit #{err_pos}")

    def test_single_bit_error_in_p0(self):
        """Test that an error in overall parity bit P0 is classified correctly and payload is unharmed."""
        data_bits = BitManipulator.binary_string_to_bits("1011001")
        enc = ExtendedHammingCode.encode(data_bits)
        orig_cw = enc["raw_codeword"]

        corrupted = list(orig_cw)
        corrupted[0] ^= 1  # Flip P0

        analysis = ExtendedHammingCode.analyze(corrupted)
        self.assertEqual(analysis["classification"], "SINGLE_BIT_P0")
        self.assertEqual(analysis["syndrome_value"], 0)
        self.assertEqual(analysis["p_check"], 1)

        fixed = ExtendedHammingCode.correct_single_bit(corrupted, 0)
        self.assertEqual(fixed, orig_cw)

    def test_all_double_bit_error_detection(self):
        """
        Test that 100% of all possible 2-bit error pairs are detected as DOUBLE_BIT_DETECTED
        by SEC-DED, preventing silent miscorrection!
        """
        data_bits = BitManipulator.binary_string_to_bits("1011")
        enc = ExtendedHammingCode.encode(data_bits)
        orig_cw = enc["raw_codeword"]
        n = len(orig_cw)

        # Test every pair (i, j) with 0 <= i < j < n
        tested_pairs = 0
        for i in range(n):
            for j in range(i + 1, n):
                corrupted = list(orig_cw)
                corrupted[i] ^= 1
                corrupted[j] ^= 1

                analysis = ExtendedHammingCode.analyze(corrupted)
                # Either classified as DOUBLE_BIT_DETECTED or if i=0 (P0) and j=pos,
                # let's observe: if P0 and bit j flip, then 2 bits flipped: p_check is 0!
                # and syndrome S = j != 0. So it is ALWAYS DOUBLE_BIT_DETECTED!
                self.assertEqual(
                    analysis["classification"],
                    "DOUBLE_BIT_DETECTED",
                    f"SEC-DED failed to detect 2-bit error at pair ({i}, {j})"
                )
                self.assertEqual(analysis["p_check"], 0, f"P_check should be even for 2-bit flip at ({i}, {j})")
                tested_pairs += 1

        self.assertGreater(tested_pairs, 10)

    def test_checksum_assisted_double_bit_resolution(self):
        """Test that the Checksum-Assisted resolver recovers original codeword on 2-bit errors."""
        data_bits = BitManipulator.binary_string_to_bits("1011001")
        enc = ExtendedHammingCode.encode(data_bits)
        orig_cw = enc["raw_codeword"]
        orig_bytes = BitManipulator.bits_to_bytes(orig_cw)
        chk, _ = InternetChecksum.calculate(orig_bytes)

        # Test several 2-bit flip pairs
        test_pairs = [(1, 3), (2, 5), (3, 7), (4, 6), (0, 4)]
        for p1, p2 in test_pairs:
            corrupted = list(orig_cw)
            corrupted[p1] ^= 1
            corrupted[p2] ^= 1

            analysis = ExtendedHammingCode.analyze(corrupted)
            self.assertEqual(analysis["classification"], "DOUBLE_BIT_DETECTED")

            resolved = ExtendedHammingCode.resolve_double_bit_error(
                corrupted, analysis["syndrome_value"], chk
            )
            self.assertIsNotNone(resolved, f"Resolver failed to find pair for ({p1}, {p2})")
            r1, r2 = resolved
            self.assertEqual(set([r1, r2]), set([p1, p2]), f"Resolver found wrong pair for ({p1}, {p2})")


class TestInternetChecksum(unittest.TestCase):

    def test_checksum_calculation_and_verification(self):
        """Test RFC 1071 calculation and verification pass."""
        bytes_data = [0x45, 0x00, 0x00, 0x3C, 0x1C, 0x46, 0x40, 0x00, 0x40, 0x06]
        chk, steps = InternetChecksum.calculate(bytes_data)

        self.assertIsInstance(chk, int)
        self.assertTrue(0 <= chk <= 0xFFFF)
        self.assertTrue(InternetChecksum.verify(bytes_data, chk))

    def test_checksum_detects_corruption(self):
        """Test that changing any byte causes verification failure."""
        bytes_data = [0x12, 0x34, 0x56, 0x78]
        chk, _ = InternetChecksum.calculate(bytes_data)

        corrupted = list(bytes_data)
        corrupted[1] ^= 0x01
        self.assertFalse(InternetChecksum.verify(corrupted, chk))

    def test_adler32_and_crc32(self):
        """Test Adler-32 and CRC-32 consistency."""
        test_bytes = [ord(c) for c in "123456789"]
        # Standard CRC32 of ASCII "123456789" is 0xCBF43926
        crc = InternetChecksum.crc32(test_bytes)
        self.assertEqual(f"0x{crc:08X}", "0xCBF43926")

        # Standard Adler-32 of "123456789" is 0x091E01DE
        adler = InternetChecksum.adler32(test_bytes)
        self.assertEqual(f"0x{adler:08X}", "0x091E01DE")


if __name__ == "__main__":
    unittest.main()

