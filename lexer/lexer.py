"""
lexer/lexer.py
================
Phase 1 of the pipeline: Lexical Analysis.

The Lexer reads the raw MiniLang source code ONE CHARACTER AT A TIME and
groups characters into Tokens (see lexer/token.py). This is a classic
hand-rolled scanner using the "maximal munch" principle: at every point it
consumes the longest possible token (e.g. "<=" is read as one token, not
"<" followed by "="; "12.5" is read as one NUMBER, not "12", ".", "5").

Responsibilities:
    - Skip whitespace.
    - Skip // line comments and /* block comments */.
    - Recognize keywords vs plain identifiers.
    - Recognize integer and float literals.
    - Recognize string literals ("...") with basic escape sequences.
    - Recognize every operator and delimiter in the language.
    - Track line/column for every token (for error messages).
    - Raise LexicalError with a precise location on any unexpected character
      or malformed literal (e.g. unterminated string).
"""

from lexer.token import Token, TokenType, KEYWORDS
from errors.errors import LexicalError


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0            # index into self.source
        self.line = 1
        self.column = 1
        self.tokens = []

    # ------------------------------------------------------------------
    # Low level character helpers
    # ------------------------------------------------------------------
    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= len(self.source):
            return "\0"
        return self.source[idx]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _match(self, expected: str) -> bool:
        """If the next character equals `expected`, consume it and return True."""
        if self._at_end() or self.source[self.pos] != expected:
            return False
        self._advance()
        return True

    def _make_token(self, type_: TokenType, lexeme: str, value, line: int, column: int) -> Token:
        return Token(type_, lexeme, value, line, column)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def tokenize(self):
        """Scan the whole source and return a list of Tokens ending in EOF."""
        while not self._at_end():
            self._skip_whitespace_and_comments()
            if self._at_end():
                break
            self._scan_token()

        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    # ------------------------------------------------------------------
    # Whitespace / comments
    # ------------------------------------------------------------------
    def _skip_whitespace_and_comments(self):
        while not self._at_end():
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                # line comment: skip to end of line
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
            elif ch == "/" and self._peek(1) == "*":
                self._skip_block_comment()
            else:
                break

    def _skip_block_comment(self):
        start_line, start_col = self.line, self.column
        self._advance()  # consume '/'
        self._advance()  # consume '*'
        while True:
            if self._at_end():
                raise LexicalError("Unterminated block comment", start_line, start_col)
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                return
            self._advance()

    # ------------------------------------------------------------------
    # Token scanning
    # ------------------------------------------------------------------
    def _scan_token(self):
        start_line, start_col = self.line, self.column
        ch = self._advance()

        # Identifiers / keywords
        if ch.isalpha() or ch == "_":
            self._scan_identifier(ch, start_line, start_col)
            return

        # Numbers
        if ch.isdigit():
            self._scan_number(ch, start_line, start_col)
            return

        # Strings
        if ch == '"':
            self._scan_string(start_line, start_col)
            return

        # Operators & delimiters
        simple = {
            "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR,
            "%": TokenType.PERCENT, "(": TokenType.LPAREN, ")": TokenType.RPAREN,
            "{": TokenType.LBRACE, "}": TokenType.RBRACE, ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
        }
        if ch in simple:
            self.tokens.append(self._make_token(simple[ch], ch, None, start_line, start_col))
            return

        if ch == "/":
            self.tokens.append(self._make_token(TokenType.SLASH, "/", None, start_line, start_col))
            return

        if ch == "=":
            if self._match("="):
                self.tokens.append(self._make_token(TokenType.EQ, "==", None, start_line, start_col))
            else:
                self.tokens.append(self._make_token(TokenType.ASSIGN, "=", None, start_line, start_col))
            return

        if ch == "!":
            if self._match("="):
                self.tokens.append(self._make_token(TokenType.NEQ, "!=", None, start_line, start_col))
            else:
                self.tokens.append(self._make_token(TokenType.NOT, "!", None, start_line, start_col))
            return

        if ch == "<":
            if self._match("="):
                self.tokens.append(self._make_token(TokenType.LE, "<=", None, start_line, start_col))
            else:
                self.tokens.append(self._make_token(TokenType.LT, "<", None, start_line, start_col))
            return

        if ch == ">":
            if self._match("="):
                self.tokens.append(self._make_token(TokenType.GE, ">=", None, start_line, start_col))
            else:
                self.tokens.append(self._make_token(TokenType.GT, ">", None, start_line, start_col))
            return

        if ch == "&":
            if self._match("&"):
                self.tokens.append(self._make_token(TokenType.AND, "&&", None, start_line, start_col))
                return
            raise LexicalError(f"Unexpected character '&' (did you mean '&&'?)", start_line, start_col)

        if ch == "|":
            if self._match("|"):
                self.tokens.append(self._make_token(TokenType.OR, "||", None, start_line, start_col))
                return
            raise LexicalError(f"Unexpected character '|' (did you mean '||'?)", start_line, start_col)

        # Anything else is an error
        raise LexicalError(f"Unexpected character '{ch}'", start_line, start_col)

    def _scan_identifier(self, first_char, start_line, start_col):
        chars = [first_char]
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            chars.append(self._advance())
        text = "".join(chars)

        if text in KEYWORDS:
            ttype = KEYWORDS[text]
            if ttype == TokenType.TRUE:
                self.tokens.append(self._make_token(ttype, text, True, start_line, start_col))
            elif ttype == TokenType.FALSE:
                self.tokens.append(self._make_token(ttype, text, False, start_line, start_col))
            else:
                self.tokens.append(self._make_token(ttype, text, None, start_line, start_col))
        else:
            self.tokens.append(self._make_token(TokenType.IDENTIFIER, text, None, start_line, start_col))

    def _scan_number(self, first_char, start_line, start_col):
        chars = [first_char]
        is_float = False

        while not self._at_end() and self._peek().isdigit():
            chars.append(self._advance())

        # Fractional part
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            chars.append(self._advance())  # consume '.'
            while not self._at_end() and self._peek().isdigit():
                chars.append(self._advance())

        text = "".join(chars)

        # Reject malformed numbers like "10.5.3" or "10abc"
        if not self._at_end() and (self._peek().isalpha() or self._peek() == "_"):
            bad = [text]
            while not self._at_end() and (self._peek().isalnum() or self._peek() == "_" or self._peek() == "."):
                bad.append(self._advance())
            raise LexicalError(f"Invalid number literal '{''.join(bad)}'", start_line, start_col)

        value = float(text) if is_float else int(text)
        self.tokens.append(self._make_token(TokenType.NUMBER, text, value, start_line, start_col))

    def _scan_string(self, start_line, start_col):
        chars = []
        while True:
            if self._at_end():
                raise LexicalError("Unterminated string literal", start_line, start_col)
            ch = self._peek()
            if ch == '"':
                self._advance()
                break
            if ch == "\n":
                raise LexicalError("Unterminated string literal (newline before closing quote)",
                                    start_line, start_col)
            if ch == "\\":
                self._advance()  # consume backslash
                if self._at_end():
                    raise LexicalError("Unterminated string literal", start_line, start_col)
                esc = self._advance()
                mapping = {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}
                if esc in mapping:
                    chars.append(mapping[esc])
                else:
                    raise LexicalError(f"Unknown escape sequence '\\{esc}'", self.line, self.column)
            else:
                chars.append(self._advance())

        text = "".join(chars)
        self.tokens.append(self._make_token(TokenType.STRING, text, text, start_line, start_col))
