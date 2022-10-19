#!/usr/bin/env python3

import argparse

from reader import MusicXMLReader, MusicXMLParseError
from writer import Jianpu99Writer, WriterError

def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help="input file in MusicXML format")
    parser.add_argument('--staff', type=int, default=1,
                        help="Which staff to convert (default: 1)")
    parser.add_argument('--ignore_key', type=bool, default=False,
                        action=argparse.BooleanOptionalAction,
                        help="Whethere to ignore key signature (default: False)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parseArguments()

    reader = MusicXMLReader(args.input_file, args.staff)
    writer = Jianpu99Writer(args.ignore_key)

    try:
        print(writer.generate(reader))
    except WriterError as e:
        print(f'error: {str(e)}')
