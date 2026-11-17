#!/usr/bin/env python3
"""
gui.py
======
A native desktop GUI for the MiniLang Compiler built with Python's standard
library Tkinter (zero external dependencies).

Features:
- Live code editor with syntax example presets
- Multi-tab visualization for each compiler phase:
  1. Output (execution results & runtime errors)
  2. Tokens (Lexer)
  3. AST (Parser)
  4. IR / Three Address Code (TAC)
  5. Full Pipeline Debug Trace
- Threaded execution with timeout / stop support
- Keyboard shortcut: F5 or Ctrl+Enter to Run
"""

import os
import sys
import io
import contextlib
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.generator import IRGenerator, format_ir
from vm.interpreter import VirtualMachine
from utils.ast_printer import print_ast
from errors.errors import MiniLangError


DEFAULT_CODE = """// MiniLang Demo Program
func factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

let num = 5;
print("Calculating factorial of:");
print(num);

let result = factorial(num);
print("Result:");
print(result);
"""


class MiniLangIDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MiniLang Compiler & IDE")
        self.geometry("1100x720")
        self.minsize(800, 500)

        # Base path
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.examples_dir = os.path.join(self.project_dir, "examples")

        self.running_thread = None
        self._setup_style()
        self._create_widgets()
        self._populate_examples()

        # Keyboard shortcuts
        self.bind("<F5>", lambda event: self.run_program())
        self.bind("<Control-Return>", lambda event: self.run_program())

    def _setup_style(self):
        self.style = ttk.Style(self)
        # Choose available theme
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        # Color palette
        self.bg_dark = "#1e1e2e"
        self.editor_bg = "#181825"
        self.editor_fg = "#cdd6f4"
        self.output_bg = "#11111b"
        self.accent_color = "#89b4fa"
        self.error_color = "#f38ba8"
        self.success_color = "#a6e3a1"
        self.font_code = ("Consolas", 11)
        self.font_ui = ("Segoe UI", 10)

        self.configure(bg=self.bg_dark)
        self.style.configure("TFrame", background=self.bg_dark)
        self.style.configure("TLabel", background=self.bg_dark, foreground="#cdd6f4", font=self.font_ui)
        self.style.configure("TButton", font=self.font_ui, padding=5)
        self.style.configure("TCombobox", font=self.font_ui)
        self.style.configure("TNotebook", background=self.bg_dark)
        self.style.configure("TNotebook.Tab", font=self.font_ui, padding=[10, 4])

    def _create_widgets(self):
        # ---------------- Top Toolbar ----------------
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        lbl_example = ttk.Label(toolbar, text="Load Example:")
        lbl_example.pack(side=tk.LEFT, padx=(0, 6))

        self.combo_examples = ttk.Combobox(toolbar, state="readonly", width=28)
        self.combo_examples.pack(side=tk.LEFT, padx=(0, 15))
        self.combo_examples.bind("<<ComboboxSelected>>", self._on_example_selected)

        self.btn_run = tk.Button(
            toolbar,
            text="▶ Run (F5)",
            command=self.run_program,
            bg="#2e7d32",
            fg="white",
            activebackground="#388e3c",
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        self.btn_run.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_compile = tk.Button(
            toolbar,
            text="⚙ Check / Compile Only",
            command=self.compile_only,
            bg="#0288d1",
            fg="white",
            activebackground="#039be5",
            activeforeground="white",
            relief=tk.FLAT,
            padx=10,
            pady=4,
            font=self.font_ui,
            cursor="hand2"
        )
        self.btn_compile.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = tk.Button(
            toolbar,
            text="🧹 Clear Editor",
            command=self.clear_editor,
            bg="#45475a",
            fg="white",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            font=self.font_ui,
            cursor="hand2"
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 6))

        # ---------------- Main Paned Window ----------------
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Left pane: Editor
        editor_frame = ttk.Frame(paned)
        paned.add(editor_frame, weight=1)

        editor_header = ttk.Frame(editor_frame)
        editor_header.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        ttk.Label(editor_header, text="Source Code (.mini)", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)

        self.editor = ScrolledText(
            editor_frame,
            wrap=tk.NONE,
            font=self.font_code,
            bg=self.editor_bg,
            fg=self.editor_fg,
            insertbackground="white",
            selectbackground="#45475a",
            padx=8,
            pady=8,
            relief=tk.FLAT,
            undo=True
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.insert(tk.END, DEFAULT_CODE)

        # Right pane: Tabs for compiler phases
        output_frame = ttk.Frame(paned)
        paned.add(output_frame, weight=1)

        self.notebook = ttk.Notebook(output_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.txt_output = self._create_tab_textbox("Program Output")
        self.txt_tokens = self._create_tab_textbox("Tokens (Lexer)")
        self.txt_ast = self._create_tab_textbox("AST (Parser)")
        self.txt_ir = self._create_tab_textbox("Three Address Code (IR)")
        self.txt_debug = self._create_tab_textbox("Full Debug Trace")

        # ---------------- Status Bar ----------------
        self.status_bar = tk.Label(
            self,
            text="Ready. Press F5 or '▶ Run' to compile and execute.",
            bg="#11111b",
            fg="#a6adc8",
            font=("Segoe UI", 9),
            anchor=tk.W,
            padx=10,
            pady=4
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_tab_textbox(self, title):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        txt = ScrolledText(
            frame,
            wrap=tk.WORD,
            font=self.font_code,
            bg=self.output_bg,
            fg=self.editor_fg,
            insertbackground="white",
            selectbackground="#45475a",
            padx=8,
            pady=8,
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        txt.pack(fill=tk.BOTH, expand=True)
        return txt

    def _set_text(self, widget: ScrolledText, content: str, error: bool = False):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        if error:
            widget.tag_config("error", foreground=self.error_color)
            widget.tag_add("error", "1.0", tk.END)
        widget.configure(state=tk.DISABLED)

    def _populate_examples(self):
        items = []
        if os.path.exists(self.examples_dir):
            for file in sorted(os.listdir(self.examples_dir)):
                if file.endswith(".mini"):
                    items.append(file)
            invalid_dir = os.path.join(self.examples_dir, "invalid")
            if os.path.exists(invalid_dir):
                for file in sorted(os.listdir(invalid_dir)):
                    if file.endswith(".mini"):
                        items.append(f"invalid/{file}")
        self.combo_examples["values"] = items

    def _on_example_selected(self, event=None):
        choice = self.combo_examples.get()
        if not choice:
            return
        path = os.path.join(self.examples_dir, choice)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.delete("1.0", tk.END)
            self.editor.insert(tk.END, content)
            self.set_status(f"Loaded example: {choice}", self.accent_color)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {e}")

    def clear_editor(self):
        self.editor.delete("1.0", tk.END)
        self.set_status("Editor cleared.", "#a6adc8")

    def set_status(self, text, color="#a6adc8"):
        self.status_bar.config(text=text, fg=color)

    def run_program(self):
        self._execute_pipeline(run_vm=True)

    def compile_only(self):
        self._execute_pipeline(run_vm=False)

    def _execute_pipeline(self, run_vm=True):
        source = self.editor.get("1.0", tk.END).strip()
        if not source:
            self.set_status("Source code is empty.", self.error_color)
            return

        debug_buffer = io.StringIO()
        output_buffer = io.StringIO()

        def log_debug(title, content):
            debug_buffer.write(f"\n{'=' * 10} {title} {'=' * 10}\n")
            debug_buffer.write(content.rstrip() + "\n")

        log_debug("SOURCE", source)

        try:
            # 1. Lexical Analysis
            tokens = Lexer(source).tokenize()
            tokens_str = "\n".join(str(t) for t in tokens)
            self._set_text(self.txt_tokens, tokens_str)
            log_debug("TOKENS", tokens_str)

            # 2. Syntax Analysis (Parsing)
            tree = Parser(tokens).parse()
            ast_str = print_ast(tree)
            self._set_text(self.txt_ast, ast_str)
            log_debug("AST", ast_str)

            # 3. Semantic Analysis
            analyzer = SemanticAnalyzer()
            errors = analyzer.analyze(tree)
            if errors:
                err_msg = "\n".join(str(e) for e in errors)
                full_msg = f"{err_msg}\n\n{len(errors)} semantic error(s) found. Compilation aborted."
                self._set_text(self.txt_output, full_msg, error=True)
                log_debug("SEMANTIC ANALYSIS", full_msg)
                self._set_text(self.txt_debug, debug_buffer.getvalue())
                self.notebook.select(0)
                self.set_status(f"Semantic Analysis Failed ({len(errors)} error(s)).", self.error_color)
                return

            log_debug("SEMANTIC ANALYSIS", "No errors found.")

            # 4. IR Generation
            ir_instructions = IRGenerator().generate(tree)
            ir_str = format_ir(ir_instructions)
            self._set_text(self.txt_ir, ir_str)
            log_debug("INTERMEDIATE CODE (TAC)", ir_str)

            # 5. Execution (Virtual Machine)
            if run_vm:
                with contextlib.redirect_stdout(output_buffer):
                    vm = VirtualMachine(ir_instructions)
                    vm.run()
                exec_output = output_buffer.getvalue()
                log_debug("EXECUTION", exec_output if exec_output else "[Program produced no output]")
                self._set_text(self.txt_output, exec_output if exec_output else "[Program finished with no output]")
                self.notebook.select(0)
                self.set_status("[OK] Program compiled and executed successfully!", self.success_color)
            else:
                self._set_text(self.txt_output, "[OK] Compilation successful! Syntax & semantic checks passed.\n(Execution skipped)")
                self.notebook.select(0)
                self.set_status("[OK] Code checked and compiled successfully!", self.success_color)

            self._set_text(self.txt_debug, debug_buffer.getvalue())

        except MiniLangError as e:
            error_str = f"Compilation / Execution Error:\n\n{e}"
            self._set_text(self.txt_output, error_str, error=True)
            log_debug("ERROR", error_str)
            self._set_text(self.txt_debug, debug_buffer.getvalue())
            self.notebook.select(0)
            self.set_status(f"Error: {e.phase} at {e.line}:{e.column or '?'}", self.error_color)
        except Exception as e:
            error_str = f"Internal Error:\n\n{e}"
            self._set_text(self.txt_output, error_str, error=True)
            self.notebook.select(0)
            self.set_status("Unexpected internal error.", self.error_color)


def main():
    app = MiniLangIDE()
    app.mainloop()


if __name__ == "__main__":
    main()
