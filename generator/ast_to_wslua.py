#!/usr/bin/env python3
"""Emit a Wireshark Lua dissector from CUM AST JSON (stdout).

Layout matches target_js / target_py3 PerCodecCtx:
  - Enum: LE int32
  - Counts: LE unsigned, width from max cardinality
  - Choice index: LE unsigned, width from alternative count
  - Optional fields: MSB-first bit mask (set_optional), then present values only
  - `using string = string`: Latin-1 C string (NUL-terminated)
  - `dynamic<char,N>`: count + N× u8 code units (not interior NUL-terminated)

Usage:
  python3 cum_to_ast.py file.cum | python3 ast_to_wslua.py [proto_abbr]
  python3 ast_to_wslua.py ast.json [proto_abbr]

Default proto_abbr: cum_pdu  (display filter prefix: cum_pdu.field...)

Wireshark Lua uses little-endian accessors for LE wire encoding.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from ast_normalize import ast_document_to_cpp_state


def cum_name_to_lua_suffix(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def lua_escape_str(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


_CUM_PRIMS = frozenset(
    {"u8", "byte", "s8", "u16", "s16", "u32", "s32", "u64", "s64", "f32", "f64", "string"}
)


class WsLuaGenerator:
    def __init__(
        self, constant, enum_, type_, choice_, sequence_, pass1_expressions, abbr: str
    ):
        self.constant_ = constant
        self.enum_ = enum_
        self.type_ = type_
        self.choice_ = choice_
        self.sequence_ = sequence_
        self.pass1_expressions_ = pass1_expressions
        self.abbr = abbr.rstrip(".")
        self.proto_fields_lua: list[str] = []
        self.seq_field_pf: dict[tuple[str, str], str | None] = {}

    def _filt(self, *parts: str) -> str:
        return ".".join([self.abbr] + [p for p in parts if p])

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

    def _enum_numeric_values(self, variants):
        next_val = 0
        out = []
        for vn, raw in variants:
            if raw is not None:
                next_val = int(str(raw).strip(), 0)
            out.append((vn, next_val))
            next_val += 1
        return out

    def _append_field(self, lua_line: str):
        self.proto_fields_lua.append(lua_line)

    def _fn_using(self, name: str) -> str:
        return "dissect_using_" + cum_name_to_lua_suffix(name)

    def _fn_seq(self, name: str) -> str:
        return "dissect_seq_" + cum_name_to_lua_suffix(name)

    def _fn_choice(self, name: str) -> str:
        return "dissect_choice_" + cum_name_to_lua_suffix(name)

    def _terminal_field_for_sequence_member(self, seq_name: str, fname: str, tname: str):
        """Register one ProtoField for filterable leaves; return Lua var or None."""
        disp = fname
        flt = self._filt(seq_name, fname)
        var = "pf_" + re.sub(r"[^a-zA-Z0-9_]", "_", flt)

        if tname in self.enum_:
            tab = cum_name_to_lua_suffix(tname) + "_enum_vals"
            self._append_field(
                'local {v} = ProtoField.int32("{f}", "{d}", base.DEC, {t})'
                .format(v=var, f=lua_escape_str(flt), d=lua_escape_str(disp), t=tab)
            )
            self.seq_field_pf[(seq_name, fname)] = var
            return var

        if tname in self.type_:
            td = self.type_[tname]
            if self._pure_optional_td(td):
                self.seq_field_pf[(seq_name, fname)] = None
                return None
            inner = td["type"]
            if inner == "string" and not any(
                k in td for k in ("dynamic_array", "array", "buffer")
            ):
                self._append_field(
                    'local {v} = ProtoField.string("{f}", "{d}")'
                    .format(v=var, f=lua_escape_str(flt), d=lua_escape_str(disp))
                )
                self.seq_field_pf[(seq_name, fname)] = var
                return var
            if td.keys() <= {"type"} and inner in _CUM_PRIMS and inner != "string":
                pft = {
                    "u8": ("uint8", "base.DEC"),
                    "byte": ("uint8", "base.HEX"),
                    "s8": ("int8", "base.DEC"),
                    "u16": ("uint16", "base.DEC"),
                    "s16": ("int16", "base.DEC"),
                    "u32": ("uint32", "base.DEC"),
                    "s32": ("int32", "base.DEC"),
                    "u64": ("uint64", "base.DEC"),
                    "s64": ("int64", "base.DEC"),
                    "f32": ("float", "base.NONE"),
                    "f64": ("double", "base.NONE"),
                }[inner]
                self._append_field(
                    'local {v} = ProtoField.{kind}("{f}", "{d}", {bs})'
                    .format(
                        v=var,
                        kind=pft[0],
                        f=lua_escape_str(flt),
                        d=lua_escape_str(disp),
                        bs=pft[1],
                    )
                )
                self.seq_field_pf[(seq_name, fname)] = var
                return var
        self.seq_field_pf[(seq_name, fname)] = None
        return None

    def emit_preamble(self):
        print("-- Generated from CUM AST — Wireshark Lua dissector (packed PER, LE).")
        print("-- Display filter prefix: {!r}".format(self.abbr))
        print("")

    def emit_helpers(self):
        print(
            r"""
