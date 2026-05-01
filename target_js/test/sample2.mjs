// Generated from CUM AST — JSDoc shapes, enums, and packed PER codecs (match target_cpp/cum/cum.hpp).

import { CodecError, PerCodecCtx, checkOptional, setOptional } from "../cum/cum.mjs";

/**
 * @enum {number}
 */
export const Gender = Object.freeze({
    Male: 10,
    Female: 11
});

/** @typedef {string} String */

/**
 * CUM optional: null when absent.
 * @typedef {(string | null)} OptionalString
 */

/**
 * CUM dynamic<char,?>: treat as string, max 22 code units.
 * @typedef {string} PhoneNumber
 */

/**
 * CUM dynamic: max 32 elements.
 * @typedef {Array<PhoneNumber>} PhoneNumberArray
 */

/**
 * CUM buffer capacity 64 (element type byte).
 * @typedef {{ len: number, buf: Uint8Array }} buffer64
 */

/**
 * @typedef {Object} PersonalPhoneEntry
 * @property {string} firstName
 * @property {(string | null)} [middleName]
 * @property {string} lastName
 * @property {string} address
 * @property {Gender} gender
 * @property {Array<PhoneNumber>} phoneNumbers
 * @property {{ len: number, buf: Uint8Array }} rawData
 */

/**
 * @typedef {Object} CorporatePhoneEntry
 * @property {string} businessName
 * @property {string} address
 * @property {Array<PhoneNumber>} phoneNumbers
 * @property {{ len: number, buf: Uint8Array }} rawData
 */

/** @typedef {PersonalPhoneEntry | CorporatePhoneEntry} PhoneEntry */

/**
 * CUM dynamic: max 255 elements.
 * @typedef {Array<PhoneEntry>} PhoneEntryArray
 */

/**
 * @typedef {Object} PhoneBook
 * @property {Array<PhoneEntry>} phoneEntryArray
 */

// --- Packed encoding (PER-byte copy, GCC enum = I32LE) ---
/** @param {typeof Gender[keyof Gender]} v */
export function encodeUsing_Gender(v, ctx) {
    ctx.writeI32LE(v);
}

/** @return {typeof Gender[keyof Gender]} */
export function decodeUsing_Gender(ctx) {
    return ctx.readI32LE();
}

// Codec: typedef String
export function encodeUsing_String(v, ctx) {
    ctx.encodeCStringLatin1(v);
}

export function decodeUsing_String(ctx) {
    return ctx.decodeCStringLatin1();
}

// Codec: typedef PhoneNumber
export function encodeUsing_PhoneNumber(arr, ctx) {
    if (arr.length > 22) throw new CodecError('PhoneNumber');
    ctx.writeCount(22, arr.length);
    for (let _i = 0; _i < arr.length; _i++) {
        const cp = arr.charCodeAt(_i);
        if (cp > 255) throw new CodecError('non Latin-1 in PhoneNumber');
        ctx.writeU8(cp);
    }
}

export function decodeUsing_PhoneNumber(ctx) {
    const n = ctx.readCount(22);
    let out = '';
    for (let j = 0; j < n; j++) out += String.fromCharCode(ctx.readU8());
    return out;
}

// Codec: typedef PhoneNumberArray
export function encodeUsing_PhoneNumberArray(arr, ctx) {
    if (arr.length > 32) throw new CodecError('PhoneNumberArray');
    ctx.writeCount(32, arr.length);
    for (let _i = 0; _i < arr.length; _i++) encodeUsing_PhoneNumber(arr[_i], ctx);
}

export function decodeUsing_PhoneNumberArray(ctx) {
    const n = ctx.readCount(32);
    const arr = [];
    for (let k = 0; k < n; k++) arr.push(decodeUsing_PhoneNumber(ctx));
    return arr;
}

// Codec: typedef buffer64
export function encodeUsing_buffer64(bp, ctx) {
    if (bp.len > 64) throw new CodecError('buffer64 len');
    ctx.writeCount(64, bp.len);
    ctx.writeBytes(bp.buf.subarray(0, bp.len), bp.len);
}

export function decodeUsing_buffer64(ctx) {
    const cap = 64;
    const len = ctx.readCount(cap);
    const out = { len, buf: new Uint8Array(cap) };
    if (len) out.buf.set(ctx.readBytes(len), 0);
    return out;
}

// Codec: typedef PhoneEntryArray
export function encodeUsing_PhoneEntryArray(arr, ctx) {
    if (arr.length > 255) throw new CodecError('PhoneEntryArray');
    ctx.writeCount(255, arr.length);
    for (let _i = 0; _i < arr.length; _i++) encodeUsing_PhoneEntry(arr[_i], ctx);
}

