import assert from "node:assert/strict";
import { Buffer } from "node:buffer";
import { PerCodecCtx } from "../cum/cum.mjs";
import { Gender, encodeUsing_PhoneBook, decodeUsing_PhoneBook } from "./sample2.mjs";

assert.equal(Gender.Male, 10);
assert.equal(Gender.Female, 11);
assert.ok(Object.isFrozen(Gender));

/** Matches `cum_test_sample2` output on GCC x86-64 (129 bytes). */
const GOLDEN_HEX =
  "030080312e666972737400312e6d6964646c6500312e6c61737400312e61646472657373000a00000002042b363339032b34340001322e627573696e6573734e616d6500322e616464726573730001032b3633082a000000000000000000322e666972737400322e6c61737400322e61646472657373000a00000001032b343200";

function hexToUint8(hex) {
  const b = Buffer.from(hex, "hex");
  return new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
}

function u8equal(a, b, n) {
  for (let i = 0; i < n; i++) if (a[i] !== b[i]) return false;
  return true;
}

function emptyRaw64() {
  return { len: 0, buf: new Uint8Array(64) };
}

function corporateRaw() {
  const buf = new Uint8Array(64);
  new DataView(buf.buffer).setBigUint64(0, 42n, true);
  return { len: 8, buf };
}

const phoneBookFixture = {
  phoneEntryArray: [
    {
      PersonalPhoneEntry: {
        firstName: "1.first",
        middleName: "1.middle",
        lastName: "1.last",
        address: "1.address",
        gender: Gender.Male,
        phoneNumbers: ["+639", "+44"],
        rawData: emptyRaw64(),
      },
    },
    {
      CorporatePhoneEntry: {
        businessName: "2.businessName",
        address: "2.address",
        phoneNumbers: ["+63"],
        rawData: corporateRaw(),
      },
    },
    {
      PersonalPhoneEntry: {
        firstName: "2.first",
        middleName: null,
        lastName: "2.last",
        address: "2.address",
        gender: Gender.Male,
        phoneNumbers: ["+42"],
        rawData: emptyRaw64(),
      },
    },
  ],
};

const buf = new Uint8Array(1024);
const enc = new PerCodecCtx(buf);
encodeUsing_PhoneBook(phoneBookFixture, enc);
const encodedLen = enc.off;
const golden = hexToUint8(GOLDEN_HEX);
assert.equal(
  encodedLen,
  golden.byteLength,
  `encoded ${encodedLen} vs golden ${golden.byteLength}`
);
assert.ok(u8equal(buf, golden, encodedLen));

const slice = buf.subarray(0, encodedLen);
const round = decodeUsing_PhoneBook(new PerCodecCtx(slice, 0));
assert.deepEqual(round.phoneEntryArray.length, phoneBookFixture.phoneEntryArray.length);
assert.deepEqual(
  round.phoneEntryArray[0].PersonalPhoneEntry.firstName,
  "1.first"
);
assert.deepEqual(round.phoneEntryArray[1].CorporatePhoneEntry.rawData.len, 8);
assert.equal(round.phoneEntryArray[1].CorporatePhoneEntry.rawData.buf[0], 42);
assert.equal(round.phoneEntryArray[2].PersonalPhoneEntry.middleName, null);