local function cum_octets_for_capacity(cap)
    local N = tonumber(cap)
    assert(N and N >= 1, "cum_octets_for_capacity: bad cap")
    if N <= 256 then return 1 end
    if N <= 65536 then return 2 end
    if N <= 4294967296 then return 4 end
    return 8
end

local function cum_octets_for_choice_arity(alts)
    local n = tonumber(alts)
    assert(n and n >= 2, "choice arity must be >= 2")
    if n < 256 then return 1 end
    if n < 65536 then return 2 end
    if n < 4294967296 then return 4 end
    return 8
end

local function cum_optional_is_set(mask_range, bit_index)
    local byte_off = math.floor(bit_index / 8)
    local bi = bit_index % 8
    local m = mask_range:range(byte_off, 1):uint()
    local bit = math.floor(128 / (2 ^ bi))
    return math.floor(m / bit) % 2 ~= 0
end

local function dissect_c_string_latin1(tvb, subtree, offset, fld)
    local start = offset
    while offset < tvb:len() and tvb(offset, 1):uint() ~= 0 do
        offset = offset + 1
    end
    if offset >= tvb:len() then
        subtree:add(tvb:range(start, tvb:len() - start), "truncated CUM string")
        return tvb:len()
    end
    local span = offset - start
    if fld then
        subtree:add(fld, tvb:range(start, span))
    else
        subtree:add(tvb:range(start, span), "string (" .. span .. " chars)")
    end
    return offset + 1
