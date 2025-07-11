#!/usr/bin/python

import sys
import re
import math

filename = sys.argv[1]

file = open(filename,mode='r')
content = file.read()

content = re.sub(r"//.*[\r]*\n", "", content)
content = re.sub(r"[\r]*\n", "", content)

expressions = content.split(";")

class CppGenerator:
    def __init__(self, constant, enum, typee, choice, sequence, pass1_expressions):
        self.constant_ = constant
        self.enum_     = enum
        self.type_     = typee
        self.choice_   = choice
        self.sequence_ = sequence
        self.pass1_expressions_ = pass1_expressions

    def determineUnsignedSize(self, n):
        if (n<256):
            return ("uint8_t", 1)
        elif (n<65536):
            return ("uint16_t", 2)
        elif (n<4294967296):
            return ("uint32_t", 4)
        else:
            return ("uint64_t", 8)

    def determineSignedSize(self, n):
        if (n<256):
            return ("int8_t", 1)
        elif (n<65536):
            return ("int16_t", 2)
        elif (n<4294967296):
            return ("int32_t", 4)
        else:
            return ("int64_t", 8)

    def processConstant(self, name, data):
        print ("constexpr auto {} = {};".format(name, self.constant_[name]))

    def processEnumeration(self, name, data):
        es = self.enum_[name]
        print ("enum {}".format(name))
        print ("{")
        j = 0
        for i in es:
            if (i[1] is not None):
                i = i[0] + " = " + i[1]
            else:
                i = i[0]
            if (j<len(es)-1):
                print ("    {},".format(i))
            else:
                print ("    {}".format(i))
            j += 1
        print ("};\n")

    def processType(self, name, data):
        ts = self.type_[name]

        if "type" not in ts:
            raise RuntimeError("type not in Type " + name)

        typewrap = "{}"
        if "optional" in ts:
            typewrap = "std::optional<{}>"

        type = ts["type"]

        veclen = None
        if "dynamic_array" in ts:
            veclen = ts["dynamic_array"]
            if (veclen==''):
                veclen = 2**32

        arrlen = None
        if "array" in ts:
            arrlen = ts["array"]

        buflen = None
        if "buffer" in ts:
            buflen = ts["buffer"]

        if veclen is not None:
            type = "cum::vector<{}, {}>".format(type, veclen)
        elif arrlen is not None:
            type = "cum::array<{}, {}>".format(type, arrlen)
        elif buflen is not None:
            type = "cum::buffer<{}, {}>".format(type, buflen)

        print ("using {} = {};".format(name, typewrap.format(type)))

    def processChoice(self, name, data):
        cs = self.choice_[name]
        j = 0
        s = ""
        for i in cs:
            if (j<len(cs)-1):
                s += i + ","
            else:
                s += i
            j  += 1
        print ("using {} = std::variant<{}>;".format(name,s))

    def processSequence(self, name, data):
        cs = self.sequence_[name]
        print ("struct " + name)
        print ("{")
        for i in cs:
            print ("    {} {};".format(i[0], i[1]))
        print ("};\n")

    def createSequenceEncoderPer(self, name, cs):
        print ("inline void encode_per(const {}& pIe, cum::per_codec_ctx& pCtx)".format(name))
        print ("{")
        print ("    using namespace cum;")

        noptionals = 0
        for i in cs:
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[i[0]]:
                    noptionals += 1
        optionalmasksz = int(math.ceil(noptionals*1.0/8))
        if optionalmasksz > 0:
            print ("    uint8_t optionalmask[{}] = {{}};".format(str(optionalmasksz)))

        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print ("    if ({})".format(field))
                    print ("    {")
                    print ("        set_optional(optionalmask, {});".format(str(j)))
                    print ("    }")
                    j += 1
        if optionalmasksz > 0:
            print ("    encode_per(optionalmask, sizeof(optionalmask), pCtx);")
        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print ("    if ({})".format(field))
                    print ("    {")
                    print ("        encode_per(*{}, pCtx);".format(field))
                    print ("    }")
                    j += 1
                else:
                    print ("    encode_per({}, pCtx);".format(field))
            else:
                print ("    encode_per({}, pCtx);".format(field))
        print ("}\n")

    def createSequenceDecoderPer(self, name, cs):
        print ("inline void decode_per(" + name + "& pIe, cum::per_codec_ctx& pCtx)")
        print ("{")
        print ("    using namespace cum;")

        noptionals = 0
        for i in cs:
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[i[0]]:
                    noptionals += 1
        optionalmasksz = int(math.ceil(noptionals*1.0/8))
        if optionalmasksz > 0:
            print ("    uint8_t optionalmask[" + str(optionalmasksz) + "] = {};")
            print ("    decode_per(optionalmask, sizeof(optionalmask), pCtx);")
        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[i[0]]:
                    print ("    if (check_optional(optionalmask, "+str(j)+"))")
                    print ("    {")
                    print ("        " + field + " = decltype(" + field + ")::value_type{};")
                    print ("        decode_per(*" + field + ", pCtx);")
                    print ("    }")
                    j += 1
                else:
                    print ("    decode_per(" + field + ", pCtx);")
            else:
                print ("    decode_per(" + field + ", pCtx);")
        print ("}\n")

    def createSequenceStrer(self, name, cs):
        print ("inline void str(const char* pName, const " + name + "& pIe, std::string& pCtx, bool pIsLast)")
        print ("{")
        print ("    using namespace cum;")
        print ("    if (!pName)")
        print ("    {")
        print ("        pCtx = pCtx + \"{\";")
        print ("    }")
        print ("    else")
        print ("    {")
        print ("        pCtx = pCtx + \"\\\"\" + pName + \"\\\":{\";")
        print ("    }")
        print ("    size_t nOptional = 0;")

        nMandatory = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print ("    if (" + field +") nOptional++;")
                    continue
                else:
                    nMandatory += 1
            else:
                nMandatory += 1
        print ("    size_t nMandatory = " + str(nMandatory) + ";")

        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print ("    if (" + field +")")
                    print ("    {")
                    print ("        str(\"" + i[1] + "\", *" + field + ", pCtx, !(nMandatory+--nOptional));")
                    print ("    }")
                    continue
            print ("    str(\"" + i[1] + "\", " + field + ", pCtx, !(--nMandatory+nOptional));")
        print ("    pCtx = pCtx + \"}\";")
        print ("    if (!pIsLast)")
        print ("    {")
        print ("        pCtx += \",\";")
        print ("    }")
        print ("}\n")

    def createChoiceEncoderPer(self, name, cs):
        print ("inline void encode_per(const " + name + "& pIe, cum::per_codec_ctx& pCtx)")
        print ("{")
        print ("    using namespace cum;")
        print ("    using TypeIndex = " + self.determineUnsignedSize(len(cs))[0] + ";")
        print ("    TypeIndex type = pIe.index();")
        print ("    encode_per(type, pCtx);")
        j = 0
        for i in cs:
            js = str(j)
            if (j>0):
                oelse = "else "
            else:
                oelse = ""
            print ("    " + oelse + "if ("+ js + " == type)")
            print ("    {")
            print ("        encode_per(std::get<" + js + ">(pIe), pCtx);")
            print ("    }")
            j += 1
        print ("}\n")

    def createChoiceDecoderPer(self, name, cs):
        print ("inline void decode_per(" + name + "& pIe, cum::per_codec_ctx& pCtx)")
        print ("{")
        print ("    using namespace cum;")
        print ("    using TypeIndex = " + self.determineUnsignedSize(len(cs))[0] + ";")
        print ("    TypeIndex type;")
        print ("    decode_per(type, pCtx);")
        j = 0
        for i in cs:
            js = str(j)
            if (j>0):
                oelse = "else "
            else:
                oelse = ""
            print ("    " + oelse + "if (" + js + " == type)")
            print ("    {")
            print ("        pIe = " + cs[j] + "();")
            print ("        decode_per(std::get<" + js + ">(pIe), pCtx);")
            print ("    }")
            j += 1
        print ("}\n")

    def createChoiceStrer(self, name, cs):
        print ("inline void str(const char* pName, const " + name + "& pIe, std::string& pCtx, bool pIsLast)")
        print ("{")
        print ("    using namespace cum;")
        print ("    using TypeIndex = " + self.determineUnsignedSize(len(cs))[0] + ";")
        print ("    TypeIndex type = pIe.index();")
        j = 0
        for i in cs:
            js = str(j)
            if (j>0):
                oelse = "else "
            else:
                oelse = ""
            print ("    " + oelse + "if ("+ js + " == type)")
            print ("    {")
            print ("        if (pName)")
            print ("            pCtx += std::string(pName) + \":{\";")
            print ("        else")
            print ("            pCtx += \"{\";")
            print ("        std::string name = \"" + i + "\";")
            print ("        str(name.c_str(), std::get<" + js + ">(pIe), pCtx, true);")
            print ("        pCtx += \"}\";")
            print ("    }")
            j += 1
        print ("    if (!pIsLast)")
        print ("    {")
        print ("        pCtx += \",\";")
        print ("    }")
        print ("}\n")

    def createEnumStrer(self, name, es):
        print ("inline void str(const char* pName, const " + name + "& pIe, std::string& pCtx, bool pIsLast)")
        print ("{")
        print ("    using namespace cum;")
        print ("    if (pName)")
        print ("    {")
        print ("        pCtx = pCtx + \"\\\"\" + pName + \"\\\":\";")
        print ("    }")

        for i in es:
            print ("    if ("+ name + "::" + i[0] +" == pIe) pCtx += \"\\\"" + i[0] + "\\\"\";")
        print ("    pCtx = pCtx + \"}\";")
        print ("    if (!pIsLast)")
        print ("    {")
        print ("        pCtx += \",\";")
        print ("    }")
        print ("}\n")

    def processSequenceCodec(self, name, data):
        cs = self.sequence_[name]
        self.createSequenceEncoderPer(name, cs)
        self.createSequenceDecoderPer(name, cs)
        self.createSequenceStrer(name, cs)

    def processChoiceCodec(self, name, data):
        cs = self.choice_[name]
        self.createChoiceEncoderPer(name, cs)
        self.createChoiceDecoderPer(name, cs)
        self.createChoiceStrer(name, cs)

    def processEnumCodec(self, name, data):
        es = self.enum_[name]
        self.createEnumStrer(name, es)


    def generate(self):
        print ("// Generating for C++")
        defname = "__CUM_MSG_HPP__";
        print ("#ifndef " + defname)
        print ("#define " + defname)
        print ("#include \"cum/cum.hpp\"")
        print ("")
        print ("namespace cum")
        print ("{")
        print ("")
        print ("/***********************************************")
        print ("/")
        print ("/            Message Definitions")
        print ("/")
        print ("************************************************/\n")

        for i in self.pass1_expressions_:
            t = i[0]
            n = i[1]
            v = i[2]

            if (t == "constant"):
                self.processConstant(n, v)
            elif (t == "enumeration"):
                self.processEnumeration(n, v)
            elif (t == "type"):
                self.processType(n, v)
            elif (t == "choice"):
                self.processChoice(n, v)
            elif (t == "sequence"):
                self.processSequence(n, v)

        print ("/***********************************************")
        print ("/")
        print ("/            Codec Definitions")
        print ("/")
        print ("************************************************/\n")

        for i in self.pass1_expressions_:
            t = i[0]
            n = i[1]
            v = i[2]

            if (t == "sequence"):
                self.processSequenceCodec(n, v)
            elif (t == "choice"):
                self.processChoiceCodec(n, v)
            elif (t == "enumeration"):
                self.processEnumCodec(n, v)
        print ("} // namespace cum")
        print ("#endif //" + defname)

