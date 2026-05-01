#!/usr/bin/env python3
import json
import sys
from ast_normalize import ast_document_to_cpp_state
from cpp_generator import CppGenerator

def load_input(argv):
    if len(argv) == 2:
        with open(argv[1], encoding="utf-8") as f:
            return f.read()
    if len(argv) == 1:
        return sys.stdin.read()
    sys.stderr.write("usage: {} [<ast json path>]\n".format(argv[0]))
    sys.stderr.write("  If no path is given, AST JSON is read from stdin.\n")
    sys.exit(2)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    raw = load_input(argv)
    doc = json.loads(raw)
    const_, enum_, type_, choice_, seq_, pass1 = ast_document_to_cpp_state(doc)
    gen = CppGenerator(const_, enum_, type_, choice_, seq_, pass1)
    gen.generate()

if __name__ == "__main__":
    main()
