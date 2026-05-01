"""
CUM Python 3 runtime — mirrors `target_js/cum/cum.mjs` / `target_cpp/cum/cum.hpp`.

Packed primitives and PER-style packing rules match the JS implementation.
"""

from __future__ import annotations

import struct
from typing import SupportsIndex, Union

BufferLike = Union[bytes, bytearray, memoryview]


class CodecError(Exception):
    """Invalid encode/decode inputs or malformed bitstream."""

    pass


def octets_for_cum_capacity(capacity: SupportsIndex) -> int:
    n = int(capacity)
    if n < 1:
        raise CodecError("invalid capacity {!r}".format(capacity))
    if n <= 256:
        return 1
    if n <= 65536:
        return 2
    if n <= 4294967296:
        return 4
    return 8


def octets_for_choice_arity(alternatives: SupportsIndex) -> int:
    n = int(alternatives)
    if n < 2:
        raise CodecError("choice must have ≥2 alternatives")
    if n < 256:
        return 1
    if n < 65536:
        return 2
    if n < 4294967296:
        return 4
    return 8


def set_optional(mask: bytearray, idx: int) -> None:
    byte = idx >> 3
    bit = idx & 7
    mask[byte] |= 0x80 >> bit


def check_optional(mask: Union[bytes, bytearray, memoryview], idx: int) -> bool:
    byte = idx >> 3
    bit = idx & 7
    return (mask[byte] & (0x80 >> bit)) != 0


def write_integral_le(buf: Union[bytes, bytearray, memoryview], dst_off: int, value: int, nbytes: int) -> None:
    v = int(value) % (1 << (nbytes * 8))
    for b in range(nbytes):
        buf[dst_off + b] = (v >> (8 * b)) & 0xFF


def read_integral_le(buf: BufferLike, src_off: int, nbytes: int) -> int:
    v = 0
    mv = buf if isinstance(buf, memoryview) else memoryview(buf)
    for b in range(nbytes):
        v |= int(mv[src_off + b]) << (8 * b)
    return v


class PerCodecCtx:
    """Packed codec cursor; corresponds to `cum::per_codec_ctx`."""

    __slots__ = ("buf", "off")

    buf: BufferLike
    off: int

    def __init__(self, backing: BufferLike, offset: int = 0):
        self.buf = backing
        self.off = int(offset)

    def remaining(self) -> int:
        return len(self.buf) - self.off

    def _bump(self, n: int) -> None:
        if self.remaining() < n:
            raise CodecError("codec attempted past end of buffer")
        self.off += n

    def write_bytes(self, src: BufferLike, length: int | None = None) -> None:
        if isinstance(src, memoryview):
            sl = len(src)
        else:
            sl = len(src)
        ln = sl if length is None else length
        if ln > sl:
            raise CodecError("write slice too long")
        if ln > self.remaining():
            raise CodecError("encode buffer full")
        mo = memoryview(src)
        self.buf[self.off : self.off + ln] = mo[:ln]
        self.off += ln

    def read_bytes(self, ln: int) -> bytes:
        if ln > self.remaining():
            raise CodecError("decode overrun")
        mv = memoryview(self.buf)
        chunk = mv[self.off : self.off + ln].tobytes()
        self.off += ln
        return chunk

    def write_i32le(self, v: int) -> None:
        if self.remaining() < 4:
            raise CodecError("encode buffer full")
        if isinstance(self.buf, bytearray):
            struct.pack_into("<i", self.buf, self.off, int(v))
        else:
            raise CodecError("encode requires a writable bytearray backing")
        self.off += 4

    def read_i32le(self) -> int:
        if self.remaining() < 4:
            raise CodecError("decode overrun")
        mv = memoryview(self.buf)
        val = struct.unpack_from("<i", mv, self.off)[0]
        self.off += 4
        return int(val)

    def write_u8(self, byte: int) -> None:
        if self.remaining() < 1:
            raise CodecError("encode buffer full")
        if not isinstance(self.buf, bytearray):
            raise CodecError("encode requires a writable bytearray backing")
        self.buf[self.off] = int(byte) & 0xFF
        self.off += 1

    def read_u8(self) -> int:
        if self.remaining() < 1:
            raise CodecError("decode overrun")
        b = memoryview(self.buf)[self.off]
        self.off += 1
        return int(b)

    def write_count(self, max_cardinality: int, count: int) -> None:
        nb = octets_for_cum_capacity(max_cardinality)
        cap = int(max_cardinality)
        if count < 0 or count > cap:
            raise CodecError(
                "collection count {} out of range (max {})".format(count, cap)
            )
        if self.remaining() < nb:
            raise CodecError("encode buffer full")
        if not isinstance(self.buf, bytearray):
            raise CodecError("encode requires a writable bytearray backing")
        write_integral_le(self.buf, self.off, int(count), nb)
        self.off += nb

    def read_count(self, max_cardinality: int) -> int:
        nb = octets_for_cum_capacity(max_cardinality)
        cap = int(max_cardinality)
        if self.remaining() < nb:
            raise CodecError("decode overrun")
        count = read_integral_le(self.buf, self.off, nb)
        self.off += nb
        if count > cap or count < 0:
            raise CodecError("decoded count {} out of range (max {})".format(count, cap))
        return count

    def encode_c_string_latin1(self, string: str) -> None:
        n = len(string) + 1
        if n > self.remaining():
            raise CodecError("encode buffer full")
        if not isinstance(self.buf, bytearray):
            raise CodecError("encode requires a writable bytearray backing")
        for ch in string:
            cp = ord(ch)
            if cp > 255:
                raise CodecError("non Latin-1 string not supported for CUM string")
            self.buf[self.off] = cp
            self.off += 1
        self.buf[self.off] = 0
        self.off += 1

    def decode_c_string_latin1(self) -> str:
        mv = memoryview(self.buf)
        start = self.off
        end = start
        max_len = len(mv)
        while end < max_len and mv[end] != 0:
            end += 1
        if end >= max_len:
            raise CodecError("unterminated C string")
        raw = mv[start:end].tobytes()
        self.off = end + 1
        return raw.decode("latin1")

    def write_choice_index(self, num_alternatives: int, index: int) -> None:
        nb = octets_for_choice_arity(num_alternatives)
        if index < 0 or index >= num_alternatives:
            raise CodecError(
                "choice index {!r} invalid ({!r} alts)".format(index, num_alternatives)
            )
        if self.remaining() < nb:
            raise CodecError("encode buffer full")
        if not isinstance(self.buf, bytearray):
            raise CodecError("encode requires a writable bytearray backing")
        write_integral_le(self.buf, self.off, index, nb)
        self.off += nb

    def read_choice_index(self, num_alternatives: int) -> int:
        nb = octets_for_choice_arity(num_alternatives)
        if self.remaining() < nb:
            raise CodecError("decode overrun")
        index = read_integral_le(self.buf, self.off, nb)
        self.off += nb
        if index >= num_alternatives or index < 0:
            raise CodecError("bad choice index {}".format(index))
        return index
