"""
semantic/symbol_table.py
==========================
Implements a SCOPED SYMBOL TABLE: the data structure the Semantic
Analyzer uses to remember every declared variable and function, what kind
of thing it is, and (for variables) what type it holds.

How it works
------------
A symbol table is a stack of "scopes". Each scope is just a Python dict
mapping name -> Symbol. When we enter a block, function body, or the
program itself, we PUSH a new empty scope. When we leave it, we POP that
scope off the stack, so names declared inside it stop being visible - this
is what gives MiniLang lexical (block) scoping.

Looking a name up walks the scope stack from the INNERMOST scope outward
to the global scope (this is why an inner `let x` can "shadow" an outer
`x`). Declaring a name only ever writes into the CURRENT (innermost)
scope, and it is an error to declare the same name twice in that same
scope.
"""


class Symbol:
    def __init__(self, name, kind, type_="any", arity=None, line=None):
        self.name = name
        self.kind = kind          # 'var' or 'func'
        self.type = type_         # 'int' | 'float' | 'string' | 'boolean' | 'any'
        self.arity = arity        # number of parameters, only for functions
        self.line = line

    def __repr__(self):
        if self.kind == "func":
            return f"<func {self.name}/{self.arity}>"
        return f"<var {self.name}:{self.type}>"


class SymbolTable:
    def __init__(self):
        # start with a single global scope
        self.scopes = [dict()]

    # ------------------------------------------------------------------
    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    @property
    def current_scope(self):
        return self.scopes[-1]

    @property
    def is_global_scope(self):
        return len(self.scopes) == 1

    # ------------------------------------------------------------------
    def declare(self, name, kind, type_="any", arity=None, line=None):
        """Declare `name` in the CURRENT scope. Returns False if it is
        already declared in this exact scope (caller should raise a
        SemanticError for duplicate declaration)."""
        if name in self.current_scope:
            return False
        self.current_scope[name] = Symbol(name, kind, type_, arity, line)
        return True

    def resolve(self, name):
        """Look a name up from innermost to outermost scope. Returns the
        Symbol, or None if not found anywhere."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def update_type(self, name, type_):
        """Update the inferred type of an already-declared variable (used
        after re-assignment) in whichever scope it lives."""
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name].type = type_
                return
