# -*- coding: utf-8 -*-

from pprint import pprint
import os
import argparse
import re

"""
jack语言的编译器前端
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


# token = Token("class Bar {\n "
#               "method Fraction foo (int y){\n"
#               "if (x < 0) {\n"
#               "let sign =\"negative\";\n"
#               "}\n"
#               "}\n"
#               "}\n")
# tokenlist = token.outtoken()
# pprint(tokenlist)


class CompilationEngine(object):
    """
    parser引擎
    """

    def __init__(self, tokenlist):
        self.tokenlist = tokenlist

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
            '<class>',
            *self.tokenlist[:3],
            *classvardec,
            *subroutinedec,
            '<symbol>}</symbol>',
            '</class>']
        return compilelist

    def complieclassvardec(self, startindex, endindex):
        """
        ( 'static' | 'field' ) type varName ( ',' varName)* ';'
        """
        classvardec = [
            '<classVarDec:>',
            *self.tokenlist[startindex:endindex + 1],
            '</classVarDec:>'
        ]
        return classvardec

    def compliesubroutinedec(self, index, startindex, endindex):
        """
        ( 'constructor' | 'function' | 'method' )
        ( 'void' | type) subroutineName '(' parameterList ')'
        subroutineBody
        """
        parameterlist = self.complieparameterlist(index + 3, startindex)
        subroutinuebody = self.compliesubroutinuebody(startindex, endindex)
        subroutinuedec = [
            '<subroutineDec>',
            *self.tokenlist[index:index + 3],
            *parameterlist,
            *subroutinuebody,
            '</subroutineDec>'
        ]
        return subroutinuedec

    def complieparameterlist(self, startindex, endindex):
        """
        ((type varName) ( ',' type varName)*)?

        """
        parameterlist = [
            '<parameterList>',
            *self.tokenlist[startindex:endindex + 1],
            '</parameterList>',
        ]
        return parameterlist

    def compliesubroutinuebody(self, startindex, endindex):
        """
        '{' varDec* statements '}'
        """
        body = self.tokenlist[startindex: endindex + 1]
        vardec = []
        statements = []
        index = 0
        while index < len(body):
            if body[index] == '<keyword>var</keyword>':
                for endindex in range(index + 1, len(body)):
                    if body[endindex] == '<symbol>;</symbol>':
                        vardec.extend(self.complievardec(body, index, endindex))
                        index = endindex
                        break
            elif body[index] in ['<keyword>{}</keyword>'.format(key) for key in ['let', 'do', 'return']]:
                for endindex in range(index + 1, len(body)):
                    if body[endindex] == '<symbol>;</symbol>':
                        statements.extend(self.compliestatement(body[index:endindex + 1]))
                        index = endindex
                        break
            elif body[index] in ['<keyword>{}</keyword>'.format(key) for key in ['if', 'while']]:
                count = 0
                for endindex in range(index + 1, len(body)):
                    # print("*********", endindex, count, body[endindex])
                    if body[endindex] == '<symbol>{</symbol>':
                        count += 1
                    if body[endindex] == '<symbol>}</symbol>':
                        count -= 1
                        if count == 0 and body[endindex + 1] != '<keyword>else</keyword>':
                            statements.extend(self.compliestatement(body[index:endindex + 1]))
                            index = endindex
                            break
            else:
                index += 1
        subroutinuebody = [
            '<subroutineBody>',
            '<symbol>{</symbol>',
            *vardec,
            '<statements>',
            *statements,
            '</statements>',
            '<symbol>}</symbol>',
            '</subroutineBody>'
        ]
        return subroutinuebody

    def complievardec(self, body, startindex, endindex):
        """
        'var' type varName ( ',' varName)* ';'
        """
        vardec = [
            '<varDec>',
            *body[startindex: endindex + 1],
            '</varDec>'
        ]
        return vardec

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
                        index = endindex
                        break
            elif body[index] in ['<keyword>{}</keyword>'.format(key) for key in ['if', 'while']]:
                count = 0
                for endindex in range(index + 1, len(body)):
                    if body[endindex] == '<keyword>{</keyword>':
                        count += 1
                    if body[endindex] == '<keyword>}</keyword>':
                        count -= 1
                        if count == 0 and (
                                        endindex >= len(body) - 1 or body[endindex + 1] != '<keyword>else</keyword>'):
                            statements.extend(self.compliestatement(body[index:endindex + 1]))
                            index = endindex
                            break
            else:
                index += 1
        statements = [
            '<statements>',
            '<symbol>{</symbol>',
            *statements,
            '<symbol>}</symbol>',
            '</statements>'
        ]
        return statements

    def letstatement(self, body):
        """
        'let' varName ( '[' expression ']' )? '=' expression ';'
        """
        firstexpress = []
        secondexpress = []
        for index in range(len(body)):
            if body[index] == '<symbol>[</symbol>':
                indexoffirst = index
            if body[index] == '<symbol>]</symbol>':
                indexofsecond = index
                firstexpress.extend(self.complieexpress(body[indexoffirst + 1:indexofsecond]))
            if body[index] == '<symbol>=</symbol>':
                indexoffirst = index
            if body[index] == '<symbol>;</symbol>':
                indexofsecond = index
                secondexpress.extend(self.complieexpress(body[indexoffirst + 1:indexofsecond]))
        statement = [
            '<letStatement>',
            *body[:3],
            *firstexpress,
            *body[indexoffirst - 1:indexoffirst + 1],
            *secondexpress,
            body[-1],
            '</letStatement>'
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
            '<ifStatement>',
            *body[:2],
            *expression,
            '<symbol>)</symbol>',
            '<symbol>{</symbol>',
            *ifstatement,
            '<symbol>}</symbol>',
            *elsestatement,
            '</ifStatement>'
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
                    statements.extend(body[index + 2:-1])
        statement = [
            '<whileStatement>',
            *body[:2],
            *expression,
            '<symbol>)</symbol>',
            '<symbol>{</symbol>',
            *statements,
            '<symbol>}</symbol>',
            '</whileStatement>'
        ]
        return statement

    def dostatement(self, body):
        """
        'do' subroutineCall ';'
        """
        subroutinecall = self.subroutinecall(body[1:-1])
        statement = [
            '<doStatement>',
            *subroutinecall,
            '</doStatement>',
        ]
        return statement

    def returnstatement(self, body):
        """
        'return' expression? ';
        """
        expression = []
        if body[1:-1]:
            expression.extend(self.complieexpress(body[1:-1]))
        statement = [
            '<ReturnStatement>',
            *expression,
            '</ReturnStatement>'
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
            elif CompilationEngine.isop(body[index]) and not CompilationEngine.isop(body[index - 1]):
                statement.extend(self.complieterm(body[lastop + 1:index]))
                statement.append(body[index])
                lastop = index
        statement.extend(self.complieterm(body[lastop + 1:]))
        statement = [
            '<expression>',
            *statement,
            '</expression>'
        ]
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
            statement.append(body[0])
            statement.extend(self.complieterm(body[1:]))
        else:
            if body[0] == '<symbol>(</symbol>':
                statement = [
                    body[0],
                    *self.complieexpress(body[1:-1]),
                    body[-1]
                ]
            elif len(body) > 2 and body[1] == '<symbol>[</symbol>':
                statement = [
                    body[:2],
                    *self.complieexpress(body[2:-1]),
                    body[-1]
                ]
            elif len(body) > 2 and (body[1] == '<symbol>(</symbol>' or body[2] == '<symbol>(</symbol>'):
                statement = self.subroutinecall(body)
            else:
                statement = body
        statement = [
            '<term>',
            *statement,
            '</term>'
        ]
        return statement

    def subroutinecall(self, body):
        """
        subroutineName '(' expressionList ')' | (className |
        varName) '.' subroutineName '(' expressionList ')'
        """
        statement = []
        index = 0
        if body[1] == '<symbol>(</symbol>':
            statement.extend(self.complieexpresslist(body[:2:-1]))
            index = 2
        elif body[3] == '<symbol>(</symbol>':
            statement.extend(self.complieexpresslist(body[:4:-1]))
            index = 4
        statement = [
            *body[:index],
            *statement,
            body[-1]
        ]
        return statement

    def complieexpresslist(self, body):
        """
        (expression ( ',' expression)* )?
        """
        lastindex = -1
        statement = []
        for index in range(len(body)):
            if body[index] == '<symbol>,</symbol>':
                statement.extend(self.complieexpress(body[lastindex + 1:index]))
        statement.extend(self.complieexpress(body[lastindex + 1:]))
        statement = [
            '<expressionList>',
            *statement,
            '</expressionList>'
        ]
        return statement

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


def main():
    myparser = argparse.ArgumentParser()
    myparser.add_argument("-f", "--infilename", help="name of input vm file")
    args = myparser.parse_args()
    outfilename = os.path.basename(args.infilename).split('.')[0]
    outfilepath = (os.path.join(os.path.dirname(args.infilename), outfilename + '.xml'))
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


if __name__ == '__main__':
    main()
