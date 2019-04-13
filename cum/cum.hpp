#ifndef __CUM_HPP__
#define __CUM_HPP__

#include <type_traits>
#include <stdexcept>
#include <variant>
#include <cstddef>
#include <cstring>
#include <string>
#include <vector>

namespace cum
{


template <size_t N>
struct GetTypeOfUnsigned
{
    using type = typename std::conditional<N<256, uint8_t,
                    typename std::conditional<N<65536, uint16_t,
                        typename std::conditional<N<4294967296, uint32_t,
                            uint64_t
                        >::type
                    >::type
                >::type;
};

template <ssize_t N>
struct GetTypeOfSigned
{
    using type = typename std::conditional<N>=-128||N<125, int8_t,
                    typename std::conditional<N>=-32768||N<32768, uint16_t,
                        typename std::conditional<N>=-2147483648||N<2147483648, uint32_t,
                            uint64_t
                        >::type
                    >::type
                >::type;
};

template <typename T, size_t>
struct vector : public std::vector<T> {};

template <typename T, size_t N>
class preallocated_vector
{
public:
    preallocated_vector(std::initializer_list<T> pList)
    {
        for (auto&& i : pList)
        {
            emplace_back(std::move(i));
        }
    }

    ~preallocated_vector()
    {
        for (size_t i = 0; i<mSize; i++)
        {
            pop_back();
        }
    }

    template <typename... U>
    void emplace_back(U&&... pArgs)
    {
        new (mData+mSize++) T(std::forward<U>(pArgs)...);
    }

    void push_back(T&& pOther)
    {
        new (mData+mSize++) T(std::move(pOther));
    }

    void pop_back()
    {
        mData[--mSize].~T();
    }

    T* data()
    {
        return mData;
    }

    T& front()
    {
        return mData[0];
    }

    T& back()
    {
        return mData[mSize-1];
    }

    T& operator[](size_t pIndex)
    {
        return mData[pIndex];
    }

    T& at(size_t pIndex)
    {
        checkBounds(pIndex);
        return mData[pIndex];
    }

    T* begin()
    {
        return mData;
    }

    T* end()
    {
        return mData+mSize;
    }

    const T* begin() const
    {
        return mData;
    }

    const T* end() const
    {
        return mData+mSize;
    }

    const T* data() const
    {
        return mData;
    }

    const T& front() const
    {
        return mData[0];
    }

    const T& back() const
    {
        return mData[mSize-1];
    }

    const T& operator[](size_t pIndex) const
    {
        return mData[pIndex];
    }

    const T& at(size_t pIndex) const
    {
        checkBounds(pIndex);
        return mData[pIndex];
    }

    size_t size() const
    {
        return mSize;
    }

    bool empty() const
    {
        return size() == 0;
    }

    size_t max_size() const
    {
        return N;
    }
private:
    void checkBounds(size_t pIndex)
    {
        if (pIndex>=N)
            throw std::out_of_range(std::string{} +
                "accesing cum::preallocated_vector@" + std::to_string(uintptr_t(this)) +
                " index=" + std::to_string(pIndex));
    }
    T mData[N];
    size_t mSize = 0;
};

class per_codec_ctx
{
public:
    enum class coder {uper, per};
    per_codec_ctx(std::byte* pData, size_t pSize)
        : mData(pData)
        , mSize(pSize)
    {}

    std::byte* get()
    {
        return mData;
    }

    void advance(size_t pSize)
    {
        mData += pSize;
        mSize -= pSize;
    }

