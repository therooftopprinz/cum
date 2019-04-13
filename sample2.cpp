#include <iostream>
#include <iomanip>
#include <string>

#include "sample2.hpp"

void printBuffer(void* pPtr, size_t pSize)
{
    uint8_t *ptr = (uint8_t*) pPtr;
    std::cout << "buffer[" << pSize << "]: ";
    for (size_t i=0; i<pSize; i++)
    {
        std::cout << std::hex << std::setw(2) << std::setfill('0') << (unsigned)ptr[i];
    }
    std::cout << "\n";
}

int main()
{
    PhoneBook pb;

    {
        pb.phoneEntryArray.emplace_back(PersonalPhoneEntry{});
        auto& phoneEntry = std::get<PersonalPhoneEntry>(pb.phoneEntryArray.back());

        phoneEntry.firstName = "1.first";
        phoneEntry.middleName = "1.middle";
        phoneEntry.lastName = "1.last";
        phoneEntry.address = "1.address";

        phoneEntry.phoneNumbers.emplace_back(std::initializer_list<char>({'+','6','3','9'}));
        phoneEntry.phoneNumbers.emplace_back(std::initializer_list<char>({'+','4','4'}));
    }

    {
        pb.phoneEntryArray.emplace_back(CorporatePhoneEntry{});
        auto& phoneEntry = std::get<CorporatePhoneEntry>(pb.phoneEntryArray.back());

        phoneEntry.businessName = "2.businessName";
        phoneEntry.address = "2.address";
        {
            phoneEntry.phoneNumbers.emplace_back();
            auto& pn = phoneEntry.phoneNumbers.back();
            pn.push_back('+');
            pn.push_back('6');
            pn.push_back('3');
        }
    }

    {
        pb.phoneEntryArray.emplace_back(PersonalPhoneEntry{});
        auto& phoneEntry = std::get<PersonalPhoneEntry>(pb.phoneEntryArray.back());

        phoneEntry.firstName = "2.first";
        phoneEntry.lastName = "2.last";
        phoneEntry.address = "2.address";

        phoneEntry.phoneNumbers.emplace_back(std::initializer_list<char>({'+','4','2'}));
    }

    std::byte buffer[1024];

    {
        cum::per_codec_ctx ctx(buffer, 1024);
        encode_per(pb, ctx);
        auto encodeSize = sizeof(buffer) - ctx.size();
        printBuffer(buffer, encodeSize);
        std::string out;
        str(nullptr, pb, out, true);
        std::cout << out << "\n";
    }

    {
        PhoneBook pbDecoded;
        cum::per_codec_ctx ctx(buffer, 1024);
        decode_per(pbDecoded, ctx);
        std::string out;
        str(nullptr, pbDecoded, out, true);
        std::cout << out << "\n";
    }
}