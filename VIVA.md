# VIVA.md - Viva Voce Preparation for MiniLang Compiler

50 questions and simple, project-specific answers, grouped by topic.
Answers reference this project's actual files so you can point to real code
during the viva.

---

## A. General Compiler Concepts

**1. What is a compiler?**
A program that translates source code written in one language (the
*source language*) into another language (the *target language*), usually
detecting and reporting errors along the way. In this project the source
language is MiniLang and the "target" is Three Address Code, which our
Virtual Machine then executes.

**2. What is the difference between a compiler and an interpreter?**
A compiler translates the *entire* program into another form before
execution (e.g. to machine code or bytecode). An interpreter executes the
program directly, often statement by statement. This project is actually a
**hybrid**: it *compiles* MiniLang all the way down to Three Address Code
(a compiler's job) and then *interprets* that IR with a Virtual Machine
(an interpreter's job) instead of emitting real machine code.

**3. Why did you build a compiler that ends in a VM instead of real machine
code?**
Generating real x86/ARM machine code requires handling registers, calling
conventions, and an OS-specific executable format - a lot of complexity
that would obscure the compiler-design concepts this project is meant to
demonstrate. A small VM that executes our own IR keeps every phase
(lexing, parsing, semantic analysis, IR generation) fully visible and
portable, while still proving the IR is genuinely executable.

**4. What are the phases of a compiler, and where does each one live in
this project?**
| Phase | Folder | Input -> Output |
|---|---|---|
| Lexical Analysis | `lexer/` | source text -> tokens |
| Syntax Analysis | `parser/` | tokens -> AST |
| Semantic Analysis | `semantic/` | AST -> checked AST + error list |
| IR Generation | `ir/` | AST -> Three Address Code |
| Code Generation / Execution | `vm/` | TAC -> program output |

**5. Why did you invent a new language instead of using an existing one?**
The project's goal is to demonstrate compiler design concepts end-to-end.
Designing MiniLang from scratch means every phase - grammar, AST shape,
scoping rules, IR - is something we designed and can explain completely,
rather than reimplementing a subset of an existing language's much larger,
messier grammar.

---

## B. Lexical Analysis

**6. What is lexical analysis?**
The first compiler phase: scanning the raw source code character by
character and grouping those characters into meaningful chunks called
*tokens* (see `lexer/lexer.py`).

**7. What is a token?**
A classified unit of source code - e.g. a keyword, identifier, number,
string, or operator - represented in this project by the `Token` class in
`lexer/token.py`, which stores a `TokenType`, the raw text, an optional
literal value, and a line/column.

**8. What is a lexeme?**
The *raw substring* of source code that a token was built from. For the
token `NUMBER(10)`, the lexeme is the text `"10"`; the token's `.value` is
the *converted* Python `int` `10`.

**9. What is the difference between a token and a lexeme?**
A lexeme is just text; a token is that text *plus its classification*
(what kind of thing it is) and its value/position. "10" is a lexeme;
`NUMBER(10)` is the token built from it.

**10. How does your lexer distinguish keywords from identifiers?**
It first scans any run of letters/digits/underscores as a generic
identifier, then checks it against a `KEYWORDS` dictionary
(`lexer/token.py`). If it's found there (`let`, `if`, `func`, ...) it
becomes that keyword's token type; otherwise it stays an `IDENTIFIER`.

**11. How does your lexer read numbers like `3.14`?**
It reads digits, and if it then sees a `.` followed by another digit, it
consumes the fractional part too and marks the token as a float
(converted with Python's `float()`); otherwise it's an int
(`int()`). See `_scan_number` in `lexer/lexer.py`.

**12. What is "maximal munch" and where do you use it?**
The rule that a lexer should always consume the *longest* possible valid
token at each point. We use it for two-character operators: when the
lexer sees `=`, it peeks at the next character - if it's also `=`, it
consumes both and produces `EQ` (`==`) instead of two separate `ASSIGN`
tokens.

**13. How are comments handled?**
`_skip_whitespace_and_comments()` in `lexer/lexer.py` skips `//` to the
end of the line, and skips everything between `/*` and `*/` (raising a
`LexicalError` if the block comment is never closed).

**14. How does the lexer report errors?**
By raising a `LexicalError` (see `errors/errors.py`) carrying the exact
line and column of the bad character, e.g. `Unexpected character '@'`.

**15. What happens with an unterminated string like `"hello`?**
The lexer keeps consuming characters looking for the closing `"`; if it
hits end-of-file or a newline first, it raises `LexicalError("Unterminated
string literal", ...)`.

---

## C. Parsing / Syntax Analysis

**16. What is parsing?**
Checking that the token stream follows the language's grammar, and
building a structured representation (the AST) of the program in the
process.

**17. What is a grammar / CFG (Context-Free Grammar)?**
A set of rules describing how valid programs can be built from smaller
pieces, written here in EBNF (see README.md Section 4 or the docstring at
the top of `parser/parser.py`). "Context-free" means each rule expands a
single symbol regardless of surrounding context.

**18. Why did you use recursive descent instead of a parser generator?**
The project requires hand-written lexing/parsing specifically so the
project demonstrates the actual parsing technique, not a generated table.
Recursive descent also maps very directly onto the grammar - one Python
method per rule - which makes it easy to read and explain.

**19. What is a recursive descent parser?**
A top-down parser made of one function per grammar rule, where each
function may call other rule-functions (including itself) exactly the way
the grammar rules refer to each other. E.g. `_term()` calls `_factor()` in
`parser/parser.py` because `term -> factor (("+"|"-") factor)*`.

**20. How does your parser handle operator precedence?**
Through the *structure of the grammar itself*: lower-precedence operators
sit in "outer" rules that call "inner" rules for higher-precedence ones.
`_logical_or -> _logical_and -> _equality -> _comparison -> _term ->
_factor -> _unary -> _call -> _primary`. Because `_term` (handles `+`/`-`)
calls `_factor` (handles `*`/`/`/`%`) for each operand, a `*` always ends
up nested *inside* a `+`, so it's evaluated first - exactly the precedence
we want.

**21. How is left-associativity implemented for `+`/`-`?**
With a `while` loop in `_term()`: after parsing one operand, it keeps
folding in `(op, right_operand)` pairs into a growing left-leaning tree, so
`a - b - c` becomes `(a - b) - c`, not `a - (b - c)`.

**22. How is assignment parsed, since `=` isn't in the same precedence
chain as `+`/`-`?**
`_assignment()` first parses a `_logical_or()` expression, and *only if*
the next token is `=` does it re-interpret that already-parsed expression
as an assignment target (and only allows this when it was a plain
`Identifier` - otherwise it raises a `ParserError`, "Invalid assignment
target"). This also makes it right-associative by having `_assignment`
call itself for the right-hand side.

**23. What does the parser do when it sees `let x = 10` with no
semicolon?**
`_var_declaration()` calls `self._expect(TokenType.SEMICOLON, "Expected
';' after variable declaration")`, which raises `ParserError` naming that
exact message with the token's line/column, since the next token (`print`
in that case) is not a semicolon.

**24. How does your parser tell a function CALL apart from a variable
reference, like `add(1,2)` vs `x`?**
`_call()` first parses a `_primary()` (which for an identifier just
produces an `Identifier` node), then checks whether the *next* token is
`(`. If so, it wraps that identifier into a `FunctionCall` node
(`_finish_call`); otherwise it's left as a plain `Identifier`.

**25. What's the difference between a parse tree and an AST?**
A parse tree records *every* grammar rule applied, including punctuation
like `;` and `(`. An AST keeps only the information that matters for later
phases - e.g. `BinaryExpression(left, "+", right)` - and throws away
syntax noise. Our parser builds the AST directly rather than a full parse
tree, which is standard practice.

---

## D. Abstract Syntax Tree

**26. What is an AST?**
A tree representation of a program's structure, where each node
represents a language construct (a declaration, an expression, a
statement) and its children are the sub-parts of that construct. See
`ast_nodes/nodes.py` for every node type this project defines.

**27. Why did you name the package `ast_nodes` instead of `ast` as the
spec suggested?**
Python's standard library already has a built-in module literally called
`ast`. Naming our own package `ast` would shadow it - any code in the
project that later tried `import ast` for the real standard-library module
would silently get ours instead. Renaming to `ast_nodes` avoids that
footgun.

**28. Walk me through the AST for `let x = 10 + 20;`.**
```
VarDeclaration: x
  BinaryExpression: +
    Literal: 10
    Literal: 20
```
A `VarDeclaration` node holds the variable's name and its initializer
expression; that initializer is a `BinaryExpression` node with operator
`"+"` and two `Literal` children.

**29. What is the AST pretty printer and why did you build one?**
`utils/ast_printer.py` recursively walks any AST and prints it as an
indented tree. It exists purely so a student (or examiner) can *visually
verify* the parser produced the tree they expect, using
`python main.py file.mini --ast`.

---

## E. Semantic Analysis

**30. What is semantic analysis, and how is it different from syntax
analysis?**
Syntax analysis checks *shape* - does the program match the grammar?
Semantic analysis checks *meaning* - does the program make sense? E.g.
`print(x);` is syntactically perfect even if `x` was never declared; only
semantic analysis catches that.

**31. What is a symbol table, and how does yours work?**
A data structure that remembers every declared name, what kind of thing
it is (variable or function), and (for variables) its inferred type. Ours
(`semantic/symbol_table.py`) is a **stack of scope dictionaries**:
entering a block pushes a new empty scope, leaving it pops that scope,
`declare()` only writes into the innermost scope, and `resolve()` searches
from innermost to outermost.

**32. How does your symbol table implement variable *scoping*?**
Every `{ ... }` block - including `if`/`while` bodies and function
bodies - gets pushed as its own scope in `SemanticAnalyzer._visit_statement`
when it sees a `Block` node. A variable declared inside is only visible
until that scope is popped, which is why an inner `let x` can safely
*shadow* an outer `x` without conflicting.

**33. What errors does the semantic analyzer detect? Give an example of
each.**
See README.md Section 8's table: undefined variable, duplicate declaration
in the same scope, invalid operand types (e.g. `"hello" - 10`), undefined
function call, wrong argument count, and `return` outside a function.

**34. How does the analyzer catch `"hello" - 10`?**
`_visit_binary()` in `semantic/analyzer.py` infers the static type of both
operands (`string` and `int`), and for operators other than `+`, both
sides must be numeric (`int`/`float`); since `string` isn't numeric here,
it appends a `SemanticError`: `Invalid operand types for '-': 'string' and
'int'`.

**35. Why does `+` allow `string + string` but not `string + int`?**
`+` is deliberately overloaded for both numeric addition and string
concatenation (a common language design choice), but only when *both*
sides are the same "compatible" kind - both numeric, or both string.
Mixing a string with a number is rejected as ambiguous rather than
silently coercing one side.

**36. How does recursion (e.g. `factorial` calling itself) pass semantic
analysis?**
Function names are **hoisted**: `SemanticAnalyzer.analyze()` does a first
pass over all top-level `FunctionDeclaration`s, declaring each function's
name and arity in the symbol table *before* analyzing any function body.
So when the analyzer later walks inside `factorial`'s own body and sees a
call to `factorial(...)`, that name already resolves.

**37. Does your semantic analyzer stop at the first error?**
No - it collects every `SemanticError` it finds into a list and keeps
going (see `analyze()` in `semantic/analyzer.py`), the same way a real
compiler reports several mistakes per run instead of forcing a
fix-one-error-at-a-time loop. Only the lexer and parser stop at the first
error, because one bad token usually makes the rest of that phase's
output meaningless anyway.

**38. What is type inference, and how "smart" is yours?**
Determining an expression's type without an explicit annotation. Ours is
intentionally simple: a variable's type comes from its initializer
expression at `let` time, and anything whose type we can't know statically
(a function's return value, a parameter) is given the type `'any'` and
skipped during type checks - a deliberate simplification, not a full type
system.

**39. What happens semantically with `return` outside a function?**
The analyzer tracks a `function_depth` counter, incremented while
visiting a function body. If it sees a `ReturnStatement` while
`function_depth == 0`, it reports `Return statement used outside of a
function`.

---

## F. Intermediate Representation

**40. What is intermediate code / an intermediate representation (IR)?**
A representation of the program that sits between the AST and final
execution - simpler and flatter than a tree, but still not tied to any
specific machine. It lets later phases (optimization, code generation)
work on a uniform, simple format instead of a nested tree.

**41. What is Three Address Code (TAC)?**
An IR style where every instruction has at most three "addresses": one
result and up to two operands, e.g. `t1 = a + b`. Complex expressions are
broken into a sequence of these simple instructions using compiler
generated **temporary variables** (`t1`, `t2`, ...).

**42. Generate the TAC for `let result = (a + b) * c;` by hand.**
```
t1 = a + b
t2 = t1 * c
result = t2
```
(matches exactly what `ir/generator.py` produces)

**43. Why do leaf expressions like `let y = x;` NOT get a wasted temporary
(`t1 = x; y = t1;`)?**
`IRGenerator._gen_expression()` returns an `Operand` directly for
`Literal`/`Identifier` nodes (no instruction emitted) and only allocates a
new temp for *compound* expressions (`BinaryExpression`, `UnaryExpression`,
`FunctionCall`). So `let y = x;` calls `_gen_expression` on the
`Identifier` `x`, gets back `VarRef("x")` with zero extra instructions, and
just emits `Assign("y", VarRef("x"))`, i.e. `y = x`.

**44. How is `if`/`else` lowered into TAC?**
Using labels and a conditional jump: evaluate the condition into an
operand, `ifFalse <cond> goto Lelse`, then the "then" code, then
`goto Lend`, then `Lelse:`, then the "else" code (if any), then `Lend:`.
See `_gen_if()` in `ir/generator.py`.

**45. How is a `while` loop lowered into TAC?**
```
Lstart:
    <code for condition>          -> c
    ifFalse c goto Lend
    <code for body>
    goto Lstart
Lend:
```
Putting the condition check at the *top* of the label naturally implements
a pre-test loop, and jumping back to `Lstart` after the body repeats it.

**46. How are function calls represented in TAC?**
Arguments are pushed one at a time with `param <value>` instructions
immediately before a `call <name>, <argcount>` instruction, which stores
its result into a fresh temporary, e.g.:
```
param 5
t5 = call factorial, 1
```

---

## G. Code Generation / Execution (the Virtual Machine)

**47. What is a virtual machine, in the compiler sense used here?**
A program that *executes* an intermediate representation directly, rather
than translating it to real machine code first. Ours
(`vm/interpreter.py`) is a simple program-counter-driven interpreter for
our TAC instruction list - conceptually similar to how the JVM executes
Java bytecode, just far simpler.

**48. Why does the VM skip over a function's body during normal
execution?**
A function's TAC instructions sit inline, in source order, between
`FuncBegin`/`FuncEnd` markers. If the VM just executed top-to-bottom
without special-casing this, it would "fall into" and run every function
body the moment it reached it, even if nothing ever called that function!
So whenever `pc` lands on a `FuncBegin`, the VM immediately jumps `pc`
straight past the matching `FuncEnd` - the body only executes when a
`Call` instruction jumps into it on purpose.

**49. How does the VM make recursion work?**
Every `Call` pushes an *activation record* (`_Frame` in
`vm/interpreter.py`) holding a **brand new, independent** dictionary for
the callee's local variables/parameters, the caller's `pc + 1` to resume
at, and where to store the return value. `pc` then jumps into the
function's body. Because each recursive call gets its own fresh
environment dictionary and its own stacked frame, `factorial(5)` calling
`factorial(4)` calling `factorial(3)`... never overwrites an outer call's
`n` - exactly like a real CPU's call stack. `Return` pops the top frame,
restores the caller's environment and `pc`, and writes the return value
into the caller's chosen destination variable.

**50. What happens end-to-end, from source code to output, for
`print("Hello World");`?**
1. **Lexer** turns the text into tokens: `PRINT`, `LPAREN`,
   `STRING("Hello World")`, `RPAREN`, `SEMICOLON`, `EOF`.
2. **Parser** builds `Program([PrintStatement(Literal("Hello World"))])`.
3. **Semantic Analyzer** visits the `PrintStatement`'s expression
   (`Literal`), finds no undeclared names or type errors, and reports zero
   errors.
4. **IR Generator** turns the literal into `Const("Hello World")` (no
   temporary needed) and emits one instruction: `print "Hello World"`.
5. **Virtual Machine** executes that one `Print` instruction, evaluates
   its operand back to the Python string `"Hello World"`, and calls
   Python's `print()`, producing the line `Hello World` on the terminal.
