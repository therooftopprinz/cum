-- Generated from CUM AST — Wireshark Lua dissector (packed PER, LE).
-- Display filter prefix: 'phonebook'

local function cum_octets_for_capacity(cap)
    local N = tonumber(cap)
    assert(N and N >= 1, "cum_octets_for_capacity: bad cap")
    if N <= 256 then return 1 end
    if N <= 65536 then return 2 end
    if N <= 4294967296 then return 4 end
    return 8
end

local function cum_octets_for_choice_arity(alts)
    local n = tonumber(alts)
    assert(n and n >= 2, "choice arity must be >= 2")
    if n < 256 then return 1 end
    if n < 65536 then return 2 end
    if n < 4294967296 then return 4 end
    return 8
end

local function cum_optional_is_set(mask_range, bit_index)
    local byte_off = math.floor(bit_index / 8)
    local bi = bit_index % 8
    local m = mask_range:range(byte_off, 1):uint()
    local bit = math.floor(128 / (2 ^ bi))
    return math.floor(m / bit) % 2 ~= 0
end

local function dissect_c_string_latin1(tvb, subtree, offset, fld)
    local start = offset
    while offset < tvb:len() and tvb(offset, 1):uint() ~= 0 do
        offset = offset + 1
    end
    if offset >= tvb:len() then
        subtree:add(tvb:range(start, tvb:len() - start), "truncated CUM string")
        return tvb:len()
    end
    local span = offset - start
    if fld then
        subtree:add(fld, tvb:range(start, span))
    else
        subtree:add(tvb:range(start, span), "string (" .. span .. " chars)")
    end
    return offset + 1
end

local gender_enum_vals = {
    [10] = "Male",
    [11] = "Female",
}

local pf_phonebook_PersonalPhoneEntry_firstName = ProtoField.string("phonebook.PersonalPhoneEntry.firstName", "firstName")
local pf_phonebook_PersonalPhoneEntry_lastName = ProtoField.string("phonebook.PersonalPhoneEntry.lastName", "lastName")
local pf_phonebook_PersonalPhoneEntry_address = ProtoField.string("phonebook.PersonalPhoneEntry.address", "address")
local pf_phonebook_PersonalPhoneEntry_gender = ProtoField.int32("phonebook.PersonalPhoneEntry.gender", "gender", base.DEC, gender_enum_vals)
local pf_phonebook_CorporatePhoneEntry_businessName = ProtoField.string("phonebook.CorporatePhoneEntry.businessName", "businessName")
local pf_phonebook_CorporatePhoneEntry_address = ProtoField.string("phonebook.CorporatePhoneEntry.address", "address")

local cum_proto = Proto("phonebook", "phonebook (CUM AST)")
cum_proto.fields = { pf_phonebook_PersonalPhoneEntry_firstName, pf_phonebook_PersonalPhoneEntry_lastName, pf_phonebook_PersonalPhoneEntry_address, pf_phonebook_PersonalPhoneEntry_gender, pf_phonebook_CorporatePhoneEntry_businessName, pf_phonebook_CorporatePhoneEntry_address }

