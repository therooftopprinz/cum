def size_expr_to_str(se):
    k = se["kind"]
    if k == "literal":
        return se["raw"]
    if k == "name":
        return se["name"]
    raise ValueError("unknown SizeExpr kind: {!r}".format(k))

def _only_optional_and_type(td):
    return td.keys() <= {"type", "optional"} and td.get("optional")

def _has_container_modifier(td):
    return any(k in td for k in ("dynamic_array", "array", "buffer"))

def td_emit_fragment(td):
    typee = td["type"]
    veclen = td.get("dynamic_array")
    arrlen = td.get("array")
    buflen = td.get("buffer")
    if veclen is not None:
        if veclen == "":
            veclen = 2**32
        return "cum::vector<{}, {}>".format(typee, veclen)
    if arrlen is not None:
        return "cum::array<{}, {}>".format(typee, arrlen)
    if buflen is not None:
        return "cum::buffer<{}, {}>".format(typee, buflen)
    return typee

def td_collapse_plain(td):
    frag = td_emit_fragment(td)
    if td.get("optional"):
        frag = "std::optional<{}>".format(frag)
    return {"type": frag}

def td_add_optional(inner_td):
    if inner_td.get("optional"):
        inner_td = td_collapse_plain(inner_td)
    merged = dict(inner_td)
    merged["optional"] = True
    return merged

def td_add_dynamic(inner_td, dim):
    td = inner_td
    if _has_container_modifier(td):
        td = td_collapse_plain(td)
    if _only_optional_and_type(td):
        wrapped = "std::optional<{}>".format(td["type"])
        return {"dynamic_array": dim, "type": wrapped}
    out = dict(td)
    out["dynamic_array"] = dim
    return out

def td_add_static(inner_td, size_s):
    td = inner_td
    if _has_container_modifier(td):
        td = td_collapse_plain(td)
    if _only_optional_and_type(td):
        wrapped = "std::optional<{}>".format(td["type"])
        return {"array": size_s, "type": wrapped}
    out = dict(td)
    out["array"] = size_s
    return out

def td_add_buffer(inner_td, cap_s):
    td = inner_td
    if _has_container_modifier(td):
        td = td_collapse_plain(td)
    if _only_optional_and_type(td):
        wrapped = "std::optional<{}>".format(td["type"])
        return {"buffer": cap_s, "type": wrapped}
    out = dict(td)
    out["buffer"] = cap_s
    return out

def type_ast_to_td(te):
    k = te["kind"]
    if k == "named":
        return {"type": te["name"]}
    if k == "optional":
        return td_add_optional(type_ast_to_td(te["inner"]))
    if k == "dynamic":
        return td_add_dynamic(type_ast_to_td(te["element"]), size_expr_to_str(te["max"]))
    if k == "static":
        return td_add_static(type_ast_to_td(te["element"]), size_expr_to_str(te["size"]))
    if k == "buffer":
        return td_add_buffer(type_ast_to_td(te["element"]), size_expr_to_str(te["capacity"]))
    raise ValueError("unknown TypeExpr kind: {!r}".format(k))

def enum_variant_tuple(v):
    name = v["name"]
    val = v.get("value")
    if val is None:
        return (name, None)
    return (name, val["raw"])

def declaration_to_pass_tuple(decl):
    k = decl["kind"]
    name = decl["name"]
    blank = ""
    if k == "constant":
        return ("constant", name, blank)
    if k == "enumeration":
        return ("enumeration", name, blank)
    if k == "using":
        return ("using", name, blank)
    if k == "choice":
        return ("choice", name, blank)
    if k == "sequence":
        return ("sequence", name, blank)
    raise ValueError("unknown declaration kind: {!r}".format(k))

def ast_document_to_cpp_state(doc):
    if doc.get("kind") != "document":
        raise ValueError('root must have kind "document"')
    decls = doc["declarations"]
    constant = {}
    enum_map = {}
    type_map = {}
    choice_map = {}
    sequence_map = {}
    pass1 = []
    for decl in decls:
        pass1.append(declaration_to_pass_tuple(decl))
        k = decl["kind"]

        if k == "constant":
            constant[decl["name"]] = decl["value"]["raw"]
        elif k == "enumeration":
            enum_map[decl["name"]] = [
                enum_variant_tuple(v) for v in decl["variants"]
            ]
        elif k == "using":
            type_map[decl["name"]] = type_ast_to_td(decl["type"])
        elif k == "choice":
            choice_map[decl["name"]] = [
                a["name"] for a in decl["alternatives"]
            ]
        elif k == "sequence":
            sequence_map[decl["name"]] = [
                (f["type"]["name"], f["name"]) for f in decl["fields"]
            ]
        else:
            raise ValueError("unknown declaration kind: {!r}".format(k))
    return constant, enum_map, type_map, choice_map, sequence_map, pass1
