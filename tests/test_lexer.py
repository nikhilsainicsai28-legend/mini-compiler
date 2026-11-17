"""
tests/test_lexer.py
=====================
Unit tests for Phase 1 (Lexical Analysis).
Run with:  python -m unittest tests.test_lexer -v
"""

import unittest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lexer.lexer import Lexer
from lexer.token import TokenType
from errors.errors import LexicalError


class TestLexer(unittest.TestCase):

    def _types(self, source):
        tokens = Lexer(source).tokenize()
        return [t.type for t in tokens]

    def test_simple_declaration(self):
        types = self._types("let x = 10 + 20;")
        expected = [
            TokenType.LET, TokenType.IDENTIFIER, TokenType.ASSIGN,
            TokenType.NUMBER, TokenType.PLUS, TokenType.NUMBER,
            TokenType.SEMICOLON, TokenType.EOF,
        ]
        self.assertEqual(types, expected)

    def test_float_literal(self):
        tokens = Lexer("let pi = 3.14;").tokenize()
        num = tokens[3]
        self.assertEqual(num.type, TokenType.NUMBER)
        self.assertEqual(num.value, 3.14)
        self.assertIsInstance(num.value, float)

    def test_integer_literal_is_int(self):
        tokens = Lexer("let x = 42;").tokenize()
        self.assertIsInstance(tokens[3].value, int)

    def test_string_literal(self):
        tokens = Lexer('let s = "hello world";').tokenize()
        self.assertEqual(tokens[3].type, TokenType.STRING)
        self.assertEqual(tokens[3].value, "hello world")

    def test_boolean_literals(self):
        tokens = Lexer("let a = true; let b = false;").tokenize()
        self.assertEqual(tokens[3].type, TokenType.TRUE)
        self.assertEqual(tokens[3].value, True)

    def test_keywords_recognized(self):
        types = self._types("if else while func return print")
        self.assertEqual(types[:-1], [
            TokenType.IF, TokenType.ELSE, TokenType.WHILE,
            TokenType.FUNC, TokenType.RETURN, TokenType.PRINT,
        ])

    def test_identifier_not_keyword(self):
        tokens = Lexer("let iffy = 1;").tokenize()
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].lexeme, "iffy")

    def test_two_char_operators(self):
        types = self._types("== != <= >= && ||")
        self.assertEqual(types[:-1], [
            TokenType.EQ, TokenType.NEQ, TokenType.LE,
            TokenType.GE, TokenType.AND, TokenType.OR,
        ])

    def test_single_char_operators(self):
        types = self._types("+ - * / % = < > !")
        self.assertEqual(types[:-1], [
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
            TokenType.PERCENT, TokenType.ASSIGN, TokenType.LT, TokenType.GT,
            TokenType.NOT,
        ])

    def test_line_comment_skipped(self):
        types = self._types("let x = 1; // this is a comment\nlet y = 2;")
        self.assertNotIn(TokenType.SLASH, types)

    def test_block_comment_skipped(self):
        types = self._types("let x = /* comment */ 1;")
        self.assertEqual(types, [
            TokenType.LET, TokenType.IDENTIFIER, TokenType.ASSIGN,
            TokenType.NUMBER, TokenType.SEMICOLON, TokenType.EOF,
        ])

    def test_line_and_column_tracking(self):
        tokens = Lexer("let x = 1;\nlet y = 2;").tokenize()
        # 'y' is on line 2
        y_token = next(t for t in tokens if t.lexeme == "y")
        self.assertEqual(y_token.line, 2)

    def test_invalid_character_raises(self):
        with self.assertRaises(LexicalError):
            Lexer("let x = @;").tokenize()

    def test_unterminated_string_raises(self):
        with self.assertRaises(LexicalError):
            Lexer('let x = "unterminated;').tokenize()

    def test_unterminated_string_with_backslash_raises(self):
        with self.assertRaises(LexicalError):
            Lexer('let x = "unterminated\\').tokenize()

    def test_unexpected_char_error_location(self):
        try:
            Lexer("let y = @;").tokenize()
            self.fail("Expected LexicalError")
        except LexicalError as e:
            self.assertEqual(e.line, 1)
            self.assertEqual(e.column, 9)


if __name__ == "__main__":
    unittest.main()