local function dissect_using_string(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "String")
    local _o0 = offset
    offset = dissect_c_string_latin1(tvb, subtree, offset, nil)

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_using_phone_number(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "PhoneNumber")
    local _o0 = offset
    local nb = cum_octets_for_capacity(22)
    local cnt = tvb(offset, nb):le_uint()
    offset = offset + nb
    local cont = subtree:add(tvb:range(offset), "PhoneNumber: " .. cnt .. " items")

    for _i = 1, cnt do
        local ch = tvb(offset, 1):uint()
        cont:add(tvb:range(offset, 1), string.format("[%d] u8 %d", _i - 1, ch))
        offset = offset + 1
    end

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_using_phone_number_array(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "PhoneNumberArray")
    local _o0 = offset
    local nb = cum_octets_for_capacity(32)
    local cnt = tvb(offset, nb):le_uint()
    offset = offset + nb
    local cont = subtree:add(tvb:range(offset), "PhoneNumberArray: " .. cnt .. " items")

    for _i = 1, cnt do
        local it = cont:add(tvb:range(offset), string.format("item [%d]", _i - 1))
        offset = dissect_using_phone_number(tvb, pinfo, it, offset)
    end

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_using_buffer64(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "buffer64")
    local _o0 = offset
    local nb = cum_octets_for_capacity(64)
    local ln = tvb(offset, nb):le_uint()
    offset = offset + nb
    local pay = tvb:range(offset, ln)
    subtree:add(pay, "buffer64 payload (" .. ln .. " octets)")
    offset = offset + ln

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_using_phone_entry_array(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "PhoneEntryArray")
    local _o0 = offset
    local nb = cum_octets_for_capacity(255)
    local cnt = tvb(offset, nb):le_uint()
    offset = offset + nb
    local cont = subtree:add(tvb:range(offset), "PhoneEntryArray: " .. cnt .. " items")

    for _i = 1, cnt do
        local it = cont:add(tvb:range(offset), string.format("item [%d]", _i - 1))
        offset = dissect_choice_phone_entry(tvb, pinfo, it, offset)
    end

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_seq_personal_phone_entry(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "PersonalPhoneEntry")
    local _o0 = offset
    local mask_r = tvb:range(offset, 1)
    subtree:add(mask_r, "optional_mask (1 octets)")
    offset = offset + 1

    offset = dissect_c_string_latin1(tvb, subtree, offset, pf_phonebook_PersonalPhoneEntry_firstName)

    if cum_optional_is_set(mask_r, 0) then
        offset = dissect_c_string_latin1(tvb, subtree, offset, nil)
    end

    offset = dissect_c_string_latin1(tvb, subtree, offset, pf_phonebook_PersonalPhoneEntry_lastName)

    offset = dissect_c_string_latin1(tvb, subtree, offset, pf_phonebook_PersonalPhoneEntry_address)

    subtree:add_le(pf_phonebook_PersonalPhoneEntry_gender, tvb:range(offset, 4))
    offset = offset + 4

    offset = dissect_using_phone_number_array(tvb, pinfo, subtree, offset)

    offset = dissect_using_buffer64(tvb, pinfo, subtree, offset)

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_seq_corporate_phone_entry(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "CorporatePhoneEntry")
    local _o0 = offset
    offset = dissect_c_string_latin1(tvb, subtree, offset, pf_phonebook_CorporatePhoneEntry_businessName)

    offset = dissect_c_string_latin1(tvb, subtree, offset, pf_phonebook_CorporatePhoneEntry_address)

    offset = dissect_using_phone_number_array(tvb, pinfo, subtree, offset)

    offset = dissect_using_buffer64(tvb, pinfo, subtree, offset)

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_seq_phone_book(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "PhoneBook")
    local _o0 = offset
    offset = dissect_using_phone_entry_array(tvb, pinfo, subtree, offset)

    subtree:set_len(offset - _o0)
    return offset
end

local function dissect_choice_phone_entry(tvb, pinfo, tree, offset)
    local subtree = tree:add(tvb:range(offset), "choice PhoneEntry")
    local _o0 = offset
    local iw = cum_octets_for_choice_arity(2)
    local idx = tvb(offset, iw):le_uint()
    subtree:add(tvb:range(offset, iw), "index: " .. idx)
    offset = offset + iw

    if idx == 0 then
        offset = dissect_seq_personal_phone_entry(tvb, pinfo, subtree, offset)
    elseif idx == 1 then
        offset = dissect_seq_corporate_phone_entry(tvb, pinfo, subtree, offset)
    else
        pinfo.cols.info:append(" [bad cum choice idx]")
        return tvb:len()
    end
    subtree:set_len(offset - _o0)
    return offset
end

-- Default top-level PDU: last sequence in file ("PhoneBook"). Adjust if needed.

function cum_proto.dissector(tvb, pinfo, tree)
    pinfo.cols.protocol = cum_proto.name
    local t = tree:add(cum_proto, tvb:range(0))
    dissect_seq_phone_book(tvb, pinfo, t, 0)
end

local udp_tbl = DissectorTable.get("udp.port")
-- Example: udp_tbl:add(59100, cum_proto)

