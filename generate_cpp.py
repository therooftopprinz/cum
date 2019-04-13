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

    def processConstant(self, name, data):
        print "constexpr auto " + name + " = " + self.constant_[name] + ";"

    def determineUnsignedSize(self, n):
        if (n<256):
            return "uint8_t"
        elif (n<65536):
            return "uint16_t"
        elif (n<4294967296):
            return "uint32_t"
        else:
            return "uint64_t"

    def determineSignedSize(self, n):
        if (n>=-128 or n<125):
            return "int8_t"
        elif (n>=-32768 or n<32768):
            return "int16_t"
        elif (n>=-2147483648 or n<2147483648):
            return "int32_t"
        else:
            return "int64_t"

    def processEnumeration(self, name, data):
        es = self.enum_[name]
        print "enum class " + name + " : " + self.determineUnsignedSize(len(es))
        print "{"
        j = 0
        for i in es:
            if (i[1] is not None):
                i = i[0] + " = " + i[1]
            else:
                i = i[0]
            if (j<len(es)-1):
                print "    " + i + ", "
            else:
                print "    " + i
            j += 1
        print "};"

    def createScalarAlias(self, name, typee, optional, width):
        if width is None:
            width = 2**32-1
        else:
            width = 2**int(width)-1

        if typee == "unsigned":
            typee = self.determineUnsignedSize(int(width))
        elif typee == "signed":
            typee = self.determineSignedSize(int(width))

        if (optional):
            typee = "std::optional<" + typee + ">"

        print "using " + name + " = " + typee + ";"

    def createVectorAlias(self, name, typee, optional, width, ts):
        if width is None:
            width = 2**32-1
        else:
            width = 2**int(width)-1

        arrlen = ts["dynamic_array"]
        if  arrlen == "":
            arrlen = str(2**32 - 1)

        prealloc = "preallocate" in ts

        if typee == "unsigned":
            typee = self.determineUnsignedSize(int(width))
        elif typee == "signed":
            typee = self.determineSignedSize(int(width))

        if prealloc == False:
            typee = "cum::vector<" + typee + ", " + arrlen +">"
            if (optional):
                typee = "std::optional<" + typee + ">"
            print "using " + name + " = " + typee + ";"
        else:
            typee = "cum::preallocated_vector<" + typee + ", " + arrlen +">"
            if (optional):
                typee = "std::optional<" + typee + ">"
            print "using " + name + " = " + typee + ";"

    def processType(self, name, data):
        ts = self.type_[name]

        if "type" not in ts:
            raise RuntimeError("type not in Type " + name)

        if "optional" in ts:
            optional = True
        else:
            optional = False

        typee = ts["type"]
        if typee == "asciiz":
            t = "std::string"
            if (optional):
                t = "std::optional<" + t + ">"
            print "using " + name + " = " + t + ";"
            return

        width = None
        if "width" in ts:
            width = ts["width"]

        arrlen = None
        if "dynamic_array" in ts:
            arrlen = ts["dynamic_array"]

        if arrlen is None:
            self.createScalarAlias(name, typee, optional, width)
        else:
            self.createVectorAlias(name, typee, optional, width, ts)

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
        print "using " + name + " = std::variant<" + s + ">;"

    def processSequence(self, name, data):
        cs = self.sequence_[name]
        print "struct " + name
        print "{"
        for i in cs:
            print "    " + i[0] + " " + i[1] + ";"
        print "};\n"

    def createSequenceEncoderPer(self, name, cs):
        print "void encode_per(const " + name + "& pIe, cum::per_codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"

        noptionals = 0
        for i in cs:
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[i[0]]:
                    noptionals += 1
        optionalmasksz = int(math.ceil(noptionals*1.0/8))
        if optionalmasksz > 0:
            print "    uint8_t optionalmask[" + str(optionalmasksz) + "] = {};"

        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print "    if (" + field +")"
                    print "    {"
                    print "        set_optional(optionalmask, " + str(j) + ");"
                    print "    }"
                    j += 0
        if optionalmasksz > 0:
            print "    encode_per(optionalmask, sizeof(optionalmask), pCtx);"
        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print "    if (" + field +")"
                    print "    {"
                    print "        encode_per(*" + field + ", pCtx);"
                    print "    }"
                    j += 1
                    continue
            print "    encode_per(" + field + ", pCtx);"
        print "}\n"

    def createSequenceEncoderUper(self, name, cs):
        print "/*void encode_uper(const " + name + "& pIe, cum::uper_codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"

        noptionals = 0
        for i in cs:
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[i[0]]:
                    noptionals += 1
        optionalmasksz = int(math.ceil(noptionals*1.0/8))
        if optionalmasksz > 0:
            print "    uint8_t optionalmask[" + str(optionalmasksz) + "] = {};"

        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print "    if (" + field +")"
                    print "    {"
                    print "        set_optional(optionalmask, " + str(j) + ");"
                    print "    }"
                    j += 0
        if optionalmasksz > 0:
            print "    encode_uper(optionalmask, sizeof(optionalmask), pCtx);"
        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print "    if (" + field +")"
                    print "    {"
                    print "        encode_uper(*" + field + ", pCtx);"
                    print "    }"
                    j += 1
                    continue
            print "    encode_uper(" + field + ", pCtx);"
        print "}*/\n"

    def createSequenceDecoderPer(self, name, cs):
        print "void decode_per(" + name + "& pIe, cum::per_codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"

        noptionals = 0
        for i in cs:
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[i[0]]:
                    noptionals += 1
        optionalmasksz = int(math.ceil(noptionals*1.0/8))
        if optionalmasksz > 0:
            print "    uint8_t optionalmask[" + str(optionalmasksz) + "] = {};"
            print "    decode_per(optionalmask, sizeof(optionalmask), pCtx);"
        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if  fieldt in self.type_:
                if "optional" in self.type_[i[0]]:
                    print "    if (check_optional(optionalmask, "+str(j)+"))"
                    print "    {"
                    print "        " + field + " = decltype(" + field + ")::value_type{};"
                    print "        decode_per(*" + field + ", pCtx);"
                    print "    }"
                    j += 1
                    continue
            print "    decode_per(" + field + ", pCtx);"
        print "}\n"

    def createSequenceStrer(self, name, cs):
        print "void str(const char* pName, const " + name + "& pIe, std::string& pCtx, bool pIsLast)"
        print "{"
        print "    using namespace cum;"
        print "    if (!pName)"
        print "    {"
        print "        pCtx = pCtx + \"{\";"
        print "    }"
        print "    else"
        print "    {"
        print "        pCtx = pCtx + \"\\\"\" + pName + \"\\\":{\";"
        print "    }"

        j = 0
        for i in cs:
            field = "pIe." + i[1]
            fieldt = i[0]
            if j == len(cs)-1:
                last = "true"
            else:
                last = "false"
            j += 1
            if  fieldt in self.type_:
                if "optional" in self.type_[fieldt]:
                    print "    if (" + field +")"
                    print "    {"
                    print "        str(\"" + i[1] + "\", *" + field + ", pCtx, " + last + ");"
                    print "    }"
                    continue
            print "    str(\"" + i[1] + "\", " + field + ", pCtx, " + last + ");"
        print "    pCtx = pCtx + \"}\";"
        print "    if (!pIsLast)"
        print "    {"
        print "        pCtx += \",\";"
        print "    }"
        print "}\n"

    def createChoiceEncoderPer(self, name, cs):
        print "void encode_per(const " + name + "& pIe, cum::per_codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"
        print "    using TypeIndex = " + self.determineUnsignedSize(len(cs)) + ";"
        print "    TypeIndex type = pIe.index();"
        print "    encode_per(type, pCtx);"
        j = 0
        for i in cs:
            js = str(j)
            if (j>0):
                oelse = "else "
            else:
                oelse = ""
            print "    " + oelse + "if ("+ js + " == type)"
            print "    {"
            print "        encode_per(std::get<" + js + ">(pIe), pCtx);"
            print "    }"
            j += 1
        print "}\n"

    def createChoiceDecoderPer(self, name, cs):
        print "void decode_per(" + name + "& pIe, cum::per_codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"
        print "    using TypeIndex = " + self.determineUnsignedSize(len(cs)) + ";"
        print "    TypeIndex type;"
        print "    decode_per(type, pCtx);"
        j = 0
        for i in cs:
            js = str(j)
            if (j>0):
                oelse = "else "
            else:
                oelse = ""
            print "    " + oelse + "if (" + js + " == type)"
            print "    {"
            print "        pIe = " + cs[j] + "{};"
            print "        decode_per(std::get<" + js + ">(pIe), pCtx);"
            print "    }"
            j += 1
        print "}\n"

    def createChoiceStrer(self, name, cs):
        print "void str(const char* pName, const " + name + "& pIe, std::string& pCtx, bool pIsLast)"
        print "{"
        print "    using namespace cum;"
        print "    using TypeIndex = " + self.determineUnsignedSize(len(cs)) + ";"
        print "    TypeIndex type = pIe.index();"
        j = 0
        for i in cs:
            js = str(j)
            if (j>0):
                oelse = "else "
            else:
                oelse = ""
            print "    " + oelse + "if ("+ js + " == type)"
            print "    {"
            print "        str(pName, std::get<" + js + ">(pIe), pCtx, true);"
            print "    }"
            j += 1
        print "    if (!pIsLast)"
        print "    {"
        print "        pCtx += \",\";"
        print "    }"
        print "}\n"

    def createEnumStrer(self, name, es):
        print "void str(const char* pName, const " + name + "& pIe, std::string& pCtx, bool pIsLast)"
        print "{"
        print "    using namespace cum;"
        print "    if (pName)"
        print "    {"
        print "        pCtx = pCtx + \"\\\"\" + pName + \"\\\":\";"
        print "    }"

        for i in es:
            print "    if ("+ name + "::" + i[0] +" == pIe) pCtx += \"\\\"" + i[0] + "\\\"\";"
        print "    pCtx = pCtx + \"}\";"
        print "    if (!pIsLast)"
        print "    {"
        print "        pCtx += \",\";"
        print "    }"
        print "}\n"

    def processSequenceCodec(self, name, data):
        cs = self.sequence_[name]
        self.createSequenceEncoderPer(name, cs)
        self.createSequenceEncoderUper(name, cs)
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
        print "// Generating for C++"
        defname = "__CUM_MSG_HPP__";
        print "#ifndef " + defname
        print "#define " + defname
        print "#include \"cum/cum.hpp\""
        print "#include <optional>"
        print ""
        print "/***********************************************"
        print "/"
        print "/            Message Definitions"
        print "/"
        print "************************************************/\n"

        for i in self.pass1_expressions_:
            t = i[0]
            n = i[1]
            v = i[2]

            if (t == "Constant"):
                self.processConstant(n, v)
            elif (t == "Enumeration"):
                self.processEnumeration(n, v)
            elif (t == "Type"):
                self.processType(n, v)
            elif (t == "Choice"):
                self.processChoice(n, v)
            elif (t == "Sequence"):
                self.processSequence(n, v)

        print "/***********************************************"
        print "/"
        print "/            Codec Definitions"
        print "/"
        print "************************************************/\n"

        for i in self.pass1_expressions_:
            t = i[0]
            n = i[1]
            v = i[2]

            if (t == "Sequence"):
                self.processSequenceCodec(n, v)
            elif (t == "Choice"):
                self.processChoiceCodec(n, v)
            elif (t == "Enumeration"):
                self.processEnumCodec(n, v)
        print "#endif //" + defname

