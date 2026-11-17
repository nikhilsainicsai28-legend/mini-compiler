"""
utils/ast_printer.py
======================
Walks an AST and prints it as an indented tree, e.g. for:

    let x = 10 + 20;

it prints:

    VarDeclaration: x
      BinaryExpression: +
        Literal: 10
        Literal: 20

This is a simple recursive tree-walker (a preview of how later phases like
the Semantic Analyzer and IR Generator will also walk the tree).
"""

from ast_nodes import nodes as ast


def print_ast(node, indent=0):
    lines = []
    _print_node(node, indent, lines)
    return "\n".join(lines)


def _pad(indent):
    return "  " * indent


def _print_node(node, indent, lines):
    if isinstance(node, ast.Program):
        lines.append(f"{_pad(indent)}Program")
        for stmt in node.statements:
            _print_node(stmt, indent + 1, lines)

    elif isinstance(node, ast.VarDeclaration):
        lines.append(f"{_pad(indent)}VarDeclaration: {node.name}")
        _print_node(node.initializer, indent + 1, lines)

    elif isinstance(node, ast.Block):
        lines.append(f"{_pad(indent)}Block")
        for stmt in node.statements:
            _print_node(stmt, indent + 1, lines)

    elif isinstance(node, ast.IfStatement):
        lines.append(f"{_pad(indent)}IfStatement")
        lines.append(f"{_pad(indent + 1)}Condition:")
        _print_node(node.condition, indent + 2, lines)
        lines.append(f"{_pad(indent + 1)}Then:")
        _print_node(node.then_branch, indent + 2, lines)
        if node.else_branch is not None:
            lines.append(f"{_pad(indent + 1)}Else:")
            _print_node(node.else_branch, indent + 2, lines)

    elif isinstance(node, ast.WhileStatement):
        lines.append(f"{_pad(indent)}WhileStatement")
        lines.append(f"{_pad(indent + 1)}Condition:")
        _print_node(node.condition, indent + 2, lines)
        lines.append(f"{_pad(indent + 1)}Body:")
        _print_node(node.body, indent + 2, lines)

    elif isinstance(node, ast.FunctionDeclaration):
        params = ", ".join(node.params)
        lines.append(f"{_pad(indent)}FunctionDeclaration: {node.name}({params})")
        _print_node(node.body, indent + 1, lines)

    elif isinstance(node, ast.ReturnStatement):
        lines.append(f"{_pad(indent)}ReturnStatement")
        if node.value is not None:
            _print_node(node.value, indent + 1, lines)

    elif isinstance(node, ast.PrintStatement):
        lines.append(f"{_pad(indent)}PrintStatement")
        _print_node(node.expression, indent + 1, lines)

    elif isinstance(node, ast.ExpressionStatement):
        lines.append(f"{_pad(indent)}ExpressionStatement")
        _print_node(node.expression, indent + 1, lines)

    elif isinstance(node, ast.Assignment):
        lines.append(f"{_pad(indent)}Assignment: {node.name}")
        _print_node(node.value, indent + 1, lines)

    elif isinstance(node, (ast.BinaryExpression, ast.Logical)):
        kind = "Logical" if isinstance(node, ast.Logical) else "BinaryExpression"
        lines.append(f"{_pad(indent)}{kind}: {node.operator}")
        _print_node(node.left, indent + 1, lines)
        _print_node(node.right, indent + 1, lines)

    elif isinstance(node, ast.UnaryExpression):
        lines.append(f"{_pad(indent)}UnaryExpression: {node.operator}")
        _print_node(node.operand, indent + 1, lines)

    elif isinstance(node, ast.Literal):
        lines.append(f"{_pad(indent)}Literal: {node.value!r}")

    elif isinstance(node, ast.Identifier):
        lines.append(f"{_pad(indent)}Identifier: {node.name}")

    elif isinstance(node, ast.FunctionCall):
        lines.append(f"{_pad(indent)}FunctionCall: {node.name}")
        for arg in node.arguments:
            _print_node(arg, indent + 1, lines)

    else:
        lines.append(f"{_pad(indent)}<unknown node {type(node).__name__}>")
