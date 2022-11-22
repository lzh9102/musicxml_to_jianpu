![CI status](https://github.com/lzh9102/musicxml_to_jianpu/actions/workflows/run-tests.yaml/badge.svg)

# Convert MusicXML to [JianPu](https://en.wikipedia.org/wiki/Numbered_musical_notation)

This is a simple program to help you create JianPu notation from any standard
notation software that outputs MusicXML.  It is still experimental and only
support a very limit set of features from MusicXML.

Currently two output formats are supported:

- [FanQie JianPu](http://zhipu.lezhi99.com/Zhipu-index.html)
  (`--grammar jianpu99`)
- [Jianpu in Lilypond](http://ssb22.user.srcf.net/mwrhome/jianpu-ly.html)
  (`--grammar jianpu-ly`)

# Usage

    usage: converter.py [-h] input_file

# Supported Features
- Simple Notes
- Rests
- Accidentals
- Ties
- Multiple parts

# Current Limitations
- All parts must be monophonic.
- Cannot handle change of key signature or time signature in the middle of the
  piece.

# License

Copyright (C) 2018 Che-Huai Lin

MIT License
