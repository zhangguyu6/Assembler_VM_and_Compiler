# -*- coding: utf-8 -*-

from pprint import pprint
import os
import argparse
import re
from collections import defaultdict

"""
jack语言的编译器后端
"""

# 符号常量
SYMBOLS = '{}()[].,;+-*/&|<>=~'
# 关键词常量
KEYWORDS = ['class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int', 'char',
            'boolean', 'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return']


class Token(object):
    """
    用于分词
    """

    def __init__(self, words):
        self.words = words

    @staticmethod
    def tyoftoken(word):
        """
        判断单字种类，jack语言支持5种单字
        :param word: 单字
        :return: 标识符
        """
        if word in KEYWORDS:
            return 'keyword'
        elif word in SYMBOLS:
            return 'symbol'
        elif word.startswith('\"') and word.endswith('\"'):
            return 'stringConstant'
        elif word.isdigit():
            return 'integerConstant'
        else:
            return 'identifier'

    def token(self, string):
        """
        将字符串分成单字，并打上标签
        :param string: jack标准输入
        :return: 有标签的单字列
        """
        stringlist = []

        def replacestring(matched):
            thestring = matched.group("strings")
            stringlist.append(thestring)
            return "\"{}\"".format(str(len(stringlist) - 1))

        string = re.sub("(?P<strings>\".*?\")", replacestring, string)
        for symbol in SYMBOLS:
            string = string.replace(symbol, " {} ".format(symbol))
        tokenlist = string.split()
        tokenlist = ["<{type}>{word}</{type}>".format(type=Token.tyoftoken(word), word=word) for word in
                     tokenlist]
        stringlist = stringlist[::-1]
        for index in range(len(tokenlist)):
            if tokenlist[index].startswith('<stringConstant>'):
                tokenlist[index] = "<stringConstant>{string}</stringConstant>".format(
                    string=stringlist.pop().strip("\""))
        return tokenlist

    def outtoken(self):
        return self.token(self.words)


