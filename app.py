import streamlit as st
import io
import os
import contextlib

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.generator import IRGenerator, format_ir
from vm.interpreter import VirtualMachine
from utils.ast_printer import print_ast
from errors.errors import MiniLangError

st.set_page_config(
    page_title="MiniLang Compiler & IDE",
    page_icon="💻",
    layout="wide"
)

st.title("💻 MiniLang Compiler & IDE")
st.caption("A multi-phase compiler pipeline: Lexer ➔ Parser ➔ Semantic Analysis ➔ IR (Three Address Code) ➔ Virtual Machine")

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

# Load sample files from examples/ directory
example_options = {"Default Demo": DEFAULT_CODE}
examples_dir = os.path.join(os.path.dirname(__file__), "examples")
if os.path.exists(examples_dir):
    for root, _, files in os.walk(examples_dir):
        for f in sorted(files):
            if f.endswith(".mini"):
                rel_path = os.path.relpath(os.path.join(root, f), examples_dir)
                try:
                    with open(os.path.join(root, f), "r", encoding="utf-8") as file_content:
                        example_options[f"examples/{rel_path}"] = file_content.read()
                except Exception:
                    pass

# Top Toolbar
col_select, col_empty = st.columns([2, 3])
with col_select:
    selected_example = st.selectbox("📂 Load Example Preset:", options=list(example_options.keys()))

if "current_code" not in st.session_state or st.session_state.get("last_selected") != selected_example:
    st.session_state["current_code"] = example_options[selected_example]
    st.session_state["last_selected"] = selected_example

# Layout: Split into Code Editor and Execution Output (like gui.py)
col_editor, col_results = st.columns([1, 1], gap="medium")

with col_editor:
    st.subheader("Source Code (.mini)")
    code_input = st.text_area(
        label="Source Code",
        value=st.session_state["current_code"],
        height=480,
        label_visibility="collapsed"
    )
    st.session_state["current_code"] = code_input

    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        run_clicked = st.button("▶ Run (Full Pipeline)", type="primary", use_container_width=True)
    with btn_col2:
        compile_only_clicked = st.button("⚙ Check / Compile Only", use_container_width=True)

with col_results:
    st.subheader("Compiler Pipeline & Output")
    tab_out, tab_tokens, tab_ast, tab_ir, tab_debug = st.tabs([
        "Program Output",
        "Tokens (Lexer)",
        "AST (Parser)",
        "Three Address Code (IR)",
        "Full Debug Trace"
    ])

    should_execute = run_clicked or compile_only_clicked
    # Auto-run once on initial load
    if not should_execute and "has_run" not in st.session_state:
        should_execute = True
        st.session_state["has_run"] = True

    if should_execute:
        debug_trace = []
        tokens = None
        ast = None
        ir_instructions = None

        try:
            # 1. Lexical Analysis
            debug_trace.append("=== PHASE 1: LEXICAL ANALYSIS ===")
            lexer = Lexer(code_input)
            tokens = lexer.tokenize()
            debug_trace.append(f"Successfully tokenized {len(tokens)} tokens.")

            with tab_tokens:
                token_lines = [
                    f"[{t.type.name:<12}] {t.lexeme!r:<15} (Line {t.line:>2}, Col {t.column:>2})"
                    for t in tokens
                ]
                st.code("\n".join(token_lines), language="text")

            # 2. Syntax Analysis (Parser)
            debug_trace.append("\n=== PHASE 2: SYNTAX ANALYSIS (PARSER) ===")
            parser = Parser(tokens)
            ast = parser.parse()
            debug_trace.append("AST built successfully.")

            with tab_ast:
                ast_buf = io.StringIO()
                print_ast(ast, out=ast_buf)
                st.code(ast_buf.getvalue(), language="text")

            # 3. Semantic Analysis
            debug_trace.append("\n=== PHASE 3: SEMANTIC ANALYSIS ===")
            analyzer = SemanticAnalyzer()
            analyzer.analyze(ast)
            debug_trace.append("Semantic checks passed (no undeclared variables, valid scopes).")

            # 4. Intermediate Representation (IR / TAC)
            debug_trace.append("\n=== PHASE 4: IR CODE GENERATION (TAC) ===")
            ir_gen = IRGenerator()
            ir_instructions = ir_gen.generate(ast)
            ir_text = format_ir(ir_instructions)
            debug_trace.append(f"Generated {len(ir_instructions)} IR instructions.")

            with tab_ir:
                st.code(ir_text, language="text")

            # 5. Virtual Machine Execution
            if run_clicked or (not compile_only_clicked):
                debug_trace.append("\n=== PHASE 5: VM EXECUTION ===")
                vm = VirtualMachine()
                exec_buf = io.StringIO()
                with contextlib.redirect_stdout(exec_buf):
                    vm.execute(ir_instructions)
                
                output = exec_buf.getvalue()
                debug_trace.append("Execution completed normally.")

                with tab_out:
                    st.success("Execution Successful!")
                    if output.strip():
                        st.code(output, language="text")
                    else:
                        st.info("(Program produced no output)")
            else:
                with tab_out:
                    st.success("Compilation Successful! (Check / Compile Only mode)")

        except MiniLangError as err:
            err_msg = str(err)
            debug_trace.append(f"\n[COMPILATION / EXECUTION ERROR]:\n{err_msg}")
            with tab_out:
                st.error(f"**Compilation / Execution Error:**\n\n{err_msg}")
        except Exception as ex:
            err_msg = f"{type(ex).__name__}: {ex}"
            debug_trace.append(f"\n[UNEXPECTED ERROR]:\n{err_msg}")
            with tab_out:
                st.error(f"**Unexpected Error:**\n\n{err_msg}")

        with tab_debug:
            st.code("\n".join(debug_trace), language="text")
