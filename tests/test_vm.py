"""
tests/test_vm.py
==================
Unit tests for Phase 5/6 (IR generation and the Virtual Machine).
Run with:  python -m unittest tests.test_vm -v
"""

import unittest
import io
import sys
import os
from contextlib import redirect_stdout

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.generator import IRGenerator
from vm.interpreter import VirtualMachine


def run_program(source):
    """Compiles and runs `source`, returning (captured_stdout, final_globals)."""
    tokens = Lexer(source).tokenize()
    tree = Parser(tokens).parse()
    errors = SemanticAnalyzer().analyze(tree)
    assert not errors, f"Unexpected semantic errors: {errors}"
    ir = IRGenerator().generate(tree)
    buf = io.StringIO()
    with redirect_stdout(buf):
        globals_env = VirtualMachine(ir).run()
    return buf.getvalue(), globals_env


class TestVirtualMachine(unittest.TestCase):

    def test_hello_world(self):
        out, _ = run_program('print("Hello World");')
        self.assertEqual(out.strip(), "Hello World")

    def test_arithmetic(self):
        out, env = run_program("""
            let x = 10;
            let y = 20;
            let sum = x + y;
            print(sum);
        """)
        self.assertEqual(out.strip(), "30")
        self.assertEqual(env["sum"], 30)

    def test_nested_expression_ir(self):
        _, env = run_program("""
            let a = 1;
            let b = 2;
            let c = 3;
            let result = (a + b) * c;
        """)
        self.assertEqual(env["result"], 9)

    def test_if_else_true_branch(self):
        out, _ = run_program("""
            let a = 10;
            let b = 20;
            if (a < b) { print("a is smaller"); } else { print("b is smaller"); }
        """)
        self.assertEqual(out.strip(), "a is smaller")

    def test_if_else_false_branch(self):
        out, _ = run_program("""
            let a = 30;
            let b = 20;
            if (a < b) { print("a is smaller"); } else { print("b is smaller"); }
        """)
        self.assertEqual(out.strip(), "b is smaller")

    def test_while_loop(self):
        out, _ = run_program("""
            let x = 0;
            while (x < 5) {
                print(x);
                x = x + 1;
            }
        """)
        self.assertEqual(out.strip().splitlines(), ["0", "1", "2", "3", "4"])

    def test_function_call(self):
        out, _ = run_program("""
            func add(a, b) { return a + b; }
            let result = add(10, 20);
            print(result);
        """)
        self.assertEqual(out.strip(), "30")

    def test_recursive_factorial(self):
        out, _ = run_program("""
            func factorial(n) {
                if (n <= 1) { return 1; }
                return n * factorial(n - 1);
            }
            let result = factorial(5);
            print(result);
        """)
        self.assertEqual(out.strip(), "120")

    def test_recursive_fibonacci(self):
        out, _ = run_program("""
            func fib(n) {
                if (n <= 1) { return n; }
                return fib(n - 1) + fib(n - 2);
            }
            print(fib(10));
        """)
        self.assertEqual(out.strip(), "55")

    def test_boolean_and_logical_ops(self):
        out, _ = run_program("""
            let a = true;
            let b = false;
            print(a && b);
            print(a || b);
            print(!a);
        """)
        self.assertEqual(out.strip().splitlines(), ["false", "true", "false"])

    def test_string_concatenation(self):
        out, _ = run_program("""
            let name = "Alice";
            print("Hello, " + name);
        """)
        self.assertEqual(out.strip(), "Hello, Alice")

    def test_modulo_and_division(self):
        out, _ = run_program("""
            print(10 % 3);
            print(10 / 2);
        """)
        self.assertEqual(out.strip().splitlines(), ["1", "5"])

    def test_nested_function_calls(self):
        out, _ = run_program("""
            func square(x) { return x * x; }
            func sumSquares(a, b) { return square(a) + square(b); }
            print(sumSquares(3, 4));
        """)
        self.assertEqual(out.strip(), "25")


if __name__ == "__main__":
    unittest.main()
