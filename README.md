![CUM](logo.svg)

# Common Universal Messaging

Common Universal Messaging is a formal notation used for describing data format for general communication.

For the **machine-oriented abstract syntax tree**, see [AST.md](AST.md). It complements this file’s surface syntax and stays independent of any single backend.

## Syntax

### Expressions
An expression is composed of
```
(expression)\s+(name)\s*(data);
```
Where expression can be:
- constant
- enumeration
- type
- choice
- sequence

And name can be `[A-Za-z0-9_]`

#### Constants
```
constant\s+(name)\s+=\s+(value);
```
#### Enumerations
```
enumeration\s+(name)\s+{
    (enumeration)(=(value),)*
};
```
#### Types
```
using (name) = (type);
using (name) = (modifier)<(type),(argument)>
```
**modifier:**
* `type` - type to alias
* `optional<type>` - optional modifier
* `static<type, Size>` - static array (default initialized)
* `dynamic<type, MaxSize>` - dynamic array (default initialized)
* `buffer<type,MaxSize>` - buffer array (unitialized)
#### Choices
```
choice Name
{
    type,...
};
```
#### Sequence
```
sequence Name
{
    fields,...
};
```

## Toolchain

Python utilities live under `generator/`. Most scripts expect to be run with `generator/` as the current working directory (or `PYTHONPATH` including `generator`) so sibling imports (`cpp_generator`, `ast_normalize`, etc.) resolve.

* **`.cum` → AST (JSON)** — [`generator/cum_to_ast.py`](generator/cum_to_ast.py)

  ```bash
  cd generator && ./cum_to_ast.py ../path/to/file.cum
  ```

  The emitted JSON follows the schema described in [AST.md](AST.md).

* **C++ header (direct from `.cum`, legacy)** — [`generator/generate_cpp.py`](generator/generate_cpp.py) prints declarations to stdout; run from `generator/` (see note above):

  ```bash
  cd generator && ./generate_cpp.py ../path/to/file.cum > output.hpp
  ```

* **C++ header (from AST JSON)** — [`generator/ast_to_cpp.py`](generator/ast_to_cpp.py) reads JSON from stdin or a file argument:

  ```bash
  cd generator && ./cum_to_ast.py ../path/to/file.cum | ./ast_to_cpp.py
  ```

* **JavaScript (JSDoc, enums, PER codecs)** — `npm run js:codegen` writes [`target_js/test/sample2.mjs`](target_js/test/sample2.mjs) (via [`target_js/scripts/codegen-sample2.mjs`](target_js/scripts/codegen-sample2.mjs), which shells to `cum_to_ast.py` and [`generator/ast_to_js.py`](generator/ast_to_js.py)). Equivalent manual pipe:

  ```bash
  cd generator && ./cum_to_ast.py ../sample2.cum | ./ast_to_js.py > ../target_js/test/sample2.mjs
  ```

* **JS tests** — `npm run js:test` (regenerates the sample module and runs `target_js/test/sample2.test.mjs`).

* **Python** — after installing the project (e.g. `pip install -e .`), use the `cum-tools` CLI: `cum-tools codegen sample2` writes generated code under `target_py3/`, and `cum-tools test sample2` regenerates and runs the Golden PER codec check.

* **C++ consuming the headers** — the CMake package installs/interface target points at [`target_cpp/`](target_cpp/) (see root [`CMakeLists.txt`](CMakeLists.txt)).

* **Wireshark Lua dissector** — [`generator/ast_to_wslua.py`](generator/ast_to_wslua.py) emits Lua that matches the packed PER layout used by JS/Python (`PerCodecCtx`: LE counts and choice index, `int32` enums, optional bitmasks, Latin-1 C strings, counted `dynamic<char,N>` octets). Redirect output into e.g. [`target_wslua/`](target_wslua/) as a personal plugin (Wireshark: *Help → About Wireshark → Folders* → *Personal Lua Plugins*).

  ```bash
  cd generator && ./cum_to_ast.py ../sample2.cum | ./ast_to_wslua.py phonebook > ../target_wslua/sample2.lua
  ```

  Arguments: optional AST JSON path first (otherwise stdin); optional **proto display-filter prefix** (`phonebook` above; default `cum_pdu`). If the first argument is not an existing file, it is treated as that prefix and JSON is read from stdin (same pattern as piping from `cum_to_ast.py`). Uncomment `udp_tbl:add(...)` in the generated script to bind a UDP port, then reload Lua dissectors (*Analyze → Reload Lua Plugins* / `Ctrl+Shift+L`).

For how parser output maps onto AST nodes, see §9 “Mapping from current internal representation” in [AST.md](AST.md).

## Encoding
### Packed Encoding
* All data are byte aligned
* Integral width is ceiled to nearest type.
* Optional mask is ceiled to the nearest octet.
* Choice index type is an integral with `min(0)` and `max(NumberOfChoices)`
* Array index type is an integral with `min(0)` and `max(N)` where N is `dynamic_array(N)`
