# Common Universal Messaging
Common Universal Messaging is a formal notation used for describing data format for general communication.

## Syntax
#### Constants
```
Constant Name
{
    constant_value
};
```
#### Enumerations
```
Enumeration Name
{
    enumeration(value),...
};
```
#### Types
```
Type Name
{
    attributes,...
};
```
**attributes:**
* `type(...)`
  * unsigned - integral
  * signed - integral, two's complement
  * float - IEEE 754 Float
  * asciiz - string
  * boolean - boolean
  * Sequence - sequence
  * Choice - choice
  * Enumeration - enumeration
* `width(N)` - numeric argument, specifies the bit width for encoding, type is chosen by the nearest possible size.
  * integal - 1 to 64
  * real - 32 or 64
  * auto computed if `max(N)` and `min(N)` are provided.
* `max(N)` - numeric argument, specifies the maximum value constraint.
* `min(N)` - numeric argument, specifies the minimum value constraint.
* `dynamic_array(N)` - numeric argument, specifies the maximum length, none (`dynamic_array()`) for no maximum
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

## Example 1
sample2.cum
```cpp
Enumeration Gender
{
    Male(10),
    Female
};

Type String
{
    type(asciiz)
};

Type OptionalString
{
    type(String) optional()
};

Type PhoneNumber
{
    type(char) dynamic_array(15)
};

Type PhoneNumberArray
{
    type(PhoneNumber) width(8) dynamic_array(32)
};

Sequence PersonalPhoneEntry
{
    String         firstName,
    OptionalString middleName,
    String         lastName,
    String         address,
    Gender         gender,
    PhoneNumberArray phoneNumbers
};

Sequence CorporatePhoneEntry
{
    String      businessName,
    String      address,
    PhoneNumberArray phoneNumbers
};

Choice PhoneEntry
{
    PersonalPhoneEntry,
    CorporatePhoneEntry
};

Type PhoneEntryArray
{
    type(PhoneEntry) dynamic_array()
};

Sequence PhoneBook
{
    PhoneEntryArray phoneEntryArray
};
```

