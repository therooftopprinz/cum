![CUM](logo.svg)

# Common Universal Messaging

Common Universal Messaging is a formal notation used for describing data format for general communication.

For the **machine-oriented abstract syntax tree**, see [AST.md](AST.md). It complements this file’s surface syntax and stays independent of any single backend.

## Syntax

### Comments
- End-of-line: `// …`
- Block: `/* … */` (may span lines; `/**` doc-style blocks use the same rules)

Comments are removed before parsing.

### Declarations
Each declaration starts with a **keyword** (what kind of thing you are defining) and an **identifier** (its name). After that you write either:

- A **block in curly braces** `{ … }`, finished with **`};`** (a semicolon right after the closing `}`), or  
- A **single line** that ends with **`;`** (like a simple assignment).

Top-level forms are: `constant`, `enumeration`, `using`, `choice`, `sequence`. **Enumeration and choice** list entries are separated by **commas** inside `{ … }`. **Sequence** fields are still separated by **`;` or `,`** (only at depth zero outside nested `< … >` in types). The parser does not split the file on every `;`—it matches balanced braces for block declarations.

#### Constants
```
constant Name = Value;
```

#### Enumerations, choices, sequences
```
enumeration Name {
    …
};

choice Name {
    …
};

sequence Name {
    …
};
```

`enumeration`, `choice`, and `sequence` **must** end with `};` (semicolon after the closing brace), like a C++ `enum class` or `struct` definition.

Between **enumeration variants** or **choice alternatives**, use **commas**. Between **sequence fields**, use **`;` or `,`** (only at depth zero outside nested `< … >` in types).

#### Type aliases
```
using Name = TypeExpr;
```

**Generic type modifiers** (in `using` only today): `optional<…>`, `static<…, …>`, `dynamic<…, …>`, `buffer<…, …>` — see [sample2.cum](sample2.cum).

## Toolchain

Python utilities live under `generator/`. Most scripts expect to be run with `generator/` as the current working directory (or `PYTHONPATH` including `generator`) so sibling imports (`cpp_generator`, `ast_normalize`, etc.) resolve.

* **`.cum` → AST (JSON)** — [`generator/cum_to_ast.py`](generator/cum_to_ast.py)

  ```bash
  cd generator && ./cum_to_ast.py ../path/to/file.cum
  ```

  The emitted JSON follows the schema described in [AST.md](AST.md).

* **C++ header (from AST JSON)** — [`generator/ast_to_cpp.py`](generator/ast_to_cpp.py) reads JSON from stdin or a file argument:

  ```bash
  cd generator && ./cum_to_ast.py ../path/to/file.cum | ./ast_to_cpp.py
  ```

* **JavaScript (JSDoc, enums, PER codecs)** — `npm run js:codegen` writes [`target_js/test/sample2.mjs`](target_js/test/sample2.mjs) (via [`target_js/scripts/codegen-sample2.mjs`](target_js/scripts/codegen-sample2.mjs), which shells to `cum_to_ast.py` and [`generator/ast_to_js.py`](generator/ast_to_js.py)). Equivalent manual pipe:

  ```bash
  cd generator && ./cum_to_ast.py ../sample2.cum | ./ast_to_js.py > ../target_js/test/sample2.mjs
  ```

* **JS tests** — `npm run js:test` (regenerates the sample module and runs `target_js/test/sample2.test.mjs`).

* **Python** — from the repository root, no pip install is required. Run `python -m cum_tools codegen sample2` to regenerate [`target_py3/test/sample2.py`](target_py3/test/sample2.py), or `python -m cum_tools test sample2` to regenerate and run the golden PER codec check. To use the codecs elsewhere, copy the runtime [`target_py3/cum/`](target_py3/cum/) plus your generated modules into your project and import locally (add that directory to `PYTHONPATH` or extend `sys.path`, same idea as the sample test does).

* **C++ consuming the headers** — the CMake package installs/interface target points at [`target_cpp/`](target_cpp/) (see root [`CMakeLists.txt`](CMakeLists.txt)).

* **Wireshark Lua dissector** — [`generator/ast_to_wslua.py`](generator/ast_to_wslua.py) emits Lua that matches the packed PER layout used by JS/Python (`PerCodecCtx`: LE counts and choice index, `int32` enums, optional bitmasks, Latin-1 C strings, counted `dynamic<char,N>` octets). Redirect output into e.g. [`target_wslua/`](target_wslua/) as a personal plugin (Wireshark: *Help → About Wireshark → Folders* → *Personal Lua Plugins*).

  ```bash
  cd generator && ./cum_to_ast.py ../sample2.cum | ./ast_to_wslua.py phonebook > ../target_wslua/test/sample2.lua
  ```

  Arguments: optional AST JSON path first (otherwise stdin); optional **proto display-filter prefix** (`phonebook` above; default `cum_pdu`). If the first argument is not an existing file, it is treated as that prefix and JSON is read from stdin (same pattern as piping from `cum_to_ast.py`). Uncomment `udp_tbl:add(...)` in the generated script to bind a UDP port, then reload Lua dissectors (*Analyze → Reload Lua Plugins* / `Ctrl+Shift+L`).

For how parser output maps onto AST nodes, see §9 in [AST.md](AST.md).

## Encoding
### Packed Encoding
* All data are byte aligned
* Integral width is ceiled to nearest type.
* Optional mask is ceiled to the nearest octet.
* Choice index type is an integral with `min(0)` and `max(NumberOfChoices)`
* Array index type is an integral with `min(0)` and `max(N)` where N is `dynamic_array(N)`
