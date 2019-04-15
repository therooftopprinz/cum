# CUM
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
    enumerations,...
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
* `type(unsigned|signed|float|asciiz)`
  * unsigned
  * signed
  * float
  * asciiz
* `width(N)` - numeric argument, specifies the bit width of the type.
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

## Cumpiler
Compiles **cum** to C++:
* C++ (ongoing): to use:`./generate_cpp.py cumfile > output.hpp`
* Python (planned) <br/>
* Wireshark dissector (planned) <br/>

## Example 1
sample2.cum
```cpp
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
    type(unsigned) width(8) dynamic_array(15)
};

Type PhoneNumberArray
{
    type(PhoneNumber) width(8) dynamic_array()
};

Sequence PersonalPhoneEntry
{
    String         firstName,
    OptionalString middleName,
    String         lastName,
    String         address,
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
#ifndef __CUM_MSG_HPP__
#define __CUM_MSG_HPP__
#include "cum/cum.hpp"
#include <optional>

/***********************************************
/
/            Message Definitions
/
************************************************/

using String = std::string;
using OptionalString = std::optional<String>;
using PhoneNumber = cum::vector<char, 15>;
using PhoneNumberArray = std::vector<PhoneNumber>;
struct PersonalPhoneEntry
{
    String firstName;
    OptionalString middleName;
    String lastName;
    String address;
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

void encode(const PersonalPhoneEntry& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t *optionalmask = new(pCtx.get()) uint8_t[1]{};
    pCtx.advance(1);
    encode(pIe.firstName, pCtx);
    if (pIe.middleName)
    {
        set_optional(optionalmask, 0);
        encode(*pIe.middleName, pCtx);
    }
    encode(pIe.lastName, pCtx);
    encode(pIe.address, pCtx);
    encode(pIe.phoneNumbers, pCtx);
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
    str("phoneNumbers", pIe.phoneNumbers, pCtx, true);
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void decode(PersonalPhoneEntry& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t *optionalmask = (uint8_t*)pCtx.get();
    pCtx.advance(1);
    decode(pIe.firstName, pCtx);
    if (check_optional(optionalmask, 0))
    {
        pIe.middleName = decltype(pIe.middleName)::value_type{};
        decode(*pIe.middleName, pCtx);
    }
    decode(pIe.lastName, pCtx);
    decode(pIe.address, pCtx);
    decode(pIe.phoneNumbers, pCtx);
}

void encode(const CorporatePhoneEntry& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    encode(pIe.businessName, pCtx);
    encode(pIe.address, pCtx);
    encode(pIe.phoneNumbers, pCtx);
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

void decode(CorporatePhoneEntry& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    decode(pIe.businessName, pCtx);
    decode(pIe.address, pCtx);
    decode(pIe.phoneNumbers, pCtx);
}

void encode(const PhoneEntry& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    using TypeIndex = uint32_t;
    TypeIndex type = pIe.index();
    encode(type, pCtx);
    if (0 == type)
    {
        encode(std::get<0>(pIe), pCtx);
    }
    else if (1 == type)
    {
        encode(std::get<1>(pIe), pCtx);
    }
}

void decode(PhoneEntry& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    using TypeIndex = uint32_t;
    TypeIndex type;
    decode(type, pCtx);
    if (0 == type)
    {
        pIe = PersonalPhoneEntry{};
        decode(std::get<0>(pIe), pCtx);
    }
    else if (1 == type)
    {
        pIe = CorporatePhoneEntry{};
        decode(std::get<1>(pIe), pCtx);
    }
}

void str(const char* pName, const PhoneEntry& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    using TypeIndex = uint32_t;
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

void encode(const PhoneBook& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    encode(pIe.phoneEntryArray, pCtx);
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

void decode(PhoneBook& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    decode(pIe.phoneEntryArray, pCtx);
}

#endif //__CUM_MSG_HPP__
```