    size_t size() const
    {
        return mSize;
    }

private:
    std::byte* mData;
    size_t mSize;
};

void encode_per(const uint8_t *pIeOctet, size_t pSize, per_codec_ctx& pCtx)
{
    if (pSize > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    std::memcpy(pCtx.get(), pIeOctet, pSize);
    pCtx.advance(pSize);
}

void decode_per(uint8_t *pIeOctet, size_t pSize, per_codec_ctx& pCtx)
{
    if (pSize > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    std::memcpy(pIeOctet, pCtx.get(), pSize);
    pCtx.advance(pSize);
}

template <typename T>
void encode_per(const T pIe, per_codec_ctx& pCtx)
{
    if (sizeof(pIe) > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    new (pCtx.get()) decltype(pIe)(pIe);
    pCtx.advance(sizeof(pIe));
}

template <typename T>
void decode_per(T& pIe, per_codec_ctx& pCtx)
{
    if (sizeof(pIe) > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    std::memcpy(&pIe, pCtx.get(), sizeof(pIe));
    pCtx.advance(sizeof(pIe));
}

template <typename T>
void str(const char* pName, const T& pIe, std::string& pCtx, bool isLast)
{
    if (!pName)
    {
        pCtx = pCtx + "\"" + std::to_string(pIe) + "\"";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":\"" + std::to_string(pIe) + "\"";
    }

    if (!isLast)
    {
        pCtx += ",";
    }
}

void str(const char* pName, const char pIe, std::string& pCtx, bool isLast)
{
    if (!pName)
    {
        pCtx = pCtx + "\"" + pIe + "\"";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":\"" + std::to_string(pIe) + "\"";
    }

    if (!isLast)
    {
        pCtx += ",";
    }
}

void encode_per(const std::string& pIe, per_codec_ctx& pCtx)
{
    const size_t strsz = pIe.size()+1;
    if (strsz > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    std::memcpy(pCtx.get(), pIe.data(), strsz);
    pCtx.advance(strsz);
}

void decode_per(std::string& pIe, per_codec_ctx& pCtx)
{
    // TODO: safer pls
    pIe = (const char*)pCtx.get();
    const size_t strsz = pIe.size()+1;
    if (strsz > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    pCtx.advance(strsz);
}

void str(const char* pName, const std::string& pIe, std::string& pCtx, bool isLast)
{
    if (!pName)
    {
        pCtx = pCtx + "\"" + pIe + "\"";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":\"" + pIe + "\"";
    }

    if (!isLast)
    {
        pCtx += ",";
    }
}

template <typename T, size_t N>
void encode_per(const cum::vector<T,N>& pIe, per_codec_ctx& pCtx)
{
    using IndexType = typename GetTypeOfUnsigned<N>::type;
    if (sizeof(IndexType) > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    encode_per(IndexType(pIe.size()), pCtx);
    for (auto& i : pIe)
    {
        encode_per(i, pCtx);
    }
}

template <typename T, size_t N>
void decode_per(cum::vector<T, N>& pIe, per_codec_ctx& pCtx)
{
    using IndexType = typename GetTypeOfUnsigned<N>::type;
    if (sizeof(IndexType) > pCtx.size())
    {
        throw std::out_of_range(__PRETTY_FUNCTION__);
    }
    IndexType size;
    decode_per(size, pCtx);
    for (IndexType i=0; i<size; i++)
    {
        pIe.emplace_back();
        decode_per(pIe.back(), pCtx);
    }
}

template <typename T, size_t N>
void str(const char* pName, const cum::vector<T,N>& pIe, std::string& pCtx, bool pIsLast)
{
    if (!pName)
    {
        pCtx = pCtx + "[";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":[";
    }
    for (size_t i=0; i<pIe.size();i++)
    {
        str(nullptr, pIe[i], pCtx, (i>=pIe.size()-1) ? true : false);
    }
    pCtx += "]";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

template <typename T, size_t N>
void encode_per(const cum::preallocated_vector<T, N>& pIe, per_codec_ctx& pCtx)
{
    using IndexType = typename GetTypeOfUnsigned<N>::type;
    if (sizeof(IndexType) > pCtx.size())
    {
        throw std::out_of_range(__PRETTY_FUNCTION__);
    }
    encode_per(IndexType(pIe.size()), pCtx);
    for (const auto& i : pIe)
    {
        encode_per(i, pCtx);
    }
}

template <typename T, size_t N>
void decode_per(cum::preallocated_vector<T, N>& pIe, per_codec_ctx& pCtx)
{
    using IndexType = typename GetTypeOfUnsigned<N>::type;
    if (sizeof(IndexType) > pCtx.size())
    {
        throw std::out_of_range(__PRETTY_FUNCTION__);
    }
    IndexType size;
    decode_per(size, pCtx);
    for (IndexType i=0; i<size; i++)
    {
        pIe.emplace_back();
        decode_per(pIe.back(), pCtx);
    }
}

template <typename T, size_t N>
void str(const char* pName, const cum::preallocated_vector<T, N>& pIe, std::string& pCtx, bool pIsLast)
{
    if (!pName)
    {
        pCtx = pCtx + "[";
    }
    else
    {
        pCtx = pCtx + "\"" + pName + "\":[";
    }
    for (size_t i=0; i<pIe.size();i++)
    {
        str(nullptr, pIe[i], pCtx, (i>=pIe.size()-1) ? true : false);
    }
    pCtx += "]";
    if (!pIsLast)
    {
        pCtx += ",";
    }
}

bool check_optional(uint8_t *pOptionalMask, size_t n)
{
    size_t opos = n >> 3;
    size_t bpos = n & 7;
    return pOptionalMask[opos] & (0x80u >> bpos);
}

void set_optional(uint8_t *pOptionalMask, size_t n)
{
    size_t opos = n >> 3;
    size_t bpos = n & 7;
    pOptionalMask[opos] |= (0x80u >> bpos);
}

} // namespace cum
#endif // __CUM_HPP__