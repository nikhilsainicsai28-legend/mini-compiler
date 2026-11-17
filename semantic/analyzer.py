"""
semantic/analyzer.py
======================
Phase 4 of the pipeline: Semantic Analysis.

The parser only checks that a program's source SHAPE follows the grammar
(syntax). It happily accepts things like `print(x);` even if `x` was never
declared, because that isn't a grammar violation - it's a MEANING
violation. That's what this phase catches, by walking the AST while
maintaining a SymbolTable (see semantic/symbol_table.py) of every name
currently in scope.

Checks performed:
    1. Undefined variable use            (e.g. `print(x);` with no `let x`)
    2. Duplicate declaration in a scope  (e.g. `let x = 1; let x = 2;`)
    3. Invalid operand types             (e.g. `"hello" - 10`)
    4. Undefined function calls
    5. Wrong number of arguments to a function call
    6. `return` used outside of a function body

Design choice: rather than raising on the FIRST problem found (like the
lexer/parser do), the analyzer collects ALL semantic errors into a list
and keeps going ("error recovery"), the same way real compilers report
several mistakes in one run instead of forcing you to fix-and-recompile
one error at a time. main.py decides what to do with that list.

Type inference here is intentionally simple (best-effort, not a full type
system): a variable's type is inferred once from its initializer, and
function calls / parameters are treated as type 'any' since MiniLang has
no type annotations. This is enough to catch the classic
`"hello" - 10` class of bug while staying simple enough to explain in a
viva.
"""

from ast_nodes import nodes as ast
from semantic.symbol_table import SymbolTable
from errors.errors import SemanticError

NUMERIC = ("int", "float")


