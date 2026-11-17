import streamlit as st
import io
import contextlib

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.generator import IRGenerator, format_ir
from vm.interpreter import VirtualMachine
from utils.ast_printer import print_ast
from errors.errors import MiniLangError

st.set_page_config(page_title="MiniLang Compiler Online", layout="wide")

st.title("💻 MiniLang Compiler & IDE")
st.caption("A multi-phase compiler pipeline: Lexer → Parser → Semantic → IR → VM")

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

code = st.text_area("Write your MiniLang code here:", value=DEFAULT_CODE, height=260)

if st.button("🚀 Run / Compile", type="primary"):
    tab_out, tab_tokens, tab_ast, tab_ir = st.tabs(["Output & Execution", "Tokens (Lexer)", "AST (Parser)", "IR (Three-Address Code)"])
    
    try:
        # Phase 1: Lexer
        tokens = Lexer(code).tokenize()
        with tab_tokens:
            token_display = "\n".join(f"[{t.type.name:<15}] {t.value!r:<12} (Line {t.line}, Col {t.col})" for t in tokens)
            st.code(token_display, language="text")

        # Phase 2: Parser
        ast = Parser(tokens).parse()
        with tab_ast:
            buf = io.StringIO()
            print_ast(ast, out=buf)
            st.code(buf.getvalue(), language="text")

        # Phase 3: Semantic Analysis
        SemanticAnalyzer().analyze(ast)

        # Phase 4: IR Generation
        ir_instructions = IRGenerator().generate(ast)
        with tab_ir:
            st.code(format_ir(ir_instructions), language="text")

        # Phase 5: Virtual Machine Execution
        with tab_out:
            exec_buf = io.StringIO()
            with contextlib.redirect_stdout(exec_buf):
                VirtualMachine().execute(ir_instructions)
            st.success("Execution Successful!")
            st.code(exec_buf.getvalue(), language="text")

    except MiniLangError as e:
        with tab_out:
            st.error(f"Compilation/Runtime Error: {e}")
    except Exception as e:
        with tab_out:
            st.error(f"Unexpected Error: {e}")