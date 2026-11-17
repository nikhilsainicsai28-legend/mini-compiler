# MiniLang Compiler

A complete, hand-written compiler/interpreter pipeline for **MiniLang**, a small
custom programming language designed from scratch for a B.Tech Compiler Design
college project.

No parser generators (PLY / ANTLR / Lark / yacc / lex) are used anywhere.
The lexer and parser are written by hand in pure Python 3, using only the
standard library, so the project genuinely demonstrates the concepts taught
in a Compiler Design course rather than hiding them behind a tool.

---

## 1. Project Objective

Design a small language, **MiniLang** (file extension `.mini`), and build a
full compiler pipeline for it that demonstrates every classical phase of
compiler design:

1. Lexical Analysis
2. Syntax Analysis / Parsing
3. Abstract Syntax Tree (AST) generation
4. Semantic Analysis
5. Intermediate Representation (Three Address Code)
6. Code Generation / Execution (a small Virtual Machine)
7. Error Handling at every phase

The goal is a project that is simple enough to explain fully in a viva, but
complete enough to actually run real programs - including recursive
functions like `factorial()` and `fibonacci()`.

---

## 2. Features

- Variables with `let`, and re-assignment (`x = x + 1;`)
- Four data types: **Integer**, **Float**, **String**, **Boolean**
- Arithmetic operators: `+  -  *  /  %`
- Comparison operators: `==  !=  <  >  <=  >=`
- Logical operators: `&&  ||  !`
- `if` / `else` conditionals
- `while` loops
- Functions with parameters, `return`, and **recursion**
- Built-in `print(expression)`
- Line comments (`// ...`) and block comments (`/* ... */`)
- A symbol table with proper **lexical block scoping** (variables declared
  inside `{ }` don't leak outside)
- Detailed, colour-free, IDE-friendly error messages with **line and column**
  numbers for lexical, syntax, semantic, and runtime errors
- A CLI with `--tokens`, `--ast`, `--ir`, `--run`, `--debug` flags
- 57 automated unit tests covering all phases (`python -m unittest`)

---

## 3. MiniLang Syntax (by example)

```javascript
// Variables and data types
let x = 10;
let pi = 3.14;
let name = "Alice";
let flag = true;

// Arithmetic
let sum = x + 5;
let area = pi * 2 * 2;

// Re-assignment
x = x + 1;

// Conditionals
if (x > 10) {
    print(x);
} else {
    print(0);
}

// Loops
let i = 0;
while (i < 5) {
    print(i);
    i = i + 1;
}

// Functions and recursion
func factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

let result = factorial(5);
print(result);      // 120
```

---

## 4. Language Grammar (EBNF)

This is the exact grammar implemented by the recursive-descent parser in
`parser/parser.py` (also documented in that file's docstring):

```
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
```

Each grammar rule is a lower level of **operator precedence** than the one
above it: `logical_or` binds loosest, `unary`/`call`/`primary` bind
tightest. This is exactly why `2 + 3 * 4` parses as `2 + (3 * 4)`: `term`
(handles `+`/`-`) calls `factor` (handles `*`/`/`/`%`) as a sub-expression,
so multiplication is naturally nested one level deeper - and therefore
evaluated first.

---

## 5. Compiler Architecture

```
   Source Code (.mini)
          |
          v
+-----------------------+
|   Lexical Analyzer     |   lexer/lexer.py
|      (Lexer)            |
+-----------------------+
          |
          v
        Tokens
          |
          v
+-----------------------+
|        Parser          |   parser/parser.py
+-----------------------+
          |
          v
         AST                ast_nodes/nodes.py
          |
          v
+-----------------------+
|  Semantic Analyzer      |   semantic/analyzer.py + symbol_table.py
+-----------------------+
          |
          v
     Checked AST
          |
          v
+-----------------------+
|  Intermediate          |   ir/generator.py
|  Representation (IR)   |
+-----------------------+
          |
          v
   Three Address Code       ir/instructions.py
          |
          v
+-----------------------+
|   Virtual Machine       |   vm/interpreter.py
|   (Interpreter)         |
+-----------------------+
          |
          v
        Output
```

`main.py` is the glue: it calls each phase in order and stops with a
formatted error message the moment any phase fails.

---

## 6. Compiler Phases Explained

### Phase 1 - Lexical Analysis (`lexer/`)
Reads the `.mini` source **character by character** and groups characters
into **tokens**: keywords, identifiers, number/string/boolean literals,
operators, and delimiters. Whitespace and comments are discarded. Every
token records the line/column it started at. Malformed input (an unknown
character, an unterminated string) raises a `LexicalError` immediately.

### Phase 2/3 - Parsing and AST (`parser/`, `ast_nodes/`)
A hand-written **recursive descent parser**: one Python method per grammar
rule (see Section 4), calling each other exactly as the grammar calls
itself. The output is an **Abstract Syntax Tree (AST)** - a tree of node
objects (`VarDeclaration`, `IfStatement`, `BinaryExpression`, ...) that
represents the program's *structure and meaning*, with all the punctuation
(`;`, `(`, `)`) thrown away because it has already done its job. A
malformed token sequence (missing `;`, unmatched `(`) raises a
`ParserError`.

### Phase 4 - Semantic Analysis (`semantic/`)
Walks the AST while maintaining a **scoped symbol table**
(`semantic/symbol_table.py`) to check things the grammar cannot express:
"is this variable actually declared before use?", "is this function called
with the right number of arguments?", "does `"hello" - 10` even make
sense?". See Section 8 below for full details. Errors are *collected*
(not raised immediately) so a single run can report several mistakes at
once, like a real compiler.

### Phase 5 - Intermediate Representation (`ir/`)
Lowers the checked AST into **Three Address Code (TAC)** - a flat list of
simple instructions with at most one operator and one destination each,
e.g. `t1 = a + b`. This is the classic "halfway between a tree and machine
code" representation taught in every compilers course. See Section 9.

### Phase 6 - Execution (`vm/`)
A small **stack-frame based Virtual Machine** walks the TAC instruction
list with a single program counter, exactly like a simplified CPU. Function
calls push an activation record (a "frame") onto a call stack so that
**recursion** (e.g. `factorial`, `fibonacci`) works correctly. See
Section 10.

### Phase 7 - Error Handling (`errors/`)
Every phase raises a subclass of `MiniLangError` with a phase name, a
message, and (where available) a line/column, so `main.py` can print a
single, consistent style of diagnostic no matter which phase failed.

---

## 7. Project Structure

```
MiniLangCompiler/
│
├── README.md
├── VIVA.md
├── requirements.txt
├── main.py
│
├── lexer/
│   ├── __init__.py
│   ├── token.py          # TokenType enum + Token class
│   └── lexer.py          # Phase 1: Lexical Analyzer
│
├── parser/
│   ├── __init__.py
│   └── parser.py         # Phase 2/3: Recursive descent parser
│
├── ast_nodes/             # (named ast_nodes, not ast, to avoid shadowing
│   ├── __init__.py        #  Python's own stdlib `ast` module)
│   └── nodes.py           # AST node class hierarchy
│
├── semantic/
│   ├── __init__.py
│   ├── symbol_table.py   # Scoped symbol table
│   └── analyzer.py       # Phase 4: Semantic Analyzer
│
├── ir/
│   ├── __init__.py
│   ├── instructions.py   # TAC instruction + operand classes
│   └── generator.py      # Phase 5: IR Generator (AST -> TAC)
│
├── vm/
│   ├── __init__.py
│   └── interpreter.py    # Phase 6: Virtual Machine (executes TAC)
│
├── errors/
│   ├── __init__.py
│   └── errors.py         # MiniLangError and its subclasses
│
├── utils/
│   ├── __init__.py
│   └── ast_printer.py    # AST pretty-printer
│
├── examples/
│   ├── hello.mini
│   ├── arithmetic.mini
│   ├── condition.mini
│   ├── loop.mini
│   ├── functions.mini
│   ├── factorial.mini
│   ├── strings_and_booleans.mini
│   └── invalid/           # 7 deliberately broken programs (see Section 13)
│       ├── 01_invalid_character.mini
│       ├── 02_missing_semicolon.mini
│       ├── 03_missing_paren.mini
│       ├── 04_undefined_variable.mini
│       ├── 05_duplicate_variable.mini
│       ├── 06_wrong_arg_count.mini
│       └── 07_invalid_type_operation.mini
│
└── tests/
    ├── __init__.py
    ├── test_lexer.py
    ├── test_parser.py
    ├── test_semantic.py
    └── test_vm.py
```

**Note on naming:** the project spec suggested an `ast/` folder, but this
repository uses `ast_nodes/` instead, because Python's standard library
already ships a built-in module called `ast`. Shadowing it with our own
package would be a classic beginner footgun (any code that tries
`import ast` for the real thing would silently get ours instead) - a small
but deliberate engineering decision worth mentioning in a viva.

---

## 8. Semantic Analysis and the Symbol Table

### How the symbol table works
`semantic/symbol_table.py` implements a **stack of scopes**. Each scope is
a plain `dict` mapping `name -> Symbol`. Entering a block (`{ ... }`,
including function bodies) **pushes** a new empty scope; leaving it
**pops** that scope off, so anything declared inside stops being visible -
this is what gives MiniLang proper block scoping and shadowing:

```javascript
let x = 10;
if (true) {
    let x = 20;   // OK: a NEW x in the inner scope, shadows the outer one
    print(x);      // 20
}
print(x);           // 10 - the outer x is untouched
```

- **`declare(name, ...)`** writes into the *current* (innermost) scope
  only, and returns `False` if that exact scope already has the name -
  which the analyzer turns into a "already declared in this scope" error.
- **`resolve(name)`** searches from the innermost scope **outward** to the
  global scope, returning the first match - or `None`, which the analyzer
  turns into a "not defined" error.

### Checks performed
| # | Check | Example that triggers it |
|---|-------|---------------------------|
| 1 | Undefined variable | `print(x);` with no `let x` anywhere in scope |
| 2 | Duplicate declaration | `let x = 10; let x = 20;` in the same scope |
| 3 | Invalid operand types | `"hello" - 10` |
| 4 | Undefined function | `foo(1, 2);` with no `func foo` |
| 5 | Wrong argument count | `add(1);` when `add` takes 2 parameters |
| 6 | `return` outside a function | a bare `return 5;` at the top level |

Type checking is intentionally a **best-effort static check**, not a full
Hindley-Milner style type system: a variable's type is inferred once from
its initializer expression, function results and parameters are treated as
type `any` (since MiniLang has no type annotations), and checks are simply
skipped whenever a type is `any`. This is enough to reliably catch the
classic `"hello" - 10` class of bug while staying something you can fully
explain on a whiteboard in five minutes.

---

## 9. Intermediate Representation - Three Address Code

Every TAC instruction has **at most three "addresses"**: one destination
and up to two sources, e.g. `t1 = a + b`. Compound expressions are broken
down using **temporary variables** (`t1`, `t2`, ...):

```javascript
let x = 10 + 20;
```
generates:
```
t1 = 10 + 20
x = t1
```

```javascript
let result = (a + b) * c;
```
generates:
```
t1 = a + b
t2 = t1 * c
result = t2
```

Control flow is lowered with **labels and conditional jumps**:

```javascript
if (x > 10) { print(x); } else { print(0); }
```
generates something like:
```
t1 = x > 10
ifFalse t1 goto Lelse1
print x
goto Lend1
Lelse1:
print 0
Lend1:
```

Functions are bracketed by `func name(params):` / `endfunc name` markers,
and calls use `param` (to push one argument) followed by `call`:

```
func factorial(n):
    t1 = n <= 1
    ifFalse t1 goto Lelse1
    return 1
    goto Lend2
Lelse1:
Lend2:
    t2 = n - 1
    param t2
    t3 = call factorial, 1
    t4 = n * t3
    return t4
    return
endfunc factorial
    param 5
    t5 = call factorial, 1
    result = t5
    print result
```

---

## 10. The Virtual Machine

`vm/interpreter.py` executes the TAC list with a single **program counter
(pc)**, exactly like a simplified CPU: look at `instructions[pc]`, do what
it says, then either move `pc` forward by one or jump it somewhere else.

Two things make function calls (and recursion) work:

1. **Skipping function bodies during normal execution.** A function's
   body sits inline in the instruction list, between `FuncBegin`/`FuncEnd`
   markers, in the order it was declared. If the VM's `pc` naturally
   reaches a `FuncBegin` while just running top-to-bottom, it immediately
   jumps `pc` past the matching `FuncEnd` - the body only runs when
   something actually **calls** it.
2. **A real call stack.** A `Call` instruction pushes an *activation
   record* (`_Frame`): a brand new, empty local environment (dict) for
   the callee's parameters and locals, the return address (`pc + 1` in the
   *caller*), and where to store the return value. `pc` then jumps to the
   function body's start. A `Return` instruction pops that frame, restores
   the caller's environment and `pc`, and stores the returned value. Since
   every call gets its **own independent environment**, calling
   `factorial(5)` which calls `factorial(4)` which calls `factorial(3)`...
   just keeps stacking fresh frames, the same way a real CPU's call stack
   does - which is exactly what makes recursion work correctly.

MiniLang functions do **not** capture outer/global variables (no
closures) - only their parameters and their own local `let` declarations
are visible inside them, which keeps the execution model simple to reason
about and explain.

---

## 11. Installation

Requirements: **Python 3.8+**, no third-party packages.

```bash
git clone <this repository>        # or just unzip it
cd MiniLangCompiler
# nothing to install - it's pure standard library
python3 --version                    # make sure this is 3.8+
```

---

## 12. How to Run

```bash
# Launch Desktop GUI / IDE
python3 gui.py

# Just run a program
python3 main.py examples/hello.mini

# Show the token stream
python3 main.py examples/hello.mini --tokens

# Show the AST
python3 main.py examples/hello.mini --ast

# Show the generated Three Address Code
python3 main.py examples/hello.mini --ir

# Show EVERY phase (source, tokens, AST, semantic result, IR, execution)
python3 main.py examples/hello.mini --debug

# Compile only (parse + semantic check), don't execute
python3 main.py examples/hello.mini --no-run
```

---

## 13. Example Programs and Sample Output

### `examples/hello.mini`
```javascript
print("Hello World");
```
```
$ python3 main.py examples/hello.mini
Hello World
```

### `examples/factorial.mini` (recursion)
```javascript
func factorial(n) {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}
let result = factorial(5);
print(result);
```
```
$ python3 main.py examples/factorial.mini
120
0
1
1
2
3
5
8
13
```
(the trailing lines are `fibonacci(0..7)`, also defined in that file)

### `examples/condition.mini`
```
$ python3 main.py examples/condition.mini
a is smaller
flag is true and a is not equal to b
at least one condition is true
```

### Full `--debug` trace for `let x = 10 + 20; print(x);`
```
========== SOURCE ==========
let x = 10 + 20;
print(x);

========== TOKENS ==========
LET(let)
IDENTIFIER(x)
ASSIGN(=)
NUMBER(10)
PLUS(+)
NUMBER(20)
SEMICOLON(;)
PRINT(print)
LPAREN(()
IDENTIFIER(x)
RPAREN())
SEMICOLON(;)
EOF

========== AST ==========
Program
  VarDeclaration: x
    BinaryExpression: +
      Literal: 10
      Literal: 20
  PrintStatement
    Identifier: x

========== SEMANTIC ANALYSIS ==========
No errors found.

========== INTERMEDIATE CODE (Three Address Code) ==========
    t1 = 10 + 20
    x = t1
    print x

========== EXECUTION ==========
30
```

### The 7 "invalid" programs in `examples/invalid/`
Each one is designed to trigger exactly one category of error (see Section
14 below for the full table of output).

---

## 14. Error Handling

Every error message follows the same format:

```
<Phase> Error at line L[, column C]:
<Description>
```

| Example file | Phase | Sample output |
|---|---|---|
| `01_invalid_character.mini` | Lexical | `Lexical Error at line 3, column 9:`<br>`Unexpected character '@'` |
| `02_missing_semicolon.mini` | Syntax | `Syntax Error at line 3, column 1:`<br>`Expected ';' after variable declaration` |
| `03_missing_paren.mini` | Syntax | `Syntax Error at line 3, column 11:`<br>`Expected ')' after if condition` |
| `04_undefined_variable.mini` | Semantic | `Semantic Error at line 2:`<br>`Variable 'x' is not defined` |
| `05_duplicate_variable.mini` | Semantic | `Semantic Error at line 3:`<br>`Variable 'x' is already declared in this scope` |
| `06_wrong_arg_count.mini` | Semantic | `Semantic Error at line 5:`<br>`Function 'add' expects 2 argument(s) but got 1` |
| `07_invalid_type_operation.mini` | Semantic | `Semantic Error at line 2:`<br>`Invalid operand types for '-': 'string' and 'int'` |

Try them yourself:
```bash
for f in examples/invalid/*.mini; do echo "=== $f ==="; python3 main.py "$f"; done
```

Lexical and syntax errors **stop at the first problem** (the standard
behaviour for these phases, since one bad token usually makes the rest of
the parse meaningless). Semantic errors are **collected and reported
together**, so a single run can point out several mistakes at once.

---

## 15. Testing

57 automated unit tests, using only the `unittest` module from the
standard library (no `pytest` dependency required, though `unittest`
output is `pytest`-compatible if you happen to have it installed):

```bash
# Run everything
python3 -m unittest discover -s tests -v

# Run one phase's tests
python3 -m unittest tests.test_lexer -v
python3 -m unittest tests.test_parser -v
python3 -m unittest tests.test_semantic -v
python3 -m unittest tests.test_vm -v
```

Coverage includes:
- **Valid programs:** hello world, arithmetic, variables, if/else, while
  loops, functions, nested expressions, boolean/logical expressions,
  recursion (factorial, fibonacci), string concatenation.
- **Invalid programs:** an unexpected character, a missing semicolon, a
  missing parenthesis, an undefined variable, a duplicate declaration,
  wrong function-argument count, an invalid type operation.

---

## 16. Limitations

Kept simple on purpose, for a college project:

- No arrays, no structs/objects, no `for` loops (only `while`).
- No static type declarations - types are *inferred*, and only checked
  where they're statically knowable (a value from a function call or a
  parameter is treated as type `any` and skipped).
