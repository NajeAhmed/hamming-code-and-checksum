"""
================================================================================
ECC & Integrity Core Library
Extended Hamming (SEC-DED) Code & RFC 1071 16-bit Internet Checksum
================================================================================
Clean, dependency-free implementation of:
1. Bit Manipulator: conversions between text/hex/binary strings and bit arrays.
2. Extended Hamming Code:
   - Parity injection at power-of-2 positions.
   - Overall parity bit P0 for SEC-DED (Single Error Correct / Double Error Detect).
   - Exact syndrome calculation and error classification.
   - Checksum-assisted 2-bit error correction resolver.
3. Transport Checksum & Digests:
   - RFC 1071 16-bit 1's complement Internet Checksum with wrap-around carry.
   - Adler-32 and CRC-32 fallback integrity hashes.
================================================================================
"""

from typing import List, Tuple, Dict, Any, Optional
import sys


# -----------------------------------------------------------------------------
# Bit Manipulator
# -----------------------------------------------------------------------------
class BitManipulator:
    """Standardized conversion between string/text/hex and binary bit arrays."""

    @staticmethod
    def text_to_bits(text: str) -> List[int]:
        """Convert ASCII text to list of bits (MSB first per byte)."""
        bits = []
        for ch in text:
            val = ord(ch) & 0xFF
            for b in range(7, -1, -1):
                bits.append((val >> b) & 1)
        return bits if bits else [0]

    @staticmethod
    def hex_to_bits(hex_str: str) -> List[int]:
        """Convert hexadecimal string (with or without '0x') to list of bits."""
        clean = hex_str.strip().lower().replace("0x", "")
        if not clean:
            return [0]
        bits = []
        for ch in clean:
            val = int(ch, 16)
            for b in range(3, -1, -1):
                bits.append((val >> b) & 1)
        return bits

    @staticmethod
    def binary_string_to_bits(bin_str: str) -> List[int]:
        """Convert string of '0's and '1's into bit array."""
        clean = [c for c in bin_str if c in ('0', '1')]
        if not clean:
            return [0]
        return [int(c) for c in clean]

    @staticmethod
    def bits_to_bytes(bits: List[int]) -> List[int]:
        """Group bits into 8-bit bytes (padded with zeros if not multiple of 8)."""
        pad_len = (8 - (len(bits) % 8)) % 8
        padded = list(bits) + [0] * pad_len
        bytes_out = []
        for i in range(0, len(padded), 8):
            byte = 0
            for b in range(8):
                byte = (byte << 1) | padded[i + b]
            bytes_out.append(byte)
        return bytes_out

    @staticmethod
    def bits_to_hex(bits: List[int]) -> str:
        """Convert bit array to hexadecimal representation."""
        pad_len = (4 - (len(bits) % 4)) % 4
        padded = [0] * pad_len + list(bits)
        hex_chars = []
        for i in range(0, len(padded), 4):
            val = (padded[i] << 3) | (padded[i+1] << 2) | (padded[i+2] << 1) | padded[i+3]
            hex_chars.append(f"{val:X}")
        return "0x" + "".join(hex_chars)


