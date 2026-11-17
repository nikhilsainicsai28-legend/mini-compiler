"""
parser/parser.py
==================
Phase 2 of the pipeline: Syntax Analysis (Parsing).

This is a hand-written RECURSIVE DESCENT PARSER: one Python method per
grammar rule, calling each other exactly the way the grammar calls itself.
No parser generator (yacc/ANTLR/PLY/Lark) is used, per project
requirements.

------------------------------------------------------------------------
FINAL GRAMMAR (EBNF), lowest precedence first
------------------------------------------------------------------------
program        -> declaration* EOF

declaration    -> varDecl | funcDecl | statement

varDecl        -> "let" IDENTIFIER "=" expression ";"

funcDecl       -> "func" IDENTIFIER "(" parameters? ")" block
parameters     -> IDENTIFIER ( "," IDENTIFIER )*

statement      -> exprStmt
                 | printStmt
                 | ifStmt
                 | whileStmt
                 | returnStmt
                 | block

exprStmt       -> expression ";"
printStmt      -> "print" "(" expression ")" ";"
ifStmt         -> "if" "(" expression ")" block ( "else" block )?
whileStmt      -> "while" "(" expression ")" block
returnStmt     -> "return" expression? ";"
block          -> "{" declaration* "}"

expression     -> assignment
assignment     -> IDENTIFIER "=" assignment | logical_or
logical_or     -> logical_and ( "||" logical_and )*
logical_and    -> equality ( "&&" equality )*
equality       -> comparison ( ( "==" | "!=" ) comparison )*
comparison     -> term ( ( "<" | ">" | "<=" | ">=" ) term )*
term           -> factor ( ( "+" | "-" ) factor )*
factor         -> unary ( ( "*" | "/" | "%" ) unary )*
unary          -> ( "!" | "-" ) unary | call
call           -> primary ( "(" arguments? ")" )*
arguments      -> expression ( "," expression )*
primary        -> NUMBER | STRING | "true" | "false"
                 | IDENTIFIER | "(" expression ")"
------------------------------------------------------------------------

Design notes for the viva:
  * `assignment` is parsed as an EXPRESSION (like in C), which is why
    `x = x + 1;` and `let y = (x = 5);`-style code both fall naturally out
    of the same rule, instead of needing a separate "assignment statement"
    production that would conflict with expression statements.
  * Each binary-operator tier (logical_or, logical_and, equality,
    comparison, term, factor) is a separate method purely to ENCODE
    OPERATOR PRECEDENCE AND ASSOCIATIVITY directly in the call structure:
    the lower a rule sits in the grammar, the higher its precedence.
  * `call` allows a primary expression to be followed by `(...)`, which is
    how function calls like `add(1, 2)` are parsed.
"""

