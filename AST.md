# Abstract Syntax Tree (AST) for Common Universal Messaging (CUM)

This document specifies a tree representation for CUM definition files (`.cum`). It is aligned with [README.md](README.md) and the constructs recognized by `generator/generate_cpp.py`, but is intentionally **independent** of C++ codegen so parsers, analyzers, and alternate backends can share one shape.

---

## 1. Design goals

| Goal | Approach |
|------|----------|
| **Faithful** | Every top-level form in the grammar maps to one explicit AST node variant. |
| **Composable** | Type expressions nest under `UsingDecl` instead of opaque strings wherever possible. |
| **Stable** | Use explicit discriminant tags (`kind`) for unions; avoid overloaded shapes. |
| **Extensible** | Optional `loc` / `comments` wrappers can be added later without renaming core fields. |

**Convention:** Below, `Identifier` means a non-empty `[A-Za-z0-9_]+` token. Numeric and symbolic constant / enum initializer text is modeled as **`Literal`** (opaque string preserved from source) until a separate constant-evaluation pass exists.

---

## 2. Root and document structure

```text
Document
  declarations: Declaration[]
```

A `Document` is the result of parsing one `.cum` file after stripping `//` line comments and normalizing newlines (as the current transpiler does). Order of `declarations` matches source order; forward references are allowed by the language and are not resolved in the AST.

---

## 3. Top-level declarations

All declarations share a tagged union:

```text
Declaration =
  | ConstantDecl
  | EnumerationDecl
  | UsingDecl
  | ChoiceDecl
  | SequenceDecl
```

### 3.1 `ConstantDecl`

```text
ConstantDecl
  kind: "constant"
  name: Identifier
  value: Literal
```

**Surface:** `constant NAME = VALUE;`  
`value` is the raw right-hand side (e.g. `16`, `-1` if the lexer permits it).

### 3.2 `EnumerationDecl`

```text
EnumerationDecl
  kind: "enumeration"
  name: Identifier
  variants: EnumVariant[]
```

```text
EnumVariant
  name: Identifier
  value: Literal | null   // null => implicit / next value (language-defined)
```

**Surface:** `enumeration Name { A = -1, B, C };`  
The current implementation stores variant values as strings or `null` for omitted `= value`.

### 3.3 `UsingDecl` (type alias)

```text
UsingDecl
  kind: "using"
  name: Identifier
  type: TypeExpr
```

**Surface:** `using Name = <TypeExpr>;`

### 3.4 `ChoiceDecl`

```text
ChoiceDecl
  kind: "choice"
  name: Identifier
  alternatives: TypeRef[]   // ordered; index is semantically significant for encoding
```

**Surface:** `choice Name { T1, T2, ... };`  
Each element is a reference to a named type (primitive, alias, sequence, choice, enumeration, etc.).

### 3.5 `SequenceDecl`

```text
SequenceDecl
  kind: "sequence"
  name: Identifier
  fields: Field[]
```

```text
Field
  type: TypeRef
  name: Identifier
```

**Surface:** `sequence Name { Type fieldName, ... };`

---

## 4. Type expressions (`TypeExpr`)

Used on the right-hand side of `using`. This is distinct from **`TypeRef`**, which is “use of a type name” in sequences, choices, and generic arguments.

```text
TypeExpr =
  | NamedType        // plain alias or builtin
  | OptionalType
  | DynamicArrayType
  | StaticArrayType
  | BufferType
```

### 4.1 `NamedType`

```text
NamedType
  kind: "named"
  name: Identifier
```

Examples: `u32`, `string`, `KeyValue`, `byte`.

### 4.2 `OptionalType`

```text
OptionalType
  kind: "optional"
  inner: TypeExpr
```

**Surface:** `optional<TypeExpr>`

### 4.3 `DynamicArrayType`

```text
DynamicArrayType
  kind: "dynamic"
  element: TypeExpr
  max: SizeExpr
```

**Surface:** `dynamic<TypeExpr, SizeExpr>`

### 4.4 `StaticArrayType`

```text
StaticArrayType
  kind: "static"
  element: TypeExpr
  size: SizeExpr
```

**Surface:** `static<TypeExpr, SizeExpr>`

### 4.5 `BufferType`

```text
BufferType
  kind: "buffer"
  element: TypeExpr
  capacity: SizeExpr
```

**Surface:** `buffer<TypeExpr, SizeExpr>` (whitespace around `,` is cosmetic).

---

## 5. Size and value expressions