class SemanticAnalyzer:
    def __init__(self):
        self.symtab = SymbolTable()
        self.errors = []
        self.function_depth = 0

    # ------------------------------------------------------------------
    def analyze(self, program: ast.Program):
        """Returns a list of SemanticError objects (empty list = OK)."""
        self.errors = []

        # Pass 1: hoist top-level function signatures so functions can be
        # called before their textual definition, and so recursive calls
        # inside a function body can find the function's own name.
        for stmt in program.statements:
            if isinstance(stmt, ast.FunctionDeclaration):
                ok = self.symtab.declare(stmt.name, "func", arity=len(stmt.params), line=stmt.line)
                if not ok:
                    self._error(f"Function '{stmt.name}' is already defined", stmt.line)

        # Pass 2: full walk
        for stmt in program.statements:
            self._visit_statement(stmt)

        return self.errors

    def _error(self, message, line=None, column=None):
        self.errors.append(SemanticError(message, line, column))

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------
    def _visit_statement(self, node):
        if isinstance(node, ast.VarDeclaration):
            self._visit_var_decl(node)
        elif isinstance(node, ast.FunctionDeclaration):
            self._visit_function_decl(node)
        elif isinstance(node, ast.Block):
            self.symtab.enter_scope()
            for s in node.statements:
                self._visit_statement(s)
            self.symtab.exit_scope()
        elif isinstance(node, ast.IfStatement):
            self._visit_expression(node.condition)
            self._visit_statement(node.then_branch)
            if node.else_branch is not None:
                self._visit_statement(node.else_branch)
        elif isinstance(node, ast.WhileStatement):
            self._visit_expression(node.condition)
            self._visit_statement(node.body)
        elif isinstance(node, ast.ReturnStatement):
            if self.function_depth == 0:
                self._error("Return statement used outside of a function", node.line)
            if node.value is not None:
                self._visit_expression(node.value)
        elif isinstance(node, ast.PrintStatement):
            self._visit_expression(node.expression)
        elif isinstance(node, ast.ExpressionStatement):
            self._visit_expression(node.expression)
        else:
            self._error(f"Unknown statement type {type(node).__name__}", getattr(node, "line", None))

    def _visit_var_decl(self, node):
        value_type = self._visit_expression(node.initializer)
        ok = self.symtab.declare(node.name, "var", type_=value_type, line=node.line)
        if not ok:
            self._error(f"Variable '{node.name}' is already declared in this scope", node.line)

    def _visit_function_decl(self, node):
        # Declare here too, in case it wasn't hoisted (e.g. a function
        # declared inside a nested block rather than at the top level).
        if node.name not in self.symtab.current_scope:
            ok = self.symtab.declare(node.name, "func", arity=len(node.params), line=node.line)
            if not ok:
                self._error(f"Function '{node.name}' is already defined", node.line)

        self.symtab.enter_scope()
        self.function_depth += 1
        seen_params = set()
        for p in node.params:
            if p in seen_params:
                self._error(f"Duplicate parameter name '{p}' in function '{node.name}'", node.line)
            seen_params.add(p)
            self.symtab.declare(p, "var", type_="any", line=node.line)
        for s in node.body.statements:
            self._visit_statement(s)
        self.function_depth -= 1
        self.symtab.exit_scope()

    # ------------------------------------------------------------------
    # Expressions - each returns an inferred type string
    # ------------------------------------------------------------------
    def _visit_expression(self, node):
        if isinstance(node, ast.Literal):
            return self._literal_type(node.value)

        if isinstance(node, ast.Identifier):
            symbol = self.symtab.resolve(node.name)
            if symbol is None:
                self._error(f"Variable '{node.name}' is not defined", node.line)
                return "any"
            if symbol.kind == "func":
                self._error(f"'{node.name}' is a function, not a variable", node.line)
                return "any"
            return symbol.type

        if isinstance(node, ast.Assignment):
            symbol = self.symtab.resolve(node.name)
            if symbol is None:
                self._error(f"Assignment to undefined variable '{node.name}'", node.line)
            value_type = self._visit_expression(node.value)
            if symbol is not None and symbol.kind == "var":
                self.symtab.update_type(node.name, value_type)
            return value_type

        if isinstance(node, ast.UnaryExpression):
            operand_type = self._visit_expression(node.operand)
            if node.operator == "-":
                if operand_type not in NUMERIC and operand_type != "any":
                    self._error(f"Unary '-' requires a numeric operand, got '{operand_type}'", node.line)
                return operand_type if operand_type in NUMERIC else "any"
            if node.operator == "!":
                if operand_type not in ("boolean", "any"):
                    self._error(f"Unary '!' requires a boolean operand, got '{operand_type}'", node.line)
                return "boolean"
            return "any"

        if isinstance(node, ast.Logical):
            left_type = self._visit_expression(node.left)
            right_type = self._visit_expression(node.right)
            for side, t in (("left", left_type), ("right", right_type)):
                if t not in ("boolean", "any"):
                    self._error(
                        f"Logical operator '{node.operator}' requires boolean operands, "
                        f"got '{t}' on the {side}", node.line)
            return "boolean"

        if isinstance(node, ast.BinaryExpression):
            return self._visit_binary(node)

        if isinstance(node, ast.FunctionCall):
            return self._visit_call(node)

        self._error(f"Unknown expression type {type(node).__name__}", getattr(node, "line", None))
        return "any"

    def _literal_type(self, value):
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        return "any"

    def _visit_binary(self, node):
        left_type = self._visit_expression(node.left)
        right_type = self._visit_expression(node.right)
        op = node.operator

        if "any" in (left_type, right_type):
            # We don't statically know one side's type (e.g. it came from a
            # function call or a parameter) - skip strict checking.
            if op in ("==", "!=", "<", ">", "<=", ">="):
                return "boolean"
            return "any"

        if op == "+":
            if left_type == "string" and right_type == "string":
                return "string"
            if left_type in NUMERIC and right_type in NUMERIC:
                return "float" if "float" in (left_type, right_type) else "int"
            self._error(
                f"Invalid operand types for '+': '{left_type}' and '{right_type}'", node.line)
            return "any"

        if op in ("-", "*", "/", "%"):
            if left_type in NUMERIC and right_type in NUMERIC:
                return "float" if "float" in (left_type, right_type) else "int"
            self._error(
                f"Invalid operand types for '{op}': '{left_type}' and '{right_type}'", node.line)
            return "any"

        if op in ("<", ">", "<=", ">="):
            if left_type in NUMERIC and right_type in NUMERIC:
                return "boolean"
            self._error(
                f"Cannot compare '{left_type}' and '{right_type}' using '{op}'", node.line)
            return "boolean"

        if op in ("==", "!="):
            return "boolean"

        return "any"

    def _visit_call(self, node):
        symbol = self.symtab.resolve(node.name)
        if node.name == "print":
            # print is a statement in MiniLang, not a callable expression
            self._error("'print' is a statement, not a function, use print(expr);", node.line)
        elif symbol is None:
            self._error(f"Function '{node.name}' is not defined", node.line)
        elif symbol.kind != "func":
            self._error(f"'{node.name}' is not a function", node.line)
        elif symbol.arity != len(node.arguments):
            self._error(
                f"Function '{node.name}' expects {symbol.arity} argument(s) "
                f"but got {len(node.arguments)}", node.line)

        for arg in node.arguments:
            self._visit_expression(arg)

        return "any"
