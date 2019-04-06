# CUM
Common Universal Messaging is a formal notation used for describing data transmitted in general communication.

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
Compiles **cum** to:
* C++ (ongoing): to use:`./generate_cpp.py cumfile > output.hpp`
* Python (planned) <br/>
* Wireshark dissector (planned) <br/>

## Example 1
sample2.meta
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
#ifndef __sample2.meta_HPP__
#define __sample2.meta_HPP__

#include <cum/cum.hpp>

using String = std::string;
using OptionalString = std::optional<String>;
using PhoneNumber = cum::vector<uint8_t, 15>;
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

void encode(const PersonalPhoneEntry& pData, cum::codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t optionalmask[1] = {};
    encode_optionalmask(optionalmask, 1, pCtx);
    encode(pIe.firstName, pCtx);
    if (cum::check_optional(optionalmask, 0))
    encode(pIe.middleName, pCtx);
    encode(pIe.lastName, pCtx);
    encode(pIe.address, pCtx);
    encode(pIe.phoneNumbers, pCtx);
}

void decode(PersonalPhoneEntry& pData, cum::codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t optionalmask[1] = {};
    encode_optionalmask(optionalmask, 1, pCtx);
    decode(pIe.firstName, pCtx);
    if (cum::check_optional(optionalmask, 0))
    decode(pIe.middleName, pCtx);
    decode(pIe.lastName, pCtx);
    decode(pIe.address, pCtx);
    decode(pIe.phoneNumbers, pCtx);
}

void encode(const CorporatePhoneEntry& pData, cum::codec_ctx& pCtx)
{
    using namespace cum;
    encode(pIe.businessName, pCtx);
    encode(pIe.address, pCtx);
    encode(pIe.phoneNumbers, pCtx);
}

void decode(CorporatePhoneEntry& pData, cum::codec_ctx& pCtx)
{
    using namespace cum;
    decode(pIe.businessName, pCtx);
    decode(pIe.address, pCtx);
    decode(pIe.phoneNumbers, pCtx);
}
void encode(const PhoneBook& pData, cum::codec_ctx& pCtx)
{
    using namespace cum;
    encode(pIe.phoneEntryArray, pCtx);
}
void decode(PhoneBook& pData, cum::codec_ctx& pCtx)
{
    using namespace cum;
    decode(pIe.phoneEntryArray, pCtx);
}

#endif //__sample2.meta_HPP__
```
