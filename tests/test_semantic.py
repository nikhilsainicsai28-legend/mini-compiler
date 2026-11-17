"""
tests/test_semantic.py
========================
Unit tests for Phase 4 (Semantic Analysis).
Run with:  python -m unittest tests.test_semantic -v
"""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer


def analyze(source):
    tokens = Lexer(source).tokenize()
    tree = Parser(tokens).parse()
    return SemanticAnalyzer().analyze(tree)


class TestSemanticAnalyzer(unittest.TestCase):

    def test_valid_program_has_no_errors(self):
        errors = analyze("""
            let x = 10;
            let y = 20;
            print(x + y);
        """)
        self.assertEqual(errors, [])

    def test_undefined_variable(self):
        errors = analyze("print(x);")
        self.assertEqual(len(errors), 1)
        self.assertIn("not defined", errors[0].message)

    def test_duplicate_declaration_same_scope(self):
        errors = analyze("let x = 10;\nlet x = 20;")
        self.assertEqual(len(errors), 1)
        self.assertIn("already declared", errors[0].message)

    def test_shadowing_in_inner_scope_is_allowed(self):
        errors = analyze("""
            let x = 10;
            if (true) {
                let x = 20;
                print(x);
            }
            print(x);
        """)
        self.assertEqual(errors, [])

    def test_invalid_type_operation_string_minus_int(self):
        errors = analyze('let x = "hello" - 10;')
        self.assertEqual(len(errors), 1)
        self.assertIn("Invalid operand types", errors[0].message)

    def test_string_concatenation_is_allowed(self):
        errors = analyze('let x = "hello " + "world";')
        self.assertEqual(errors, [])

    def test_undefined_function_call(self):
        errors = analyze("let x = foo(1, 2);")
        self.assertEqual(len(errors), 1)
        self.assertIn("is not defined", errors[0].message)

    def test_wrong_argument_count(self):
        errors = analyze("""
            func add(a, b) { return a + b; }
            let x = add(1);
        """)
        self.assertEqual(len(errors), 1)
        self.assertIn("expects 2 argument", errors[0].message)

    def test_correct_argument_count_ok(self):
        errors = analyze("""
            func add(a, b) { return a + b; }
            let x = add(1, 2);
        """)
        self.assertEqual(errors, [])

    def test_return_outside_function(self):
        errors = analyze("return 5;")
        self.assertEqual(len(errors), 1)
        self.assertIn("outside of a function", errors[0].message)

    def test_return_inside_function_ok(self):
        errors = analyze("func f() { return 1; }")
        self.assertEqual(errors, [])

    def test_recursive_function_allowed(self):
        errors = analyze("""
            func factorial(n) {
                if (n <= 1) { return 1; }
                return n * factorial(n - 1);
            }
        """)
        self.assertEqual(errors, [])

    def test_forward_reference_between_functions(self):
        # helper() is defined AFTER main() calls it - should still resolve
        # because of the hoisting pass.
        errors = analyze("""
            func main() { return helper(); }
            func helper() { return 42; }
        """)
        self.assertEqual(errors, [])

    def test_comparison_type_error(self):
        errors = analyze('let x = "abc" > 5;')
        self.assertEqual(len(errors), 1)
        self.assertIn("Cannot compare", errors[0].message)

    def test_multiple_errors_collected(self):
        errors = analyze("""
            print(undefinedVar);
            let y = "text" - 1;
        """)
        self.assertEqual(len(errors), 2)


if __name__ == "__main__":
    unittest.main()
