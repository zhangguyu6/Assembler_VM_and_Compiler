# -*- coding: utf-8 -*-
"""
一个简单的汇编器
用于hack计算机
"""

import re
import os
import argparse
from pprint import pprint


# a=16
# b="{:0>16b}".format(a)

def A_instruction(instruction):
    """
    A指令转换函数
    :param instruction: A指令(@int)
    :return: binstruction:二进制机器码
    """
    address = int(instruction[1:])
    binstruction = "{:0>16b}".format(address)
    return binstruction


# print(A_instruction(str('@16')))

COMP_DICT = {
    '0': '101010',
    '1': '111111',
    '-1': '111010',
    'D': '001100',
    'A': '110000',
    '!D': '001101',
    '!A': '110001',
    '-D': '001111',
    '-A': '110011',
    'D+1': '011111',
    'A+1': '110111',
    'D-1': '001110',
    'A-1': '110010',
    'D+A': '000010',
    'D-A': '010011',
    'A-D': '000111',
    'D&A': '000000',
    'D|A': '010101',
}

DEST_DICT = {
    'null': '000',
    'M': '001',
    'D': '010',
    'MD': '011',
    'A': '100',
    'AM': '101',
    'AD': '110',
    "AMD": '111',
}

JUMP_DICT = {
    'null': '000',
    'JGT': '001',
    'JEQ': '010',
    'JGE': '011',
    'JLT': '100',
    'JNE': '101',
    'JLE': '110',
    'JMP': '111',
}


def C_instruction(comp, dest='null', jump='null'):
    """
    C指令转换函数
    :param dest: 目的指令
    :param comp: 计算指令
    :param jump: 跳转指令
    :return: binstruction:二进制机器码
    """
    if 'M' in comp:
        a = '1'
        comp = comp.replace('M', 'A')
    else:
        a = '0'

    comp_instruction = COMP_DICT[comp]
    dest_instruction = DEST_DICT[dest]
    jump_instruction = JUMP_DICT[jump]
    binstruction = '111' + a + comp_instruction + dest_instruction + jump_instruction
    return int(binstruction)


PRE_SYMBOL_TABLE = {
    'R0': 0,
    'R1': 1,
    'R2': 2,
    'R3': 3,
    'R4': 4,
    'R5': 5,
    'R6': 6,
    'R7': 7,
    'R8': 8,
    'R9': 9,
    'R10': 10,
    'R11': 11,
    'R12': 12,
    'R13': 13,
    'R14': 14,
    'R15': 15,
    'SCREEN': 16384,
    'KBD': 24576,
    'SP': 0,
    'LCL': 1,
    'ARG': 2,
    'THIS': 3,
    'THAT': 4,
}
# print(C_instruction('M','M','null'))





# 找出一行的标签，指令和注释
pattern = '\((?P<label>\w+)\)'
pattern2 = '^(?P<instruction>[\w|()@;=+-]*)(//){0,1}(?P<doc>\w*)'


def symbol_label(instruction):
    """
    第一次遍历文件，找到（label），在符号表中加入label变量
    :param instruction: 所有指令
    :return: None
    """
    global linenum, _SYMBOL_TABLE

    if not instruction.startswith('(') \
            and not instruction.startswith('//'):
        linenum += 1

    if instruction.startswith('(') \
            and instruction.endswith(')'):
        label = \
            re.compile(pattern).search(instruction).groupdict()['label']

        linegoto = linenum
        _SYMBOL_TABLE[label] = linegoto


def symbol_var(instruction):
    """
    第二次遍历文件，找到@var，在符号表中新建索引
    :param instruction: 所有指令
    :return:
    """
    global linenum, _SYMBOL_TABLE
    if instruction.startswith('@'):
        var = instruction[1:]
        if var not in _SYMBOL_TABLE.keys():
            VAR_DICT[var] = len(VAR_DICT) + 16

    _SYMBOL_TABLE = {**_SYMBOL_TABLE, **VAR_DICT}


# pprint(symbol_table('@i'))
# match = re.compile(pattern2).search('adada//ada')
# print(match.groupdict())

def parser(instruction):
    """
    指令解析，根据不同的指令调用不同的指令函数
    :param instruction: 除（label）外的所有指令
    :return: binstruction: 二进制机器码
    """
    for var in _SYMBOL_TABLE.keys():
        if var in instruction:
            instruction = instruction.replace(var, str(_SYMBOL_TABLE[var]))

    # 当前指令为A指令
    if instruction.startswith('@'):
        binstruction = A_instruction(instruction)
        return binstruction

    # 当前指令为B指令
    else:
        dest = 'null'
        jump = 'null'
        inlist = ''

        if '=' in instruction:
            inlist = instruction.split('=')
            dest = inlist[0]
        if ';' in instruction:
            if inlist:
                inlist = inlist[1].split(';')
            else:
                inlist = instruction.split(';')
            comp = inlist[0]
            jump = inlist[1]
        else:
            comp = inlist[1]

        binstruction = C_instruction(comp, dest=dest, jump=jump)
        return binstruction


if __name__ == '__main__':

    # 浅拷贝预处理符号表
    _SYMBOL_TABLE = {**PRE_SYMBOL_TABLE}
    # 变量表
    VAR_DICT = {}
    # 行号
    linenum = 0
    # 增加命令行参数，汇编文件在当前目录输入，输出
    myparser = argparse.ArgumentParser()
    myparser.add_argument("-f", "--infilename", help="name of input assembly file")
    myparser.add_argument("-o", "--outfilename", help="name of output assembly file")
    currentdir = os.getcwd()
    args = myparser.parse_args()

    # 输出文件
    fo = open(currentdir + '/' + args.outfilename, 'w')
    # 第一次遍历
    with open(currentdir + '/' + args.infilename, 'r') as f:
        for line in f:
            if line == '\n' or line.startswith('//'):
                continue
            # 去首尾空格
            line = line.strip()
            # 去掉注释
            instruction = \
                re.compile(pattern2).search(line).groupdict()['instruction'].strip()
            symbol_label(instruction)
    # 第二次遍历
    with open(currentdir + '/' + args.infilename, 'r') as f:
        for line in f:
            if line == '\n' or line.startswith('//'):
                continue
            # 去首尾空格
            line = line.strip()
            # 去掉注释
            instruction = \
                re.compile(pattern2).search(line).groupdict()['instruction'].strip()
            symbol_var(instruction)
    # 第三次遍历
    with open(currentdir + '/' + args.infilename, 'r') as f:
        for line in f:
            if line == '\n' or line.startswith('//') or line.startswith('('):
                continue
            # 去首尾空格
            line = line.strip()
            # 去掉注释
            instruction = \
                re.compile(pattern2).search(line).groupdict()['instruction'].strip()
            binstruction = parser(instruction)
            fo.write(str(binstruction) + '\n')
        fo.close()
