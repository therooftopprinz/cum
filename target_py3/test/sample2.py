# Generated from CUM AST — Python 3 annotated types / IntEnum and PER codecs (match target_cpp / target_js).
from __future__ import annotations

from enum import IntEnum

from typing import Optional, TypedDict, Union

from cum.cum import CodecError, PerCodecCtx, check_optional, set_optional

class Gender(IntEnum):
    Male = 10
    Female = 11

String = str  # CUM using String

OptionalString = Optional[str]  # CUM using OptionalString
# CUM optional; use None when absent.

PhoneNumber = str  # CUM using PhoneNumber
# CUM dynamic<char,?>: str of at most 22 Latin-1 code units.

PhoneNumberArray = list[PhoneNumber]  # CUM using PhoneNumberArray
# CUM dynamic sequence: at most 32 elements.

class Td_buffer64(TypedDict):
    """
    CUM buffer capacity '64' (element type byte).
    """
    len: int
    buf: bytearray

# runtime alias naming the same structurally as the CUM `using buffer64`
buffer64 = Td_buffer64

class PersonalPhoneEntry(TypedDict):
    firstName: str
    middleName: Optional[str]
    lastName: str
    address: str
    gender: Gender
    phoneNumbers: list[PhoneNumber]
    rawData: Td_buffer64

class CorporatePhoneEntry(TypedDict):
    businessName: str
    address: str
    phoneNumbers: list[PhoneNumber]
    rawData: Td_buffer64

class PhoneEntry_PersonalPhoneEntry(TypedDict):
    PersonalPhoneEntry: PersonalPhoneEntry

class PhoneEntry_CorporatePhoneEntry(TypedDict):
    CorporatePhoneEntry: CorporatePhoneEntry

PhoneEntry = Union[
    PhoneEntry_PersonalPhoneEntry,
    PhoneEntry_CorporatePhoneEntry
]

PhoneEntryArray = list[PhoneEntry]  # CUM using PhoneEntryArray
# CUM dynamic sequence: at most 255 elements.

class PhoneBook(TypedDict):
    phoneEntryArray: list[PhoneEntry]

# --- Packed encoding (PER-byte aligned, enums as i32 LE) ---

def encode_using_gender(v: int, ctx: PerCodecCtx) -> None:
    ctx.write_i32le(int(v))

def decode_using_gender(ctx: PerCodecCtx) -> int:
    return int(ctx.read_i32le())

def encode_using_string(v: str, ctx: PerCodecCtx) -> None:
    ctx.encode_c_string_latin1(v)

def decode_using_string(ctx: PerCodecCtx) -> str:
    return ctx.decode_c_string_latin1()

def encode_using_phone_number(obj, ctx: PerCodecCtx) -> None:
    if len(obj) > 22: raise CodecError('PhoneNumber')
    ctx.write_count(22, len(obj))
    for ch in obj:
        cp = ord(ch)
        if cp > 255: raise CodecError('non Latin-1 in PhoneNumber')
        ctx.write_u8(cp)

def decode_using_phone_number(ctx: PerCodecCtx):
    n = ctx.read_count(22)
    parts = []
    for _ in range(n):
        parts.append(chr(ctx.read_u8()))
    return ''.join(parts)

def encode_using_phone_number_array(obj, ctx: PerCodecCtx) -> None:
    if len(obj) > 32: raise CodecError('PhoneNumberArray')
    ctx.write_count(32, len(obj))
    for it in obj:
        encode_using_phone_number(it, ctx)

def decode_using_phone_number_array(ctx: PerCodecCtx):
    n = ctx.read_count(32)
    arr = []
    for _ in range(n):
        arr.append(decode_using_phone_number(ctx))
    return arr

def encode_using_buffer64(bp, ctx: PerCodecCtx) -> None:
    if bp['len'] > 64: raise CodecError('buffer64 len')
    ctx.write_count(64, bp['len'])
    mv = memoryview(bp['buf'])
    ctx.write_bytes(mv[:bp['len']], bp['len'])

def decode_using_buffer64(ctx: PerCodecCtx):
    cap = 64
    ln = ctx.read_count(cap)
    out_buf = bytearray(cap)
    blob = ctx.read_bytes(ln)
    if ln:
        out_buf[:ln] = blob
    return {'len': ln, 'buf': out_buf}

