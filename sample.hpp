// Enumeration:  ('Cause', ('Ok', None))
// Constant:  ('MAX_REQUEST_SIZE', '16')
// Constant:  ('MAX_VALUE_SIZE', '64')
// Type:  ('Key', {'type': 'unsigned'})
// Type:  ('Key', {'width': '8'})
// Type:  ('Key', {'min': '1'})
// Type:  ('Key', {'max': '255'})
// Type:  ('KeyArray', {'type': 'Key'})
// Type:  ('KeyArray', {'dynamic_array': 'MAX_REQUEST_SIZE'})
// Type:  ('TrId', {'type': 'unsigned'})
// Type:  ('TrId', {'optional': ''})
// Type:  ('TrId', {'min': '0'})
// Type:  ('TrId', {'max': '255'})
// Type:  ('OctetString', {'type': 'unsigned'})
// Type:  ('OctetString', {'width': '8'})
// Type:  ('OctetString', {'dynamic_array': 'MAX_VALUE_SIZE'})
// Sequence:  KeyValue ('Key', 'key')
// Sequence:  KeyValue ('OctetString', 'value')
// Type:  ('KeyValueArray', {'type': 'KeyValue'})
// Type:  ('KeyValueArray', {'width': '8'})
// Type:  ('KeyValueArray', {'dynamic_array': 'MAX_REQUEST_SIZE'})
// Sequence:  SetRequest ('KeyValueArray', 'data')
// Sequence:  SetResponse ('Cause', 'cause')
// Sequence:  GetRequest ('KeyArray', 'data')
// Sequence:  GetResponse ('KeyValueArray', 'data')
// Choice:  ('PDU_Messages', 'SetRequest')
// Choice:  ('PDU_Messages', 'SetResponse')
// Choice:  ('PDU_Messages', 'GetRequest')
// Choice:  ('PDU_Messages', 'GetResponse')
// Sequence:  PDU ('TrId', 'trId')
// Sequence:  PDU ('PDU_Messages', 'message')
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

enum class Cause : uint8_t
{
    Ok
};

constexpr auto MAX_REQUEST_SIZE = 16;
constexpr auto MAX_VALUE_SIZE = 64;
using Key = uint8_t;
using KeyArray = cum::vector<Key, MAX_REQUEST_SIZE>;
using TrId = std::optional<uint32_t>;
using OctetString = cum::vector<uint8_t, MAX_VALUE_SIZE>;
struct KeyValue
{
    Key key;
    OctetString value;
};

using KeyValueArray = cum::vector<KeyValue, MAX_REQUEST_SIZE>;
struct SetRequest
{
    KeyValueArray data;
};

struct SetResponse
{
    Cause cause;
};

struct GetRequest
{
    KeyArray data;
};

struct GetResponse
{
    KeyValueArray data;
};

using PDU_Messages = std::variant<SetRequest,SetResponse,GetRequest,GetResponse>;
struct PDU
{
    TrId trId;
    PDU_Messages message;
};

/***********************************************
/
/            Codec Definitions
/
************************************************/

inline void str(const char* pName, const Cause& pIe, std::string& pCtx, bool pIsLast)
{
    using namespace cum;
    if (pName)
    {
        pCtx = pCtx + "\"" + pName + "\":";
    }
    if (Cause::Ok == pIe) pCtx += "\"Ok\"";
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const KeyValue& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.key, pCtx);
    encode_per(pIe.value, pCtx);
}

inline void decode_per(KeyValue& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.key, pCtx);
    decode_per(pIe.value, pCtx);
}

inline void str(const char* pName, const KeyValue& pIe, std::string& pCtx, bool pIsLast)
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
    size_t nMandatory = 2;
    str("key", pIe.key, pCtx, !(--nMandatory+nOptional));
    str("value", pIe.value, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const SetRequest& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.data, pCtx);
}

inline void decode_per(SetRequest& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.data, pCtx);
}

inline void str(const char* pName, const SetRequest& pIe, std::string& pCtx, bool pIsLast)
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
    str("data", pIe.data, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const SetResponse& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.cause, pCtx);
}