# -----------------------------------------------------------------------------
# Extended Hamming Code (SEC-DED) Architecture
# -----------------------------------------------------------------------------
class ExtendedHammingCode:
    """
    Implements Extended Hamming Code with Single Error Correction and
    Double Error Detection (SEC-DED).
    
    Layout of Codeword:
      Index 0: P0 (Overall Parity bit across all bits 1..n)
      Index 1, 2, 4, 8, ...: Parity bits P1, P2, P4, P8...
      Index 3, 5, 6, 7, 9...: Data bits D3, D5, D6, D7, D9...
    """

    @staticmethod
    def calc_parity_bits(m: int) -> int:
        """
        Calculates minimum parity bits r required for m data bits:
        2^r >= m + r + 1
        """
        r = 1
        while (1 << r) < (m + r + 1):
            r += 1
        return r

    @classmethod
    def encode(cls, data_bits: List[int]) -> Dict[str, Any]:
        """
        Encodes a list of data bits into an Extended Hamming Codeword.
        Returns codeword dictionary containing cell information and metadata.
        """
        m = len(data_bits)
        r = cls.calc_parity_bits(m)
        total_len = m + r  # indices 1..total_len

        # Step 1: Assign positions
        codeword_cells = []
        data_idx = 0

        # Slot 0 is P0 (placeholder)
        codeword_cells.append({
            "pos": 0,
            "role": "P0",
            "is_parity": True,
            "bit": 0,
            "covers": []
        })

        for i in range(1, total_len + 1):
            if (i & (i - 1)) == 0:
                # Power of 2: Parity bit Pi
                codeword_cells.append({
                    "pos": i,
                    "role": f"P{i}",
                    "is_parity": True,
                    "bit": 0,
                    "covers": []
                })
            else:
                # Data bit
                bit_val = data_bits[data_idx] if data_idx < m else 0
                codeword_cells.append({
                    "pos": i,
                    "role": f"D{i}",
                    "is_parity": False,
                    "bit": bit_val,
                    "data_idx": data_idx,
                    "covers": []
                })
                data_idx += 1

        # Step 2: Compute parity bits P_j at power-of-2 positions
        # Parity bit at position 2^k checks positions where bit k of index is 1.
        for j in range(r):
            p_pos = 1 << j
            parity_xor = 0
            covers = []
            for p in range(1, total_len + 1):
                if (p & p_pos) != 0:
                    covers.append(p)
                    if p != p_pos:
                        parity_xor ^= codeword_cells[p]["bit"]

            codeword_cells[p_pos]["bit"] = parity_xor
            codeword_cells[p_pos]["covers"] = covers

        # Step 3: Compute Overall Parity Bit P0 (Even parity over all bits 1..total_len)
        p0_xor = 0
        all_positions = list(range(1, total_len + 1))
        for p in all_positions:
            p0_xor ^= codeword_cells[p]["bit"]

        codeword_cells[0]["bit"] = p0_xor
        codeword_cells[0]["covers"] = all_positions

        return {
            "m": m,
            "r": r,
            "total_bits": total_len + 1,
            "codeword_cells": codeword_cells,
            "raw_codeword": [c["bit"] for c in codeword_cells]
        }

    @classmethod
    def analyze(cls, codeword: List[int]) -> Dict[str, Any]:
        """
        Analyzes a received codeword (including bit 0 as P0).
        Calculates syndrome vector S and overall parity check P_check.
        Classifies error:
          - VALID
          - SINGLE_BIT_CORRECTABLE (data or regular parity)
          - SINGLE_BIT_P0 (in overall parity)
          - DOUBLE_BIT_DETECTED (2-bit error, uncorrectable by SEC-DED alone)
          - MULTI_BIT_DETECTED
        """
        n = len(codeword) - 1
        r = 0
        while (1 << r) <= n:
            r += 1

        syndrome_value = 0
        syndrome_bits = []
        equations = []

        # Check each parity bit P_j (j = 0..r-1, position = 2^j)
        for j in range(r):
            p_pos = 1 << j
            xor_sum = 0
            checked_positions = []

            for p in range(1, n + 1):
                if (p & p_pos) != 0:
                    checked_positions.append(p)
                    xor_sum ^= codeword[p]

            syndrome_bits.append(xor_sum)
            if xor_sum == 1:
                syndrome_value |= p_pos

            equations.append({
                "parity_pos": p_pos,
                "bit_idx": j,
                "syndrome_bit": xor_sum,
                "checked_positions": checked_positions,
                "passed": (xor_sum == 0)
            })

        # Overall Parity Check: XOR over ALL bits 0..n
        p_check = 0
        for bit in codeword:
            p_check ^= bit

        # Error Classification
        if syndrome_value == 0 and p_check == 0:
            classification = "VALID"
            error_pos = None
            desc = "Codeword valid; no error detected."
        elif syndrome_value != 0 and p_check == 1:
            classification = "SINGLE_BIT_CORRECTABLE"
            error_pos = syndrome_value
            desc = f"Single bit error at position #{syndrome_value}. Fully correctable."
        elif syndrome_value == 0 and p_check == 1:
            classification = "SINGLE_BIT_P0"
            error_pos = 0
            desc = "Single bit error in overall parity bit P0. Payload data is pristine."
        elif syndrome_value != 0 and p_check == 0:
            classification = "DOUBLE_BIT_DETECTED"
            error_pos = None
            desc = f"Double bit error detected! Syndrome S={syndrome_value}, even parity. Uncorrectable by standalone SEC-DED."
        else:
            classification = "MULTI_BIT_DETECTED"
            error_pos = None
            desc = "Multi-bit error detected."

        return {
            "r": r,
            "syndrome_value": syndrome_value,
            "syndrome_bits": syndrome_bits,
            "p_check": p_check,
            "classification": classification,
            "error_pos": error_pos,
            "description": desc,
            "equations": equations
        }

    @staticmethod
    def correct_single_bit(codeword: List[int], error_pos: int) -> List[int]:
        """Invert bit at error_pos to restore pristine codeword."""
        corrected = list(codeword)
        if 0 <= error_pos < len(corrected):
            corrected[error_pos] ^= 1
        return corrected

    @classmethod
    def resolve_double_bit_error(
        cls,
        codeword: List[int],
        syndrome_value: int,
        target_checksum: int
    ) -> Optional[Tuple[int, int]]:
        """
        Adapts SEC-DED for 2-bit error correction by combining syndrome algebraic
        relations (i ^ j = S) with transport Checksum verification.
        Returns (pos1, pos2) of the true flipped bits if resolved, else None.
        """
        n = len(codeword) - 1
        S = syndrome_value
        candidate_pairs = []

        # Candidate A: error in P0 (0) and bit S
        if 0 < S <= n:
            candidate_pairs.append((0, S))

        # Candidate B: error in pair (i, j) where i ^ j == S
        for i in range(1, n + 1):
            j = i ^ S
            if i < j <= n:
                candidate_pairs.append((i, j))

        # Test each candidate pair against target transport checksum
        for p1, p2 in candidate_pairs:
            test_cw = list(codeword)
            test_cw[p1] ^= 1
            test_cw[p2] ^= 1

            test_bytes = BitManipulator.bits_to_bytes(test_cw)
            calc_chk, _ = InternetChecksum.calculate(test_bytes)
            if calc_chk == target_checksum:
                return (p1, p2)

        return None


