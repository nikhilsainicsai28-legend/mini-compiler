"""
ast_nodes/nodes.py
====================
Defines every Abstract Syntax Tree (AST) node produced by the Parser.

NOTE ON PACKAGE NAME: this package is called `ast_nodes` rather than `ast`
(even though the project spec suggests an `ast/` folder) because Python's
standard library already has a built-in module named `ast`. Naming our own
package `ast` would shadow the real one, which is a common beginner
mistake worth avoiding - and worth mentioning in a viva if asked!

Design: each node is a small, self-describing class. Every node keeps the
`line`/`column` of the token it started from so the Semantic Analyzer and
VM can report accurate error locations later.

We use plain Python classes (not @dataclass) so the constructors can stay
explicit and easy to read for students unfamiliar with dataclasses.
"""


class Node:
    """Base class for all AST nodes."""
    line = None
    column = None


# ----------------------------------------------------------------------
# Program / top level
# ----------------------------------------------------------------------
class Program(Node):
    def __init__(self, statements):
        self.statements = statements


# ----------------------------------------------------------------------
# Statements
# ----------------------------------------------------------------------
class VarDeclaration(Node):
    """let IDENTIFIER = expression ;"""
    def __init__(self, name, initializer, line, column):
        self.name = name
        self.initializer = initializer
        self.line = line
        self.column = column


class Block(Node):
    """{ statement* }"""
    def __init__(self, statements, line=None, column=None):
        self.statements = statements
        self.line = line
        self.column = column


class IfStatement(Node):
    def __init__(self, condition, then_branch, else_branch, line, column):
        self.condition = condition
        self.then_branch = then_branch   # Block
        self.else_branch = else_branch   # Block or None
        self.line = line
        self.column = column


class WhileStatement(Node):
    def __init__(self, condition, body, line, column):
        self.condition = condition
        self.body = body                 # Block
        self.line = line
        self.column = column


class FunctionDeclaration(Node):
    def __init__(self, name, params, body, line, column):
        self.name = name
        self.params = params             # list[str]
        self.body = body                 # Block
        self.line = line
        self.column = column


class ReturnStatement(Node):
    def __init__(self, value, line, column):
        self.value = value               # Expression or None
        self.line = line
        self.column = column


class PrintStatement(Node):
    def __init__(self, expression, line, column):
        self.expression = expression
        self.line = line
        self.column = column


class ExpressionStatement(Node):
    """An expression used as a statement, e.g. `x = x + 1;` or `foo();`"""
    def __init__(self, expression, line, column):
        self.expression = expression
        self.line = line
        self.column = column


# ----------------------------------------------------------------------
# Expressions
# ----------------------------------------------------------------------
class Assignment(Node):
    """IDENTIFIER = expression"""
    def __init__(self, name, value, line, column):
        self.name = name
        self.value = value
        self.line = line
        self.column = column


class Logical(Node):
    """left (&& | ||) right -- kept separate from BinaryExpression so the
    IR generator / VM can short-circuit if desired."""
    def __init__(self, left, operator, right, line, column):
        self.left = left
        self.operator = operator
        self.right = right
        self.line = line
        self.column = column


class BinaryExpression(Node):
    def __init__(self, left, operator, right, line, column):
        self.left = left
        self.operator = operator
        self.right = right
        self.line = line
        self.column = column


class UnaryExpression(Node):
    def __init__(self, operator, operand, line, column):
        self.operator = operator
        self.operand = operand
        self.line = line
        self.column = column


class Literal(Node):
    """A constant value: number, string or boolean."""
    def __init__(self, value, line, column):
        self.value = value
        self.line = line
        self.column = column


class Identifier(Node):
    def __init__(self, name, line, column):
        self.name = name
        self.line = line
        self.column = column


class FunctionCall(Node):
    def __init__(self, name, arguments, line, column):
        self.name = name
        self.arguments = arguments       # list[Expression]
        self.line = line
        self.column = column
