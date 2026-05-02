#!/usr/bin/env python3
"""Parse a .cum definition file and print its AST as JSON to stdout."""

import json
import re
import sys


def strip_c_style_comments(raw: str) -> str:
    """Remove // line comments and /* */ block comments (C/C++-style)."""
    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        if i + 1 < n:
            two = raw[i : i + 2]
            if two == "//":
                i += 2
                while i < n and raw[i] != "\n":
                    i += 1
                continue
            if two == "/*":
                i += 2
                while i + 1 < n and raw[i : i + 2] != "*/":
                    i += 1
                if i + 1 >= n:
                    raise ValueError("unclosed block comment (missing '*/')")
                i += 2
                continue
        out.append(raw[i])
        i += 1
    return "".join(out)


def collapse_ws(raw: str) -> str:
    return re.sub(r"\s+", " ", strip_c_style_comments(raw)).strip()


def skip_ws(s: str, i: int) -> int:
    n = len(s)
    while i < n and s[i] in " \t\r\n":
        i += 1
    return i


def read_identifier(s: str, i: int) -> tuple[str, int]:
    start = i
    n = len(s)
    while i < n and (s[i].isalnum() or s[i] == "_"):
        i += 1
    if i == start:
        raise ValueError("expected identifier at {!r}".format(s[max(0, start - 8) : start + 24]))
    return s[start:i], i


def find_matching_brace(s: str, open_idx: int) -> int:
    if open_idx >= len(s) or s[open_idx] != "{":
        raise ValueError("expected '{{' at {}".format(open_idx))
    depth = 1
    i = open_idx + 1
    while i < len(s) and depth:
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise ValueError("unbalanced '{{' in {!r}...".format(s[open_idx : open_idx + 40]))
    return i


def scan_type_until_semicolon(s: str, start: int) -> int:
    """Scan from first char of type expr through terminating ';' (outside nested '<>')."""
    depth = 0
    i = start
    while i < len(s):
        c = s[i]
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
        elif c == ";" and depth == 0:
            return i + 1
        i += 1
    raise ValueError("unterminated using / type (missing ';')")


def parse_constant_tail_end(s: str, start: int) -> int:
    """After 'constant', parse name = value; return index after ';'."""
    i = skip_ws(s, start)
    _, i = read_identifier(s, i)
    i = skip_ws(s, i)
    if i >= len(s) or s[i] != "=":
        raise ValueError("constant: expected '='")
    i += 1
    while i < len(s) and s[i] != ";":
        i += 1
    if i >= len(s):
        raise ValueError("constant: missing ';'")
    return i + 1


def parse_using_tail_end(s: str, start: int) -> int:
    """After 'using', parse name = TypeExpr; return index after ';'."""
    i = skip_ws(s, start)
    _, i = read_identifier(s, i)
    i = skip_ws(s, i)
    if i >= len(s) or s[i] != "=":
        raise ValueError("using: expected '='")
    i += 1
    i = skip_ws(s, i)
    return scan_type_until_semicolon(s, i)


def parse_block_keyword_tail_end(s: str, start: int, kw: str) -> int:
    """After enumeration|choice|sequence keyword: Name { ... }; (C/C++-style closing)."""
    i = skip_ws(s, start)
    _, i = read_identifier(s, i)
    i = skip_ws(s, i)
    if i >= len(s) or s[i] != "{":
        raise ValueError("{}: expected '{{' before body".format(kw))
    i = find_matching_brace(s, i)
    i = skip_ws(s, i)
    if i >= len(s) or s[i] != ";":
        raise ValueError(kw + ": expected ';' after '}' (close blocks like };)")
    i += 1
    return i


def split_top_level_declarations(s: str) -> list[str]:
    decls = []
    i = 0
    n = len(s)
    while i < n:
        i = skip_ws(s, i)
        if i >= n:
            break
        start = i
        if s.startswith("constant", i) and (i + 8 == n or not (s[i + 8].isalnum() or s[i + 8] == "_")):
            i = parse_constant_tail_end(s, i + len("constant"))
        elif s.startswith("enumeration", i) and (
            i + 11 == n or not (s[i + 11].isalnum() or s[i + 11] == "_")
        ):
            i = parse_block_keyword_tail_end(s, i + len("enumeration"), "enumeration")
        elif s.startswith("using", i) and (i + 5 == n or not (s[i + 5].isalnum() or s[i + 5] == "_")):
            i = parse_using_tail_end(s, i + len("using"))
        elif s.startswith("choice", i) and (i + 6 == n or not (s[i + 6].isalnum() or s[i + 6] == "_")):
            i = parse_block_keyword_tail_end(s, i + len("choice"), "choice")
        elif s.startswith("sequence", i) and (i + 8 == n or not (s[i + 8].isalnum() or s[i + 8] == "_")):
            i = parse_block_keyword_tail_end(s, i + len("sequence"), "sequence")
        else:
            raise ValueError(
                "parse error at {!r}: expected top-level declaration keyword".format(
                    s[i : min(n, i + 40)]
                )
            )
        decls.append(s[start:i].strip())
    return decls


def preprocess(raw: str) -> list[str]:
    return split_top_level_declarations(collapse_ws(raw))


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
    val = tail.lstrip("=").strip().rstrip(";").strip()
    return {
        "kind": "constant",
        "name": name,
        "value": {"raw": val},
    }


def extract_braced_inner(tail: str) -> str:
    """Tail begins with optional ws then '{'; return inner between outermost braces."""
    t = tail.strip()
    i = skip_ws(t, 0)
    if i >= len(t) or t[i] != "{":
        raise ValueError("expected '{{' after name, got {!r}".format(tail[:80]))
    end_after = find_matching_brace(t, i)
    return t[i + 1 : end_after - 1]


def split_body_list_items(body: str, *, allow_semicolon: bool = True) -> list[str]:
    """Split body on ',' and optionally ';' at depth 0 outside nested '<>'."""
    depth = 0
    parts = []
    start = 0
    body = body.strip()
    for i, c in enumerate(body):
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
            if depth < 0:
                raise ValueError("invalid type nesting in body")
        elif depth == 0:
            if c == "," or (allow_semicolon and c == ";"):
                chunk = body[start:i].strip()
                if chunk:
                    parts.append(chunk)
                start = i + 1
    tail = body[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def parse_enumeration(name: str, tail: str):
    body = extract_braced_inner(tail).strip()
    parts = split_body_list_items(body, allow_semicolon=False)
    variants = []
    for p in parts:
        if "=" in p:
            n, _, v = p.partition("=")
            variants.append({"name": n.strip(), "value": {"raw": v.strip()}})
        else:
            variants.append({"name": p.strip(), "value": None})
    return {"kind": "enumeration", "name": name, "variants": variants}


def parse_using(name: str, tail: str):
    rhs = tail.lstrip("=").strip().rstrip(";").strip()
    return {
        "kind": "using",
        "name": name,
        "type": parse_type_expr(rhs),
    }


def parse_choice(name: str, tail: str):
    body = extract_braced_inner(tail).strip()
    alts = split_body_list_items(body, allow_semicolon=False)
    return {
        "kind": "choice",
        "name": name,
        "alternatives": [{"name": a} for a in alts],
    }


def parse_sequence(name: str, tail: str):
    body = extract_braced_inner(tail).strip()
    bits = split_body_list_items(body)
    fields = []
    for bit in bits:
        m = re.match(r"^(.*?)[ \t]+([A-Za-z0-9_]+)$", bit)
        if m is None:
            raise RuntimeError("sequence {}: cannot parse field {!r}".format(name, bit))
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
