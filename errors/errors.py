"""
errors/errors.py
=================
Centralised error types for MiniLang.

Every phase of the compiler (lexer, parser, semantic analyzer, VM) raises
one of these exceptions instead of a bare Python exception. This lets
main.py catch a single family of errors and print a consistent,
well-formatted diagnostic such as:

    Semantic Error at line 5, column 3:
    Variable 'x' is not defined

Keeping all error classes in one place also makes it easy to explain in a
viva: "our compiler has one error class per phase, all derived from a
common MiniLangError base class."
"""


class MiniLangError(Exception):
    """Base class for every error the MiniLang toolchain can raise."""

    #: Human readable phase name, overridden by subclasses.
    phase = "Error"

    def __init__(self, message: str, line: int = None, column: int = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(self.format())

    def format(self) -> str:
        if self.line is not None and self.column is not None:
            location = f"line {self.line}, column {self.column}"
        elif self.line is not None:
            location = f"line {self.line}"
        else:
            location = "unknown location"
        return f"{self.phase} at {location}:\n{self.message}"

    def __str__(self):
        return self.format()


class LexicalError(MiniLangError):
    """Raised by the Lexer for malformed characters, unterminated strings, etc."""
    phase = "Lexical Error"


class ParserError(MiniLangError):
    """Raised by the Parser when the token stream does not match the grammar.

    NOTE: named ParserError (not SyntaxError) so we don't shadow the
    built-in Python SyntaxError class.
    """
    phase = "Syntax Error"


class SemanticError(MiniLangError):
    """Raised by the Semantic Analyzer: undefined names, type errors, etc."""
    phase = "Semantic Error"


class MiniLangRuntimeError(MiniLangError):
    """Raised by the Virtual Machine while executing IR (e.g. division by zero)."""
    phase = "Runtime Error"