from lexer.token import TokenType
from ast_nodes import nodes as ast
from errors.errors import ParserError


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------
    # Token stream helpers
    # ------------------------------------------------------------------
    def _peek(self):
        return self.tokens[self.pos]

    def _previous(self):
        return self.tokens[self.pos - 1]

    def _at_end(self):
        return self._peek().type == TokenType.EOF

    def _advance(self):
        if not self._at_end():
            self.pos += 1
        return self._previous()

    def _check(self, ttype):
        if self._at_end():
            return ttype == TokenType.EOF
        return self._peek().type == ttype

    def _match(self, *types):
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _expect(self, ttype, message):
        if self._check(ttype):
            return self._advance()
        tok = self._peek()
        raise ParserError(message, tok.line, tok.column)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def parse(self):
        statements = []
        while not self._at_end():
            statements.append(self._declaration())
        return ast.Program(statements)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------
    def _declaration(self):
        if self._check(TokenType.LET):
            return self._var_declaration()
        if self._check(TokenType.FUNC):
            return self._function_declaration()
        return self._statement()

    def _var_declaration(self):
        let_tok = self._advance()  # consume 'let'
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected variable name after 'let'")
        self._expect(TokenType.ASSIGN, f"Expected '=' after variable name '{name_tok.lexeme}'")
        initializer = self._expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return ast.VarDeclaration(name_tok.lexeme, initializer, let_tok.line, let_tok.column)

    def _function_declaration(self):
        func_tok = self._advance()  # consume 'func'
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected function name after 'func'")
        self._expect(TokenType.LPAREN, f"Expected '(' after function name '{name_tok.lexeme}'")
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENTIFIER, "Expected parameter name").lexeme)
            while self._match(TokenType.COMMA):
                params.append(self._expect(TokenType.IDENTIFIER, "Expected parameter name").lexeme)
        self._expect(TokenType.RPAREN, "Expected ')' after parameter list")
        body = self._block()
        return ast.FunctionDeclaration(name_tok.lexeme, params, body, func_tok.line, func_tok.column)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------
    def _statement(self):
        if self._check(TokenType.PRINT):
            return self._print_statement()
        if self._check(TokenType.IF):
            return self._if_statement()
        if self._check(TokenType.WHILE):
            return self._while_statement()
        if self._check(TokenType.RETURN):
            return self._return_statement()
        if self._check(TokenType.LBRACE):
            return self._block()
        return self._expression_statement()

    def _print_statement(self):
        tok = self._advance()  # 'print'
        self._expect(TokenType.LPAREN, "Expected '(' after 'print'")
        expr = self._expression()
        self._expect(TokenType.RPAREN, "Expected ')' after print expression")
        self._expect(TokenType.SEMICOLON, "Expected ';' after print statement")
        return ast.PrintStatement(expr, tok.line, tok.column)

    def _if_statement(self):
        tok = self._advance()  # 'if'
        self._expect(TokenType.LPAREN, "Expected '(' after 'if'")
        condition = self._expression()
        self._expect(TokenType.RPAREN, "Expected ')' after if condition")
        then_branch = self._block()
        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._block()
        return ast.IfStatement(condition, then_branch, else_branch, tok.line, tok.column)

    def _while_statement(self):
        tok = self._advance()  # 'while'
        self._expect(TokenType.LPAREN, "Expected '(' after 'while'")
        condition = self._expression()
        self._expect(TokenType.RPAREN, "Expected ')' after while condition")
        body = self._block()
        return ast.WhileStatement(condition, body, tok.line, tok.column)

    def _return_statement(self):
        tok = self._advance()  # 'return'
        value = None
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after return statement")
        return ast.ReturnStatement(value, tok.line, tok.column)

    def _block(self):
        tok = self._expect(TokenType.LBRACE, "Expected '{' to start a block")
        statements = []
        while not self._check(TokenType.RBRACE) and not self._at_end():
            statements.append(self._declaration())
        self._expect(TokenType.RBRACE, "Expected '}' to close block")
        return ast.Block(statements, tok.line, tok.column)

    def _expression_statement(self):
        tok = self._peek()
        expr = self._expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after expression")
        return ast.ExpressionStatement(expr, tok.line, tok.column)

    # ------------------------------------------------------------------
    # Expressions (precedence climbing via recursive descent)
    # ------------------------------------------------------------------
    def _expression(self):
        return self._assignment()

    def _assignment(self):
        expr = self._logical_or()
        if self._check(TokenType.ASSIGN):
            eq_tok = self._advance()
            value = self._assignment()  # right-associative
            if isinstance(expr, ast.Identifier):
                return ast.Assignment(expr.name, value, eq_tok.line, eq_tok.column)
            raise ParserError("Invalid assignment target", eq_tok.line, eq_tok.column)
        return expr

    def _logical_or(self):
        expr = self._logical_and()
        while self._check(TokenType.OR):
            op = self._advance()
            right = self._logical_and()
            expr = ast.Logical(expr, op.lexeme, right, op.line, op.column)
        return expr

    def _logical_and(self):
        expr = self._equality()
        while self._check(TokenType.AND):
            op = self._advance()
            right = self._equality()
            expr = ast.Logical(expr, op.lexeme, right, op.line, op.column)
        return expr

    def _equality(self):
        expr = self._comparison()
        while self._check(TokenType.EQ) or self._check(TokenType.NEQ):
            op = self._advance()
            right = self._comparison()
            expr = ast.BinaryExpression(expr, op.lexeme, right, op.line, op.column)
        return expr

    def _comparison(self):
        expr = self._term()
        while self._peek().type in (TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op = self._advance()
            right = self._term()
            expr = ast.BinaryExpression(expr, op.lexeme, right, op.line, op.column)
        return expr

    def _term(self):
        expr = self._factor()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance()
            right = self._factor()
            expr = ast.BinaryExpression(expr, op.lexeme, right, op.line, op.column)
        return expr

    def _factor(self):
        expr = self._unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._advance()
            right = self._unary()
            expr = ast.BinaryExpression(expr, op.lexeme, right, op.line, op.column)
        return expr

    def _unary(self):
        if self._peek().type in (TokenType.NOT, TokenType.MINUS):
            op = self._advance()
            operand = self._unary()
            return ast.UnaryExpression(op.lexeme, operand, op.line, op.column)
        return self._call()

    def _call(self):
        expr = self._primary()
        while self._check(TokenType.LPAREN):
            expr = self._finish_call(expr)
        return expr

    def _finish_call(self, callee):
        paren_tok = self._advance()  # consume '('
        if not isinstance(callee, ast.Identifier):
            raise ParserError("Only functions can be called", paren_tok.line, paren_tok.column)
        arguments = []
        if not self._check(TokenType.RPAREN):
            arguments.append(self._expression())
            while self._match(TokenType.COMMA):
                arguments.append(self._expression())
        self._expect(TokenType.RPAREN, "Expected ')' after arguments")
        return ast.FunctionCall(callee.name, arguments, paren_tok.line, paren_tok.column)

    def _primary(self):
        tok = self._peek()

        if self._match(TokenType.NUMBER):
            return ast.Literal(self._previous().value, tok.line, tok.column)
        if self._match(TokenType.STRING):
            return ast.Literal(self._previous().value, tok.line, tok.column)
        if self._match(TokenType.TRUE):
            return ast.Literal(True, tok.line, tok.column)
        if self._match(TokenType.FALSE):
            return ast.Literal(False, tok.line, tok.column)
        if self._match(TokenType.IDENTIFIER):
            return ast.Identifier(self._previous().lexeme, tok.line, tok.column)
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        raise ParserError(f"Unexpected token '{tok.lexeme or tok.type.name}'", tok.line, tok.column)
