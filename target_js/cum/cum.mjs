/**
 * CUM JavaScript runtime — mirrors `target_cpp/cum/cum.hpp`.
 *
 * Packed (byte-aligned PER-style) primitives live here; other coding rules can be
 * added to this same module alongside, like the single-header C++ layout.
 */

export class CodecError extends Error {
  constructor(message) {
    super(message);
    this.name = "CodecError";
  }
}

/**
 * Prefix width for lengths/counts capped at `capacity` (dynamic_array / buffer cap).
 * Mirrors cum.hpp `DetermineUnsignedType<N>`: N<=256 -> 1 byte, etc.
 */
export function octetsForCumCapacity(capacity) {
  const N = Number(capacity);
  if (!(N >= 1) || Number.isNaN(N)) throw new CodecError(`invalid capacity ${capacity}`);
  if (N <= 256) return 1;
  if (N <= 65536) return 2;
  if (N <= 4294967296) return 4;
  return 8;
}

/** Discriminator octets for variant index; mirrors CppGenerator.determineUnsignedSize(len(cs)). */
export function octetsForChoiceArity(alternatives) {
  const n = Number(alternatives);
  if (!(n >= 2)) throw new CodecError("choice must have ≥2 alternatives");
  if (n < 256) return 1;
  if (n < 65536) return 2;
  if (n < 4294967296) return 4;
  return 8;
}

export function setOptional(mask, idx) {
  const byte = idx >> 3;
  const bit = idx & 7;
  mask[byte] |= 0x80 >> bit;
}

export function checkOptional(mask, idx) {
  const byte = idx >> 3;
  const bit = idx & 7;
  return (mask[byte] & (0x80 >> bit)) !== 0;
}

export function writeIntegralLE(dst, dstOff, value, nbytes) {
  let v = BigInt(value >>> 0);
  if (nbytes < 8) {
    const max = BigInt(1) << BigInt(nbytes * 8);
    v = v & (max - BigInt(1));
  }
  for (let b = 0; b < nbytes; b++) {
    dst[dstOff + b] = Number(v & BigInt(0xff));
    v >>= BigInt(8);
  }
}

export function readIntegralLE(src, srcOff, nbytes) {
  let v = BigInt(0);
  for (let b = 0; b < nbytes; b++) {
    v |= BigInt(src[srcOff + b]) << BigInt(8 * b);
  }
  return Number(v);
}

/** Packed codec cursor; corresponds to cum::per_codec_ctx + encode_per overloads. */
export class PerCodecCtx {
  /**
   * @param {Uint8Array} backing
   * @param {number} offset
   * @param {"encode" | "decode"} mode
   */
  constructor(backing, offset = 0, mode = "encode") {
    this.buf = backing;
    this.off = offset;
    this.mode = mode;
  }

  remaining() {
    return this.buf.byteLength - this.off;
  }

  bump(n) {
    if (this.remaining() < n) {
      throw new CodecError(`${this.mode} attempted past end of buffer`);
    }
    this.off += n;
  }

  writeBytes(src, len = src.byteLength) {
    if (len > src.byteLength) throw new CodecError("write slice too long");
    if (len > this.remaining()) throw new CodecError("encode buffer full");
    this.buf.set(src.subarray(0, len), this.off);
    this.off += len;
  }

  readBytes(len) {
    if (len > this.remaining()) throw new CodecError("decode overrun");
    const out = this.buf.slice(this.off, this.off + len);
    this.off += len;
    return out;
  }

  writeI32LE(v) {
    if (this.remaining() < 4) throw new CodecError("encode buffer full");
    writeIntegralLE(this.buf, this.off, v, 4);
    this.off += 4;
  }

  readI32LE() {
    if (this.remaining() < 4) throw new CodecError("decode overrun");
    const v = readIntegralLE(this.buf, this.off, 4);
    this.off += 4;
    /** @type {number} */
    return v | 0;
  }

  writeU8(byte) {
    if (this.remaining() < 1) throw new CodecError("encode buffer full");
    this.buf[this.off++] = byte & 0xff;
  }

  readU8() {
    if (this.remaining() < 1) throw new CodecError("decode overrun");
    return this.buf[this.off++];
  }

  writeCount(maxCardinality, count) {
    const nb = octetsForCumCapacity(maxCardinality);
    const cap = Number(maxCardinality);
    if (!(count >= 0) || count > cap) {
      throw new CodecError(`collection count ${count} out of range (max ${cap})`);
    }
    if (this.remaining() < nb) throw new CodecError("encode buffer full");
    writeIntegralLE(this.buf, this.off, count, nb);
    this.off += nb;
  }

  readCount(maxCardinality) {
    const nb = octetsForCumCapacity(maxCardinality);
    const cap = Number(maxCardinality);
    if (this.remaining() < nb) throw new CodecError("decode overrun");
    const count = readIntegralLE(this.buf, this.off, nb);
    this.off += nb;
    if (count > cap || count < 0) {
      throw new CodecError(`decoded count ${count} out of range (max ${cap})`);
    }
    return count;
  }

  encodeCStringLatin1(str) {
    const n = str.length + 1;
    if (n > this.remaining()) throw new CodecError("encode buffer full");
    for (let i = 0; i < str.length; i++) {
      const cp = str.charCodeAt(i);
      if (cp > 255) throw new CodecError("non Latin-1 string not supported for CUM string");
      this.buf[this.off++] = cp;
    }
    this.buf[this.off++] = 0;
  }

  decodeCStringLatin1() {
    let end = this.off;
    while (end < this.buf.byteLength && this.buf[end] !== 0) end++;
    if (end >= this.buf.byteLength) throw new CodecError("unterminated C string");
    const slice = this.buf.subarray(this.off, end);
    this.off = end + 1;
    let s = "";
    for (let i = 0; i < slice.byteLength; i++) s += String.fromCharCode(slice[i]);
    return s;
  }

  writeChoiceIndex(numAlternatives, index) {
    const nb = octetsForChoiceArity(numAlternatives);
    if (!(index >= 0) || index >= numAlternatives) {
      throw new CodecError(`choice index ${index} invalid (${numAlternatives} alts)`);
    }
    if (this.remaining() < nb) throw new CodecError("encode buffer full");
    writeIntegralLE(this.buf, this.off, index, nb);
    this.off += nb;
  }

  readChoiceIndex(numAlternatives) {
    const nb = octetsForChoiceArity(numAlternatives);
    if (this.remaining() < nb) throw new CodecError("decode overrun");
    const index = readIntegralLE(this.buf, this.off, nb);
    this.off += nb;
    if (index >= numAlternatives || index < 0) throw new CodecError(`bad choice index ${index}`);
    return index;
  }
}
