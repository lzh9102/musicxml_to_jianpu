#!/usr/bin/env python3

import argparse

from reader import MusicXMLReader, MusicXMLParseError
from writer import Jianpu99Writer, WriterError

def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help="input file in MusicXML format")
    return parser.parse_args()


if __name__ == "__main__":
    args = parseArguments()

    reader = MusicXMLReader(args.input_file)
    writer = Jianpu99Writer()

    try:
        print(writer.generate(reader))
    except WriterError as e:
        print("error: %s" % str(e))
