"""
================================================================================
ECC & Integrity Studio — Desktop GUI Application (Python / Tkinter)
================================================================================
Classic, retro-functional desktop application implementing:
1. Extended Hamming Code with SEC-DED (Single Error Correction, Double Error Detection)
2. Checksum-Assisted 2-Bit Error Correction Resolver (Syndrome + RFC 1071 tie-breaker)
3. 16-bit RFC 1071 Internet Checksum step-by-step arithmetic
4. Interactive visual bit grid with click-to-flip and parity coverage highlighting.

Aesthetics:
- Classic Win32 / Sysinternals utility look with beveled borders and monospace registers.
- High-contrast, legible bit displays.
- Zero external dependencies beyond standard Python library.
================================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
from typing import List, Dict, Any, Optional

from ecc_core import BitManipulator, ExtendedHammingCode, InternetChecksum


class ECCStudioGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ECC & Integrity Studio — Extended Hamming SEC-DED & RFC 1071 Checksum")
        self.geometry("1060;720".replace(";", "x"))
        self.minsize(920, 640)

        # Application State
        self.data_bits: List[int] = []
        self.encoded_data: Optional[Dict[str, Any]] = None
        self.codeword_cells: List[Dict[str, Any]] = []
        self.reference_checksum: int = 0
        self.bit_buttons: List[tk.Button] = []
        self.bit_labels: List[tk.Label] = []

        # Color Theme (Classic Retro Utility Palette)
        self.COLOR_BG = "#ece9d8"
        self.COLOR_FACE = "#f0f0f0"
        self.COLOR_WINDOW = "#ffffff"
        self.COLOR_PARITY = "#e8f0fe"
        self.COLOR_OVERALL = "#f3e8fd"
        self.COLOR_DATA = "#ffffff"
        self.COLOR_FLIPPED = "#ffebee"
        self.COLOR_HIGHLIGHT = "#fff8e1"

        self.configure(bg=self.COLOR_BG)
        self._setup_styles()
        self._build_ui()
        self._load_preset("nybble")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLOR_BG)
        style.configure("TLabelframe", background=self.COLOR_BG)
        style.configure("TLabelframe.Label", background=self.COLOR_BG, font=("Segoe UI", 9, "bold"))
        style.configure("TLabel", background=self.COLOR_BG, font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("TNotebook", background=self.COLOR_BG)
        style.configure("TNotebook.Tab", font=("Segoe UI", 9, "bold"), padding=[8, 4])

    def _build_ui(self):
        # Top Menu Bar
        menu_bar = tk.Menu(self)
        
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Reset to Default", command=lambda: self._load_preset("nybble"))
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        preset_menu = tk.Menu(menu_bar, tearoff=0)
        preset_menu.add_command(label="4-bit Nybble [1011] (Hamming 8,4 SEC-DED)", command=lambda: self._load_preset("nybble"))
        preset_menu.add_command(label="8-bit ASCII 'A' [01000001] (Hamming 13,8)", command=lambda: self._load_preset("byte_a"))
        preset_menu.add_command(label="11-bit Word [10110010110] (Hamming 16,11)", command=lambda: self._load_preset("word_11"))
        preset_menu.add_command(label="16-bit Hex 0xCAFE (Hamming 22,16)", command=lambda: self._load_preset("hex_cafe"))
        menu_bar.add_cascade(label="Presets", menu=preset_menu)

        inject_menu = tk.Menu(menu_bar, tearoff=0)
        inject_menu.add_command(label="Inject 1 Random Error", command=lambda: self._inject_errors(1))
        inject_menu.add_command(label="Inject 2 Random Errors", command=lambda: self._inject_errors(2))
        inject_menu.add_command(label="Revert Errors", command=self._clear_errors)
        inject_menu.add_command(label="Auto-Correct (SEC)", command=self._apply_auto_correction)
        inject_menu.add_command(label="Resolve 2-Bit Error (DEC + Checksum)", command=self._resolve_double_bit_error)
        menu_bar.add_cascade(label="Error Injection", menu=inject_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About ECC Studio", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menu_bar)

        # MAIN CONTENT
        main_frame = tk.Frame(self, bg=self.COLOR_BG, padx=6, pady=4)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. TOP PANEL: Input & Simulator Controls
        top_frame = tk.LabelFrame(main_frame, text=" Data Encoding & Hardware Simulator Controls ", bg=self.COLOR_BG, font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        top_frame.pack(fill=tk.X, pady=(0, 4))

        row1 = tk.Frame(top_frame, bg=self.COLOR_BG)
        row1.pack(fill=tk.X, pady=2)

        tk.Label(row1, text="Format:", bg=self.COLOR_BG, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.format_var = tk.StringVar(value="Binary")
        format_combo = ttk.Combobox(row1, textvariable=self.format_var, values=["Binary", "Hexadecimal", "ASCII Text"], state="readonly", width=12)
        format_combo.pack(side=tk.LEFT, padx=(0, 10))
        format_combo.bind("<<ComboboxSelected>>", self._on_format_changed)

        tk.Label(row1, text="Payload:", bg=self.COLOR_BG, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.input_entry = tk.Entry(row1, font=("Consolas", 11), bg="#ffffff", relief=tk.SUNKEN, bd=2)
        self.input_entry.insert(0, "1011001")
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.input_entry.bind("<Return>", lambda e: self._encode_data())

        btn_encode = tk.Button(row1, text="⚡ Encode & Build Grid", font=("Segoe UI", 9, "bold"), relief=tk.RAISED, bd=2, bg="#d4e4f7", fg="#002266", padx=8, command=self._encode_data)
        btn_encode.pack(side=tk.LEFT, padx=3)

        btn_clear = tk.Button(row1, text="↺ Clear Errors", font=("Segoe UI", 9), relief=tk.RAISED, bd=2, bg=self.COLOR_FACE, padx=6, command=self._clear_errors)
        btn_clear.pack(side=tk.LEFT, padx=3)

        # Simulator Row
        row2 = tk.Frame(top_frame, bg=self.COLOR_BG)
        row2.pack(fill=tk.X, pady=(6, 2))

        tk.Label(row2, text="Hardware Injector:", bg=self.COLOR_BG, font=("Segoe UI", 9, "bold"), fg="#444").pack(side=tk.LEFT, padx=(0, 6))

        btn_inj1 = tk.Button(row2, text="⚡ Inject 1 Bit Error", font=("Segoe UI", 9), relief=tk.RAISED, bd=2, bg=self.COLOR_FACE, padx=6, command=lambda: self._inject_errors(1))
        btn_inj1.pack(side=tk.LEFT, padx=3)

        btn_inj2 = tk.Button(row2, text="⚡ Inject 2 Bit Errors", font=("Segoe UI", 9, "bold"), relief=tk.RAISED, bd=2, bg="#fce8e6", fg="#961714", padx=6, command=lambda: self._inject_errors(2))
        btn_inj2.pack(side=tk.LEFT, padx=3)

        self.btn_autocorrect = tk.Button(row2, text="✔ Auto-Correct (SEC)", font=("Segoe UI", 9, "bold"), relief=tk.RAISED, bd=2, bg="#e6f4ea", fg="#0d5a23", padx=8, command=self._apply_auto_correction)
        self.btn_autocorrect.pack(side=tk.LEFT, padx=3)

        self.btn_resolve_2bit = tk.Button(row2, text="⚡ Resolve 2-Bit Error (DEC + Checksum)", font=("Segoe UI", 9, "bold"), relief=tk.RAISED, bd=2, bg="#fff8e1", fg="#b06000", padx=8, command=self._resolve_double_bit_error)
        self.btn_resolve_2bit.pack(side=tk.LEFT, padx=3)

        self.lbl_stats = tk.Label(row2, text="Bits: 7 Data | 4 Parity + P0", bg=self.COLOR_BG, font=("Segoe UI", 9), fg="#555")
        self.lbl_stats.pack(side=tk.RIGHT, padx=4)

        # 2. MIDDLE AREA: Bit Grid + Checksum Block
        mid_paned = tk.PanedWindow(main_frame, orient=tk.HORIZONTAL, bg=self.COLOR_BG, sashwidth=4, sashrelief=tk.RAISED)
        mid_paned.pack(fill=tk.BOTH, expand=False, pady=4)

        # Left: Interactive Bit Grid Frame
        grid_frame = tk.LabelFrame(mid_paned, text=" Codeword Bit Register (Click any bit to toggle 0 ↔ 1) ", bg=self.COLOR_BG, font=("Segoe UI", 9, "bold"), padx=6, pady=6)
        mid_paned.add(grid_frame, minsize=580)

        # Canvas for scrollable bit cells
        self.grid_canvas = tk.Canvas(grid_frame, bg="#fafafa", relief=tk.SUNKEN, bd=2, height=135)
        self.grid_scroll = tk.Scrollbar(grid_frame, orient=tk.HORIZONTAL, command=self.grid_canvas.xview)
        self.grid_canvas.configure(xscrollcommand=self.grid_scroll.set)

        self.cells_container = tk.Frame(self.grid_canvas, bg="#fafafa")
        self.grid_canvas.create_window((0, 0), window=self.cells_container, anchor="nw")
        self.cells_container.bind("<Configure>", lambda e: self.grid_canvas.configure(scrollregion=self.grid_canvas.bbox("all")))

        self.grid_canvas.pack(fill=tk.BOTH, expand=True)
        self.grid_scroll.pack(fill=tk.X)

        # Right: Checksum & Integrity Block
        chk_frame = tk.LabelFrame(mid_paned, text=" RFC 1071 Checksum & Digests ", bg=self.COLOR_BG, font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        mid_paned.add(chk_frame, minsize=280)

        # Checksum Displays
        tk.Label(chk_frame, text="16-bit Internet Checksum:", bg=self.COLOR_BG, font=("Segoe UI", 8, "bold"), fg="#555").pack(anchor="w")
        self.lbl_chk_hex = tk.Label(chk_frame, text="0x0000", font=("Consolas", 14, "bold"), bg="#ffffff", relief=tk.SUNKEN, bd=2, padx=6, pady=2)
        self.lbl_chk_hex.pack(fill=tk.X, pady=(2, 4))

        self.lbl_chk_bin = tk.Label(chk_frame, text="0000 0000 0000 0000", font=("Consolas", 9), bg=self.COLOR_BG, fg="#333")
        self.lbl_chk_bin.pack(anchor="w", pady=(0, 6))

        tk.Label(chk_frame, text="Receiver Verification Status:", bg=self.COLOR_BG, font=("Segoe UI", 8, "bold"), fg="#555").pack(anchor="w")
        self.lbl_verif_status = tk.Label(chk_frame, text="PASS (0xFFFF)", font=("Segoe UI", 10, "bold"), bg="#e6f4ea", fg="#0d5a23", relief=tk.SUNKEN, bd=1, pady=2)
        self.lbl_verif_status.pack(fill=tk.X, pady=(2, 6))

        tk.Label(chk_frame, text="Fallback Hashes:", bg=self.COLOR_BG, font=("Segoe UI", 8, "bold"), fg="#555").pack(anchor="w")
        self.lbl_hashes = tk.Label(chk_frame, text="Adler-32: 0x00000000\nCRC-32:   0x00000000", font=("Consolas", 9), bg="#ffffff", relief=tk.SUNKEN, bd=1, justify=tk.LEFT, padx=4, pady=3)
        self.lbl_hashes.pack(fill=tk.X, pady=2)

        # 3. BOTTOM PANEL: Analysis Log & Notebook
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # Tab 1: Syndrome & SEC-DED Analysis
        tab_syndrome = tk.Frame(notebook, bg="#ffffff", padx=8, pady=8)
        notebook.add(tab_syndrome, text=" Syndrome & SEC-DED Diagnostic Analysis ")

        self.lbl_status_banner = tk.Label(
            tab_syndrome,
            text="STATUS: CODEWORD VALID (NO ERRORS DETECTED)\nSyndrome S = 0 | Overall Parity P_check = 0 (Even)",
            font=("Segoe UI", 10, "bold"),
            bg="#e6f4ea",
            fg="#0d5a23",
            relief=tk.SOLID,
            bd=1,
            padx=10,
            pady=6,
            justify=tk.LEFT
        )
        self.lbl_status_banner.pack(fill=tk.X, pady=(0, 6))

        self.txt_syndrome_math = tk.Text(tab_syndrome, font=("Consolas", 10), bg="#fafafa", relief=tk.SUNKEN, bd=2, height=10)
        self.txt_syndrome_math.pack(fill=tk.BOTH, expand=True)

        # Tab 2: RFC 1071 Checksum Math
        tab_chk_math = tk.Frame(notebook, bg="#ffffff", padx=8, pady=8)
        notebook.add(tab_chk_math, text=" RFC 1071 16-bit 1's Complement Arithmetic ")

        self.txt_chk_steps = tk.Text(tab_chk_math, font=("Consolas", 10), bg="#fafafa", relief=tk.SUNKEN, bd=2)
        self.txt_chk_steps.pack(fill=tk.BOTH, expand=True)

        # Tab 3: Matrix Foundations (H & G)
        tab_matrix = tk.Frame(notebook, bg="#ffffff", padx=8, pady=8)
        notebook.add(tab_matrix, text=" Parity Check Matrix (H) & Linear Algebra ")

        self.txt_matrix = tk.Text(tab_matrix, font=("Consolas", 10), bg="#fafafa", relief=tk.SUNKEN, bd=2)
        self.txt_matrix.pack(fill=tk.BOTH, expand=True)

        # 4. STATUS BAR
        status_bar = tk.Frame(self, bg=self.COLOR_BG, relief=tk.SUNKEN, bd=1)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.sb_ready = tk.Label(status_bar, text="Ready", bg=self.COLOR_BG, relief=tk.SUNKEN, bd=1, width=12, anchor="w", padx=4)
        self.sb_ready.pack(side=tk.LEFT, padx=1, pady=1)

        self.sb_errors = tk.Label(status_bar, text="Errors: 0", bg=self.COLOR_BG, relief=tk.SUNKEN, bd=1, width=12, anchor="w", padx=4)
        self.sb_errors.pack(side=tk.LEFT, padx=1, pady=1)

        self.sb_diag = tk.Label(status_bar, text="Diagnosis: Codeword Pristine", bg=self.COLOR_BG, relief=tk.SUNKEN, bd=1, anchor="w", padx=4)
        self.sb_diag.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1, pady=1)

        self.sb_chk = tk.Label(status_bar, text="Checksum: 0x0000", bg=self.COLOR_BG, relief=tk.SUNKEN, bd=1, width=18, anchor="e", padx=4)
        self.sb_chk.pack(side=tk.RIGHT, padx=1, pady=1)

    # -------------------------------------------------------------------------
    # UI Actions & Preset Loaders
    # -------------------------------------------------------------------------
    def _on_format_changed(self, event=None):
        fmt = self.format_var.get()
        self.input_entry.delete(0, tk.END)
        if fmt == "Binary":
            self.input_entry.insert(0, "1011001")
        elif fmt == "Hexadecimal":
            self.input_entry.insert(0, "4B")
        elif fmt == "ASCII Text":
            self.input_entry.insert(0, "OK")
        self._encode_data()

    def _load_preset(self, preset: str):
        if preset == "nybble":
            self.format_var.set("Binary")
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, "1011")
        elif preset == "byte_a":
            self.format_var.set("Binary")
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, "01000001")
        elif preset == "word_11":
            self.format_var.set("Binary")
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, "10110010110")
        elif preset == "hex_cafe":
            self.format_var.set("Hexadecimal")
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, "CAFE")
        self._encode_data()

    def _encode_data(self):
        fmt = self.format_var.get()
        raw_val = self.input_entry.get().strip()

        if fmt == "Binary":
            self.data_bits = BitManipulator.binary_string_to_bits(raw_val)
        elif fmt == "Hexadecimal":
            self.data_bits = BitManipulator.hex_to_bits(raw_val)
        else:
            self.data_bits = BitManipulator.text_to_bits(raw_val)

        # Cap for high density interactive UI
        if len(self.data_bits) > 24:
            self.data_bits = self.data_bits[:24]

        self.encoded_data = ExtendedHammingCode.encode(self.data_bits)
        self.codeword_cells = [dict(c) for c in self.encoded_data["codeword_cells"]]

        # Clean reference checksum
        clean_cw = [c["bit"] for c in self.codeword_cells]
        clean_bytes = BitManipulator.bits_to_bytes(clean_cw)
        self.reference_checksum, _ = InternetChecksum.calculate(clean_bytes)

        self._refresh_all()

    def _toggle_bit(self, pos: int):
        if 0 <= pos < len(self.codeword_cells):
            prev = self.codeword_cells[pos]["bit"]
            self.codeword_cells[pos]["bit"] = 1 if prev == 0 else 0
            self._refresh_all()

    def _inject_errors(self, count: int):
        n = len(self.codeword_cells)
        if n == 0:
            return
        if count == 1:
            idx = random.randint(0, n - 1)
            self._toggle_bit(idx)
        elif count == 2:
            if n < 2:
                return
            idx1 = random.randint(0, n - 1)
            idx2 = random.randint(0, n - 1)
            while idx2 == idx1:
                idx2 = random.randint(0, n - 1)
            self.codeword_cells[idx1]["bit"] ^= 1
            self.codeword_cells[idx2]["bit"] ^= 1
            self._refresh_all()

    def _clear_errors(self):
        if not self.encoded_data:
            return
        orig_cells = self.encoded_data["codeword_cells"]
        for i in range(len(self.codeword_cells)):
            self.codeword_cells[i]["bit"] = orig_cells[i]["bit"]
        self._refresh_all()

    def _apply_auto_correction(self):
        curr_cw = [c["bit"] for c in self.codeword_cells]
        analysis = ExtendedHammingCode.analyze(curr_cw)

        if analysis["classification"] in ("SINGLE_BIT_CORRECTABLE", "SINGLE_BIT_P0"):
            err_pos = analysis["error_pos"]
            self._toggle_bit(err_pos)
            messagebox.showinfo("Auto-Correction", f"Successfully corrected 1-bit error at position #{err_pos} ({self.codeword_cells[err_pos]['role']})!")
        elif analysis["classification"] == "DOUBLE_BIT_DETECTED":
            messagebox.showwarning(
                "SEC-DED Protection",
                "Cannot perform standard SEC auto-correction: SEC-DED detected a DOUBLE-BIT error!\n\n"
                "Standard Hamming would falsely miscorrect a 3rd bit. Use the 'Resolve 2-Bit Error' button to break the tie with the Checksum."
            )
        else:
            messagebox.showinfo("Status", "Codeword is already pristine.")

    def _resolve_double_bit_error(self):
        curr_cw = [c["bit"] for c in self.codeword_cells]
        analysis = ExtendedHammingCode.analyze(curr_cw)

        if analysis["classification"] != "DOUBLE_BIT_DETECTED":
            messagebox.showinfo("Resolution", "No active 2-bit error to resolve.")
            return

        resolved = ExtendedHammingCode.resolve_double_bit_error(
            curr_cw, analysis["syndrome_value"], self.reference_checksum
        )

        if resolved:
            p1, p2 = resolved
            self.codeword_cells[p1]["bit"] ^= 1
            self.codeword_cells[p2]["bit"] ^= 1
            self._refresh_all()
            messagebox.showinfo(
                "2-Bit Error Corrected",
                f"✔ Successfully isolated and corrected 2-bit error at positions #{p1} ({self.codeword_cells[p1]['role']}) and #{p2} ({self.codeword_cells[p2]['role']})!\n\n"
                f"Candidate pair satisfied S={analysis['syndrome_value']} and restored reference Checksum 0x{self.reference_checksum:04X}."
            )
        else:
            messagebox.showerror("Resolution Error", "Could not uniquely resolve candidate pair with reference checksum.")

    # -------------------------------------------------------------------------
    # Renderers
    # -------------------------------------------------------------------------
    def _refresh_all(self):
        curr_cw = [c["bit"] for c in self.codeword_cells]
        orig_cw = [c["bit"] for c in self.encoded_data["codeword_cells"]]
        analysis = ExtendedHammingCode.analyze(curr_cw)

        self._render_bit_grid(orig_cw, analysis)
        self._render_checksum(curr_cw)
        self._render_syndrome_analysis(analysis)
        self._render_matrix(analysis)
        self._render_status_bar(orig_cw, curr_cw, analysis)

    def _render_bit_grid(self, orig_cw: List[int], analysis: Dict[str, Any]):
        # Clear container
        for widget in self.cells_container.winfo_children():
            widget.destroy()

        self.bit_buttons = []
        r = analysis["r"]

        for i, cell in enumerate(self.codeword_cells):
            is_flipped = (cell["bit"] != orig_cw[i])
            is_p0 = (i == 0)
            is_parity = cell["is_parity"]

            # Color styling
            if is_flipped:
                bg_col = self.COLOR_FLIPPED
                border_col = "#d93025"
            elif is_p0:
                bg_col = self.COLOR_OVERALL
                border_col = "#8430ce"
            elif is_parity:
                bg_col = self.COLOR_PARITY
                border_col = "#1a73e8"
            else:
                bg_col = self.COLOR_DATA
                border_col = "#999999"

            cell_box = tk.Frame(self.cells_container, bg=bg_col, relief=tk.SOLID, bd=1, padx=2, pady=2)
            cell_box.pack(side=tk.LEFT, padx=3, pady=4)

            # Role Label
            lbl_role = tk.Label(cell_box, text=cell["role"], font=("Consolas", 9, "bold"), bg=bg_col, fg=border_col)
            lbl_role.pack(fill=tk.X)

            # Bit Value Button
            val_btn = tk.Button(
                cell_box,
                text=str(cell["bit"]),
                font=("Consolas", 20, "bold"),
                bg=bg_col,
                relief=tk.RAISED,
                bd=2,
                width=2,
                command=lambda pos=i: self._toggle_bit(pos)
            )
            val_btn.pack(pady=2)
            self.bit_buttons.append(val_btn)

            # Hover events for parity coverage
            if is_parity:
                val_btn.bind("<Enter>", lambda e, pos=i: self._highlight_coverage(pos))
                val_btn.bind("<Leave>", lambda e: self._clear_highlight())

            # Status / Sub-label
            sub_txt = f"[FLIP {orig_cw[i]}]" if is_flipped else ("P0" if is_p0 else ("Parity" if is_parity else "Data"))
            fg_sub = "#c5221f" if is_flipped else "#666"
            lbl_sub = tk.Label(cell_box, text=sub_txt, font=("Segoe UI", 8), bg=bg_col, fg=fg_sub)
            lbl_sub.pack()

            # Index & Binary Address
            bin_addr = f"{i:0{max(3, r)}b}"
            lbl_addr = tk.Label(cell_box, text=f"#{i} ({bin_addr})", font=("Consolas", 8), bg=bg_col, fg="#444")
            lbl_addr.pack()

        # Update stats
        m = self.encoded_data["m"]
        tot = len(self.codeword_cells)
        self.lbl_stats.config(text=f"Bits: {m} Data | {analysis['r']} Parity + P0 | Total: {tot}")

    def _highlight_coverage(self, parity_pos: int):
        parity_obj = self.codeword_cells[parity_pos]
        covers = parity_obj.get("covers", [])
        for idx, btn in enumerate(self.bit_buttons):
            if idx == parity_pos or idx in covers:
                btn.config(bg=self.COLOR_HIGHLIGHT)

    def _clear_highlight(self):
        curr_cw = [c["bit"] for c in self.codeword_cells]
        orig_cw = [c["bit"] for c in self.encoded_data["codeword_cells"]]
        for i, btn in enumerate(self.bit_buttons):
            is_flipped = (curr_cw[i] != orig_cw[i])
            if is_flipped:
                btn.config(bg=self.COLOR_FLIPPED)
            elif i == 0:
                btn.config(bg=self.COLOR_OVERALL)
            elif self.codeword_cells[i]["is_parity"]:
                btn.config(bg=self.COLOR_PARITY)
            else:
                btn.config(bg=self.COLOR_DATA)

    def _render_checksum(self, curr_cw: List[int]):
        raw_bytes = BitManipulator.bits_to_bytes(curr_cw)
        chk, steps = InternetChecksum.calculate(raw_bytes)
        adler = InternetChecksum.adler32(raw_bytes)
        crc = InternetChecksum.crc32(raw_bytes)

        self.lbl_chk_hex.config(text=f"0x{chk:04X}")
        bin_str = f"{chk:016b}"
        grouped_bin = " ".join([bin_str[i:i+4] for i in range(0, 16, 4)])
        self.lbl_chk_bin.config(text=grouped_bin)

        is_valid = InternetChecksum.verify(raw_bytes, chk)
        if is_valid:
            self.lbl_verif_status.config(text="PASS (Sum = 0xFFFF)", bg="#e6f4ea", fg="#0d5a23")
        else:
            self.lbl_verif_status.config(text="FAIL (Corrupted)", bg="#fce8e6", fg="#961714")

        self.lbl_hashes.config(text=f"Adler-32: 0x{adler:08X}\nCRC-32:   0x{crc:08X}")

        # Checksum arithmetic steps tab
        self.txt_chk_steps.delete("1.0", tk.END)
        txt = "RFC 1071 16-BIT 1'S COMPLEMENT INTERNET CHECKSUM BREAKDOWN\n"
        txt += "=" * 70 + "\n"
        for s in steps:
            if s["action"] == "segmentation":
                txt += f"• Segmentation: {s['bytes_count']} bytes grouped into {len(s['words'])} 16-bit word(s) (Odd padded: {s['odd_padded']})\n"
                for w_idx, w in enumerate(s["words"]):
                    txt += f"    Word #{w_idx+1}: 0x{w:04X} ({w:016b})\n"
            elif s["action"] == "add_word":
                carry_txt = f"Carry +{s['carry_wrapped']} wrapped" if s['carry_wrapped'] else "No carry"
                txt += f"• Add Word #{s['index']+1} [0x{s['word']:04X}]: 0x{s['prev_accum']:04X} + 0x{s['word']:04X} = 0x{s['new_accum']:04X} ({carry_txt})\n"
            elif s["action"] == "ones_complement_inversion":
                txt += f"• Bitwise Inversion (~Sum): ~0x{s['final_accum']:04X} = 0x{s['checksum']:04X} ({s['checksum']:016b})\n"

        txt += "=" * 70 + "\n"
        txt += f"Receiver Verification Check: Sum(Words) + Checksum = 0x{0xFFFF:04X} ({'PASS' if is_valid else 'FAIL'})\n"
        self.txt_chk_steps.insert(tk.END, txt)

    def _render_syndrome_analysis(self, analysis: Dict[str, Any]):
        c = analysis["classification"]
        S = analysis["syndrome_value"]
        p_check = analysis["p_check"]
        s_bin = f"{S:0{analysis['r']}b}"

        if c == "VALID":
            self.lbl_status_banner.config(
                text=f"STATUS: CODEWORD VALID (NO ERRORS DETECTED)\nSyndrome S = {S} (0b{s_bin}) | Overall Parity P_check = {p_check} (Even)",
                bg="#e6f4ea", fg="#0d5a23"
            )
            self.btn_autocorrect.config(state=tk.DISABLED)
            self.btn_resolve_2bit.config(state=tk.DISABLED)
        elif c in ("SINGLE_BIT_CORRECTABLE", "SINGLE_BIT_P0"):
            self.lbl_status_banner.config(
                text=f"STATUS: 1-BIT ERROR DETECTED AT BIT #{analysis['error_pos']} (CORRECTABLE)\nSyndrome S = {S} (0b{s_bin}) | Overall Parity P_check = {p_check} (Odd)",
                bg="#fffde7", fg="#b06000"
            )
            self.btn_autocorrect.config(state=tk.NORMAL)
            self.btn_resolve_2bit.config(state=tk.DISABLED)
        elif c == "DOUBLE_BIT_DETECTED":
            self.lbl_status_banner.config(
                text=f"STATUS: 2-BIT DOUBLE ERROR DETECTED — UNCORRECTABLE WITH STANDALONE SEC-DED\nSyndrome S = {S} (0b{s_bin}) | Overall Parity P_check = {p_check} (Even) [DEC Resolver Available]",
                bg="#fce8e6", fg="#961714"
            )
            self.btn_autocorrect.config(state=tk.DISABLED)
            self.btn_resolve_2bit.config(state=tk.NORMAL)

        # Equations & Decision Matrix Table
        self.txt_syndrome_math.delete("1.0", tk.END)
        txt = "SYNDROME BITWISE MODULO-2 (XOR) PARITY EQUATIONS:\n"
        txt += "-" * 74 + "\n"
        for eq in analysis["equations"]:
            pos_names = [self.codeword_cells[p]["role"] for p in eq["checked_positions"]]
            vals = [str(self.codeword_cells[p]["bit"]) for p in eq["checked_positions"]]
            status = "✓ [PASS]" if eq["passed"] else "✗ [MISMATCH -> 1]"
            formula = f"s{eq['bit_idx']} = " + " ⊕ ".join(pos_names)
            calc = " ⊕ ".join(vals) + f" = {eq['syndrome_bit']}"
            txt += f"{formula:<36} => {calc:<20} {status}\n"

        txt += "-" * 74 + "\n"
        txt += f"P_check = ⊕ (all bits 0..n) => {p_check} ({'Even: Parity Satisfied' if p_check == 0 else 'Odd: Parity Violated'})\n"
        txt += f"Computed Syndrome Vector: S = {S} (Binary: 0b{s_bin})\n\n"

        txt += "SEC-DED HARDWARE DECISION TRUTH TABLE:\n"
        txt += "-" * 74 + "\n"
        txt += "  Syndrome (S)   | P_check (Overall) | Classification       | Active\n"
        txt += "-" * 74 + "\n"
        txt += f"  S == 0         | P_check == 0      | No Error             | {'<<< ACTIVE' if c == 'VALID' else ''}\n"
        txt += f"  S != 0         | P_check == 1      | Single Bit Error     | {'<<< ACTIVE' if c == 'SINGLE_BIT_CORRECTABLE' else ''}\n"
        txt += f"  S == 0         | P_check == 1      | Error in P0          | {'<<< ACTIVE' if c == 'SINGLE_BIT_P0' else ''}\n"
        txt += f"  S != 0         | P_check == 0      | Double Bit (2-Bit)   | {'<<< ACTIVE' if c == 'DOUBLE_BIT_DETECTED' else ''}\n"
        txt += "-" * 74 + "\n"

        if c == "DOUBLE_BIT_DETECTED":
            txt += "\n[!] 2-Bit Error Tie-Breaker Candidates (i ⊕ j = S):\n"
            curr_cw = [cell["bit"] for cell in self.codeword_cells]
            n = len(curr_cw) - 1
            cand_pairs = []
            if 0 < S <= n:
                cand_pairs.append((0, S))
            for i in range(1, n + 1):
                j = i ^ S
                if i < j <= n:
                    cand_pairs.append((i, j))

            for p1, p2 in cand_pairs:
                test_cw = list(curr_cw)
                test_cw[p1] ^= 1
                test_cw[p2] ^= 1
                test_bytes = BitManipulator.bits_to_bytes(test_cw)
                chk, _ = InternetChecksum.calculate(test_bytes)
                is_match = (chk == self.reference_checksum)
                flag = "★ [MATCH! TARGET RESTORED]" if is_match else "✗ [MISMATCH]"
                txt += f"    Pair (#{p1}, #{p2}) [{self.codeword_cells[p1]['role']}, {self.codeword_cells[p2]['role']}]: Checksum 0x{chk:04X} {flag}\n"

        self.txt_syndrome_math.insert(tk.END, txt)

    def _render_matrix(self, analysis: Dict[str, Any]):
        n = len(self.codeword_cells) - 1
        r = analysis["r"]
        self.txt_matrix.delete("1.0", tk.END)

        txt = f"PARITY CHECK MATRIX H  [{r} rows × {n} columns]:\n"
        txt += "(Columns 1 to n correspond directly to binary index)\n\n"

        role_header = "     " + "".join([f"{self.codeword_cells[c]['role']:>4}" for c in range(1, n + 1)])
        col_header  = "     " + "".join([f"{c:>4}" for c in range(1, n + 1)])
        div         = "     " + "----" * n

        txt += role_header + "\n" + col_header + "\n" + div + "\n"

        for row in range(r):
            p_pos = 1 << row
            row_bits = "".join([f"{1 if (col & p_pos) != 0 else 0:>4}" for col in range(1, n + 1)])
            txt += f"s{row} |{row_bits}\n"

        txt += "\nOverall Parity Vector P0 checks all columns: [ 1 1 1 ... 1 ]\n\n"
        txt += "HARDWARE BITMASK EQUATIONS:\n"
        for row in range(r):
            mask = 1 << row
            txt += f"  Bitmask for P{mask:2d}: (pos & 0x{mask:X}) != 0\n"

        txt += "\nTHEORY OF 2-BIT CORRECTION (DEC) ADAPTATION:\n"
        txt += "  Standard Extended Hamming distance d_min = 4.\n"
        txt += "  When 2 bits flip at (i, j), syndrome is S = col(i) ⊕ col(j) = i ⊕ j.\n"
        txt += "  Because multiple pairs produce the exact same XOR sum S, standalone SEC-DED halts to prevent corruption.\n"
        txt += "  By checking each candidate pair against the 16-bit Internet Checksum (RFC 1071),\n"
        txt += "  the tie is broken, enabling full 2-bit error correction without ambiguity!\n"

        self.txt_matrix.insert(tk.END, txt)

    def _render_status_bar(self, orig_cw: List[int], curr_cw: List[int], analysis: Dict[str, Any]):
        flipped = sum(1 for i in range(len(curr_cw)) if curr_cw[i] != orig_cw[i])
        self.sb_errors.config(text=f"Errors: {flipped}")
        self.sb_ready.config(text="Modified" if flipped > 0 else "Pristine")
        self.sb_diag.config(text=f"Diagnosis: {analysis['classification']} ({analysis['description']})")
        self.sb_chk.config(text=f"Checksum: {self.lbl_chk_hex.cget('text')}")

    def _show_about(self):
        messagebox.showinfo(
            "About ECC Studio",
            "ECC & Integrity Studio v2.4\n\n"
            "Extended Hamming Code (SEC-DED) with Checksum-Assisted 2-Bit Correction & RFC 1071 16-bit Checksum Engine.\n\n"
            "Crafted for systems engineers and computer science pedagogy."
        )


if __name__ == "__main__":
    app = ECCStudioGUI()
    app.mainloop()

