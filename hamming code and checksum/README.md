# ECC & Integrity Studio
### Extended Hamming Code (SEC-DED) & RFC 1071 Internet Checksum

A classic, retro-functional systems utility and educational tool designed to explore **Error Detection and Correction (EDAC)** at the bit and packet layers.

The application implements:
1. **Extended Hamming Code (SEC-DED Architecture)**: 
   - Single Error Correction (SEC) & Double Error Detection (DED).
   - Parity bit injection at powers of 2 ($P_1, P_2, P_4, P_8, \dots$).
   - Overall parity bit ($P_0$) monitoring the complete block.
   - **Checksum-Assisted 2-Bit Error Correction (DEC)**: Adapts SEC-DED for full 2-bit error correction by combining syndrome algebraic pair relations ($i \oplus j = S$) with RFC 1071 transport checksum verification.
2. **Internet Checksum Engine (RFC 1071)**:
   - 16-bit 1's complement addition with end-around carry wrapping.
   - Bitwise inversion (one's complement) and receiver verification (`0xFFFF`).
   - Secondary integrity digests: **Adler-32** and **CRC-32** (IEEE 802.3).

---

## Visual & Aesthetic Philosophy

- **Classic Retro-Functional Design**: Inspired by classic Win32 and Sysinternals utilities (Process Explorer, WinRAR, Resource Hacker).
- **Tactile Bit Manipulation**: Click directly on individual bit cells in the monospace register grid to toggle them ($0 \leftrightarrow 1$).
- **Parity Coverage Inspection**: Hovering over any parity bit highlights every data bit it monitors; hovering over any data bit highlights its monitoring parity bits.
- **Zero AI Bloat**: No generic filler features, dark-mode toggles, or floating cards with blurred drop shadows. Every visual element conveys concrete information (bit states, binary addresses, register hex values, and arithmetic carries).

---

## Architecture & Code Structure

```
├── index.html              # Standalone zero-dependency Web Application (Open directly in Edge/Chrome)
├── ecc_core.py             # Pure Python 3 Core Library (Bit Manipulator, SEC-DED, RFC 1071, CRC32)
├── hamming_checksum_gui.py # Native Python Desktop GUI (Tkinter) with classic Win32 styling
├── test_ecc.py             # Comprehensive Unit Test Suite
└── README.md               # Systems architecture, mathematical proofs, and user guide
```

---

## Mathematical Foundations & Algorithms

### 1. Extended Hamming Code (SEC-DED)

For $m$ data bits, the number of parity bits $r$ is chosen such that:
$$2^r \ge m + r + 1$$

#### Codeword Bit Allocation:
- **Index 0**: Overall Parity Bit $P_0$ (checks all bits $1 \dots n$).
- **Index $2^j$ ($j = 0, 1, 2, \dots$)**: Parity Bits $P_1, P_2, P_4, P_8, \dots$.
- **Remaining indices**: Data Bits $D_3, D_5, D_6, D_7, D_9, \dots$.

#### Parity Equations (Even Parity):
Each parity bit $P_{2^j}$ satisfies:
$$P_{2^j} = \bigoplus_{k: (k \ \& \ 2^j) \neq 0, k \neq 2^j} c_k$$

The overall parity bit $P_0$ satisfies:
$$P_0 = \bigoplus_{k=1}^n c_k$$

#### Syndrome Vector ($S$) & Parity Check ($P_{check}$):
Upon receiving codeword $c'$:
$$s_j = \bigoplus_{k: (k \ \& \ 2^j) \neq 0} c'_k \quad (j = 0 \dots r-1)$$
$$S = \sum_{j=0}^{r-1} s_j 2^j$$
$$P_{check} = \bigoplus_{i=0}^n c'_i$$

#### SEC-DED Decision Truth Table:
| Syndrome $S$ | Overall Parity $P_{check}$ | Error Classification | Hardware Action |
|:---|:---|:---|:---|
| $S = 0$ | $P_{check} = 0$ (Even) | **Pristine Codeword** | Accept payload. |
| $S \neq 0$ | $P_{check} = 1$ (Odd) | **1-Bit Error at position $S$** | Invert bit $c'_S$ (Corrected). |
| $S = 0$ | $P_{check} = 1$ (Odd) | **1-Bit Error in $P_0$** | Invert $P_0$. Payload intact. |
| $S \neq 0$ | $P_{check} = 0$ (Even) | **2-Bit Double Error** | Standalone uncorrectable; trigger DEC Resolver! |

---

### 2. Adapting SEC-DED for 2-Bit Correction (DEC)

In standard linear coding, Extended Hamming code has minimum Hamming distance $d_{min} = 4$.
When two bit errors occur at positions $i$ and $j$ ($1 \le i < j \le n$):
$$S = \text{column}_i \oplus \text{column}_j = i \oplus j$$

Because multiple distinct pairs $(i, j)$ yield the exact same XOR sum $S$, standalone Hamming decoding cannot pinpoint which pair flipped without risking silent corruption.

#### The Checksum Tie-Breaker:
The system combines the physical-layer SEC-DED syndrome with the transport-layer **RFC 1071 Checksum**:
1. When $S \neq 0$ and $P_{check} = 0$ (2-bit error flagged), enumerate candidate pairs $(i, j)$ satisfying $i \oplus j = S$ (and $(0, S)$ for $P_0$).
2. In a 12-bit block, there are at most 6 candidate pairs.
3. For each candidate pair, simulate inverting bits $i$ and $j$ and recalculate the 16-bit Internet Checksum.
4. The candidate pair that restores the transmitted reference checksum is the **exact 2-bit error pair**, resolving the ambiguity and restoring pristine data!

---

### 3. Internet Checksum Arithmetic (RFC 1071)

The Internet Checksum divides the payload into 16-bit big-endian words:
1. **Word Segmentation**: Pad with a zero byte if odd-length.
2. **One's Complement Sum**:
   $$\text{Sum} = \sum_{k=1}^N \text{Word}_k$$
   Any carry out of bit 15 wraps around and adds to the least-significant bit (end-around carry).
3. **One's Complement Inversion**:
   $$\text{Checksum} = \sim \text{Sum} \ \& \ \text{0xFFFF}$$
4. **Receiver Verification**:
   $$\text{Sum}(\text{Words}) + \text{Checksum} == \text{0xFFFF}$$
   If any bit is corrupted, the sum will differ from `0xFFFF`, flagging packet-level corruption.

---

## Quick Start & Usage

### Option 1: Standalone Web Application (Zero Installation)
Double-click `index.html` or open it in any browser (Microsoft Edge, Chrome, Firefox):
```powershell
Start-Process "index.html"
```
- Select data format (`Binary`, `Hexadecimal`, or `ASCII Text`).
- Click **⚡ Encode & Build Grid** to generate codeword and parity bits.
- Click any bit cell in the grid to flip it manually ($0 \leftrightarrow 1$), or click **⚡ Inject 1 Bit Error** / **⚡ Inject 2 Bit Errors**.
- Observe the real-time syndrome recalculation, parity equations, and verification status.
- Click **✔ Auto-Correct (SEC)** for 1-bit errors, or **⚡ Resolve 2-Bit Error** for 2-bit errors.

### Option 2: Python Desktop Application (Tkinter)
Run the desktop GUI from PowerShell or command prompt (requires Python 3.8+):
```powershell
python hamming_checksum_gui.py
```

### Option 3: Command-Line Interface (CLI Demo)
Run the modular core library directly:
```powershell
python ecc_core.py
```

### Option 4: Automated Unit Tests
Verify all 0-bit, 1-bit, and 2-bit error conditions:
```powershell
python -m unittest test_ecc.py
```

---

## Verification & Test Coverage

The test suite in `test_ecc.py` asserts:
- **100% SEC Verification**: Every single bit position $1 \dots n$ is injected with an error and verified to be pinpointed by $S = k$ and automatically corrected.
- **$P_0$ Isolation**: Inverting $P_0$ yields $S=0, P_{check}=1$ without altering payload data.
- **100% DED Guarantee**: Every possible pair of bits $(i, j)$ across the codeword is tested to guarantee that SEC-DED flags $P_{check} = 0$, completely preventing silent single-bit miscorrections.
- **DEC Resolution**: The Checksum-Assisted resolver successfully isolates and repairs 100% of tested 2-bit error pairs.
- **RFC 1071 RFC Compliance**: Validates standard IP packet header vectors and carry wrap-around.

