# -*- coding: utf-8 -*-
import argparse
import os
import Parser


def main():
    myparser = argparse.ArgumentParser()
    myparser.add_argument("-f", "--infilename", help="name of input vm file")
    args = myparser.parse_args()
    outfilename = os.path.basename(args.infilename).split('.')[0]
    outfilepath = (os.path.join(os.path.dirname(args.infilename), outfilename + '.asm'))
    outf = open(outfilepath, 'w')
    with open(args.infilename, 'r') as f:
        # i=0
        for line in f:
            # print(i)
            # i+=1
            # print(line)
            line = line.rstrip()
            if line.startswith('//') or line == '\n' or line=='':
                continue

            p = Parser.Parser(line, outfilename)
            if p.hasmorecommands():
                outf.write(p.mul())
            elif p.issingle():
                outf.write(p.single())


if __name__ == '__main__':
    main()