- `&&` / `||` are **not short-circuited** in the VM (both sides are always
  evaluated) - fine since MiniLang has no side-effecting expressions other
  than assignment and calls, but worth knowing.
- Functions cannot access global/outer variables (no closures) - only
  their own parameters and locals.
- No standard library beyond `print`.
- The VM is a straightforward tree-walking-style bytecode interpreter, not
  a real compiled binary - by design (see Section 10: "code generation OR
  execution", and this project chose an interpreter/VM for portability and
  clarity).

---

## 17. Future Improvements

- Arrays / lists and a `for` loop.
- User-defined types / structs.
- Static type annotations with a real type checker.
- Short-circuit evaluation for `&&` / `||`.
- Closures (functions capturing their defining scope).
- A real bytecode format (e.g. serialized to a `.minic` file) so IR can be
  saved and executed without re-compiling.
- A simple standard library (`len()`, `input()`, math functions).
- Compiling IR down further to real x86/LLVM IR instead of interpreting it.

---

## 18. Quick Reference: Full Pipeline in One Sentence Each

1. **Lexer**: characters -> tokens.
2. **Parser**: tokens -> AST (checks *shape*/grammar).
3. **Semantic Analyzer**: AST -> AST + error list (checks *meaning*).
4. **IR Generator**: AST -> Three Address Code.
5. **Virtual Machine**: Three Address Code -> program output.

See `VIVA.md` for 40+ viva questions and answers about this exact project.