class ExpressionParser:
    def __init__(self):
        self.constant_ = {}
        self.enum_     = {}
        self.type_     = {}
        self.choice_   = {}
        self.sequence_ = {}
        self.pass1_expressions_ = []

    def processConstant(self, name, data):
        data = data.lstrip("=").strip()
        print ("// Constant: ", (name, data))
        self.constant_[name] = data;

    def processEnumeration(self, name, data):
        data = data.lstrip("{").rstrip("}")
        data = [i.strip() for i in data.split(",")]
        self.enum_[name] = []
        for i in data:
            match = re.match(r"^([A-Za-z0-9_]+)\s*(?:=\s*([A-Za-z0-9_\-]+))*", i)
            i = (match.group(1), match.group(2))
            self.enum_[name].append(i)
            print ("// Enumeration: ", (name, i))

    def processType(self, name, data):
        data = [i.strip() for i in data.split(", ")]
        self.type_[name] = {}
        for i in data:
            if (i == ''):
                continue
            match = re.match(r"^([A-Za-z0-9_]+)\s*(?:=\s*(.*?))*$", i)
            self.type_[name][match.group(1)] = match.group(2)
            print ("// Type: ", (name, {match.group(1): match.group(2)}))

    def processChoice(self, name, data):
        data = data.lstrip("{").rstrip("}")
        data = [i.strip() for i in data.split(",")]
        self.choice_[name] = []
        for i in data:
            self.choice_[name].append(i)
            print ("// Choice: ", (name, i))

    def processSequence(self, name, data):
        data = data.lstrip("{").rstrip("}")
        data = [i.strip() for i in data.split(",")]
        self.sequence_[name] = []
        for i in data:
            match = re.match(r"^(.*?)[ \t]+(.*?)$", i)
            if match is None:
                print ("// Pattern not found in '{}' ".format(i))
                raise RuntimeError("processing error: " + str(name) + " : " + str(data))
            t = match.group(1)
            n = match.group(2)
            self.sequence_[name].append((t, n))
            print ("// Sequence: ", name, (t, n))

    def pass1(self, expressions):
        for i in expressions:
            i = i.strip()
            match = re.match(r"([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*(.*)", i);
            if match is None:
                continue
            t = match.group(1).strip()
            n = match.group(2).strip()
            v = match.group(3).strip()

            # print ("// Expression: {} | t={} | n={} | v={}".format(i, t, n, v))

            self.pass1_expressions_.append((t,n,v))

            if (t == "constant"):
                self.processConstant(n, v)
            elif (t == "enumeration"):
                self.processEnumeration(n, v)
            elif (t == "type"):
                self.processType(n, v)
            elif (t == "choice"):
                self.processChoice(n, v)
            elif (t == "sequence"):
                self.processSequence(n, v)

    def parse(self, expressions):
        self.pass1(expressions)
        generator = CppGenerator(self.constant_, self.enum_, self.type_, self.choice_, self.sequence_, self.pass1_expressions_)
        generator.generate()

parser = ExpressionParser()
parser.parse(expressions)
