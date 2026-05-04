"""Golden-vector test for generated sample2 codecs (parity with JS / C++)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "target_py3") not in sys.path:
    sys.path.insert(0, str(_ROOT / "target_py3"))

from cum.cum import PerCodecCtx

from sample2 import (
    Gender,
    decode_using_phone_book,
    encode_using_phone_book,
)


def _hex_to_bytes(h: str) -> bytes:
    return bytes.fromhex(h)


def _u8equal(a: memoryview | bytes | bytearray, b: bytes, n: int) -> bool:
    for i in range(n):
        if a[i] != b[i]:
            return False
    return True


def main() -> None:
    assert Gender.Male == 10
    assert Gender.Female == 11
    assert issubclass(Gender, int)

    # Matches target_js/test/sample2.test.mjs GOLDEN_HEX (129 bytes vs C++ GCC x86-64).
    golden_hex = "030080312e666972737400312e6d6964646c6500312e6c61737400312e61646472657373000a00000002042b363339032b34340001322e627573696e6573734e616d6500322e616464726573730001032b3633082a000000000000000000322e666972737400322e6c61737400322e61646472657373000a00000001032b343200"
    golden = _hex_to_bytes(golden_hex)

    def empty_raw64():
        return {"len": 0, "buf": bytearray(64)}

    def corporate_raw():
        b = bytearray(64)
        b[0] = 42
        return {"len": 8, "buf": b}

    phone_book_fixture = {
        "phoneEntryArray": [
            {
                "PersonalPhoneEntry": {
                    "firstName": "1.first",
                    "middleName": "1.middle",
                    "lastName": "1.last",
                    "address": "1.address",
                    "gender": Gender.Male,
                    "phoneNumbers": ["+639", "+44"],
                    "rawData": empty_raw64(),
                },
            },
            {
                "CorporatePhoneEntry": {
                    "businessName": "2.businessName",
                    "address": "2.address",
                    "phoneNumbers": ["+63"],
                    "rawData": corporate_raw(),
                },
            },
            {
                "PersonalPhoneEntry": {
                    "firstName": "2.first",
                    "middleName": None,
                    "lastName": "2.last",
                    "address": "2.address",
                    "gender": Gender.Male,
                    "phoneNumbers": ["+42"],
                    "rawData": empty_raw64(),
                },
            },
        ],
    }

    buf = bytearray(1024)
    ctx = PerCodecCtx(buf)
    encode_using_phone_book(phone_book_fixture, ctx)
    encoded_len = ctx.off

    assert encoded_len == len(golden), (
        "encoded {!r} vs golden {!r}".format(encoded_len, len(golden))
    )
    assert _u8equal(buf, golden, encoded_len)

    rnd = decode_using_phone_book(PerCodecCtx(bytes(buf[:encoded_len])))
    assert (
        len(rnd["phoneEntryArray"]) == len(phone_book_fixture["phoneEntryArray"])
    )
    assert (
        rnd["phoneEntryArray"][0]["PersonalPhoneEntry"]["firstName"]
        == "1.first"
    )
    assert (
        rnd["phoneEntryArray"][1]["CorporatePhoneEntry"]["rawData"]["len"] == 8
    )
    assert rnd["phoneEntryArray"][1]["CorporatePhoneEntry"]["rawData"]["buf"][0] == 42
    assert rnd["phoneEntryArray"][2]["PersonalPhoneEntry"]["middleName"] is None

    print("sample2_py3_golden_ok")


if __name__ == "__main__":
    main()
