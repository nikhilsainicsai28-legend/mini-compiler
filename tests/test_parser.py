"""
tests/test_parser.py
======================
Unit tests for Phase 2/3 (Parsing and AST construction).
Run with:  python -m unittest tests.test_parser -v
"""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lexer.lexer import Lexer
from parser.parser import Parser
from ast_nodes import nodes as ast
from errors.errors import ParserError


def parse(source):
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


class TestParser(unittest.TestCase):

    def test_var_declaration(self):
        tree = parse("let x = 10;")
        self.assertEqual(len(tree.statements), 1)
        decl = tree.statements[0]
        self.assertIsInstance(decl, ast.VarDeclaration)
        self.assertEqual(decl.name, "x")
        self.assertIsInstance(decl.initializer, ast.Literal)
        self.assertEqual(decl.initializer.value, 10)

    def test_binary_expression_precedence(self):
        # 2 + 3 * 4 should parse as 2 + (3 * 4), i.e. '+' is the root
        tree = parse("let x = 2 + 3 * 4;")
        expr = tree.statements[0].initializer
        self.assertIsInstance(expr, ast.BinaryExpression)
        self.assertEqual(expr.operator, "+")
        self.assertIsInstance(expr.right, ast.BinaryExpression)
        self.assertEqual(expr.right.operator, "*")

    def test_parentheses_override_precedence(self):
        # (2 + 3) * 4 should parse with '*' at the root
        tree = parse("let x = (2 + 3) * 4;")
        expr = tree.statements[0].initializer
        self.assertEqual(expr.operator, "*")
        self.assertIsInstance(expr.left, ast.BinaryExpression)
        self.assertEqual(expr.left.operator, "+")

    def test_assignment_statement(self):
        tree = parse("let x = 1;\nx = 5;")
        stmt = tree.statements[1]
        self.assertIsInstance(stmt, ast.ExpressionStatement)
        self.assertIsInstance(stmt.expression, ast.Assignment)
        self.assertEqual(stmt.expression.name, "x")

    def test_if_else(self):
        tree = parse('if (x > 10) { print(x); } else { print(0); }')
        stmt = tree.statements[0]
        self.assertIsInstance(stmt, ast.IfStatement)
        self.assertIsNotNone(stmt.then_branch)
        self.assertIsNotNone(stmt.else_branch)

    def test_if_without_else(self):
        tree = parse('if (x > 10) { print(x); }')
        stmt = tree.statements[0]
        self.assertIsNone(stmt.else_branch)

    def test_while_loop(self):
        tree = parse("while (x < 10) { x = x + 1; }")
        stmt = tree.statements[0]
        self.assertIsInstance(stmt, ast.WhileStatement)
        self.assertEqual(len(stmt.body.statements), 1)

    def test_function_declaration(self):
        tree = parse("func add(a, b) { return a + b; }")
        fn = tree.statements[0]
        self.assertIsInstance(fn, ast.FunctionDeclaration)
        self.assertEqual(fn.name, "add")
        self.assertEqual(fn.params, ["a", "b"])
        self.assertIsInstance(fn.body.statements[0], ast.ReturnStatement)

    def test_function_call(self):
        tree = parse("let result = add(1, 2);")
        call = tree.statements[0].initializer
        self.assertIsInstance(call, ast.FunctionCall)
        self.assertEqual(call.name, "add")
        self.assertEqual(len(call.arguments), 2)

    def test_logical_operators(self):
        tree = parse("let x = a && b || c;")
        expr = tree.statements[0].initializer
        # || has lower precedence than && so it should be at the root
        self.assertEqual(expr.operator, "||")
        self.assertEqual(expr.left.operator, "&&")

    def test_unary_operators(self):
        tree = parse("let x = -5; let y = !true;")
        neg = tree.statements[0].initializer
        self.assertIsInstance(neg, ast.UnaryExpression)
        self.assertEqual(neg.operator, "-")
        notb = tree.statements[1].initializer
        self.assertEqual(notb.operator, "!")

    def test_missing_semicolon_raises(self):
        with self.assertRaises(ParserError):
            parse("let x = 10\nprint(x);")

    def test_missing_paren_raises(self):
        with self.assertRaises(ParserError):
            parse("if (x > 5 { print(x); }")

    def test_missing_closing_brace_raises(self):
        with self.assertRaises(ParserError):
            parse("if (x > 5) { print(x); ")


if __name__ == "__main__":
    unittest.main()
