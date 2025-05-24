# Common Universal Messaging
Common Universal Messaging is a formal notation used for describing data format for general communication.

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
type (name) ((key(=value)*),*)*
```
**attributes:**
* `type` - type to alias
* `optional` - optional modifier
* `array(=N)` - static array
* `dynamic_array(=N)` - dynamic array
#### Choices
```
Choice Name
{
    type,...
};
```
#### Sequence
```
Sequence Name
{
    fields,...
};
```

## Transpiler
Compiles common universal messenging to C++:
* C++ (ongoing): to use:`./generate_cpp.py cumfile > output.hpp`
* Python (planned) <br/>
* Wireshark dissector (planned) <br/>

## Encoding
### Packed Encoding
* All data are byte aligned
* Integral width is ceiled to nearest type.
* Optional mask is ceiled to the nearest octet.
* Choice index type is an integral with `min(0)` and `max(NumberOfChoices)`
* Array index type is an integral with `min(0)` and `max(N)` where N is `dynamic_array(N)`
### Unaligned Packed Encoding
* Integral width is encoded as is.
* Optional mask is encoded as is.
