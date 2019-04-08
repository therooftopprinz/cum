#ifndef __CUM_HPP__
#define __CUM_HPP__

#include <stdexcept>
#include <variant>
#include <cstddef>
#include <cstring>
#include <string>
#include <vector>

namespace cum
{

template <typename T, size_t N>
class vector
{
public:
    vector()
    {}

    ~vector()
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
                "accesing cum::vector@" + std::to_string(uintptr_t(this)) +
                " index=" + std::to_string(pIndex));
    }
    T mData[N];
    size_t mSize = 0;
};

class codec_ctx
{
public:
    enum class coder {compact, byte_aligned, aligned};
    codec_ctx(std::byte* pData, size_t pSize)
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

template <typename T>
void encode(const T pIe, codec_ctx& pCtx)
{
    if (sizeof(pIe) > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    new (pCtx.get()) decltype(pIe)(pIe);
    pCtx.advance(sizeof(pIe));
}

template <typename T>
void decode(T& pIe, codec_ctx& pCtx)
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
        pCtx = pCtx + pName + ":\"" + std::to_string(pIe) + "\"";
    }

    if (!isLast)
    {
        pCtx += ",";
    }
}

void encode(const std::string& pIe, codec_ctx& pCtx)
{
    const size_t strsz = pIe.size()+1;
    if (strsz > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    std::memcpy(pCtx.get(), pIe.data(), strsz);
    pCtx.advance(strsz);
}

void decode(std::string& pIe, codec_ctx& pCtx)
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
        pCtx = pCtx + pName + ":\"" + pIe + "\"";
    }

    if (!isLast)
    {
        pCtx += ",";
    }
}

template <typename T>
void encode(const std::vector<T>& pIe, codec_ctx& pCtx)
{
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
        throw std::out_of_range(__PRETTY_FUNCTION__);
    encode(IndexType(pIe.size()), pCtx);
    for (auto& i : pIe)
    {
        encode(i, pCtx);
    }
}

template <typename T>
void decode(std::vector<T>& pIe, codec_ctx& pCtx)
{
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
    {
        throw std::out_of_range(__PRETTY_FUNCTION__);
    }
    IndexType size;
    decode(size, pCtx);
    for (IndexType i=0; i<size; i++)
    {
        pIe.emplace_back();
        decode(pIe.back(), pCtx);
    }
}

template <typename T>
void str(const char* pName, const std::vector<T>& pIe, std::string& pCtx, bool pIsLast)
{
    if (!pName)
    {
        pCtx = pCtx + "[";
    }
    else
    {
        pCtx = pCtx + pName + ":[";
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
void encode(const cum::vector<T, N>& pIe, codec_ctx& pCtx)
{
    // TODO: Base IndexType on N
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
    {
        throw std::out_of_range(__PRETTY_FUNCTION__);
    }
    encode(IndexType(pIe.size()), pCtx);
    for (const auto& i : pIe)
    {
        encode(i, pCtx);
    }
}

template <typename T, size_t N>
void decode(cum::vector<T, N>& pIe, codec_ctx& pCtx)
{
    // TODO: Base IndexType on N
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
    {
        throw std::out_of_range(__PRETTY_FUNCTION__);
    }
    IndexType size;
    decode(size, pCtx);
    for (IndexType i=0; i<size; i++)
    {
        pIe.emplace_back();
        decode(pIe.back(), pCtx);
    }
}

template <typename T, size_t N>
void str(const char* pName, const cum::vector<T, N>& pIe, std::string& pCtx, bool pIsLast)
{
    if (!pName)
    {
        pCtx = pCtx + "[";
    }
    else
    {
        pCtx = pCtx + pName + ":[";
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
    return pOptionalMask[opos] & (1 << bpos);
}

void set_optional(uint8_t *pOptionalMask, size_t n)
{
    size_t opos = n >> 3;
    size_t bpos = n & 7;
    pOptionalMask[opos] |= (1 << bpos);
}

} // namespace cum
#endif // __CUM_HPP__