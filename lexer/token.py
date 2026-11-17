"""
lexer/token.py
===============
Defines the Token class and every TokenType the MiniLang lexer can produce.

A *lexeme* is the raw substring from the source code (e.g. "10", "x", "+").
A *token* is the classified unit built from a lexeme: it records what KIND
of lexeme it is (TokenType), the literal Python value it represents where
relevant (e.g. int 10 instead of the string "10"), and where it appeared
in the source (line, column) so later phases can produce good error
messages.
"""

from enum import Enum, auto


class TokenType(Enum):
    # Literals
    NUMBER = auto()          # 10, 3.14
    STRING = auto()          # "hello"
    IDENTIFIER = auto()      # x, sum, factorial

    # Keywords
    LET = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FUNC = auto()
    RETURN = auto()
    PRINT = auto()
    TRUE = auto()
    FALSE = auto()

    # Arithmetic operators
    PLUS = auto()            # +
    MINUS = auto()           # -
    STAR = auto()            # *
    SLASH = auto()           # /
    PERCENT = auto()         # %

    # Comparison operators
    EQ = auto()               # ==
    NEQ = auto()               # !=
    LT = auto()               # <
    GT = auto()               # >
    LE = auto()               # <=
    GE = auto()               # >=

    # Logical operators
    AND = auto()               # &&
    OR = auto()               # ||
    NOT = auto()               # !

    # Assignment
    ASSIGN = auto()           # =

    # Delimiters
    LPAREN = auto()           # (
    RPAREN = auto()           # )
    LBRACE = auto()           # {
    RBRACE = auto()           # }
    COMMA = auto()             # ,
    SEMICOLON = auto()         # ;

    # Special
    EOF = auto()


# Reserved words -> TokenType. Anything else that looks like an identifier
# stays an IDENTIFIER.
KEYWORDS = {
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "func": TokenType.FUNC,
    "return": TokenType.RETURN,
    "print": TokenType.PRINT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
}


class Token:
    """A single classified unit of source code."""

    __slots__ = ("type", "lexeme", "value", "line", "column")

    def __init__(self, type_: TokenType, lexeme: str, value, line: int, column: int):
        self.type = type_
        self.lexeme = lexeme      # raw text as it appeared in the source
        self.value = value        # converted literal value (int/float/str/bool) or None
        self.line = line
        self.column = column

    def __repr__(self):
        if self.value is not None and self.type in (TokenType.NUMBER, TokenType.STRING,
                                                      TokenType.TRUE, TokenType.FALSE):
            return f"{self.type.name}({self.value!r})"
        if self.type == TokenType.IDENTIFIER:
            return f"IDENTIFIER({self.lexeme})"
        if self.type == TokenType.EOF:
            return "EOF"
        return f"{self.type.name}({self.lexeme})"

    def __str__(self):
        return self.__repr__()
