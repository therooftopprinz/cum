#!/usr/bin/env python3
from __future__ import annotations
import json
import math
import re
import sys
from ast_normalize import ast_document_to_cpp_state

def cum_primitive_to_py(name: str) -> str:
    """Map naked CUM built-in names used in TD fields to runtime Python names."""
    if name == "string":
        return "str"
    return name

def cum_name_to_py_snake(name: str) -> str:
    """Map C-style PascalCase / mixed identifiers to PEP 8 function suffixes (approximate)."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

def _py_td_class_name(cum_alias: str) -> str:
    """TypedDict class name for a CUM type alias (buffer wrappers, etc.)."""
    if cum_alias.isidentifier():
        return "Td_" + cum_alias
    return "Td_" + re.sub(r"\W", "_", cum_alias)

class PyGenerator:
    def __init__(self, constant, enum_, type_, choice_, sequence_, pass1_expressions):
        self.constant_ = constant
        self.enum_ = enum_
        self.type_ = type_
        self.choice_ = choice_
        self.sequence_ = sequence_
        self.pass1_expressions_ = pass1_expressions

    def _cum_constraint_lines(self, td):
        tc = dict(td)
        tc.pop("optional", None)
        notes = []
        typee = tc["type"]
        veclen = tc.get("dynamic_array")
        arrlen = tc.get("array")
        buflen = tc.get("buffer")
        if veclen is not None:
            if typee == "char":
                notes.append(
                    "CUM dynamic<char,?>: str of at most {} Latin-1 code units.".format(
                        veclen
                    )
                )
            else:
                notes.append(
                    "CUM dynamic sequence: at most {} elements.".format(veclen)
                )
        elif arrlen is not None:
            notes.append(
                "CUM static array: fixed length {!r} (not emitted separately in Python)."
                .format(arrlen)
            )
        elif buflen is not None:
            notes.append(
                "CUM buffer capacity {!r} (element type {}).".format(buflen, typee)
            )
        if td.get("optional"):
            notes.append("CUM optional; use None when absent.")
        return notes

    def _buffer_td_ref(self, alias):
        return _py_td_class_name(alias)

    def _td_plain_inner(self, alias, td_without_optional):
        typee = td_without_optional["type"]
        veclen = td_without_optional.get("dynamic_array")
        arrlen = td_without_optional.get("array")
        buflen = td_without_optional.get("buffer")
        if veclen is not None:
            if typee == "char":
                return "str"
            return "list[{}]".format(typee)
        if arrlen is not None:
            return "list[{}]  # fixed len {!r}".format(typee, arrlen)
        if buflen is not None:
            return self._buffer_td_ref(alias)
        return cum_primitive_to_py(typee)

    def _field_annotation(self, field_type_name: str) -> str:
        if field_type_name in self.type_:
            return self._annotation_for_typedef_alias(field_type_name)
        return cum_primitive_to_py(field_type_name)

    def _annotation_for_typedef_alias(self, alias):
        td = self.type_[alias]
        inner = self._td_plain_inner(
            alias, {k: v for k, v in td.items() if k != "optional"}
        )
        if td.get("optional"):
            return "Optional[" + inner + "]"
        return inner

    def emit_header(self):
        print(
            "# Generated from CUM AST — Python 3 annotated types / IntEnum and PER codecs "
            "(match target_cpp / target_js)."
        )
        print("from __future__ import annotations")
        print("")
        print("from enum import IntEnum")
        print("")
        print("from typing import Optional, TypedDict, Union")
        print("")
        print(
            "from cum.cum import CodecError, PerCodecCtx, check_optional, set_optional, "
            "read_integral_le, write_integral_le"
        )
        print("")
        print("# CUM u8/u16/u32/u64 → Python int (TypedDict annotations)")
        print("u8 = u16 = u32 = u64 = int")
        print("")

    def emit_constant(self, name):
        print("{} = {}\n".format(name, self.constant_[name]))

    def _enum_numeric_values(self, variants):
        next_val = 0
        out = []
        for vn, raw in variants:
            if raw is not None:
                next_val = int(str(raw).strip(), 0)
            out.append((vn, next_val))
            next_val += 1
        return out

    def emit_enumeration(self, name):
        pairs = self._enum_numeric_values(self.enum_[name])
        print("class {}(IntEnum):".format(name))
        for vn, vv in pairs:
            print("    {} = {}".format(vn, vv))
        print("")

    def emit_buffer_td(self, alias):
        td = self.type_[alias]
        if td.get("buffer") is None:
            return
        cls = self._buffer_td_ref(alias)
        notes = self._cum_constraint_lines(td)
        print("class {}(TypedDict):".format(cls))
        if notes:
            print('    """')
            for ln in notes:
                print("    " + ln)
            print('    """')
        print("    len: int")
        print("    buf: bytearray")
        print("")
        print(
            "# runtime alias naming the same structurally as the CUM `using {}`".format(alias)
        )
        print("{} = {}\n".format(alias, cls))

    def emit_using_assign(self, name):
        """Emit a runtime type alias assignment (handles forward refs via PEP 563)."""
        td = self.type_[name]
        ann = self._annotation_for_typedef_alias(name)
        notes = self._cum_constraint_lines(td)
        print("{} = {}  # CUM using {}".format(name, ann, name))
        if notes:
            for ln in notes:
                print("# {}".format(ln))
        print("")

    def emit_sequence(self, name):
        fields = self.sequence_[name]
        print("class {}(TypedDict):".format(name))
        if not fields:
            print("    pass  # CUM empty sequence")
        else:
            for tname, fname in fields:
                ann = self._field_annotation(tname)
                print("    {}: {}".format(fname, ann))
        print("")

    def emit_choice_wrappers(self, name):
        alts = self.choice_[name]
        for ak in alts:
            print("class {}_{}(TypedDict):".format(name, ak))
            print("    {}: {}".format(ak, ak))
            print("")
        parts = ",\n".join("    {}_{}".format(name, ak) for ak in alts)
        print("{} = Union[\n{}\n]\n".format(name, parts))

    def _pure_optional_td(self, td):
        return td.keys() <= {"type", "optional"} and td.get("optional")

    def _optional_mask_octets_sequence(self, sequence_name):
        fields = self.sequence_[sequence_name]
        nop = sum(
            1 for t, _ in fields if t in self.type_ and self.type_[t].get("optional")
        )
        if nop <= 0:
            return None
        return int(math.ceil(nop / 8.0))

    def _cum_int_literal(self, raw):
        s = str(raw).strip()
        if (
            ")" in s
            or ("+" in s and not s.startswith("+"))
            or ("-" in s[1:] if s.startswith("-") else "-" in s)
            or "*" in s
        ):
            raise RuntimeError("unsupported numeric expr {!r}".format(raw))
        return int(s, 0) if len(s) >= 2 and s[:2].lower() in ("0x", "0o", "0b") else int(s)

    _PRIMITIVE_FIELDS = frozenset({"u8", "u16", "u32", "u64"})

    def _emit_packed_primitive_helpers(self):
        """PER codecs for naked u8/u16/u32/u64 and Latin-1 C strings (sequence / dynamic<u8>)."""
        print("# Unsigned fixed-width scalars (LE; match target_cpp on LE hosts)")
        for n, nbytes in (("u8", 1), ("u16", 2), ("u32", 4), ("u64", 8)):
            print("def encode_using_{0}(v, ctx: PerCodecCtx) -> None:".format(n))
            if nbytes == 1:
                print("    ctx.write_u8(int(v))")
            else:
                mod = 1 << (8 * nbytes)
                print("    if not isinstance(ctx.buf, bytearray):")
                print("        raise CodecError('encode requires a bytearray backing')")
                print(
                    "    vv = int(v) % {}\n".format(mod)
                    + "    write_integral_le(ctx.buf, ctx.off, vv, {})".format(nbytes)
                )
                print("    ctx.off += {}".format(nbytes))
            print("")
            print("def decode_using_{0}(ctx: PerCodecCtx) -> int:".format(n))
            if nbytes == 1:
                print("    return ctx.read_u8()")
            else:
                print("    if ctx.remaining() < {}:".format(nbytes))
                print("        raise CodecError('decode overrun')")
                print(
                    "    v = read_integral_le(ctx.buf, ctx.off, {})".format(nbytes)
                )
                print("    ctx.off += {}".format(nbytes))
                print("    return int(v)")
            print("")

        print("def encode_using_string(v: str, ctx: PerCodecCtx) -> None:")
        print("    ctx.encode_c_string_latin1(v)")
        print("")
        print("def decode_using_string(ctx: PerCodecCtx) -> str:")
        print("    return ctx.decode_c_string_latin1()")
        print("")

    def emit_enum_codec(self, name):
        sn = cum_name_to_py_snake(name)
        print(
            "def encode_using_{}(v: int, ctx: PerCodecCtx) -> None:\n".format(sn)
            + "    ctx.write_i32le(int(v))"
        )
        print("")
        print(
            "def decode_using_{}(ctx: PerCodecCtx) -> {}:\n".format(sn, name)
            + "    return {}(int(ctx.read_i32le()))".format(name)
        )
        print("")

    def emit_using_codec(self, alias):
        td = self.type_[alias]
        if self._pure_optional_td(td):
            return
        sn = cum_name_to_py_snake(alias)
        elem_type = td["type"]
        dyn = td.get("dynamic_array")
        buf_cap = td.get("buffer")

        if dyn is not None:
            mx = self._cum_int_literal(dyn)
            print("def encode_using_{}(obj, ctx: PerCodecCtx) -> None:".format(sn))
            print(
                "    if len(obj) > {}: raise CodecError('{!s}')"
                .format(mx, alias)
            )
            print("    ctx.write_count({}, len(obj))".format(mx))
            if elem_type == "char":
                print("    for ch in obj:")
                print(
                    "        cp = ord(ch)\n"
                    "        if cp > 255: raise CodecError('non Latin-1 in {!s}')"
                    .format(alias)
                )
                print("        ctx.write_u8(cp)")
            else:
                print("    for it in obj:")
                print(
                    "        encode_using_{}(it, ctx)".format(cum_name_to_py_snake(elem_type))
                )
            print("")
            print("def decode_using_{}(ctx: PerCodecCtx):".format(sn))
            print("    n = ctx.read_count({})".format(mx))
            if elem_type == "char":
                print("    parts = []\n    for _ in range(n):")
                print("        parts.append(chr(ctx.read_u8()))")
                print("    return ''.join(parts)")
            else:
                print("    arr = []\n    for _ in range(n):")
                print(
                    "        arr.append(decode_using_{}(ctx))"
                    .format(cum_name_to_py_snake(elem_type))
                )
                print("    return arr")
            print("")
            return

        if buf_cap is not None:
            cap = self._cum_int_literal(buf_cap)
            print("def encode_using_{}(bp, ctx: PerCodecCtx) -> None:".format(sn))
            print(
                "    if bp['len'] > {}: raise CodecError('{!s} len')"
                .format(cap, alias)
            )
            print(
                "    ctx.write_count({}, bp['len'])\n"
                "    mv = memoryview(bp['buf'])\n"
                "    ctx.write_bytes(mv[:bp['len']], bp['len'])".format(cap)
            )
            print("")
            print("def decode_using_{}(ctx: PerCodecCtx):".format(sn))
            print("    cap = {}".format(cap))
            print("    ln = ctx.read_count(cap)")
            print("    out_buf = bytearray(cap)")
            print("    blob = ctx.read_bytes(ln)")
            print(
                "    if ln:\n"
                "        out_buf[:ln] = blob\n"
                "    return {'len': ln, 'buf': out_buf}"
            )
            print("")
            return

        if td.get("array") is not None:
            if elem_type == "u8":
                mx = self._cum_int_literal(td["array"])
                print("def encode_using_{}(obj, ctx: PerCodecCtx) -> None:".format(sn))
                print(
                    "    if len(obj) != {}: raise CodecError('{!s} length')"
                    .format(mx, alias)
                )
                print("    ctx.write_count({}, len(obj))".format(mx))
                print("    for it in obj:")
                print("        encode_using_u8(it, ctx)")
                print("")
                print("def decode_using_{}(ctx: PerCodecCtx):".format(sn))
                print("    n = ctx.read_count({})".format(mx))
                print("    arr = []")
                print("    for _ in range(n):")
                print("        arr.append(decode_using_u8(ctx))")
                print("    return arr")
                print("")
                return
            raise RuntimeError("static arrays are not emitted for {}".format(alias))

        if elem_type == "string":
            # Emitted once in _emit_packed_primitive_helpers as encode_using_string.
            return

        raise RuntimeError("cannot emit Python codec for using {} (= {!r})".format(alias, td))

    def _encode_optional_field_inline(self, tname, fld_access):
        td = dict(self.type_[tname])
        if not td.get("optional"):
            raise RuntimeError("expected optional {}".format(tname))
        td.pop("optional", None)
        inn = td["type"]
        sn_inner = cum_name_to_py_snake(inn)
        print("    if {} is not None:".format(fld_access))

        if td.keys() <= {"type"} and inn == "string":
            print("        encode_using_string({}, ctx)".format(fld_access))
            return

        if len(td) != 1 or "type" not in td:
            raise RuntimeError("complex optional {}".format(td))

        if inn in self.type_:
            print(
                "        encode_using_{}({}, ctx)"
                .format(sn_inner, fld_access)
            )
        elif inn in self.sequence_ or inn in self.choice_ or inn in self.enum_:
            print(
                "        encode_using_{}({}, ctx)"
                .format(sn_inner, fld_access)
            )
        else:
            raise RuntimeError("optional inner {!r}".format(td))

    def _decode_optional_field_inline(self, tname, fld_access, oid):
        td = dict(self.type_[tname])
        td.pop("optional", None)
        inn = td["type"]
        sn_inner = cum_name_to_py_snake(inn)
        print("    if check_optional(optional_mask, {}):".format(oid))
        if td.keys() <= {"type"} and inn == "string":
            print(
                "        {} = decode_using_string(ctx)"
                .format(fld_access)
            )
        elif inn in self.type_ or inn in self.sequence_ or inn in self.choice_ or inn in self.enum_:
            print(
                "        {} = decode_using_{}(ctx)"
                .format(fld_access, sn_inner)
            )
        else:
            raise RuntimeError("optional decode {!r}".format(td))
        print("    else:")
        print("        {} = None".format(fld_access))

    def _encode_mandatory_typedef_alias(self, tname, fld_access):
        if tname not in self.type_:
            raise RuntimeError("unknown mandatory field typedef {}".format(tname))
        if self.type_[tname].get("optional"):
            raise RuntimeError("misclassified optional {}".format(tname))
        td = dict(self.type_[tname])
        sn_t = cum_name_to_py_snake(tname)

        dv = td.get("dynamic_array")
        if dv is not None and td["type"] == "char":
            mx = self._cum_int_literal(dv)
            print(
                "    if len({}) > {}: raise CodecError('{!s}')"
                .format(fld_access, mx, tname)
            )

        buf = td.get("buffer")
        if buf is not None:
            cap = self._cum_int_literal(buf)
            print(
                "    if {}['len'] > {}: raise CodecError('{!s}')"
                .format(fld_access, cap, tname)
            )

        print("    encode_using_{}({}, ctx)".format(sn_t, fld_access))

    def _encode_one_field_ordered(self, tname, fname):
        fa = 'pie["{}"]'.format(fname)
        sn = cum_name_to_py_snake(tname)
        if tname in self.type_ and self.type_[tname].get("optional"):
            self._encode_optional_field_inline(tname, fa)
            return
        if tname in self._PRIMITIVE_FIELDS:
            print("    encode_using_{}({}, ctx)".format(tname, fa))
            return
        if tname == "string":
            print("    encode_using_string({}, ctx)".format(fa))
            return
        if tname in self.type_:
            self._encode_mandatory_typedef_alias(tname, fa)
        elif tname in self.enum_ or tname in self.sequence_ or tname in self.choice_:
            print("    encode_using_{}({}, ctx)".format(sn, fa))
        else:
            raise RuntimeError("{}.{} unsupported type {}".format(fname, fname, tname))

    def emit_sequence_codec(self, name):
        flds = self.sequence_[name]
        mask_oct = self._optional_mask_octets_sequence(name)
        sn = cum_name_to_py_snake(name)
        print("# Codec: sequence {}".format(name))
        print("def encode_using_{}(pie, ctx: PerCodecCtx) -> None:".format(sn))
        if mask_oct is not None:
            print(
                "    optional_mask = bytearray({})".format(mask_oct)
            )
            oid = 0
            for tname, fname in flds:
                if tname in self.type_ and self.type_[tname].get("optional"):
                    fa = 'pie["{}"]'.format(fname)
                    print("    if {} is not None:".format(fa))
                    print("        set_optional(optional_mask, {})".format(oid))
                    oid += 1
            print("    ctx.write_bytes(optional_mask, len(optional_mask))")
        for tname, fname in flds:
            self._encode_one_field_ordered(tname, fname)
        print("")
        print("def decode_using_{}(ctx: PerCodecCtx):".format(sn))
        print("    pie = {}".format("{}"))
        if mask_oct is not None:
            print(
                "    optional_mask = ctx.read_bytes({})".format(mask_oct)
            )
        oid = 0
        for tname, fname in flds:
            fa = 'pie["{}"]'.format(fname)
            if tname in self.type_ and self.type_[tname].get("optional"):
                self._decode_optional_field_inline(tname, fa, oid)
                oid += 1
                continue
            snt = cum_name_to_py_snake(tname)
            if tname in self._PRIMITIVE_FIELDS:
                print("    {} = decode_using_{}(ctx)".format(fa, tname))
            elif tname == "string":
                print("    {} = decode_using_string(ctx)".format(fa))
            elif tname in self.type_ or tname in self.enum_ or tname in self.sequence_ or tname in self.choice_:
                print("    {} = decode_using_{}(ctx)".format(fa, snt))
            else:
                raise RuntimeError("{} decode {}".format(fname, tname))
        print("    return pie")
        print("")

    def emit_choice_codec(self, name):
        alts = self.choice_[name]
        sn = cum_name_to_py_snake(name)
        print("# Codec: choice {}".format(name))
        print("def encode_using_{}(pie, ctx: PerCodecCtx) -> None:".format(sn))
        for idx, ak in enumerate(alts):
            head = "if" if idx == 0 else "elif"
            print(
                "    {} {!r} in pie and pie[{!r}] is not None:"
                .format(head, ak, ak)
            )
            print("        ctx.write_choice_index({}, {})".format(len(alts), idx))
            print(
                "        encode_using_{}(pie[{!r}], ctx)"
                .format(cum_name_to_py_snake(ak), ak)
            )
            print("        return")
        print(
            "    raise CodecError('encode_using_{}: exactly one discriminant key expected')"
            .format(sn)
        )
        print("")
        print("def decode_using_{}(ctx: PerCodecCtx):".format(sn))
        print("    idx = ctx.read_choice_index({})".format(len(alts)))
        for idx, ak in enumerate(alts):
            kw = "if" if idx == 0 else "elif"
            print("    {} idx == {}:".format(kw, idx))
            print(
                "        return {{{!r}: decode_using_{}(ctx)}}"
                .format(ak, cum_name_to_py_snake(ak))
            )
        print("    raise CodecError('bad choice index')")
        print("")

    def generate(self):
        self.emit_header()
        # Declaration stream matches .cum source order so type aliases resolve.
        for kind, nm, _ in self.pass1_expressions_:
            if kind == "constant":
                self.emit_constant(nm)
            elif kind == "enumeration":
                self.emit_enumeration(nm)
            elif kind == "using":
                td = self.type_[nm]
                if td.get("buffer") is not None:
                    self.emit_buffer_td(nm)
                else:
                    self.emit_using_assign(nm)
            elif kind == "sequence":
                self.emit_sequence(nm)
            elif kind == "choice":
                self.emit_choice_wrappers(nm)

        print("# --- Packed encoding (PER-byte aligned, enums as i32 LE) ---\n")

        self._emit_packed_primitive_helpers()

        for kind, nm, _ in self.pass1_expressions_:
            if kind == "enumeration":
                self.emit_enum_codec(nm)
            elif kind == "using":
                self.emit_using_codec(nm)

        for kind, nm, _ in self.pass1_expressions_:
            if kind == "sequence":
                self.emit_sequence_codec(nm)
            elif kind == "choice":
                self.emit_choice_codec(nm)

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
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(
            "ast_to_py: invalid JSON (line {} column {}): {}\n".format(
                e.lineno, e.colno, e.msg
            )
        )
        if raw.strip():
            sys.stderr.write("First input fragment: {!r}\n".format(raw[:160]))
        else:
            sys.stderr.write(
                "(empty stdin — pipe JSON from ./generator/cum_to_ast.py file.cum)\n"
            )
        sys.exit(1)
    const_, enum_, type_, choice_, seq_, pass1 = ast_document_to_cpp_state(doc)
    gen = PyGenerator(const_, enum_, type_, choice_, seq_, pass1)
    gen.generate()

if __name__ == "__main__":
    main()
