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
        print "constexpr auto "+name+" = "+self.constant_[name]+";"

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
            if (j<len(es)-1):
                print "    " + i + ", "
            else:
                print "    " + i
            j += 1
        print "};"

    def createScalarAlias(self, name, typee, optional, width):
        if width is None:
            width = 2^32-1

        if typee == "unsigned":
            typee = self.determineUnsignedSize(int(width))
        elif typee == "signed":
            typee = self.determineSignedSize(int(width))

        if (optional):
            typee = "std::optional<" + typee + ">"

        print "using " + name + " = " + typee + ";"

    def createVectorAlias(self, name, typee, optional, width, arrlen):
        if width is None:
            width = 2^32-1

        if typee == "unsigned":
            typee = self.determineUnsignedSize(int(width))
        elif typee == "signed":
            typee = self.determineSignedSize(int(width))

        if arrlen == "":
            typee = "std::vector<" + typee + ">"
            if (optional):
                typee = "std::optional<" + typee + ">"
            print "using " + name + " = " + typee + ";"
        else:
            typee = "cum::vector<" + typee + ", " + arrlen +">"
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
            self.createVectorAlias(name, typee, optional, width, arrlen)

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
        print "};"

    def createSequenceEncoder(self, name, cs):
        print "void encode(const " + name + "& pData, cum::codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"

        noptionals = 0
        for i in cs:
            if "optional" in self.type_[i[0]]:
                noptionals += 1
        print "    // noptionals = " + str(noptionals)
        optionalmasksz = int(math.ceil(noptionals*1.0/8))
        if optionalmasksz > 0:
            print "    uint8_t *optionalmask = new(pCtx.get()) uint8_t[" + str(optionalmasksz) + "]{};"
            print "    pCtx.advance(" + str(optionalmasksz) + ");"
        j = 0
        for i in cs:
            field = "pIe." + i[1]
            if "optional" in self.type_[i[0]]:
                print "    if (" + field +")"
                print "    {"
                print "        cum::set_optional(optionalmask, " + str(j) + ");"
                print "        encode(*" + field + ", pCtx);"
                print "    }"
            else:
                print "    encode(" + field + ", pCtx);"
        print "}"

    def createSequenceDecoder(self, name, cs):
        print "void decode(" + name + "& pData, cum::codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"

        noptionals = 0
        for i in cs:
            if "optional" in self.type_[i[0]]:
                noptionals += 1
        print "    // noptionals = " + str(noptionals)
        optionalmasksz = int(math.ceil(noptionals*1.0/8))
        if optionalmasksz > 0:
            print "    uint8_t optionalmask[" + str(optionalmasksz) + "] = {};"
            print "    encode_optionalmask(optionalmask, " + str(noptionals) + ", pCtx);"

        j = 0
        for i in cs:
            field = "pIe." + i[1]
            if "optional" in self.type_[i[0]]:
                print "    if (cum::check_optional(optionalmask, "+str(j)+"))"
                print "    {"
                print "        " + field + " = cum::optional_inner<decltype(" + field + ")>::type{};"
                print "        decode(*" + field + ", pCtx);"
                print "    }"
            else:
                print "    decode(" + field + ", pCtx);"
        print "}"

    def createChoiceEncoder(self, name, cs):
        print "void encode(const " + name + "& pData, cum::codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"
        print "    using TypeIndex = uint32_t;"
        print "    TypeIndex type = pIe.index();"
        print "    encode(type, pCtx);"
        j = 0
        for i in cs:
            js = str(j)
            print "    if (type==" + js + ") encode(std::get<" + js + ">(pData), pCtx);"
            j += 1
        print "}"

    def createChoiceDecoder(self, name, cs):
        print "void decode(" + name + "& pData, cum::codec_ctx& pCtx)"
        print "{"
        print "    using namespace cum;"
        print "    using TypeIndex = uint32_t;"
        print "    TypeIndex type"
        print "    decode(type, pCtx);"
        j = 0
        for i in cs:
            js = str(j)
            print "    if (type==" + js + ") {pData = " + cs[j] + "{}; decode(std::get<" + js + ">(pData), pCtx);}"
            j += 1
        print "}"

    def processSequenceCodec(self, name, data):
        cs = self.sequence_[name]
        self.createSequenceEncoder(name, cs)
        self.createSequenceDecoder(name, cs)

    def processChoiceCodec(self, name, data):
        cs = self.choice_[name]
        self.createChoiceEncoder(name, cs)
        self.createChoiceDecoder(name, cs)


    def generate(self):
        print "// Generating for C++"
        defname = "__" + sys.argv[1] + "_HPP__";
        print "#ifndef " + defname
        print "#define " + defname
        print "#include \"cum/cum.hpp\""
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

        for i in self.pass1_expressions_:
            t = i[0]
            n = i[1]
            v = i[2]

            if (t == "Sequence"):
                self.processSequenceCodec(n, v)
            elif (t == "Choice"):
                self.processChoiceCodec(n, v)
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