def encode_using_phone_entry_array(obj, ctx: PerCodecCtx) -> None:
    if len(obj) > 255: raise CodecError('PhoneEntryArray')
    ctx.write_count(255, len(obj))
    for it in obj:
        encode_using_phone_entry(it, ctx)

def decode_using_phone_entry_array(ctx: PerCodecCtx):
    n = ctx.read_count(255)
    arr = []
    for _ in range(n):
        arr.append(decode_using_phone_entry(ctx))
    return arr

# Codec: sequence PersonalPhoneEntry
def encode_using_personal_phone_entry(pie, ctx: PerCodecCtx) -> None:
    optional_mask = bytearray(1)
    if pie["middleName"] is not None:
        set_optional(optional_mask, 0)
    ctx.write_bytes(optional_mask, len(optional_mask))
    encode_using_string(pie["firstName"], ctx)
    if pie["middleName"] is not None:
        encode_using_string(pie["middleName"], ctx)
    encode_using_string(pie["lastName"], ctx)
    encode_using_string(pie["address"], ctx)
    encode_using_gender(pie["gender"], ctx)
    encode_using_phone_number_array(pie["phoneNumbers"], ctx)
    if pie["rawData"]['len'] > 64: raise CodecError('buffer64')
    encode_using_buffer64(pie["rawData"], ctx)

def decode_using_personal_phone_entry(ctx: PerCodecCtx):
    pie = {}
    optional_mask = ctx.read_bytes(1)
    pie["firstName"] = decode_using_string(ctx)
    if check_optional(optional_mask, 0):
        pie["middleName"] = decode_using_string(ctx)
    else:
        pie["middleName"] = None
    pie["lastName"] = decode_using_string(ctx)
    pie["address"] = decode_using_string(ctx)
    pie["gender"] = decode_using_gender(ctx)
    pie["phoneNumbers"] = decode_using_phone_number_array(ctx)
    pie["rawData"] = decode_using_buffer64(ctx)
    return pie

# Codec: sequence CorporatePhoneEntry
def encode_using_corporate_phone_entry(pie, ctx: PerCodecCtx) -> None:
    encode_using_string(pie["businessName"], ctx)
    encode_using_string(pie["address"], ctx)
    encode_using_phone_number_array(pie["phoneNumbers"], ctx)
    if pie["rawData"]['len'] > 64: raise CodecError('buffer64')
    encode_using_buffer64(pie["rawData"], ctx)

def decode_using_corporate_phone_entry(ctx: PerCodecCtx):
    pie = {}
    pie["businessName"] = decode_using_string(ctx)
    pie["address"] = decode_using_string(ctx)
    pie["phoneNumbers"] = decode_using_phone_number_array(ctx)
    pie["rawData"] = decode_using_buffer64(ctx)
    return pie

# Codec: choice PhoneEntry
def encode_using_phone_entry(pie, ctx: PerCodecCtx) -> None:
    if 'PersonalPhoneEntry' in pie and pie['PersonalPhoneEntry'] is not None:
        ctx.write_choice_index(2, 0)
        encode_using_personal_phone_entry(pie['PersonalPhoneEntry'], ctx)
        return
    elif 'CorporatePhoneEntry' in pie and pie['CorporatePhoneEntry'] is not None:
        ctx.write_choice_index(2, 1)
        encode_using_corporate_phone_entry(pie['CorporatePhoneEntry'], ctx)
        return
    raise CodecError('encode_using_phone_entry: exactly one discriminant key expected')

def decode_using_phone_entry(ctx: PerCodecCtx):
    idx = ctx.read_choice_index(2)
    if idx == 0:
        return {'PersonalPhoneEntry': decode_using_personal_phone_entry(ctx)}
    elif idx == 1:
        return {'CorporatePhoneEntry': decode_using_corporate_phone_entry(ctx)}
    raise CodecError('bad choice index')

# Codec: sequence PhoneBook
def encode_using_phone_book(pie, ctx: PerCodecCtx) -> None:
    encode_using_phone_entry_array(pie["phoneEntryArray"], ctx)

def decode_using_phone_book(ctx: PerCodecCtx):
    pie = {}
    pie["phoneEntryArray"] = decode_using_phone_entry_array(ctx)
    return pie

