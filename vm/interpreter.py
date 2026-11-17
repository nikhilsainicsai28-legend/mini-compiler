"""
vm/interpreter.py
====================
Phase 6 of the pipeline: Execution (a simple Virtual Machine / IR
interpreter, used here instead of generating real machine code).

The VM executes the flat list of IR instructions with a single program
counter (pc), the same way a CPU executes machine instructions:

    1. Look at instructions[pc].
    2. Do whatever it says.
    3. Move pc forward, or jump it somewhere else (for Jump/Call/Return).

Two preprocessing maps make this simple:
    label_map  : label name -> instruction index      (for goto)
    func_info  : function name -> {start, end, params} (for calls)

FUNCTIONS AND SKIPPING
-----------------------
Function bodies are lowered between FuncBegin/FuncEnd (see ir/generator.py)
but sit inline in the instruction list, in the order they were declared.
During ordinary top-to-bottom ("straight line") execution the VM must NOT
execute a function's body - it should only run when explicitly called.
So whenever the VM's pc naturally reaches a FuncBegin instruction, it just
jumps straight past the matching FuncEnd. The only other way to enter a
function body is via a Call instruction, which jumps pc to the body's
start and pushes a CALL FRAME so execution can return correctly
afterwards - this is exactly how a real call stack works, and this is
also what makes RECURSION (e.g. factorial) work: every call gets its own
fresh, independent local environment (dict of name -> value), and the
previous frame is preserved on `call_stack` until the callee returns.

SCOPING MODEL: to keep the VM simple to explain, a called function's
environment does NOT see the caller's local variables (no closures) - it
only has its parameters and whatever it assigns locally, plus it can call
other functions (including itself). Top-level code runs in one shared
"global" environment.
"""

from ir.instructions import (
    Const, VarRef, Assign, BinOp, UnaryOp, Print, Label, Jump, JumpIfFalse,
    FuncBegin, FuncEnd, Param, Call, Return,
)
from errors.errors import MiniLangRuntimeError


class _Frame:
    """One activation record on the call stack."""
    __slots__ = ("env", "return_pc", "return_dest")

    def __init__(self, env, return_pc, return_dest):
        self.env = env
        self.return_pc = return_pc
        self.return_dest = return_dest  # name in the CALLER's env to store the result in


class VirtualMachine:
    def __init__(self, instructions):
        self.instructions = instructions
        self.label_map = {}
        self.func_info = {}
        self._preprocess()

    # ------------------------------------------------------------------
    def _preprocess(self):
        open_funcs = []
        for idx, instr in enumerate(self.instructions):
            if isinstance(instr, Label):
                self.label_map[instr.name] = idx
            elif isinstance(instr, FuncBegin):
                open_funcs.append((instr.name, instr.params, idx))
            elif isinstance(instr, FuncEnd):
                name, params, begin_idx = open_funcs.pop()
                self.func_info[name] = {
                    "start": begin_idx + 1,   # first instruction of the body
                    "end": idx,               # index of the FuncEnd itself
                    "params": params,
                }

    # ------------------------------------------------------------------
    def run(self):
        """Execute the whole program. Returns the final global environment
        (handy for tests that want to inspect variable values)."""
        globals_env = {}
        env = globals_env
        call_stack = []
        pending_args = []

        pc = 0
        n = len(self.instructions)

        while pc < n:
            instr = self.instructions[pc]

            if isinstance(instr, FuncBegin):
                # Skip over the whole function body during linear execution.
                pc = self.func_info[instr.name]["end"] + 1
                continue

            if isinstance(instr, (FuncEnd, Label)):
                pc += 1
                continue

            if isinstance(instr, Assign):
                env[instr.dest] = self._eval(instr.src, env)
                pc += 1

            elif isinstance(instr, BinOp):
                left = self._eval(instr.left, env)
                right = self._eval(instr.right, env)
                env[instr.dest] = self._apply_binop(instr.op, left, right)
                pc += 1

            elif isinstance(instr, UnaryOp):
                operand = self._eval(instr.operand, env)
                env[instr.dest] = self._apply_unaryop(instr.op, operand)
                pc += 1

            elif isinstance(instr, Print):
                value = self._eval(instr.value, env)
                print(self._stringify(value))
                pc += 1

            elif isinstance(instr, Jump):
                pc = self.label_map[instr.label]

            elif isinstance(instr, JumpIfFalse):
                cond = self._eval(instr.cond, env)
                pc = self.label_map[instr.label] if not self._truthy(cond) else pc + 1

            elif isinstance(instr, Param):
                pending_args.append(self._eval(instr.value, env))
                pc += 1

            elif isinstance(instr, Call):
                info = self.func_info.get(instr.name)
                if info is None:
                    raise MiniLangRuntimeError(f"Call to undefined function '{instr.name}'")

                argcount = instr.argcount
                args = pending_args[-argcount:] if argcount > 0 else []
                if argcount > 0:
                    del pending_args[-argcount:]

                if len(args) != len(info["params"]):
                    raise MiniLangRuntimeError(
                        f"Function '{instr.name}' expects {len(info['params'])} "
                        f"argument(s) but got {len(args)}")

                new_env = dict(zip(info["params"], args))
                call_stack.append(_Frame(env, pc + 1, instr.dest))
                env = new_env
                pc = info["start"]

            elif isinstance(instr, Return):
                value = self._eval(instr.value, env) if instr.value is not None else None
                if not call_stack:
                    # Defensive guard; semantic analysis already forbids
                    # `return` at the top level.
                    break
                frame = call_stack.pop()
                if frame.return_dest is not None:
                    frame.env[frame.return_dest] = value
                env = frame.env
                pc = frame.return_pc

            else:
                raise MiniLangRuntimeError(f"Unknown IR instruction: {instr}")

        return globals_env

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _eval(self, operand, env):
        if isinstance(operand, Const):
            return operand.value
        if isinstance(operand, VarRef):
            if operand.name not in env:
                raise MiniLangRuntimeError(f"Undefined variable '{operand.name}' at runtime")
            return env[operand.name]
        raise MiniLangRuntimeError(f"Invalid IR operand: {operand}")

    def _truthy(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        return value is not None

    def _apply_binop(self, op, left, right):
        try:
            if op == "+":
                if isinstance(left, str) or isinstance(right, str):
                    return self._stringify(left) + self._stringify(right) \
                        if isinstance(left, str) and isinstance(right, str) else left + right
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    raise MiniLangRuntimeError("Division by zero")
                result = left / right
                if isinstance(left, int) and isinstance(right, int) and left % right == 0:
                    return left // right
                return result
            if op == "%":
                if right == 0:
                    raise MiniLangRuntimeError("Modulo by zero")
                return left % right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            if op == ">=":
                return left >= right
            if op == "&&":
                return self._truthy(left) and self._truthy(right)
            if op == "||":
                return self._truthy(left) or self._truthy(right)
        except TypeError as e:
            raise MiniLangRuntimeError(f"Type error evaluating '{left!r} {op} {right!r}': {e}")
        raise MiniLangRuntimeError(f"Unknown binary operator '{op}'")

    def _apply_unaryop(self, op, operand):
        if op == "-":
            return -operand
        if op == "!":
            return not self._truthy(operand)
        raise MiniLangRuntimeError(f"Unknown unary operator '{op}'")

    def _stringify(self, value):
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "null"
        return str(value)
