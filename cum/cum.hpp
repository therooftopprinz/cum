#ifndef __CUM_HPP__
#define __CUM_HPP__

#include <exception>
#include <cstring>
#include <string>

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
        new (mData+mSize) T(std::forward<U>(pArgs)...);
        mSize++;
    }

    void push_back(T&& pOther)
    {
        new (mData+mSize) std::move(pOther);
        mSize++;
    }

    void pop_back()
    {
        mData[mSize-1].~T();
        mSize--;
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
        return nData[pIndex];
    }

    T& at(size_t pIndex)
    {
        checkBounds(pIndex);
        return nData[pIndex];
    }

    T* begin()
    {
        return mData;
    }

    T* end()
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
        return nData[pIndex];
    }

    const T& at(size_t pIndex) const
    {
        checkBounds(pIndex);
        return nData[pIndex];
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
    size_t mSize;
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
        mSize -= mSize;
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
void encode(const T pIe, pCtx)
{
    if (sizeof(pIe) > pCtx.size())
        throw std::out_of_range();
    new (pCtx.data()) decltype(pIe)(pIe);
    pCtx.advance(sizeof(pIe));
}

template <typename T>
void decode(T& pIe, pCtx)
{
    if (sizeof(pIe) > pCtx.size())
        throw std::out_of_range();
    std::memcpy(pCtx.data(), sizeof(pIe));
    pCtx.advance(sizeof(pIe));
}

template <typename T>
void encode(const std::vector<T>& pIe, pCtx)
{
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
        throw std::out_of_range();
    encode(IndexType(pIe.size()), pCtx);
    for (auto& i : pIe)
        encode(i, pCtx);
}

template <typename T>
void decode(std::vector<T>& pIe, pCtx)
{
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
        throw std::out_of_range();
    IndexType size;
    decode(size, pCtx);
    for (IndexType i=0; i<size; i++)
    {
        pIe.push_back();
        decode(pIe.back(), pCtx);
    }
}

template <typename T, size_t N>
void encode(const cum::vector<T, N>& pIe, pCtx)
{
    // TODO: Base IndexType on N
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
        throw std::out_of_range();
    encode(IndexType(pIe.size()), pCtx);
    for (auto& i : pIe)
        encode(i, pCtx);
}

template <typename T, size_t N>
void decode(cum::vector<T, N>& pIe, pCtx)
{
    // TODO: Base IndexType on N
    using IndexType = uint32_t;
    if (sizeof(IndexType) > pCtx.size())
        throw std::out_of_range();
    IndexType size;
    decode(size, pCtx);
    for (IndexType i=0; i<size; i++)
    {
        pIe.push_back();
        decode(pIe.back(), pCtx);
    }
}

void check_optional(uint8_t *pOptionalMask, size_t n)
{
    return false;
}

// template <typename... Ts>
// void encode(const std::variant:<Ts...>& pIe, pCtx)
// {
//     // TODO: Base TypeIndex on N
//     using TypeIndex = uint32_t;
//     TypeIndex type = pIe.index();
//     encode(type, pCtx);
//     std::visit([&pCtx](auto&& pIe){encode(pIe, pCtx);}, pIe);
// }

// template <typename... Ts>
// void decode(std::variant<Ts...>& pIe, pCtx)
// {
//     // TODO: Base TypeIndex on N
//     using TypeIndex = uint32_t;
//     TypeIndex type;
//     // decide(type, pCtx);
//     // std::visit([&pCtx ](auto&& pIe){encode(pIe, pCtx);}, pIe);
// }

#endif __CUM_HPP__