inline void decode_per(SetResponse& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.cause, pCtx);
}

inline void str(const char* pName, const SetResponse& pIe, std::string& pCtx, bool pIsLast)
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
    str("cause", pIe.cause, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const GetRequest& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.data, pCtx);
}

inline void decode_per(GetRequest& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.data, pCtx);
}

inline void str(const char* pName, const GetRequest& pIe, std::string& pCtx, bool pIsLast)
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
    str("data", pIe.data, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const GetResponse& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    encode_per(pIe.data, pCtx);
}

inline void decode_per(GetResponse& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    decode_per(pIe.data, pCtx);
}

inline void str(const char* pName, const GetResponse& pIe, std::string& pCtx, bool pIsLast)
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
    str("data", pIe.data, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const PDU_Messages& pIe, cum::per_codec_ctx& pCtx)
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
    else if (2 == type)
    {
        encode_per(std::get<2>(pIe), pCtx);
    }
    else if (3 == type)
    {
        encode_per(std::get<3>(pIe), pCtx);
    }
}

inline void decode_per(PDU_Messages& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    using TypeIndex = uint8_t;
    TypeIndex type;
    decode_per(type, pCtx);
    if (0 == type)
    {
        pIe = SetRequest();
        decode_per(std::get<0>(pIe), pCtx);
    }
    else if (1 == type)
    {
        pIe = SetResponse();
        decode_per(std::get<1>(pIe), pCtx);
    }
    else if (2 == type)
    {
        pIe = GetRequest();
        decode_per(std::get<2>(pIe), pCtx);
    }
    else if (3 == type)
    {
        pIe = GetResponse();
        decode_per(std::get<3>(pIe), pCtx);
    }
}

inline void str(const char* pName, const PDU_Messages& pIe, std::string& pCtx, bool pIsLast)
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
        std::string name = "SetRequest";
        str(name.c_str(), std::get<0>(pIe), pCtx, true);
        pCtx += "}";
    }
    else if (1 == type)
    {
        if (pName)
            pCtx += std::string(pName) + ":{";
        else
            pCtx += "{";
        std::string name = "SetResponse";
        str(name.c_str(), std::get<1>(pIe), pCtx, true);
        pCtx += "}";
    }
    else if (2 == type)
    {
        if (pName)
            pCtx += std::string(pName) + ":{";
        else
            pCtx += "{";
        std::string name = "GetRequest";
        str(name.c_str(), std::get<2>(pIe), pCtx, true);
        pCtx += "}";
    }
    else if (3 == type)
    {
        if (pName)
            pCtx += std::string(pName) + ":{";
        else
            pCtx += "{";
        std::string name = "GetResponse";
        str(name.c_str(), std::get<3>(pIe), pCtx, true);
        pCtx += "}";
    }
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

inline void encode_per(const PDU& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t optionalmask[1] = {};
    if (pIe.trId)
    {
        set_optional(optionalmask, 0);
    }
    encode_per(optionalmask, sizeof(optionalmask), pCtx);
    if (pIe.trId)
    {
        encode_per(*pIe.trId, pCtx);
    }
    encode_per(pIe.message, pCtx);
}

inline void decode_per(PDU& pIe, cum::per_codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t optionalmask[1] = {};
    decode_per(optionalmask, sizeof(optionalmask), pCtx);
    if (check_optional(optionalmask, 0))
    {
        pIe.trId = decltype(pIe.trId)::value_type{};
        decode_per(*pIe.trId, pCtx);
    }
    decode_per(pIe.message, pCtx);
}

inline void str(const char* pName, const PDU& pIe, std::string& pCtx, bool pIsLast)
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
    if (pIe.trId) nOptional++;
    size_t nMandatory = 1;
    if (pIe.trId)
    {
        str("trId", *pIe.trId, pCtx, !(nMandatory+--nOptional));
    }
    str("message", pIe.message, pCtx, !(--nMandatory+nOptional));
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

#endif //__CUM_MSG_HPP__
