#!/usr/bin/python

import re
import sys

from cpp_generator import CppGenerator


def _preprocess(content):
    content = re.sub(r"//.*[\r]*\n", "", content)
    content = re.sub(r"[\r]*\n", "", content)
    return content.split(";")

class ExpressionParser:
    def __init__(self):
        self.constant_ = {}
        self.enum_     = {}
        self.type_     = {}
        self.choice_   = {}
        self.sequence_ = {}
        self.pass1_expressions_ = []

    def processConstant(self, name, data):
        data = data.lstrip("=").strip()
        print ("// Constant: ", (name, data))
        self.constant_[name] = data;

    def processEnumeration(self, name, data):
        data = data.lstrip("{").rstrip("}")
        data = [i.strip() for i in data.split(",")]
        self.enum_[name] = []
        for i in data:
            match = re.match(r"^([A-Za-z0-9_]+)\s*(?:=\s*([A-Za-z0-9_\-]+))*", i)
            i = (match.group(1), match.group(2))
            self.enum_[name].append(i)
            print ("// Enumeration: ", (name, i))

    def processUsing(self, name, data):
        rhs = data.lstrip("=").strip()
        td = {}

        def set_and_log():
            self.type_[name] = td
            print("// Using: ", (name, td))

        m = re.match(r"^optional<([^>]+)>$", rhs)
        if m:
            td["type"] = m.group(1).strip()
            td["optional"] = True
            return set_and_log()

        for mod, field in (
            ("dynamic", "dynamic_array"),
            ("static", "array"),
            ("buffer", "buffer"),
        ):
            m = re.match(
                r"^{}<([^,]+),\s*([^>]+)>$".format(re.escape(mod)), rhs
            )
            if m:
                td["type"] = m.group(1).strip()
                td[field] = m.group(2).strip()
                return set_and_log()

        td["type"] = rhs
        set_and_log()

    def processChoice(self, name, data):
        data = data.lstrip("{").rstrip("}")
        data = [i.strip() for i in data.split(",")]
        self.choice_[name] = []
        for i in data:
            self.choice_[name].append(i)
            print ("// Choice: ", (name, i))

    def processSequence(self, name, data):
        data = data.lstrip("{").rstrip("}")
        data = [i.strip() for i in data.split(",")]
        self.sequence_[name] = []
        for i in data:
            match = re.match(r"^(.*?)[ \t]+(.*?)$", i)
            if match is None:
                print ("// Pattern not found in '{}' ".format(i))
                raise RuntimeError("processing error: " + str(name) + " : " + str(data))
            t = match.group(1)
            n = match.group(2)
            self.sequence_[name].append((t, n))
            print ("// Sequence: ", name, (t, n))

    def pass1(self, expressions):
        for i in expressions:
            i = i.strip()
            match = re.match(r"([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*(.*)", i);
            if match is None:
                continue
            t = match.group(1).strip()
            n = match.group(2).strip()
            v = match.group(3).strip()

            # print ("// Expression: {} | t={} | n={} | v={}".format(i, t, n, v))

            self.pass1_expressions_.append((t,n,v))

            if (t == "constant"):
                self.processConstant(n, v)
            elif (t == "enumeration"):
                self.processEnumeration(n, v)
            elif (t == "using"):
                self.processUsing(n, v)
            elif (t == "choice"):
                self.processChoice(n, v)
            elif (t == "sequence"):
                self.processSequence(n, v)

    def parse(self, expressions):
        self.pass1(expressions)
        generator = CppGenerator(self.constant_, self.enum_, self.type_, self.choice_, self.sequence_, self.pass1_expressions_)
        generator.generate()


def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        sys.stderr.write("usage: {} <cum file>\n".format(argv[0]))
        sys.exit(2)
    filename = argv[1]
    with open(filename, mode="r") as f:
        content = f.read()
    expressions = _preprocess(content)
    parser = ExpressionParser()
    parser.parse(expressions)


if __name__ == "__main__":
    main()