class CompilationEngine(object):
    """
    parser引擎
    """

    def __init__(self, tokenlist):
        self.tokenlist = tokenlist
        self.class_symbol_table = [defaultdict(list), defaultdict(list)]
        self.subroutine_symbol_table = defaultdict(list)
        self.aug_symbol_table = defaultdict(list)
        self.method = {}
        self.currentreturn = 1
        self.classname = ''
        self.currentlab = 0

    def complieclass(self):
        """
        'class' className '{' classVarDec* subroutineDec* '}'
        """
        classvardec = []
        subroutinedec = []
        index = 0
        while index < len(self.tokenlist):
            if self.tokenlist[index] in ('<keyword>static</keyword>',
                                         '<keyword>field</keyword>'):
                for endindex in range(index + 1, len(self.tokenlist)):
                    if self.tokenlist[endindex] == '<symbol>;</symbol>':
                        classvardec.extend(self.complieclassvardec(index, endindex))
                        index = endindex
                        break
            elif self.tokenlist[index] in ('<keyword>constructor</keyword>',
                                           '<keyword>function</keyword>',
                                           '<keyword>method</keyword>'):
                count = 0
                for sbindex in range(index + 3, len(self.tokenlist)):
                    if self.tokenlist[sbindex] == '<symbol>{</symbol>':
                        if count == 0:
                            startlindex = sbindex
                        count += 1

                    if self.tokenlist[sbindex] == '<symbol>}</symbol>':
                        count -= 1
                        if count == 0:
                            subroutinedec.extend(self.compliesubroutinedec(index, startlindex, sbindex))
                            index = sbindex
                            break
                    if sbindex == len(self.tokenlist) - 1 and count != 0:
                        raise Exception(count)
            else:
                index += 1
        compilelist = [
            *classvardec,
            *subroutinedec,
        ]

        return compilelist

    def complieclassvardec(self, startindex, endindex):
        """
        ( 'static' | 'field' ) type varName ( ',' varName)* ';'
        """

        body = self.tokenlist[startindex:endindex + 1]
        self.insertdec(body, self.class_symbol_table[0], 'static')
        self.insertdec(body, self.class_symbol_table[1], 'field')
        return []

    def compliesubroutinedec(self, index, startindex, endindex):
        """
        ( 'constructor' | 'function' | 'method' )
        ( 'void' | type) subroutineName '(' parameterList ')'
        subroutineBody
        """
        if self.tokenlist[index + 1] == "<keyword>void</keyword>":
            self.currentreturn = 0
        self.subroutine_symbol_table = defaultdict(list)
        self.method[self.tokenlist[index + 2]] = self.tokenlist[index]
        body = self.tokenlist[index:endindex + 1]
        parameterlist = self.complieparameterlist(index + 3, startindex)
        subroutinuebody = self.compliesubroutinuebody(startindex, endindex)
        functiondec = self.compliefunctiondec(CompilationEngine.typeof(body[0]))
        subroutinuedec = [
            *functiondec,
            *parameterlist,
            *subroutinuebody
        ]
        return subroutinuedec

    def compliefunctiondec(self, name):
        varcount = len(self.subroutine_symbol_table)
        statement = [CompilationEngine.writefunction(self.classname + '.' + name, varcount)]
        if name == 'method':
            statement.append(CompilationEngine.writepush('argument', 0))
            statement.append(CompilationEngine.writepop('pointer', 0))
        elif name == 'constructor':
            statement.append(CompilationEngine.writepush('constant', len(self.class_symbol_table[1])))
            statement.append(CompilationEngine.writecall('Memory.alloc', 1))
            statement.append(CompilationEngine.writepush('pointer', 0))
        return statement

    def complieparameterlist(self, startindex, endindex):
        """
        ((type varName) ( ',' type varName)*)?

        """
        parameterlist = [
        ]
        return parameterlist

    def compliesubroutinuebody(self, startindex, endindex):
        """
        '{' varDec* statements '}'
        """
        body = self.tokenlist[startindex: endindex + 1]
        vardec = []
        statements = []
        index = 1
        while index < len(body):

            if body[index] == '<keyword>var</keyword>':
                for _index in range(index + 1, len(body)):
                    if body[_index] == '<symbol>;</symbol>':
                        vardec.extend(self.complievardec(body, index, _index))
                        index = _index+1

                        break
            else:
                # pprint(body[index:endindex-1])
                statements=self.compliestatements(body[index:endindex-1])

                break
        subroutinuebody = [
            *vardec,
            *statements,
        ]

        return subroutinuebody

    def complievardec(self, body, startindex, endindex):
        """
        'var' type varName ( ',' varName)* ';'
        """
        body = body[startindex: endindex + 1]
        self.insertdec(body, self.subroutine_symbol_table, 'var')
        vardec = []
        return vardec

    def insertdec(self, body, table, kind):
        segment={
            'const':'constant',
            'arg':'argumrnt',
            'field':'this',
            'static':'static',
            'var':'local'
        }
        index = len(table)
        patten = ">(\S*)<"
        kindof = re.findall(patten, body[0])[0]
        typeof = re.findall(patten, body[1])[0]
        firstvarname = re.findall(patten, body[2])[0]
        if kindof == kind:
            table[firstvarname].extend([index, typeof, segment.get(kindof,kindof)])
            for word in body[3:]:
                if word.startswith("<identifier>"):
                    name = re.findall(patten, word)[0]
                    index = len(table)
                    table[name].extend([index, typeof, segment.get(kindof,kindof)])

    def compliestatement(self, body):
        """
        letStatement | ifStatement | whileStatement |doStatement | returnStatement
        """
        # print(body)
        if body[0] == '<keyword>let</keyword>':
            return self.letstatement(body)
        elif body[0] == '<keyword>if</keyword>':

            return self.ifstatement(body)
        elif body[0] == '<keyword>while</keyword>':

            return self.whilestatement(body)
        elif body[0] == '<keyword>do</keyword>':
            return self.dostatement(body)
        elif body[0] == '<keyword>return</keyword>':
            return self.returnstatement(body)

    def compliestatements(self, body):
        """
        statement*
        """
        statements = []
        index = 0
        while index < len(body):

            if body[index] in ['<keyword>{}</keyword>'.format(key) for key in ['let', 'do', 'return']]:
                for endindex in range(index + 1, len(body)):
                    if body[endindex] == '<symbol>;</symbol>':
                        statements.extend(self.compliestatement(body[index:endindex + 1]))
                        # print(body[index:endindex + 1])
                        # pprint(self.compliestatement(body[index:endindex + 1]))
                        # print('*******************************')
                        index = endindex
                        break
            elif body[index] in ['<keyword>{}</keyword>'.format(key) for key in ['if', 'while']]:
                count = 0
                for endindex in range(index + 1, len(body)):
                    if body[endindex] == '<symbol>{</symbol>':
                        count += 1
                    if body[endindex] == '<symbol>}</symbol>':
                        count -= 1
                    if count == 0 and body[endindex] == '<symbol>}</symbol>' :
                        if endindex<len(body)-1:
                            if body[endindex + 1] != '<keyword>else</keyword>':
                                statements.extend(self.compliestatement(body[index:endindex + 1]))
                                index = endindex
                                break
                            else:
                                statements.extend(self.compliestatement(body[index:endindex + 1]))
                                index = endindex
                                break
            else:
                index += 1
        statements = [
            *statements,
        ]

        return statements

    def letstatement(self, body):
        """
        'let' varName ( '[' expression ']' )? '=' expression ';'
        """
        firstexpress = []
        secondexpress = []
        ass = []
        patten = ">(\S*)<"
        varname = re.findall(patten, body[1])[0]
        for index in range(len(body)):
            if body[index] == '<symbol>[</symbol>':
                indexoffirst = index
            if body[index] == '<symbol>]</symbol>':
                indexofsecond = index
                firstexpress.append(CompilationEngine.writepush(self.findseg(varname)[2], self.findseg(varname)[0]))
                firstexpress.extend(self.complieexpress(body[indexoffirst + 1:indexofsecond]))
                firstexpress.append(CompilationEngine.writearithmetic('add'))

            if body[index] == '<symbol>=</symbol>':
                indexoffirst = index
            if body[index] == '<symbol>;</symbol>':
                indexofsecond = index
                secondexpress.extend(self.complieexpress(body[indexoffirst + 1:indexofsecond]))

        if firstexpress:
            ass.append(CompilationEngine.writepop('temp', 0))
            ass.append(CompilationEngine.writepop('pointer', 1))
            ass.append(CompilationEngine.writepush('temp', 0))
            ass.append(CompilationEngine.writepush('that', 0))
        else:
            ass.append(CompilationEngine.writepop(self.findseg(varname)[2], self.findseg(varname)[0]))
        statement = [
            *firstexpress,
            *secondexpress,
            *ass
        ]
        return statement

    def ifstatement(self, body):
        """
        'if' '(' expression ')' '{' statements '}'( 'else' '{' statements '}' )?
        """
        expression = []
        ifstatement = []
        elsestatement = []
        count = 1
        bracecount = 0
        ifindex = 0
        for index in range(len(body)):
            if body[index] == '<symbol>)</symbol>':
                count -= 1
                if count == 0:
                    expression.extend(self.complieexpress(body[2:index]))
                    ifindex = index + 1
            if body[index] == '<symbol>{</symbol>':
                bracecount += 1
            elif body[index] == '<symbol>}</symbol>':
                bracecount -= 1
                if bracecount == 0 and index != len(body) - 1:
                    ifstatement.extend(self.compliestatements(body[ifindex:index]))
                    elsestatement.extend(['<keyword>else</keyword>', '<symbol>{</symbol>'])
                    elsestatement.extend(self.compliestatements(body[index + 3:-2]))
                    elsestatement.append('<symbol>{</symbol>')
                    break
                elif bracecount == 0:
                    ifstatement.extend(self.compliestatements(body[ifindex:index]))
                    break
        statement = [
            *expression,
            CompilationEngine.writearithmetic('not'),
            CompilationEngine.writeif(self.currentlab),
            *ifstatement,
            CompilationEngine.writegoto(self.currentlab + 1),
            self.writelabel(),
            *elsestatement,
            self.writelabel(),
        ]
        return statement

    def whilestatement(self, body):
        """
        'while' '(' expression ')' '{' statements '}'
        """
        expression = []
        statements = []
        count = 1
        for index in range(len(body)):
            if body[index] == '<symbol>)</symbol>':
                count -= 1
                if count == 0:
                    expression.extend(self.complieexpress(body[2:index]))
                    statements.extend(self.compliestatements(body[index+1:]))
        statement = [
            self.writelabel(),
            *expression,
            CompilationEngine.writearithmetic('not'),
            CompilationEngine.writeif(self.currentlab),
            *statements,
            CompilationEngine.writegoto(self.currentlab - 1),
            self.writelabel()
        ]
        return statement

    def dostatement(self, body):
        """
        'do' subroutineCall ';'
        """
        subroutinecall = self.subroutinecall(body[1:-1])
        statement = [
            *subroutinecall,
            CompilationEngine.writepop("temp", 0)
        ]
        return statement

    def returnstatement(self, body):
        """
        'return' expression? ';
        """
        expression = []
        if body[1:-1]:
            expression.extend(self.complieexpress(body[1:-1]))
        else:
            expression.append(CompilationEngine.writepush('constant', 0))
        statement = [
            *expression,
            CompilationEngine.writereturn()
        ]
        return statement

    def complieexpress(self, body):
        """
        term (op term)*
        """
        statement = []
        lastop = -1

        for index in range(len(body)):
            if index == 0 and CompilationEngine.isunaryop(body[0]):
                lastop = -1
            elif CompilationEngine.isunaryop(body[index]) and CompilationEngine.isop(body[index - 1]):
                lastop = index - 1
            elif CompilationEngine.isop(body[index]) and not CompilationEngine.isop(body[index - 1]):
                statement.extend(self.complieterm(body[lastop + 1:index]))
                if lastop != -1:
                    statement.append(self.writearithmetic(CompilationEngine.typeof(body[lastop])))
                lastop = index

        if lastop != -1:
            statement.extend(self.complieterm(body[lastop + 1:]))
            statement.append(self.writearithmetic(CompilationEngine.typeof(body[lastop])))
        else:
            statement.extend(self.complieterm(body))

        return statement

    def complieterm(self, body):
        """
        integerConstant | stringConstant | keywordConstant |varName |
        varName '[' expression ']' | subroutineCall |
        '(' expression ')' | unaryOp term
        """
        statement = []
        if not body:
            pass
        elif CompilationEngine.isunaryop(body[0]):
            statement.extend(self.complieterm(body[1:]))
            statement.append(CompilationEngine.writearithmetic(body[0]))
        else:
            if body[0] == '<symbol>(</symbol>':
                statement.extend([
                    *self.complieexpress(body[1:-1]),
                ])
            elif len(body) == 1 and body[0].startswith('<identifier>'):
                name = CompilationEngine.typeof(body[0])
                statement.append(CompilationEngine.writepush(self.findseg(name)[2], self.findseg(name)[0]))
            elif len(body) > 2 and body[1] == '<symbol>[</symbol>':
                name = CompilationEngine.typeof(body[0]
                                                )
                statement.extend([
                    CompilationEngine.writepush(self.findseg(name)[2], self.findseg(name)[0]),
                    *self.complieexpress(body[2:-1]),
                    CompilationEngine.writearithmetic('add'),
                    CompilationEngine.writepop('pointer', 1),
                    CompilationEngine.writepush('that', 0)
                ])
            elif len(body) > 2 and (body[1] == '<symbol>(</symbol>' or body[3] == '<symbol>(</symbol>'):
                statement.extend(self.subroutinecall(body))
            else:
                if body[0].startswith('<integerConstant>'):
                    statement.append(CompilationEngine.writepush('constant', int(CompilationEngine.typeof(body[0]))))
                elif body[0].startswith('<stringConstant>'):
                    str = CompilationEngine.typeof(body[0])
                    statement.extend([
                        CompilationEngine.writepush('constant', len(str)),
                        CompilationEngine.writecall('String new', 1)
                    ])
                    for index in range(len(str)):
                        statement.append(CompilationEngine.writepush('constant', ord(str[index])))
                        statement.append(CompilationEngine.writecall('String.appendChar', 2))
                elif body[0].startswith('<keyword>true'):
                    statement.append(CompilationEngine.writepush('constant', -1))
                elif body[0].startswith('<keyword>fasle') or body[0].startswith('<keyword>null'):
                    statement.append(CompilationEngine.writepush('constant', 0))
                elif body[0].startswith('<keyword>that'):
                    statement.append(CompilationEngine.writepush('pointer', 0))

        # pprint(body)
        # pprint(statement)
        # print('______________________')
        return statement

    def subroutinecall(self, body):
        """
        subroutineName '(' expressionList ')' | (className |
        varName) '.' subroutineName '(' expressionList ')'
        """
        statement = []
        if body[1] == '<symbol>(</symbol>':
            method = self.method.get(body[0])
            nargs = self.complieexpresslist(body[2:-1])[1]
            name = CompilationEngine.typeof(body[0])
            if method == "<keyword>method</keyword>":
                statement.append(CompilationEngine.writepush('pointer', 0))
                nargs += 1
            statement.extend(self.complieexpresslist(body[2:-1])[0])
            statement.append(CompilationEngine.writecall(name, nargs))

        elif body[3] == '<symbol>(</symbol>':
            nargs = self.complieexpresslist(body[2:-1])[1]
            name = CompilationEngine.typeof(body[0]) + CompilationEngine.typeof(body[1]) + CompilationEngine.typeof(
                body[2])
            statement.extend(self.complieexpresslist(body[4:-1])[0])
            statement.append(CompilationEngine.writecall(name, nargs))

        return statement

    def complieexpresslist(self, body):
        """
        (expression ( ',' expression)* )?
        """
        lastindex = -1
        statement = []
        narg = 1
        for index in range(len(body)):
            if body[index] == '<symbol>,</symbol>':
                narg += 1
                statement.extend(self.complieexpress(body[lastindex + 1:index]))
        statement.extend(self.complieexpress(body[lastindex + 1:]))
        if len(body) == 2:
            narg = 0

        return statement, narg

    @staticmethod
    def isop(syb):
        for op in "+-*/&|<>=":
            if '<symbol>{}</symbol>'.format(op) == syb:
                return True
        return False

    @staticmethod
    def isunaryop(syb):
        for op in "-~":
            if '<symbol>{}</symbol>'.format(op) == syb:
                return True
        return False

    @staticmethod
    def writepush(segment, index):
        return "push {} {}".format(segment, index)

    @staticmethod
    def writepop(segment, index):
        return "pop {} {}".format(segment, index)

    @staticmethod
    def writearithmetic(command):
        defult = {
            '+': 'add',
            '-': 'sub',
            '*': 'call Math.multiply 2',
            '/': 'call Math.divide 2',
            '<': 'lt',
            '>': 'gt',
            '=': 'eq',
            '&': 'and',
            '|': 'or',
        }
        return defult.get(command, command)

    def writelabel(self):
        self.currentlab += 1
        return "label L{}".format(self.currentlab - 1)

    @staticmethod
    def writegoto(label):
        return "goto L{}".format(label)

    @staticmethod
    def writeif(label):
        return "if-goto L{}".format(label)

    @staticmethod
    def writecall(name, nargs):
        return "call {} {}".format(name, nargs)

    @staticmethod
    def writefunction(name, nlocals):
        return "function {} {}".format(name, nlocals)

    @staticmethod
    def writereturn():
        return "return"

    @staticmethod
    def typeof(word):
        pattern = ">(.*)<"
        return re.findall(pattern, word)[0]

    def findseg(self, varname):
        if self.subroutine_symbol_table.get(varname):
            return self.subroutine_symbol_table.get(varname)
        elif self.aug_symbol_table.get(varname):
            return self.aug_symbol_table.get(varname)
        elif self.class_symbol_table[0].get(varname):
            return self.class_symbol_table[0].get(varname)
        elif self.class_symbol_table[1].get(varname):
            return self.class_symbol_table[1].get(varname)
        else:
            print(self.subroutine_symbol_table)
            raise Exception("can not find var",varname)


def main():
    myparser = argparse.ArgumentParser()
    myparser.add_argument("-f", "--infilename", help="name of input vm file")
    args = myparser.parse_args()
    outfilename = os.path.basename(args.infilename).split('.')[0]
    outfilepath = (os.path.join(os.path.dirname(args.infilename), outfilename + '.vm'))
    outf = open(outfilepath, 'w')
    with open(args.infilename, 'r') as f:
        # i=0
        tokenlist = []
        for line in f:
            line = line.rstrip()
            if line.startswith('/') or line == '\n' or line == '':
                continue
            tokenlist.extend(line)

        token = Token(''.join(tokenlist))
        co = CompilationEngine(token.outtoken())
        outf.write('\n'.join(co.complieclass()))
        outf.write('\n')
        # print(co.class_symbol_table[0])
        # print(co.class_symbol_table[1])
        # print(co.subroutine_symbol_table)
        # print(co.aug_symbol_table)

if __name__ == '__main__':
    main()

