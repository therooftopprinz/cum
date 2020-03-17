// Enumeration:  ('Gender', ('Male', '10'))
// Enumeration:  ('Gender', ('Female', None))
// Type:  ('String', {'type': 'asciiz'})
// Type:  ('OptionalString', {'type': 'String'})
// Type:  ('OptionalString', {'optional': ''})
// Type:  ('PhoneNumber', {'type': 'char'})
// Type:  ('PhoneNumber', {'dynamic_array': '15'})
// Type:  ('PhoneNumberArray', {'type': 'PhoneNumber'})
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
// Type:  ('PhoneEntryArray', {'dynamic_array': '255'})
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
using PhoneNumber = cum::vector<char, 15>;
using PhoneNumberArray = cum::vector<PhoneNumber, 32>;
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
using PhoneEntryArray = cum::vector<PhoneEntry, 255>;
struct PhoneBook
{
    PhoneEntryArray phoneEntryArray;
};

/***********************************************
/
/            Codec Definitions
/
************************************************/

inline void str(const char* pName, const Gender& pIe, std::string& pCtx, bool pIsLast)
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

inline void encode_per(const PersonalPhoneEntry& pIe, cum::per_codec_ctx& pCtx)
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
    encode_per(pIe.gender, pCtx);
    encode_per(pIe.phoneNumbers, pCtx);
}

inline void decode_per(PersonalPhoneEntry& pIe, cum::per_codec_ctx& pCtx)
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

inline void str(const char* pName, const PersonalPhoneEntry& pIe, std::string& pCtx, bool pIsLast)
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
    size_t nOptional = 0;
    if (pIe.middleName) nOptional++;
    size_t nMandatory = 5;
    str("firstName", pIe.firstName, pCtx, !(--nMandatory+nOptional));
    if (pIe.middleName)
    {
        str("middleName", *pIe.middleName, pCtx, !(nMandatory+--nOptional));
    }
    str("lastName", pIe.lastName, pCtx, !(--nMandatory+nOptional));
    str("address", pIe.address, pCtx, !(--nMandatory+nOptional));
    str("gender", pIe.gender, pCtx, !(--nMandatory+nOptional));
    str("phoneNumbers", pIe.phoneNumbers, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const CorporatePhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.businessName, pCtx);
    encode_per(pIe.address, pCtx);
    encode_per(pIe.phoneNumbers, pCtx);
}

inline void decode_per(CorporatePhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.businessName, pCtx);
    decode_per(pIe.address, pCtx);
    decode_per(pIe.phoneNumbers, pCtx);
}

inline void str(const char* pName, const CorporatePhoneEntry& pIe, std::string& pCtx, bool pIsLast)
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
    size_t nOptional = 0;
    size_t nMandatory = 3;
    str("businessName", pIe.businessName, pCtx, !(--nMandatory+nOptional));
    str("address", pIe.address, pCtx, !(--nMandatory+nOptional));
    str("phoneNumbers", pIe.phoneNumbers, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const PhoneEntry& pIe, cum::per_codec_ctx& pCtx)
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

inline void decode_per(PhoneEntry& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    using TypeIndex = uint8_t;
    TypeIndex type;
    decode_per(type, pCtx);
    if (0 == type)
    {
        pIe = PersonalPhoneEntry();
        decode_per(std::get<0>(pIe), pCtx);
    }
    else if (1 == type)
    {
        pIe = CorporatePhoneEntry();
        decode_per(std::get<1>(pIe), pCtx);
    }
}

inline void str(const char* pName, const PhoneEntry& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    using TypeIndex = uint8_t;
    TypeIndex type = pIe.index();
    if (0 == type)
    {
        if (pName)
            pCtx += std::string(pName) + ":{";
        else
            pCtx += "{";
        std::string name = "PersonalPhoneEntry";
        str(name.c_str(), std::get<0>(pIe), pCtx, true);
        pCtx += "}";
    }
    else if (1 == type)
    {
        if (pName)
            pCtx += std::string(pName) + ":{";
        else
            pCtx += "{";
        std::string name = "CorporatePhoneEntry";
        str(name.c_str(), std::get<1>(pIe), pCtx, true);
        pCtx += "}";
    }
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const PhoneBook& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.phoneEntryArray, pCtx);
}

inline void decode_per(PhoneBook& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.phoneEntryArray, pCtx);
}

inline void str(const char* pName, const PhoneBook& pIe, std::string& pCtx, bool pIsLast)
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
    size_t nOptional = 0;
    size_t nMandatory = 1;
    str("phoneEntryArray", pIe.phoneEntryArray, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

#endif //__CUM_MSG_HPP__