generated c++:
```cpp
// Enumeration:  ('Gender', ('Male', '10'))
// Enumeration:  ('Gender', ('Female', None))
// Type:  ('String', {'type': 'asciiz'})
// Type:  ('OptionalString', {'type': 'String'})
// Type:  ('OptionalString', {'optional': ''})
// Type:  ('PhoneNumber', {'type': 'char'})
// Type:  ('PhoneNumber', {'dynamic_array': '15'})
// Type:  ('PhoneNumberArray', {'type': 'PhoneNumber'})
// Type:  ('PhoneNumberArray', {'width': '8'})
// Type:  ('PhoneNumberArray', {'dynamic_array': '32'})
// Sequence:  PersonalPhoneEntry ('String', 'firstName')
// Sequence:  PersonalPhoneEntry ('OptionalString', 'middleName')
// Sequence:  PersonalPhoneEntry ('String', 'lastName')
// Sequence:  PersonalPhoneEntry ('String', 'address')
// Sequence:  PersonalPhoneEntry ('Gender', 'gender')
// Sequence:  PersonalPhoneEntry ('PhoneNumberArray', 'phoneNumbers')
// Sequence:  CorporatePhoneEntry ('String', 'businessName')
// Sequence:  CorporatePhoneEntry ('String', 'address')
// Sequence:  CorporatePhoneEntry ('PhoneNumberArray', 'phoneNumbers')
// Choice:  ('PhoneEntry', 'PersonalPhoneEntry')
// Choice:  ('PhoneEntry', 'CorporatePhoneEntry')
// Type:  ('PhoneEntryArray', {'type': 'PhoneEntry'})
// Type:  ('PhoneEntryArray', {'dynamic_array': ''})
// Sequence:  PhoneBook ('PhoneEntryArray', 'phoneEntryArray')
// Generating for C++
#ifndef __CUM_MSG_HPP__
#define __CUM_MSG_HPP__
#include "cum/cum.hpp"
#include <optional>

/***********************************************
/
/            Message Definitions
/
************************************************/

enum class Gender : uint8_t
{
    Male = 10, 
    Female
};

using String = std::string;
using OptionalString = std::optional<String>;
using PhoneNumber = std::vector<char>;
using PhoneNumberArray = std::vector<PhoneNumber>;
struct PersonalPhoneEntry
{
    String firstName;
    OptionalString middleName;
    String lastName;
    String address;
    Gender gender;
    PhoneNumberArray phoneNumbers;
};

struct CorporatePhoneEntry
{
    String businessName;
    String address;
    PhoneNumberArray phoneNumbers;
};

using PhoneEntry = std::variant<PersonalPhoneEntry,CorporatePhoneEntry>;
using PhoneEntryArray = std::vector<PhoneEntry>;
struct PhoneBook
{
    PhoneEntryArray phoneEntryArray;
};

/***********************************************
/
/            Codec Definitions
/
************************************************/

void str(const char* pName, const Gender& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    if (pName)
    {
        pCtx = pCtx + "\"" + pName + "\":";
    }
    if (Gender::Male == pIe) pCtx += "\"Male\"";
    if (Gender::Female == pIe) pCtx += "\"Female\"";
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void encode_per(const PersonalPhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t optionalmask[1] = {};
    if (pIe.middleName)
    {
        set_optional(optionalmask, 0);
    }
    encode_per(optionalmask, sizeof(optionalmask), pCtx);
    encode_per(pIe.firstName, pCtx);
    if (pIe.middleName)
    {
        encode_per(*pIe.middleName, pCtx);
    }
    encode_per(pIe.lastName, pCtx);
    encode_per(pIe.address, pCtx);
    encode_per(pIe.phoneNumbers, 1, pCtx);
}

void decode_per(PersonalPhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t optionalmask[1] = {};
    decode_per(optionalmask, sizeof(optionalmask), pCtx);
    decode_per(pIe.firstName, pCtx);
    if (check_optional(optionalmask, 0))
    {
        pIe.middleName = decltype(pIe.middleName)::value_type{};
        decode_per(*pIe.middleName, pCtx);
    }
    decode_per(pIe.lastName, pCtx);
    decode_per(pIe.address, pCtx);
    decode_per(pIe.gender, pCtx);
    decode_per(pIe.phoneNumbers, pCtx);
}

void str(const char* pName, const PersonalPhoneEntry& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    if (!pName)
    {
        pCtx = pCtx + "{";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":{";
    }
    str("firstName", pIe.firstName, pCtx, false);
    if (pIe.middleName)
    {
        str("middleName", *pIe.middleName, pCtx, false);
    }
    str("lastName", pIe.lastName, pCtx, false);
    str("address", pIe.address, pCtx, false);
    str("gender", pIe.gender, pCtx, false);
    str("phoneNumbers", pIe.phoneNumbers, pCtx, true);
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void encode_per(const CorporatePhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.businessName, pCtx);
    encode_per(pIe.address, pCtx);
    encode_per(pIe.phoneNumbers, 1, pCtx);
}

void decode_per(CorporatePhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.businessName, pCtx);
    decode_per(pIe.address, pCtx);
    decode_per(pIe.phoneNumbers, pCtx);
}

void str(const char* pName, const CorporatePhoneEntry& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    if (!pName)
    {
        pCtx = pCtx + "{";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":{";
    }
    str("businessName", pIe.businessName, pCtx, false);
    str("address", pIe.address, pCtx, false);
    str("phoneNumbers", pIe.phoneNumbers, pCtx, true);
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void encode_per(const PhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    using TypeIndex = uint8_t;
    TypeIndex type = pIe.index();
    encode_per(type, pCtx);
    if (0 == type)
    {
        encode_per(std::get<0>(pIe), pCtx);
    }
    else if (1 == type)
    {
        encode_per(std::get<1>(pIe), pCtx);
    }
}

void decode_per(PhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    using TypeIndex = uint8_t;
    TypeIndex type;
    decode_per(type, pCtx);
    if (0 == type)
    {
        pIe = PersonalPhoneEntry{};
        decode_per(std::get<0>(pIe), pCtx);
    }
    else if (1 == type)
    {
        pIe = CorporatePhoneEntry{};
        decode_per(std::get<1>(pIe), pCtx);
    }
}

void str(const char* pName, const PhoneEntry& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    using TypeIndex = uint8_t;
    TypeIndex type = pIe.index();
    if (0 == type)
    {
        str(pName, std::get<0>(pIe), pCtx, true);
    }
    else if (1 == type)
    {
        str(pName, std::get<1>(pIe), pCtx, true);
    }
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void encode_per(const PhoneBook& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.phoneEntryArray, 4, pCtx);
}

void decode_per(PhoneBook& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.phoneEntryArray, pCtx);
}

void str(const char* pName, const PhoneBook& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    if (!pName)
    {
        pCtx = pCtx + "{";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":{";
    }
    str("phoneEntryArray", pIe.phoneEntryArray, pCtx, true);
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

#endif //__CUM_MSG_HPP__

```