# -----------------------------------------------------------------------------
# Internet Checksum (RFC 1071) & Digest Calculation
# -----------------------------------------------------------------------------
class InternetChecksum:
    """
    Implements RFC 1071 16-bit 1's complement Internet Checksum
    (as used in IPv4, TCP, and UDP).
    """

    @staticmethod
    def calculate(byte_data: List[int]) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Computes 16-bit Internet Checksum over an array of bytes.
        Returns:
          - checksum: 16-bit unsigned integer
          - steps: list of step dictionaries for diagnostics
        """
        steps = []
        padded = list(byte_data)
        odd_padded = False
        if len(padded) % 2 != 0:
            padded.append(0)
            odd_padded = True

        words = []
        for i in range(0, len(padded), 2):
            w = (padded[i] << 8) | padded[i + 1]
            words.append(w)

        steps.append({
            "action": "segmentation",
            "bytes_count": len(byte_data),
            "odd_padded": odd_padded,
            "words": words
        })

        accum = 0
        for idx, word in enumerate(words):
            prev = accum
            accum += word
            carry = 0
            if accum > 0xFFFF:
                carry = accum >> 16
                accum = (accum & 0xFFFF) + carry

            steps.append({
                "action": "add_word",
                "index": idx,
                "word": word,
                "prev_accum": prev,
                "new_accum": accum,
                "carry_wrapped": carry
            })

        while accum >> 16:
            accum = (accum & 0xFFFF) + (accum >> 16)

        checksum = (~accum) & 0xFFFF
        steps.append({
            "action": "ones_complement_inversion",
            "final_accum": accum,
            "checksum": checksum
        })

        return checksum, steps

    @classmethod
    def verify(cls, byte_data: List[int], checksum: int) -> bool:
        """
        Verifies packet integrity:
        Summing data words + checksum in 1's complement must yield 0xFFFF.
        """
        padded = list(byte_data)
        if len(padded) % 2 != 0:
            padded.append(0)

        accum = 0
        for i in range(0, len(padded), 2):
            w = (padded[i] << 8) | padded[i + 1]
            accum += w
            if accum > 0xFFFF:
                accum = (accum & 0xFFFF) + (accum >> 16)

        accum += checksum
        while accum >> 16:
            accum = (accum & 0xFFFF) + (accum >> 16)

        return accum == 0xFFFF

    @staticmethod
    def adler32(byte_data: List[int]) -> int:
        """Adler-32 checksum."""
        MOD = 65521
        a, b = 1, 0
        for byte in byte_data:
            a = (a + byte) % MOD
            b = (b + a) % MOD
        return ((b << 16) | a) & 0xFFFFFFFF

    @staticmethod
    def crc32(byte_data: List[int]) -> int:
        """Standard CRC-32 (IEEE 802.3 polynomial 0xEDB88320)."""
        crc = 0xFFFFFFFF
        for byte in byte_data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc >>= 1
        return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


# -----------------------------------------------------------------------------
# Standalone CLI Demo
# -----------------------------------------------------------------------------
def run_cli_demo():
    print("=" * 78)
    print("ECC & INTEGRITY STUDIO — Extended Hamming (SEC-DED) & RFC 1071 Checksum")
    print("=" * 78)

    sample_input = "1011001"
    print(f"[*] Input Data Bits: {sample_input}")

    data_bits = BitManipulator.binary_string_to_bits(sample_input)
    enc = ExtendedHammingCode.encode(data_bits)
    cw = enc["raw_codeword"]

    print(f"[*] Encoded Codeword ({enc['total_bits']} bits):")
    for cell in enc["codeword_cells"]:
        print(f"    Index #{cell['pos']:2d} [{cell['role']:3s}] = {cell['bit']}")

    # Checksum calculation
    raw_bytes = BitManipulator.bits_to_bytes(cw)
    chk, steps = InternetChecksum.calculate(raw_bytes)
    print(f"\n[*] RFC 1071 Checksum: 0x{chk:04X} (Binary: {chk:016b})")
    print(f"[*] Adler-32: 0x{InternetChecksum.adler32(raw_bytes):08X}")
    print(f"[*] CRC-32:   0x{InternetChecksum.crc32(raw_bytes):08X}")

    # Case 1: Pristine Codeword
    print("\n--- CASE 1: Pristine Transmission (0 Errors) ---")
    res0 = ExtendedHammingCode.analyze(cw)
    print(f"Status: {res0['classification']} — {res0['description']}")
    print(f"Syndrome S = {res0['syndrome_value']}, P_check = {res0['p_check']}")

    # Case 2: 1-Bit Error
    print("\n--- CASE 2: Single-Bit Error Injection (Bit #3 flipped) ---")
    cw_1bit = list(cw)
    cw_1bit[3] ^= 1
    res1 = ExtendedHammingCode.analyze(cw_1bit)
    print(f"Status: {res1['classification']} — {res1['description']}")
    print(f"Syndrome S = {res1['syndrome_value']} => Pinpoints bit #{res1['error_pos']}")
    corrected_cw = ExtendedHammingCode.correct_single_bit(cw_1bit, res1['error_pos'])
    print(f"Auto-Corrected Codeword matches original: {corrected_cw == cw}")

    # Case 3: 2-Bit Error
    print("\n--- CASE 3: Double-Bit Error Injection (Bits #3 and #5 flipped) ---")
    cw_2bit = list(cw)
    cw_2bit[3] ^= 1
    cw_2bit[5] ^= 1
    res2 = ExtendedHammingCode.analyze(cw_2bit)
    print(f"Status: {res2['classification']} — {res2['description']}")
    print(f"Syndrome S = {res2['syndrome_value']}, P_check = {res2['p_check']} (Even!)")
    print("[*] SEC-DED DED Active: Standalone auto-correction blocked to prevent corruption.")

    # Checksum-assisted 2-bit correction
    print("\n[*] Invoking Checksum-Assisted 2-Bit DEC Resolver:")
    resolved_pair = ExtendedHammingCode.resolve_double_bit_error(
        cw_2bit, res2['syndrome_value'], chk
    )
    if resolved_pair:
        p1, p2 = resolved_pair
        print(f"    ✔ Successfully resolved candidate pair: Bits #{p1} and #{p2}!")
        cw_recovered = list(cw_2bit)
        cw_recovered[p1] ^= 1
        cw_recovered[p2] ^= 1
        print(f"    ✔ Recovered Codeword matches original: {cw_recovered == cw}")
    else:
        print("    ✗ Could not resolve pair.")

    print("\n" + "=" * 78)


if __name__ == "__main__":
    run_cli_demo()