end
""".strip()
        )
        print("")

    def emit_enum_value_tables(self):
        for kind, nm, _ in self.pass1_expressions_:
            if kind != "enumeration":
                continue
            tab = cum_name_to_lua_suffix(nm) + "_enum_vals"
            print("local {} = {{".format(tab))
            for vname, vint in self._enum_numeric_values(self.enum_[nm]):
                print(
                    "    [{}] = \"{}\",".format(int(vint), lua_escape_str(vname))
                )
            print("}")
            print("")

    def collect_proto_fields(self):
        self.proto_fields_lua = []
        self.seq_field_pf = {}
        for kind, seq_name, _ in self.pass1_expressions_:
            if kind != "sequence":
                continue
            for tname, fname in self.sequence_[seq_name]:
                if tname in self.type_ and self.type_[tname].get("optional"):
                    continue
                self._terminal_field_for_sequence_member(seq_name, fname, tname)

    def emit_proto_fields_block(self):
        if not self.proto_fields_lua:
            print("-- (no sequence-level primitive / enum ProtoFields)")
            print("")
            return
        for ln in self.proto_fields_lua:
            print(ln)
        print("")

    def emit_proto_object(self):
        print(
            'local cum_proto = Proto("{0}", "{0} (CUM AST)")'
            .format(lua_escape_str(self.abbr))
        )

    def emit_proto_fields_assignment(self):
        if not self.proto_fields_lua:
            print("cum_proto.fields = {}")
            print("")
            return
        vars_list = []
        for ln in self.proto_fields_lua:
            # `local pf_x = ProtoField...`
            rest = ln[len("local ") :]
            sp = rest.split("=", 1)[0].strip()
            vars_list.append(sp)
        print("cum_proto.fields = { " + ", ".join(vars_list) + " }")
        print("")

    def _emit_dissect_typedef_body(self, alias: str, td: dict, indent: str, nst: str):
        """Print Lua statements consuming tvb from `offset` into subtree node `nst`."""
        if self._pure_optional_td(td):
            return
        elem = td["type"]
        dyn = td.get("dynamic_array")
        buf_cap = td.get("buffer")
        flt = lua_escape_str(self._filt(alias))

        if dyn is not None:
            mx = self._cum_int_literal(dyn)
            print(
                indent
                + "local nb = cum_octets_for_capacity({mx})\n".format(mx=mx)
                + indent
                + "local cnt = tvb(offset, nb):le_uint()\n"
                + indent
                + "offset = offset + nb\n"
                + indent
                + 'local cont = {nst}:add(tvb:range(offset), "{alias}: " .. cnt .. " items")\n'
                .format(nst=nst, alias=lua_escape_str(alias))
            )
            if elem == "char":
                print(
                    indent
                    + "for _i = 1, cnt do\n"
                    + indent
                    + "    local ch = tvb(offset, 1):uint()\n"
                    + indent
                    + '    cont:add(tvb:range(offset, 1), string.format("[%d] u8 %d", _i - 1, ch))\n'
                    + indent
                    + "    offset = offset + 1\n"
                    + indent
                    + "end\n"
                )
            else:
                elem_enum = cum_name_to_lua_suffix(elem) + "_enum_vals" if elem in self.enum_ else None
                if elem in self.enum_:
                    print(
                        indent
                        + "for _i = 1, cnt do\n"
                        + indent
                        + "    local it = cont:add(tvb:range(offset, 4), string.format(\"enum item [%d]\", _i - 1))\n"
                        + indent
                        + "    it:add_le(ProtoField.int32(\"{flt}.dyn\", \"{elem}\", base.DEC, {tab}), tvb:range(offset, 4))\n"
                        .format(flt=flt, elem=lua_escape_str(elem), tab=elem_enum)
                        + indent
                        + "    offset = offset + 4\n"
                        + indent
                        + "end\n"
                    )
                else:
                    fn = (
                        self._fn_using(elem)
                        if elem in self.type_
                        else self._fn_seq(elem)
                        if elem in self.sequence_
                        else self._fn_choice(elem)
                        if elem in self.choice_
                        else None
                    )
                    if fn is None:
                        raise RuntimeError("dynamic element type {!r} unsupported".format(elem))
                    print(
                        indent
                        + "for _i = 1, cnt do\n"
                        + indent
                        + "    local it = cont:add(tvb:range(offset), string.format(\"item [%d]\", _i - 1))\n"
                        + indent
                        + "    offset = {fn}(tvb, pinfo, it, offset)\n".format(fn=fn)
                        + indent
                        + "end\n"
                    )
            return

        if buf_cap is not None:
            cap = self._cum_int_literal(buf_cap)
            print(
                indent
                + "local nb = cum_octets_for_capacity({cap})\n".format(cap=cap)
                + indent
                + "local ln = tvb(offset, nb):le_uint()\n"
                + indent
                + "offset = offset + nb\n"
                + indent
                + "local pay = tvb:range(offset, ln)\n"
                + indent
                + '{nst}:add(pay, "{alias} payload (" .. ln .. " octets)")\n'
                .format(nst=nst, alias=lua_escape_str(alias))
                + indent
                + "offset = offset + ln\n"
            )
            return

        if td.get("array") is not None:
            raise RuntimeError("static array typedef {!r} not supported in wslua".format(alias))

        if elem == "string":
            print(
                indent
                + "offset = dissect_c_string_latin1(tvb, {nst}, offset, nil)\n".format(nst=nst)
            )
            return

        if elem in _CUM_PRIMS and td.keys() <= {"type"}:
            self._emit_primitive_into_subtree(elem, flt, alias, indent, nst)
            return

        raise RuntimeError("cannot emit Lua dissect for using {} (= {!r})".format(alias, td))

    def _emit_primitive_into_subtree(self, elem: str, flt: str, label: str, indent: str, nst: str):
        """Emit add + offset bump for a leaf typedef (plain primitive)."""
        lb = lua_escape_str(label)
        if elem in ("u8", "byte"):
            print(
                indent
                + '{nst}:add(ProtoField.uint8("{flt}.v", "{lb}", base.HEX), tvb:range(offset, 1))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 1\n"
            )
            return
        if elem == "s8":
            print(
                indent
                + '{nst}:add(ProtoField.int8("{flt}.v", "{lb}", base.DEC), tvb:range(offset, 1))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 1\n"
            )
            return
        if elem == "u16":
            print(
                indent
                + '{nst}:add_le(ProtoField.uint16("{flt}.v", "{lb}", base.HEX), tvb:range(offset, 2))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 2\n"
            )
            return
        if elem == "s16":
            print(
                indent
                + '{nst}:add_le(ProtoField.int16("{flt}.v", "{lb}", base.DEC), tvb:range(offset, 2))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 2\n"
            )
            return
        if elem == "u32":
            print(
                indent
                + '{nst}:add_le(ProtoField.uint32("{flt}.v", "{lb}", base.HEX), tvb:range(offset, 4))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 4\n"
            )
            return
        if elem == "s32":
            print(
                indent
                + '{nst}:add_le(ProtoField.int32("{flt}.v", "{lb}", base.DEC), tvb:range(offset, 4))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 4\n"
            )
            return
        if elem == "u64":
            print(
                indent
                + '{nst}:add_le(ProtoField.uint64("{flt}.v", "{lb}", base.HEX), tvb:range(offset, 8))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 8\n"
            )
            return
        if elem == "s64":
            print(
                indent
                + '{nst}:add_le(ProtoField.int64("{flt}.v", "{lb}", base.DEC), tvb:range(offset, 8))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 8\n"
            )
            return
        if elem == "f32":
            print(
                indent
                + '{nst}:add_le(ProtoField.float("{flt}.v", "{lb}", base.NONE), tvb:range(offset, 4))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 4\n"
            )
            return
        if elem == "f64":
            print(
                indent
                + '{nst}:add_le(ProtoField.double("{flt}.v", "{lb}", base.NONE), tvb:range(offset, 8))\n'
                .format(nst=nst, flt=flt, lb=lb)
                + indent
                + "offset = offset + 8\n"
            )
            return
        raise RuntimeError("primitive {!r}".format(elem))

    def emit_using_dissectors(self):
        for kind, nm, _ in self.pass1_expressions_:
            if kind != "using":
                continue
            td = self.type_[nm]
            if self._pure_optional_td(td):
                continue
            print("local function {}(tvb, pinfo, tree, offset)".format(self._fn_using(nm)))
            print("    local subtree = tree:add(tvb:range(offset), \"{}\")".format(nm))
            print("    local _o0 = offset")
            self._emit_dissect_typedef_body(nm, td, "    ", "subtree")
            print("    subtree:set_len(offset - _o0)")
            print("    return offset")
            print("end")
            print("")

    def _dissect_field_expr(self, seq_name: str, tname: str, fname: str, pfvar: str | None):
        """Lua expression `offset = ...` for one field (non-optional path)."""
        ind = "    "
        if tname in self.type_ and self.type_[tname].get("optional"):
            raise RuntimeError("optional must be handled by caller")
        if pfvar and tname in self.enum_:
            return (
                ind
                + "subtree:add_le({}, tvb:range(offset, 4))\n".format(pfvar)
                + ind
                + "offset = offset + 4\n"
            )
        if tname in self.enum_:
            return (
                ind
                + "subtree:add_le(ProtoField.int32(\"{0}\", \"{1}\", base.DEC, {2}), tvb:range(offset, 4))\n"
                .format(
                    lua_escape_str(self._filt(seq_name, fname)),
                    lua_escape_str(fname),
                    cum_name_to_lua_suffix(tname) + "_enum_vals",
                )
                + ind
                + "offset = offset + 4\n"
            )
        if tname in self.type_:
            td = self.type_[tname]
            if self._pure_optional_td(td):
                raise RuntimeError("bare optional typedef as mandatory field")
            inner = td["type"]
            if inner == "string" and not any(
                k in td for k in ("dynamic_array", "array", "buffer")
            ):
                if pfvar:
                    return (
                        ind
                        + "offset = dissect_c_string_latin1(tvb, subtree, offset, {})\n"
                        .format(pfvar)
                    )
                return ind + "offset = dissect_c_string_latin1(tvb, subtree, offset, nil)\n"
            if td.keys() <= {"type"} and inner in _CUM_PRIMS and inner != "string":
                sizes = {
                    "u8": 1,
                    "byte": 1,
                    "s8": 1,
                    "u16": 2,
                    "s16": 2,
                    "u32": 4,
                    "s32": 4,
                    "u64": 8,
                    "s64": 8,
                    "f32": 4,
                    "f64": 8,
                }[inner]
                if pfvar:
                    if sizes == 1:
                        fn_add = (
                            ind
                            + "subtree:add({}, tvb:range(offset, 1))\n".format(
                                pfvar
                            )
                            + ind
                            + "offset = offset + 1\n"
                        )
                    else:
                        fn_add = (
                            ind
                            + "subtree:add_le({}, tvb:range(offset, {}))\n".format(
                                pfvar, sizes
                            )
                            + ind
                            + "offset = offset + {}\n".format(sizes)
                        )
                    return fn_add
                return (
                    ind
                    + "offset = {fn}(tvb, pinfo, subtree, offset)\n".format(
                        fn=self._fn_using(tname)
                    )
                )
            return (
                ind
                + "offset = {fn}(tvb, pinfo, subtree, offset)\n"
                .format(fn=self._fn_using(tname))
            )
        if tname in self.sequence_:
            return (
                ind
                + "offset = {fn}(tvb, pinfo, subtree, offset)\n"
                .format(fn=self._fn_seq(tname))
            )
        if tname in self.choice_:
            return (
                ind
                + "offset = {fn}(tvb, pinfo, subtree, offset)\n"
                .format(fn=self._fn_choice(tname))
            )
        raise RuntimeError("sequence field {}: unsupported type {}".format(fname, tname))

    def _optional_inner_dissect(
        self, seq_name: str, tname: str, fname: str, optional_idx: int, mask_var: str
    ):
        """Block for optional typedef field."""
        td = dict(self.type_[tname])
        assert td.pop("optional", None) is True
        inn = td["type"]
        lines = []
        lines.append(
            "    if cum_optional_is_set({}, {}) then\n".format(mask_var, optional_idx)
        )
        if inn == "string" and td.keys() <= {"type"}:
            lines.append(
                "        offset = dissect_c_string_latin1(tvb, subtree, offset, nil)\n"
            )
        elif inn in self.enum_:
            lines.append(
                "        subtree:add_le(ProtoField.int32(\"{0}\", \"{1}\", base.DEC, {2}), tvb:range(offset, 4))\n"
                .format(
                    lua_escape_str(self._filt(seq_name, fname)),
                    lua_escape_str(fname),
                    cum_name_to_lua_suffix(inn) + "_enum_vals",
                )
            )
            lines.append("        offset = offset + 4\n")
        elif inn in _CUM_PRIMS:
            sz = {
                "u8": 1,
                "byte": 1,
                "s8": 1,
                "u16": 2,
                "s16": 2,
                "u32": 4,
                "s32": 4,
                "u64": 8,
                "s64": 8,
                "f32": 4,
                "f64": 8,
            }[inn]
            lines.append(
                "        subtree:add(tvb:range(offset, {sz}), \"{fn} ({inn})\")\n"
                .format(sz=sz, fn=fname, inn=inn)
            )
            lines.append("        offset = offset + {}\n".format(sz))
        elif inn in self.type_:
            lines.append(
                "        offset = {}(tvb, pinfo, subtree, offset)\n".format(
                    self._fn_using(inn)
                )
            )
        elif inn in self.sequence_:
            lines.append(
                "        offset = {}(tvb, pinfo, subtree, offset)\n".format(
                    self._fn_seq(inn)
                )
            )
        elif inn in self.choice_:
            lines.append(
                "        offset = {}(tvb, pinfo, subtree, offset)\n".format(
                    self._fn_choice(inn)
                )
            )
        else:
            raise RuntimeError("optional inner {!r}".format(inn))
        lines.append("    end\n")
        return "".join(lines)

    def emit_sequence_dissectors(self):
        for kind, seq_name, _ in self.pass1_expressions_:
            if kind != "sequence":
                continue
            fields = self.sequence_[seq_name]
            mask_oct = self._optional_mask_octets_sequence(seq_name)
            print("local function {}(tvb, pinfo, tree, offset)".format(self._fn_seq(seq_name)))
            print(
                "    local subtree = tree:add(tvb:range(offset), \"{}\")".format(seq_name)
            )
            print("    local _o0 = offset")
            if mask_oct is not None:
                print(
                    "    local mask_r = tvb:range(offset, {})\n".format(mask_oct)
                    + "    subtree:add(mask_r, \"optional_mask ({} octets)\")\n".format(
                        mask_oct
                    )
                    + "    offset = offset + {}\n".format(mask_oct)
                )
            oid = 0
            for tname, fname in fields:
                mask_expr = "mask_r" if mask_oct is not None else "nil"
                if tname in self.type_ and self.type_[tname].get("optional"):
                    print(
                        self._optional_inner_dissect(
                            seq_name, tname, fname, oid, mask_expr
                        )
                    )
                    oid += 1
                    continue
                pf = self.seq_field_pf.get((seq_name, fname))
                print(self._dissect_field_expr(seq_name, tname, fname, pf))
            print("    subtree:set_len(offset - _o0)")
            print("    return offset")
            print("end")
            print("")

    def emit_choice_dissectors(self):
        for kind, nm, _ in self.pass1_expressions_:
            if kind != "choice":
                continue
            alts = self.choice_[nm]
            nar = len(alts)
            print("local function {}(tvb, pinfo, tree, offset)".format(self._fn_choice(nm)))
            print("    local subtree = tree:add(tvb:range(offset), \"choice {}\")".format(nm))
            print("    local _o0 = offset")
            print(
                "    local iw = cum_octets_for_choice_arity({})\n".format(nar)
                + "    local idx = tvb(offset, iw):le_uint()\n"
                + "    subtree:add(tvb:range(offset, iw), \"index: \" .. idx)\n"
                + "    offset = offset + iw\n"
            )
            for i, ak in enumerate(alts):
                kw = "if" if i == 0 else "elseif"
                print("    {} idx == {} then".format(kw, i))
                fn = (
                    self._fn_seq(ak)
                    if ak in self.sequence_
                    else self._fn_using(ak)
                    if ak in self.type_
                    else self._fn_choice(ak)
                    if ak in self.choice_
                    else None
                )
                if ak in self.enum_:
                    print(
                        "        subtree:add_le(ProtoField.int32(\"{0}.{1}\", \"{1}\", base.DEC, {2}), tvb:range(offset, 4))\n"
                        .format(
                            lua_escape_str(self._filt(nm)),
                            lua_escape_str(ak),
                            cum_name_to_lua_suffix(ak) + "_enum_vals",
                        )
                        + "        offset = offset + 4\n"
                    )
                elif fn:
                    print(
                        "        offset = {}(tvb, pinfo, subtree, offset)".format(fn)
                    )
                else:
                    raise RuntimeError("choice branch {!r} unsupported".format(ak))
            print("    else")
            print(
                '        pinfo.cols.info:append(" [bad cum choice idx]")\n'
                "        return tvb:len()\n"
                "    end"
            )
            print("    subtree:set_len(offset - _o0)")
            print("    return offset")
            print("end")
            print("")

    def emit_dissector_registration(self):
        roots = [
            nm for kind, nm, _ in self.pass1_expressions_ if kind == "sequence"
        ]
        if not roots:
            print("-- No sequence declarations; register nothing.")
            return
        default_root = roots[-1]
        print(
            '-- Default top-level PDU: last sequence in file ("{}"). Adjust if needed.'.format(
                default_root
            )
        )
        dfs = self._fn_seq(default_root)
        print("")
        print(
            """function cum_proto.dissector(tvb, pinfo, tree)
    pinfo.cols.protocol = cum_proto.name
    local t = tree:add(cum_proto, tvb:range(0))"""
        )
        print("    {}(tvb, pinfo, t, 0)".format(dfs))
        print("end")
        print("")
        print(
            "local udp_tbl = DissectorTable.get(\"udp.port\")\n"
            "-- Example: udp_tbl:add(59100, cum_proto)\n"
        )

    def generate(self):
        self.emit_preamble()
        self.emit_helpers()
        self.emit_enum_value_tables()
        self.collect_proto_fields()
        self.emit_proto_fields_block()
        self.emit_proto_object()
        self.emit_proto_fields_assignment()
        self.emit_using_dissectors()
        self.emit_sequence_dissectors()
        self.emit_choice_dissectors()
        self.emit_dissector_registration()


def load_input(argv):
    """Read AST JSON. See module docstring for argv conventions."""
    if len(argv) > 3:
        sys.stderr.write("usage: {} [-|<ast.json>] [proto_abbr]\n".format(argv[0]))
        sys.exit(2)
    if len(argv) <= 1:
        return sys.stdin.read()
    if argv[1] == "-":
        return sys.stdin.read()
    if len(argv) >= 2 and os.path.isfile(argv[1]):
        with open(argv[1], encoding="utf-8") as f:
            return f.read()
    if len(argv) == 2:
        return sys.stdin.read()
    with open(argv[1], encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    if argv is None:
        argv = sys.argv
    raw = load_input(argv)
    abbr = "cum_pdu"
    if len(argv) == 3:
        abbr = argv[2]
    elif (
        len(argv) == 2
        and argv[1] != "-"
        and not os.path.isfile(argv[1])
    ):
        abbr = argv[1]

    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(
            "ast_to_wslua: invalid JSON (line {} column {}): {}\n".format(
                e.lineno, e.colno, e.msg
            )
        )
        sys.exit(1)
    const_, enum_, type_, choice_, seq_, pass1 = ast_document_to_cpp_state(doc)
    WsLuaGenerator(const_, enum_, type_, choice_, seq_, pass1, abbr).generate()


if __name__ == "__main__":
    main()