export function decodeUsing_PhoneEntryArray(ctx) {
    const n = ctx.readCount(255);
    const arr = [];
    for (let k = 0; k < n; k++) arr.push(decodeUsing_PhoneEntry(ctx));
    return arr;
}

// Codec: sequence PersonalPhoneEntry
export function encodeUsing_PersonalPhoneEntry(pIe, ctx) {
    const optionalMask = new Uint8Array(1);
    if (pIe.middleName !== null && pIe.middleName !== undefined)
 { setOptional(optionalMask, 0); }
    ctx.writeBytes(optionalMask, optionalMask.byteLength);
    encodeUsing_String(pIe.firstName, ctx);
    if (pIe.middleName !== null && pIe.middleName !== undefined) {
        encodeUsing_String(pIe.middleName, ctx);
    }
    encodeUsing_String(pIe.lastName, ctx);
    encodeUsing_String(pIe.address, ctx);
    encodeUsing_Gender(pIe.gender, ctx);
    encodeUsing_PhoneNumberArray(pIe.phoneNumbers, ctx);
    if ((pIe.rawData).len > 64) throw new CodecError('buffer64');
    encodeUsing_buffer64(pIe.rawData, ctx);
}

export function decodeUsing_PersonalPhoneEntry(ctx) {
    const pIe = {};
    const optionalMask = ctx.readBytes(1);
    pIe.firstName = decodeUsing_String(ctx);
    if (checkOptional(optionalMask, 0)) {
        pIe.middleName = decodeUsing_String(ctx);
    } else {
        pIe.middleName = null;
    }
    pIe.lastName = decodeUsing_String(ctx);
    pIe.address = decodeUsing_String(ctx);
    pIe.gender = decodeUsing_Gender(ctx);
    pIe.phoneNumbers = decodeUsing_PhoneNumberArray(ctx);
    pIe.rawData = decodeUsing_buffer64(ctx);
    return pIe;
}

// Codec: sequence CorporatePhoneEntry
export function encodeUsing_CorporatePhoneEntry(pIe, ctx) {
    encodeUsing_String(pIe.businessName, ctx);
    encodeUsing_String(pIe.address, ctx);
    encodeUsing_PhoneNumberArray(pIe.phoneNumbers, ctx);
    if ((pIe.rawData).len > 64) throw new CodecError('buffer64');
    encodeUsing_buffer64(pIe.rawData, ctx);
}

export function decodeUsing_CorporatePhoneEntry(ctx) {
    const pIe = {};
    pIe.businessName = decodeUsing_String(ctx);
    pIe.address = decodeUsing_String(ctx);
    pIe.phoneNumbers = decodeUsing_PhoneNumberArray(ctx);
    pIe.rawData = decodeUsing_buffer64(ctx);
    return pIe;
}

// Codec: choice PhoneEntry
export function encodeUsing_PhoneEntry(pIe, ctx) {
    if (Object.prototype.hasOwnProperty.call(pIe, 'PersonalPhoneEntry') && pIe['PersonalPhoneEntry'] !== undefined) {
        ctx.writeChoiceIndex(2, 0);
        encodeUsing_PersonalPhoneEntry(pIe['PersonalPhoneEntry'], ctx);
        return;
    }
    else if (Object.prototype.hasOwnProperty.call(pIe, 'CorporatePhoneEntry') && pIe['CorporatePhoneEntry'] !== undefined) {
        ctx.writeChoiceIndex(2, 1);
        encodeUsing_CorporatePhoneEntry(pIe['CorporatePhoneEntry'], ctx);
        return;
    }
    throw new CodecError("encodeUsing_PhoneEntry: exactly one discriminant key expected");
}

export function decodeUsing_PhoneEntry(ctx) {
    const idx = ctx.readChoiceIndex(2);
    switch (idx) {
        case 0:
            return { ['PersonalPhoneEntry']: decodeUsing_PersonalPhoneEntry(ctx) };
        case 1:
            return { ['CorporatePhoneEntry']: decodeUsing_CorporatePhoneEntry(ctx) };
        default:
            throw new CodecError("bad choice index");
    }
}

// Codec: sequence PhoneBook
export function encodeUsing_PhoneBook(pIe, ctx) {
    encodeUsing_PhoneEntryArray(pIe.phoneEntryArray, ctx);
}

export function decodeUsing_PhoneBook(ctx) {
    const pIe = {};
    pIe.phoneEntryArray = decodeUsing_PhoneEntryArray(ctx);
    return pIe;
}