Until the language defines a full expression grammar, **`SizeExpr`** and constant-like positions are represented uniformly:

```text
SizeExpr =
  | LiteralSize     // numeric literal as string
  | NameRef         // reference to a named constant or future symbol
```

```text
LiteralSize
  kind: "literal"
  raw: Literal
```

```text
NameRef
  kind: "name"
  name: Identifier
```

Examples:

- `MAX_REQUEST_SIZE` → `NameRef("MAX_REQUEST_SIZE")`
- `64` → `LiteralSize("64")`
- `255` → `LiteralSize("255")`

**Note:** The current transpiler passes size arguments through as strings; the AST keeps that contract so tools can defer evaluation.

---

## 6. Type references (`TypeRef`)

Any place the grammar expects “a type name” (field type, choice arm, generic argument where only names appear today):

```text
TypeRef
  name: Identifier
```

Nested `optional<...>` or `dynamic<...>` are **not** allowed inside `sequence` / `choice` arms in current samples; authors introduce a `using` alias instead. If the grammar is relaxed later, `TypeRef` can be generalized to `TypeExpr` without changing declaration nodes.

---

## 7. Literals

```text
Literal
  raw: string   // source text exactly as parsed (trimmed per token rules)
```

Used for numeric constants, negative enum values (e.g. `-1`), hex if ever added, etc.

---

## 8. Recommended JSON serialization

Stable, machine-friendly encoding:

- Every node carries `"kind"` where the variant is not obvious from context.
- Use `null` for omitted optional fields (e.g. enum implicit value).
- Preserve declaration order in `declarations`.

**Sketch for** `constant MAX_REQUEST_SIZE = 16;`:

```json
{
  "kind": "document",
  "declarations": [
    {
      "kind": "constant",
      "name": "MAX_REQUEST_SIZE",
      "value": { "raw": "16" }
    }
  ]
}
```

**Sketch for** `using KeyArray = dynamic<Key, MAX_REQUEST_SIZE>;`:

```json
{
  "kind": "using",
  "name": "KeyArray",
  "type": {
    "kind": "dynamic",
    "element": { "kind": "named", "name": "Key" },
    "max": { "kind": "name", "name": "MAX_REQUEST_SIZE" }
  }
}
```

**Sketch for** `sequence PDU { TrId trId, PDU_Messages message };`:

```json
{
  "kind": "sequence",
  "name": "PDU",
  "fields": [
    { "type": { "name": "TrId" }, "name": "trId" },
    { "type": { "name": "PDU_Messages" }, "name": "message" }
  ]
}
```

---

## 9. Mapping from current internal representation

The current `ExpressionParser` in `generator/generate_cpp.py` splits on `;` and records `(keyword, name, tail)` tuples, then fills:

| Parser map / tuple | AST node |
|--------------------|----------|
| `constant`, name, `= value` | `ConstantDecl` |
| `enumeration`, name, `{ ... }` | `EnumerationDecl` with `EnumVariant[]` |
| `using`, name, `= rhs` | `UsingDecl` with parsed `TypeExpr` |
| `choice`, name, `{ a, b }` | `ChoiceDecl` |
| `sequence`, name, `{ type field, ... }` | `SequenceDecl` |

---

## 10. Future extensions (non-normative)

If the language grows, these AST additions are anticipated:

- **Modules / imports:** `ImportDecl`, optional `module` wrapper on `Document`.
- **Attributes / annotations:** `attributes: Attr[]` on any `Declaration` or `Field`.
- **Rich expressions:** Replace `Literal` / `SizeExpr` with a full `Expr` subtree for computed sizes and defaults.
- **Parameterized definitions:** Generic `sequence`/`choice` with type parameters.

---

## 11. Quick reference — node kinds

| `kind` | Parent / role |
|--------|----------------|
| *(root)* | `Document` |
| `constant` | Top-level |
| `enumeration` | Top-level |
| `using` | Top-level |
| `choice` | Top-level |
| `sequence` | Top-level |
| `named` | `TypeExpr` leaf |
| `optional` | `TypeExpr` |
| `dynamic` | `TypeExpr` |
| `static` | `TypeExpr` |
| `buffer` | `TypeExpr` |
| `literal` | `SizeExpr` |
| `name` | `SizeExpr` (name reference) |

`EnumVariant` and `Field` do not require a `kind` if their parent table disambiguates them in JSON; adding `"kind": "field"` / `"enum_variant"` is optional for uniformity.
