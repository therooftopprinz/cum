#!/usr/bin/env python3
"""Parse a .cum definition file and print its AST as JSON to stdout."""

import json
import re
import sys


def preprocess(raw: str) -> list[str]:
    content = re.sub(r"//.*[\r]*\n", "", raw)
    content = re.sub(r"[\r]*\n", "", content)
    return content.split(";")


def take_angle_inner(s: str, open_paren: int) -> str:
    """Return content between s[open_paren]=='<' and its matching '>'."""
    if open_paren >= len(s) or s[open_paren] != "<":
        raise ValueError("expected '<'")
    depth = 0
    i = open_paren
    while i < len(s):
        c = s[i]
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
            if depth == 0:
                return s[open_paren + 1 : i]
        i += 1
    raise ValueError("unclosed '<' in type expression")


def split_top_level_comma(inner: str) -> tuple[str, str]:
    """Split inner on first comma that is not inside nested angle brackets."""
    depth = 0
    for i, c in enumerate(inner):
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
        elif c == "," and depth == 0:
            left, right = inner[:i].strip(), inner[i + 1 :].strip()
            return left, right
    raise ValueError("expected ',' in generic type")


def parse_size_expr(s: str):
    raw = s.strip()
    if re.fullmatch(r"-?\d+", raw):
        return {"kind": "literal", "raw": raw}
    return {"kind": "name", "name": raw}


def parse_type_expr(rhs: str):
    rhs = rhs.strip()
    generics = ("optional", "dynamic", "static", "buffer")
    for gen in generics:
        prefix = gen + "<"
        if rhs.startswith(prefix):
            open_i = rhs.index("<")
            inner = take_angle_inner(rhs, open_i).strip()

            if gen == "optional":
                return {"kind": "optional", "inner": parse_type_expr(inner)}

            elem_s, dim_s = split_top_level_comma(inner)
            elem = parse_type_elem(elem_s)
            dim = parse_size_expr(dim_s)
            if gen == "dynamic":
                return {"kind": "dynamic", "element": elem, "max": dim}
            if gen == "static":
                return {"kind": "static", "element": elem, "size": dim}
            return {"kind": "buffer", "element": elem, "capacity": dim}

    return {"kind": "named", "name": rhs}


def parse_type_elem(s: str):
    """Element position in generic wrappers: reuse full TypeExpr rules."""
    return parse_type_expr(s)


def split_declarations(expr: str):
    m = re.match(r"^\s*$", expr)
    if m:
        return None
    m = re.match(r"([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*(.*)", expr)
    if m is None:
        return None
    return (m.group(1).strip(), m.group(2).strip(), m.group(3).strip())


def parse_constant(name: str, tail: str):
    val = tail.lstrip("=").strip()
    return {
        "kind": "constant",
        "name": name,
        "value": {"raw": val},
    }


def parse_enumeration(name: str, tail: str):
    body = tail.lstrip("{").rstrip("}").strip()
    parts = [p.strip() for p in body.split(",") if p.strip()]
    variants = []
    for p in parts:
        if "=" in p:
            n, _, v = p.partition("=")
            variants.append(
                {"name": n.strip(), "value": {"raw": v.strip()}}
            )
        else:
            variants.append({"name": p.strip(), "value": None})
    return {"kind": "enumeration", "name": name, "variants": variants}


def parse_using(name: str, tail: str):
    rhs = tail.lstrip("=").strip()
    return {
        "kind": "using",
        "name": name,
        "type": parse_type_expr(rhs),
    }


def parse_choice(name: str, tail: str):
    body = tail.lstrip("{").rstrip("}").strip()
    alts = [a.strip() for a in body.split(",") if a.strip()]
    return {
        "kind": "choice",
        "name": name,
        "alternatives": [{"name": a} for a in alts],
    }


def parse_sequence(name: str, tail: str):
    body = tail.lstrip("{").rstrip("}").strip()
    bits = [b.strip() for b in body.split(",") if b.strip()]
    fields = []
    for bit in bits:
        m = re.match(r"^(.*?)[ \t]+([A-Za-z0-9_]+)$", bit)
        if m is None:
            raise RuntimeError(
                "sequence {}: cannot parse field {!r}".format(name, bit)
            )
        type_name = m.group(1).strip()
        field_name = m.group(2).strip()
        fields.append({"type": {"name": type_name}, "name": field_name})
    return {"kind": "sequence", "name": name, "fields": fields}


def declaration_for(keyword: str, name: str, tail: str):
    if keyword == "constant":
        return parse_constant(name, tail)
    if keyword == "enumeration":
        return parse_enumeration(name, tail)
    if keyword == "using":
        return parse_using(name, tail)
    if keyword == "choice":
        return parse_choice(name, tail)
    if keyword == "sequence":
        return parse_sequence(name, tail)
    return None


def parse_document(expressions):
    declarations = []
    for raw in expressions:
        expr = raw.strip()
        if not expr:
            continue
        sp = split_declarations(expr)
        if sp is None:
            continue
        keyword, name, tail = sp
        decl = declaration_for(keyword, name, tail)
        if decl is not None:
            declarations.append(decl)
    return {"kind": "document", "declarations": declarations}


def main():
    prog = sys.argv[0]
    if len(sys.argv) > 2:
        sys.stderr.write("usage: {} [cum file]\n".format(prog))
        sys.exit(2)
    if len(sys.argv) == 2:
        with open(sys.argv[1], encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()
    expressions = preprocess(raw)
    doc = parse_document(expressions)
    sys.stdout.write(json.dumps(doc, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
