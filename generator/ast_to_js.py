#!/usr/bin/env python3
import json
import math
import sys
from ast_normalize import ast_document_to_cpp_state

class JsGenerator:
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
                notes.append("CUM dynamic<char,?>: treat as string, max {} code units.".format(veclen))
            else:
                notes.append("CUM dynamic: max {} elements.".format(veclen))
        elif arrlen is not None:
            notes.append("CUM static array: fixed length {}.".format(arrlen))
        elif buflen is not None:
            notes.append(
                "CUM buffer capacity {} (element type {}).".format(buflen, typee)
            )
        if td.get("optional"):
            notes.append("CUM optional: null when absent.")
        return notes

    def _td_plain_inner(self, td_without_optional):
        typee = td_without_optional["type"]
        veclen = td_without_optional.get("dynamic_array")
        arrlen = td_without_optional.get("array")
        buflen = td_without_optional.get("buffer")
        if veclen is not None:
            if typee == "char":
                return "string"
            return "Array<{!s}>".format(typee)
        if arrlen is not None:
            return "ReadonlyArray<{!s}>".format(typee)
        if buflen is not None:
            if typee == "byte":
                return "{ len: number, buf: Uint8Array }"
            return "{ len: number, buf: ArrayBufferView }"
        return typee

    def _td_jsdoc_type(self, td):
        tc = dict(td)
        optional = tc.pop("optional", None)
        inner = self._td_plain_inner(tc)
        if optional:
            return "({} | null)".format(inner)
        return inner

    def emit_constant(self, name):
        print("/** @readonly */")
        print("export const {} = {};".format(name, self.constant_[name]))
        print("")

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
        print("/**")
        print(" * @enum {number}")
        print(" */")
        print("export const {} = Object.freeze({{".format(name))
        for i, (n, v) in enumerate(pairs):
            comma = "," if i < len(pairs) - 1 else ""
            print("    {}: {}{}".format(n, v, comma))
        print("});")
        print("")

    def emit_using(self, name):
        td = self.type_[name]
        js_t = self._td_jsdoc_type(td)
        notes = self._cum_constraint_lines(td)
        if notes:
            print("/**")
            for ln in notes:
                print(" * {}".format(ln))
            print(" * @typedef {{{}}} {}".format(js_t, name))
            print(" */")
            print("")
        else:
            print("/** @typedef {{{}}} {} */".format(js_t, name))
            print("")

    def emit_choice(self, name):
        alts = self.choice_[name]
        union = " | ".join(alts)
        print("/** @typedef {{{}}} {} */".format(union, name))
        print("")

    def emit_sequence(self, name):
        fields = self.sequence_[name]
        print("/**")
        print(" * @typedef {{Object}} {}".format(name))
        for tname, fname in fields:
            if tname in self.type_:
                td = self.type_[tname]
                jt = self._td_jsdoc_type(td)
                optional = bool(self.type_[tname].get("optional"))
            else:
                jt = tname
                optional = False
            if optional:
                print(" * @property {{{}}} [{}]".format(jt, fname))
            else:
                print(" * @property {{{}}} {}".format(jt, fname))
        print(" */")
        print("")

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

    def emit_runtime_import(self):
        print(
            'import { CodecError, PerCodecCtx, checkOptional, setOptional } '
            'from "../cum/cum.mjs";'
        )
        print("")

    def emit_enum_codec(self, name):
        print("/** @param {typeof %s[keyof %s]} v */" % (name, name))
        print("export function encodeUsing_{}(v, ctx) {{".format(name))
        print("    ctx.writeI32LE(v);")
        print("}")
        print("")
        print("/** @return {typeof %s[keyof %s]} */" % (name, name))
        print("export function decodeUsing_{}(ctx) {{".format(name))
        print("    return ctx.readI32LE();")
        print("}")
        print("")

    def emit_using_codec(self, alias):
        td = self.type_[alias]
        if self._pure_optional_td(td):
            return
        print("// Codec: typedef {}".format(alias))
        elem_type = td["type"]
        dyn = td.get("dynamic_array")
        buf_cap = td.get("buffer")

        if dyn is not None:
            mx = self._cum_int_literal(dyn)
            print("export function encodeUsing_{}(arr, ctx) {{".format(alias))
            print("    if (arr.length > {}) throw new CodecError('{}');".format(mx, alias))
            print("    ctx.writeCount({}, arr.length);".format(mx))
            if elem_type == "char":
                print("    for (let _i = 0; _i < arr.length; _i++) {")
                print("        const cp = arr.charCodeAt(_i);")
                print(
                    "        if (cp > 255) throw new CodecError('non Latin-1 in {}');".format(
                        alias
                    )
                )
                print("        ctx.writeU8(cp);")
                print("    }")
            else:
                print("    for (let _i = 0; _i < arr.length; _i++) encodeUsing_%s(arr[_i], ctx);"
                      % elem_type)
            print("}")
            print("")
            print("export function decodeUsing_{}(ctx) {{".format(alias))
            print("    const n = ctx.readCount({});".format(mx))
            if elem_type == "char":
                print("    let out = '';")
                print("    for (let j = 0; j < n; j++) out += String.fromCharCode(ctx.readU8());")
                print("    return out;")
            else:
                print("    const arr = [];")
                print("    for (let k = 0; k < n; k++) arr.push(decodeUsing_{}(ctx));".format(elem_type))
                print("    return arr;")
            print("}")
            print("")
            return

        if buf_cap is not None:
            cap = self._cum_int_literal(buf_cap)
            print("export function encodeUsing_{}(bp, ctx) {{".format(alias))
            print("    if (bp.len > {}) throw new CodecError('{} len');".format(cap, alias))
            print("    ctx.writeCount({}, bp.len);".format(cap))
            print("    ctx.writeBytes(bp.buf.subarray(0, bp.len), bp.len);")
            print("}")
            print("")
            print("export function decodeUsing_{}(ctx) {{".format(alias))
            print("    const cap = {};".format(cap))
            print("    const len = ctx.readCount(cap);")
            print("    const out = { len, buf: new Uint8Array(cap) };")
            print("    if (len) out.buf.set(ctx.readBytes(len), 0);")
            print("    return out;")
            print("}")
            print("")
            return

        if td.get("array") is not None:
            raise RuntimeError("static arrays are not emitted for {}".format(alias))

        if elem_type == "string":
            print("export function encodeUsing_{}(v, ctx) {{".format(alias))
            print("    ctx.encodeCStringLatin1(v);")
            print("}")
            print("")
            print("export function decodeUsing_{}(ctx) {{".format(alias))
            print("    return ctx.decodeCStringLatin1();")
            print("}")
            print("")
            return

        raise RuntimeError("cannot emit JS codec for using {} (= {!r})".format(alias, td))

    def _encode_optional_field_inline(self, tname, fld_access):
        td = dict(self.type_[tname])
        if not td.get("optional"):
            raise RuntimeError("expected optional {}".format(tname))
        td.pop("optional", None)

        inn = td["type"]
        print(
            "    if ({} !== null && {} !== undefined) {{".format(fld_access, fld_access)
        )

        if td.keys() <= {"type"} and inn == "string":
            print("        encodeUsing_String({}, ctx);".format(fld_access))
            print("    }")
            return

        if len(td) != 1 or "type" not in td:
            raise RuntimeError("complex optional {}".format(td))

        if inn in self.type_:
            print("        encodeUsing_{}({}, ctx);".format(inn, fld_access))
        elif inn in self.sequence_ or inn in self.choice_ or inn in self.enum_:
            print("        encodeUsing_{}({}, ctx);".format(inn, fld_access))
        else:
            raise RuntimeError("optional inner {!r}".format(td))
        print("    }")

    def _decode_optional_field_inline(self, tname, fld_access, oid):
        td = dict(self.type_[tname])
        td.pop("optional", None)
        inn = td["type"]
        print("    if (checkOptional(optionalMask, {})) {{".format(oid))
        if td.keys() <= {"type"} and inn == "string":
            print(
                "        {} = decodeUsing_String(ctx);".format(fld_access))
        elif inn in self.type_ or inn in self.sequence_ or inn in self.choice_ or inn in self.enum_:
            print(
                "        {} = decodeUsing_{}(ctx);".format(fld_access, inn))
        else:
            raise RuntimeError("optional decode {!r}".format(td))
        print("    } else {")
        print("        {} = null;".format(fld_access))
        print("    }")

    def _encode_mandatory_typedef_alias(self, tname, fld_access):
        if tname not in self.type_:
            raise RuntimeError("unknown mandatory field typedef {}".format(tname))
        if self.type_[tname].get("optional"):
            raise RuntimeError("misclassified optional {}".format(tname))

        td = dict(self.type_[tname])

        dv = td.get("dynamic_array")
        if dv is not None and td["type"] == "char":
            mx = self._cum_int_literal(dv)
            print(
                "    if (({}).length > {}) throw new CodecError('{}');".format(
                    fld_access, mx, tname)
            )

        buf = td.get("buffer")
        if buf is not None:
            cap = self._cum_int_literal(buf)
            print(
                "    if (({}).len > {}) throw new CodecError('{}');".format(fld_access, cap, tname))

        print("    encodeUsing_{}({}, ctx);".format(tname, fld_access))

    def _encode_one_field_ordered(self, tname, fname):
        fa = "pIe.{}".format(fname)
        if tname in self.type_ and self.type_[tname].get("optional"):
            self._encode_optional_field_inline(tname, fa)
            return

        if tname in self.type_:
            self._encode_mandatory_typedef_alias(tname, fa)
        elif tname in self.enum_ or tname in self.sequence_ or tname in self.choice_:
            print("    encodeUsing_{}({}, ctx);".format(tname, fa))
        else:
            raise RuntimeError("{}.{} unsupported type {}".format(fname, fname, tname))

    def emit_sequence_codec(self, name):
        flds = self.sequence_[name]
        mask_oct = self._optional_mask_octets_sequence(name)

        print("// Codec: sequence {}".format(name))
        print("export function encodeUsing_{}(pIe, ctx) {{".format(name))
        if mask_oct is not None:
            print("    const optionalMask = new Uint8Array({});".format(mask_oct))
            oid = 0
            for tname, fname in flds:
                if tname in self.type_ and self.type_[tname].get("optional"):
                    fa = "pIe.{}".format(fname)
                    print("    if ({0} !== null && {0} !== undefined)".format(fa))
                    print(" {{ setOptional(optionalMask, {}); }}".format(oid))
                    oid += 1
            print("    ctx.writeBytes(optionalMask, optionalMask.byteLength);")

        for tname, fname in flds:
            self._encode_one_field_ordered(tname, fname)

        print("}")
        print("")
        print("export function decodeUsing_{}(ctx) {{".format(name))
        print("    const pIe = {};")
        if mask_oct is not None:
            print("    const optionalMask = ctx.readBytes({});".format(mask_oct))
        oid = 0
        for tname, fname in flds:
            fa = "pIe.{}".format(fname)
            if tname in self.type_ and self.type_[tname].get("optional"):
                self._decode_optional_field_inline(tname, fa, oid)
                oid += 1
                continue
            if tname in self.type_ or tname in self.enum_ or tname in self.sequence_ or tname in self.choice_:
                print("    {} = decodeUsing_{}(ctx);".format(fa, tname))
            else:
                raise RuntimeError("{} decode {}".format(fname, tname))
        print("    return pIe;")
        print("}")
        print("")

    def emit_choice_codec(self, name):
        alts = self.choice_[name]
        print("// Codec: choice {}".format(name))
        print("export function encodeUsing_{}(pIe, ctx) {{".format(name))

        for idx, ak in enumerate(alts):
            cond = (
                "if (Object.prototype.hasOwnProperty.call(pIe, {0!r}) "
                "&& pIe[{0!r}] !== undefined) {{".format(ak)
                if idx == 0
                else "else if (Object.prototype.hasOwnProperty.call(pIe, {0!r}) "
                "&& pIe[{0!r}] !== undefined) {{".format(ak)
            )
            print("    " + cond)
            print("        ctx.writeChoiceIndex({}, {});".format(len(alts), idx))
            print("        encodeUsing_{0}(pIe[{0!r}], ctx);".format(ak))
            print("        return;")
            print("    }")
        print(
            '    throw new CodecError("encodeUsing_{}: '
            'exactly one discriminant key expected");'.format(name)
        )
        print("}")

        print("")
        print("export function decodeUsing_{}(ctx) {{".format(name))
        print("    const idx = ctx.readChoiceIndex({});".format(len(alts)))
        print("    switch (idx) {")
        for idx, ak in enumerate(alts):
            print("        case {}:".format(idx))
            print(
                "            return {{ [{0!r}]: decodeUsing_{0}(ctx) }};".format(ak)
            )
        print("        default:")
        print(
            '            throw new CodecError("bad choice index");'
        )
        print("    }")
        print("}")

        print("")

    def generate(self):
        print(
            "// Generated from CUM AST — JSDoc shapes, enums, and packed PER codecs "
            "(match target_cpp/cum/cum.hpp)."
        )
        print("")
        self.emit_runtime_import()

        for i in self.pass1_expressions_:
            kind, nm, _ = i
            if kind == "constant":
                self.emit_constant(nm)
            elif kind == "enumeration":
                self.emit_enumeration(nm)
            elif kind == "using":
                self.emit_using(nm)
            elif kind == "choice":
                self.emit_choice(nm)
            elif kind == "sequence":
                self.emit_sequence(nm)

        print("// --- Packed encoding (PER-byte copy, GCC enum = I32LE) ---")

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
            "ast_to_js: invalid JSON (line {} column {}): {}\n".format(
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
    gen = JsGenerator(const_, enum_, type_, choice_, seq_, pass1)
    gen.generate()


if __name__ == "__main__":
    main()