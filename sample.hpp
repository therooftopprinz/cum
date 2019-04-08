// Enumeration:  ('Cause', 'Ok')
// Constant:  ('MAX_REQUEST_SIZE', '16')
// Constant:  ('MAX_VALUE_SIZE', '64')
// Type:  ('Key', {'type': 'unsigned'})
// Type:  ('Key', {'width': '8'})
// Type:  ('Key', {'min': '1'})
// Type:  ('Key', {'max': '255'})
// Type:  ('KeyArray', {'type': 'key'})
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
// Type:  ('KeyValueArray', {'dynamic_array': 'MAX_REQUEST_SIZE'})
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
using KeyArray = cum::vector<key, MAX_REQUEST_SIZE>;
using TrId = std::optional<uint8_t>;
using OctetString = cum::vector<uint8_t, MAX_VALUE_SIZE>;
struct KeyValue
{
    Key key;
    OctetString value;
};

using KeyValueArray = cum::vector<KeyValue, MAX_REQUEST_SIZE>;
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

void encode(const KeyValue& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
}

void str(const char* pName, const KeyValue& pIe, std::string& pCtx, bool pIsLast)
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
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void decode(KeyValue& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
}

void encode(const SetResponse& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    encode(pIe.cause, pCtx);
}

void str(const char* pName, const SetResponse& pIe, std::string& pCtx, bool pIsLast)
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
    str("cause", pIe.cause, pCtx, true);
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void decode(SetResponse& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    decode(pIe.cause, pCtx);
}

void encode(const GetRequest& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
}

void str(const char* pName, const GetRequest& pIe, std::string& pCtx, bool pIsLast)
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
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void decode(GetRequest& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
}

void encode(const GetResponse& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
}

void str(const char* pName, const GetResponse& pIe, std::string& pCtx, bool pIsLast)
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
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void decode(GetResponse& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
}

void encode(const PDU_Messages& pIe, cum::codec_ctx& pCtx)
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
    else if (2 == type)
    {
        encode(std::get<2>(pIe), pCtx);
    }
    else if (3 == type)
    {
        encode(std::get<3>(pIe), pCtx);
    }
}

void decode(PDU_Messages& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    using TypeIndex = uint32_t;
    TypeIndex type;
    decode(type, pCtx);
    if (0 == type)
    {
        pIe = SetRequest{};
        decode(std::get<0>(pIe), pCtx);
    }
    else if (1 == type)
    {
        pIe = SetResponse{};
        decode(std::get<1>(pIe), pCtx);
    }
    else if (2 == type)
    {
        pIe = GetRequest{};
        decode(std::get<2>(pIe), pCtx);
    }
    else if (3 == type)
    {
        pIe = GetResponse{};
        decode(std::get<3>(pIe), pCtx);
    }
}

void str(const char* pName, const PDU_Messages& pIe, std::string& pCtx, bool pIsLast)
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
    else if (2 == type)
    {
        str(pName, std::get<2>(pIe), pCtx, true);
    }
    else if (3 == type)
    {
        str(pName, std::get<3>(pIe), pCtx, true);
    }
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void encode(const PDU& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t *optionalmask = new(pCtx.get()) uint8_t[1]{};
    pCtx.advance(1);
    if (pIe.trId)
    {
        set_optional(optionalmask, 0);
        encode(*pIe.trId, pCtx);
    }
    encode(pIe.message, pCtx);
}

void str(const char* pName, const PDU& pIe, std::string& pCtx, bool pIsLast)
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
    if (pIe.trId)
    {
        str("trId", *pIe.trId, pCtx, false);
    }
    str("message", pIe.message, pCtx, true);
    pCtx = pCtx + "}";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

void decode(PDU& pIe, cum::codec_ctx& pCtx)
{
    using namespace cum;
    uint8_t *optionalmask = (uint8_t*)pCtx.get();
    pCtx.advance(1);
    if (check_optional(optionalmask, 0))
    {
        pIe.trId = decltype(pIe.trId)::value_type{};
        decode(*pIe.trId, pCtx);
    }
    decode(pIe.message, pCtx);
}

#endif //__CUM_MSG_HPP__
