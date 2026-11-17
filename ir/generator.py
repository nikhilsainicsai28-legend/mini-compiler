"""
ir/generator.py
=================
Phase 5 of the pipeline: Intermediate Representation generation.

Walks the (semantically checked) AST and emits a flat list of Three
Address Code instructions (see ir/instructions.py).

The key idea for expression code generation is:

    _gen_expression(node) -> Operand

Every expression node, once "generated", collapses into a single Operand
(a Const or a VarRef) that later instructions can refer to. Compound
expressions introduce a fresh TEMPORARY variable (t1, t2, ...) to hold
their result, e.g.:

    let result = (a + b) * c;

        t1 = a + b
        t2 = t1 * c
        result = t2

while simple "leaf" expressions (a bare literal or identifier) are
returned directly with NO temporary, which is why

    let y = x;

generates just

        y = x

instead of a wasteful `t1 = x; y = t1;`.

Control flow (if/while) is lowered using LABELS and conditional jumps,
exactly as a simple stack machine / bytecode VM would expect:

    if (cond) { A } else { B }

        <code for cond>          -> c
        ifFalse c goto Lelse1
        <code for A>
        goto Lend1
    Lelse1:
        <code for B>
    Lend1:

Functions are lowered as a labelled region of instructions bracketed by
FuncBegin/FuncEnd; the VM SKIPS this region during normal top-to-bottom
execution and only jumps into it when a Call instruction is executed
(see vm/interpreter.py).
"""

from ast_nodes import nodes as ast
from ir.instructions import (
    Const, VarRef, Assign, BinOp, UnaryOp, Print, Label, Jump, JumpIfFalse,
    FuncBegin, FuncEnd, Param, Call, Return,
)


class IRGenerator:
    def __init__(self):
        self.instructions = []
        self._temp_count = 0
        self._label_count = 0

    # ------------------------------------------------------------------
    def generate(self, program: ast.Program):
        self.instructions = []
        for stmt in program.statements:
            self._gen_statement(stmt)
        return self.instructions

    def _emit(self, instr):
        self.instructions.append(instr)

    def _new_temp(self):
        self._temp_count += 1
        return f"t{self._temp_count}"

    def _new_label(self, hint):
        self._label_count += 1
        return f"{hint}{self._label_count}"

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------
    def _gen_statement(self, node):
        if isinstance(node, ast.VarDeclaration):
            operand = self._gen_expression(node.initializer)
            self._emit(Assign(node.name, operand))

        elif isinstance(node, ast.Block):
            for s in node.statements:
                self._gen_statement(s)

        elif isinstance(node, ast.IfStatement):
            self._gen_if(node)

        elif isinstance(node, ast.WhileStatement):
            self._gen_while(node)

        elif isinstance(node, ast.FunctionDeclaration):
            self._gen_function(node)

        elif isinstance(node, ast.ReturnStatement):
            operand = self._gen_expression(node.value) if node.value is not None else None
            self._emit(Return(operand))

        elif isinstance(node, ast.PrintStatement):
            operand = self._gen_expression(node.expression)
            self._emit(Print(operand))

        elif isinstance(node, ast.ExpressionStatement):
            self._gen_expression(node.expression)  # result discarded

        else:
            raise NotImplementedError(f"IR generation not implemented for {type(node).__name__}")

    def _gen_if(self, node):
        cond = self._gen_expression(node.condition)
        else_label = self._new_label("Lelse")
        end_label = self._new_label("Lend")

        self._emit(JumpIfFalse(cond, else_label))
        self._gen_statement(node.then_branch)
        self._emit(Jump(end_label))
        self._emit(Label(else_label))
        if node.else_branch is not None:
            self._gen_statement(node.else_branch)
        self._emit(Label(end_label))

    def _gen_while(self, node):
        start_label = self._new_label("Lstart")
        end_label = self._new_label("Lend")

        self._emit(Label(start_label))
        cond = self._gen_expression(node.condition)
        self._emit(JumpIfFalse(cond, end_label))
        self._gen_statement(node.body)
        self._emit(Jump(start_label))
        self._emit(Label(end_label))

    def _gen_function(self, node):
        self._emit(FuncBegin(node.name, node.params))
        for s in node.body.statements:
            self._gen_statement(s)
        # Implicit `return` in case the function body falls off the end
        # without an explicit return statement.
        self._emit(Return(None))
        self._emit(FuncEnd(node.name))

    # ------------------------------------------------------------------
    # Expressions -> Operand (Const or VarRef)
    # ------------------------------------------------------------------
    def _gen_expression(self, node):
        if isinstance(node, ast.Literal):
            return Const(node.value)

        if isinstance(node, ast.Identifier):
            return VarRef(node.name)

        if isinstance(node, ast.Assignment):
            operand = self._gen_expression(node.value)
            self._emit(Assign(node.name, operand))
            return VarRef(node.name)

        if isinstance(node, ast.UnaryExpression):
            operand = self._gen_expression(node.operand)
            dest = self._new_temp()
            self._emit(UnaryOp(dest, node.operator, operand))
            return VarRef(dest)

        if isinstance(node, (ast.BinaryExpression, ast.Logical)):
            left = self._gen_expression(node.left)
            right = self._gen_expression(node.right)
            dest = self._new_temp()
            self._emit(BinOp(dest, node.operator, left, right))
            return VarRef(dest)

        if isinstance(node, ast.FunctionCall):
            arg_operands = [self._gen_expression(arg) for arg in node.arguments]
            for operand in arg_operands:
                self._emit(Param(operand))
            dest = self._new_temp()
            self._emit(Call(dest, node.name, len(arg_operands)))
            return VarRef(dest)

        raise NotImplementedError(f"IR generation not implemented for {type(node).__name__}")


def format_ir(instructions):
    """Pretty-print a list of IR instructions, indenting everything that
    is not a Label/FuncBegin/FuncEnd for readability."""
    lines = []
    for instr in instructions:
        from ir.instructions import Label as L, FuncBegin as FB, FuncEnd as FE
        if isinstance(instr, (L, FB, FE)):
            lines.append(repr(instr))
        else:
            lines.append("    " + repr(instr))
    return "\n".join(lines)
