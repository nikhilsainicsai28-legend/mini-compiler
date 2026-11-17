#!/usr/bin/env python3
"""
main.py
========
Command line entry point for the MiniLang compiler/interpreter.

Usage:
    python main.py program.mini                # lex, parse, check, run
    python main.py program.mini --tokens        # also show tokens
    python main.py program.mini --ast           # also show the AST
    python main.py program.mini --ir            # also show the IR (TAC)
    python main.py program.mini --run            # (default) execute the program
    python main.py program.mini --debug          # show EVERY phase

This file is intentionally just "glue": it calls into lexer/, parser/,
semantic/, ir/, and vm/ in order, catching MiniLangError so that every
phase reports failures the same way.
"""

import argparse
import sys

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.generator import IRGenerator, format_ir
from vm.interpreter import VirtualMachine
from utils.ast_printer import print_ast
from errors.errors import MiniLangError


def build_arg_parser():
    p = argparse.ArgumentParser(
        prog="main.py",
        description="MiniLang compiler/interpreter - Compiler Design mini project",
    )
    p.add_argument("file", help="path to a .mini source file")
    p.add_argument("--tokens", action="store_true", help="print the token stream")
    p.add_argument("--ast", action="store_true", help="print the abstract syntax tree")
    p.add_argument("--ir", action="store_true", help="print the generated three-address code")
    p.add_argument("--run", action="store_true", help="execute the program (default behaviour)")
    p.add_argument("--debug", action="store_true", help="show every phase: source, tokens, AST, "
                                                          "semantic analysis, IR, and execution")
    p.add_argument("--no-run", action="store_true", help="compile only, do not execute")
    return p


def section(title):
    print(f"\n{'=' * 10} {title} {'=' * 10}")


def main(argv=None):
    args = build_arg_parser().parse_args(argv)

    if not args.file.endswith(".mini"):
        print(f"Warning: '{args.file}' does not use the .mini extension.", file=sys.stderr)

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print(f"Could not read file '{args.file}': {e}", file=sys.stderr)
        return 1

    show_tokens = args.tokens or args.debug
    show_ast = args.ast or args.debug
    show_ir = args.ir or args.debug
    show_semantic_header = args.debug
    should_run = args.run or args.debug or not (args.tokens or args.ast or args.ir or args.no_run)
    if args.no_run:
        should_run = False

    if args.debug:
        section("SOURCE")
        print(source.rstrip())

    try:
        # ---------------- Phase 1: Lexical Analysis ----------------
        tokens = Lexer(source).tokenize()
        if show_tokens:
            section("TOKENS")
            for t in tokens:
                print(t)

        # ---------------- Phase 2/3: Parsing -> AST -----------------
        tree = Parser(tokens).parse()
        if show_ast:
            section("AST")
            print(print_ast(tree))

        # ---------------- Phase 4: Semantic Analysis ----------------
        if show_semantic_header:
            section("SEMANTIC ANALYSIS")
        errors = SemanticAnalyzer().analyze(tree)
        if errors:
            for e in errors:
                print(f"\n{e}", file=sys.stderr)
            print(f"\n{len(errors)} semantic error(s) found. Compilation aborted.", file=sys.stderr)
            return 1
        elif show_semantic_header:
            print("No errors found.")

        # ---------------- Phase 5: IR Generation --------------------
        ir_instructions = IRGenerator().generate(tree)
        if show_ir:
            section("INTERMEDIATE CODE (Three Address Code)")
            print(format_ir(ir_instructions))

        # ---------------- Phase 6: Execution -------------------------
        if should_run:
            if args.debug:
                section("EXECUTION")
            VirtualMachine(ir_instructions).run()

    except MiniLangError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