class ExpressionParser:
    def __init__(self):
        self.constant_ = {}
        self.enum_     = {}
        self.type_     = {}
        self.choice_   = {}
        self.sequence_ = {}
        self.pass1_expressions_ = []

    def processConstant(self, name, data):
        data = data.strip()
        print "// Constant: ", (name, data)
        self.constant_[name] = data;

    def processEnumeration(self, name, data):
        data = [i.strip() for i in data.split(",")]
        self.enum_[name] = []
        for i in data:
            match = re.match(r"^(.*?)(?:\((.*?)\))*$", i)
            i = (match.group(1), match.group(2))
            self.enum_[name].append(i)
            print "// Enumeration: ", (name, i)

    def processType(self, name, data):
        data = [i for i in data.split(" ")]
        self.type_[name] = {}
        for i in data:
            if (i == ''):
                continue
            match = re.match(r"^(.*?)\((.*?)\)$", i)
            self.type_[name][match.group(1)] = match.group(2)
            print "// Type: ", (name, {match.group(1): match.group(2)})

    def processChoice(self, name, data):
        data = [i.strip() for i in data.split(",")]
        self.choice_[name] = []
        for i in data:
            self.choice_[name].append(i)
            print "// Choice: ", (name, i)

    def processSequence(self, name, data):
        data = [i.strip() for i in data.split(",")]
        self.sequence_[name] = []
        for i in data:
            match = re.match(r"^(.*?)[ \t]+(.*?)$", i)
            if match is None:
                raise RuntimeError("processing error: " + str(name) + " : " + str(data))
            t = match.group(1)
            n = match.group(2)
            self.sequence_[name].append((t, n))
            print "// Sequence: ", name, (t, n)

    def pass1(self, expressions):
        for i in expressions:
            i = i.strip()

            match = re.match(r"(.*?)[ \t]+(.*?){(.*?)}", i);
            if match is None:
                continue
            t = match.group(1).strip()
            n = match.group(2).strip()
            v = match.group(3).strip()

            self.pass1_expressions_.append((t,n,v))

            if (t == "Constant"):
                self.processConstant(n, v)
            elif (t == "Enumeration"):
                self.processEnumeration(n, v)
            elif (t == "Type"):
                self.processType(n, v)
            elif (t == "Choice"):
                self.processChoice(n, v)
            elif (t == "Sequence"):
                self.processSequence(n, v)

    def parse(self, expressions):
        self.pass1(expressions)
        generator = CppGenerator(self.constant_, self.enum_, self.type_, self.choice_, self.sequence_, self.pass1_expressions_)
        generator.generate()

parser = ExpressionParser()
parser.parse(expressions)
