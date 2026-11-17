"""
ir/instructions.py
=====================
Defines the Three Address Code (TAC) instruction set used as MiniLang's
Intermediate Representation (IR).

"Three address code" means every instruction has AT MOST three operands
(one result + two sources), e.g.

    t1 = a + b

This is the classic IR taught in compiler courses because it sits halfway
between a tree (AST) and real machine code: it's flat (a simple list of
instructions, easy for a VM to step through) but still symbolic (variable
names, not registers/memory addresses).

Operands
--------
An instruction's operands are either:
    Const(value)  - a literal constant, e.g. Const(10), Const("hi")
    VarRef(name)  - a reference to a variable OR a compiler-generated
                    temporary (t1, t2, ...) - both live in the same
                    "variable environment" at execution time, so we don't
                    need to distinguish them at the IR level.

Instructions
------------
    Assign(dest, src)                 dest = src
    BinOp(dest, op, left, right)      dest = left op right
    UnaryOp(dest, op, operand)        dest = op operand
    Print(value)                      print(value)
    Label(name)                       name:
    Jump(label)                       goto label
    JumpIfFalse(cond, label)          if not cond: goto label
    FuncBegin(name, params)           marks start of a function body
    FuncEnd(name)                     marks end of a function body
    Param(value)                      push one argument for the next Call
    Call(dest, name, argcount)        dest = call name (argcount args)
    Return(value)                     return value   (value may be None)
"""


# ----------------------------------------------------------------------
# Operands
# ----------------------------------------------------------------------
class Operand:
    pass


class Const(Operand):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        if isinstance(self.value, str):
            return f'"{self.value}"'
        return repr(self.value)


class VarRef(Operand):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name


def fmt(operand):
    """Render an Operand (or raw literal) for pretty-printing."""
    if isinstance(operand, Operand):
        return repr(operand)
    return repr(operand)


# ----------------------------------------------------------------------
# Instructions
# ----------------------------------------------------------------------
class Instruction:
    pass


class Assign(Instruction):
    def __init__(self, dest, src):
        self.dest = dest
        self.src = src

    def __repr__(self):
        return f"{self.dest} = {fmt(self.src)}"


class BinOp(Instruction):
    def __init__(self, dest, op, left, right):
        self.dest = dest
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        return f"{self.dest} = {fmt(self.left)} {self.op} {fmt(self.right)}"


class UnaryOp(Instruction):
    def __init__(self, dest, op, operand):
        self.dest = dest
        self.op = op
        self.operand = operand

    def __repr__(self):
        return f"{self.dest} = {self.op}{fmt(self.operand)}"


class Print(Instruction):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"print {fmt(self.value)}"


class Label(Instruction):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"{self.name}:"


class Jump(Instruction):
    def __init__(self, label):
        self.label = label

    def __repr__(self):
        return f"goto {self.label}"


class JumpIfFalse(Instruction):
    def __init__(self, cond, label):
        self.cond = cond
        self.label = label

    def __repr__(self):
        return f"ifFalse {fmt(self.cond)} goto {self.label}"


class FuncBegin(Instruction):
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def __repr__(self):
        return f"func {self.name}({', '.join(self.params)}):"


class FuncEnd(Instruction):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"endfunc {self.name}"


class Param(Instruction):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"param {fmt(self.value)}"


class Call(Instruction):
    def __init__(self, dest, name, argcount):
        self.dest = dest      # VarRef of temp receiving the result, or None
        self.name = name
        self.argcount = argcount

    def __repr__(self):
        prefix = f"{self.dest} = " if self.dest else ""
        return f"{prefix}call {self.name}, {self.argcount}"


class Return(Instruction):
    def __init__(self, value):
        self.value = value    # Operand or None

    def __repr__(self):
        return f"return {fmt(self.value)}" if self.value is not None else "return"
