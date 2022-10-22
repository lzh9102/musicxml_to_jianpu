#!/usr/bin/env python3

import argparse

from reader import MusicXMLReader, MusicXMLParseError
from writer import WriterError, createWriter, getGrammars

def parseArguments():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('input_file', help="input file in MusicXML format")
    parser.add_argument('--grammar', choices=getGrammars(),
                        default=getGrammars()[0],
                        help="Which grammar to use in writing")
    parser.add_argument('--staff', type=int, default=1,
                        help="Which staff to convert")
    parser.add_argument('--ignore_key', type=bool, default=False,
                        action=argparse.BooleanOptionalAction,
                        help="Whethere to ignore key signature")
    return parser.parse_args()


if __name__ == "__main__":
    args = parseArguments()

    reader = MusicXMLReader(args.input_file, args.staff)
    writer = createWriter(args.grammar, ignore_key=args.ignore_key)

    try:
        print(writer.generate(reader))
    except WriterError as e:
        print(f'error: {str(e)}')
