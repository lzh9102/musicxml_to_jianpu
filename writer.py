#!/usr/bin/env python

from fractions import Fraction
from reader import Measure

STEP_TO_NUMBER = {
    'C': 1,
    'D': 2,
    'E': 3,
    'F': 4,
    'G': 5,
    'A': 6,
    'B': 7
}

def stepToNumber(step):
    return str(STEP_TO_NUMBER[step])

def generateOctaveMark(octave):
    if octave >= 4:
        return "'" * (octave - 4)
    else:
        return "," * (4 - octave)

def generateTimeSuffix(duration, divisions):
    note_length = Fraction(duration, divisions)
    if duration < divisions: # less than quarter notes: add / and continue
        return generateTimeSuffix(duration*2, divisions) + "/"
    elif duration == divisions: # quarter notes
        return ""
    elif duration * 2 == divisions * 3: # syncopated notes
        return "."
    else: # sustained more than 1.5 quarter notes: add - and continue
        return " -" + generateTimeSuffix(duration - divisions, divisions)

def generateHeader(reader):
    title = reader.getWorkTitle()
    key = reader.getInitialKeySignature().replace('b', '$') # flat is represented by '$' in this format
    time = reader.getInitialTimeSignature()

    header = "V: 1.0\n" # jianpu99 version number
    if title:
        header += "B: %s\n" % title
    header += "D: %s\n" % key
    header += "P: %s\n" % time

    composer = reader.getComposer()
    if composer:
        header += "Z: %s\n" % composer

    return header

def getNoteDisplayedDuration(note):
    if note.isTuplet():
        return note.getDisplayedDuration()
    else:
        return note.getDuration()

NOTE_DEGREE_TABLE = {
    'C': 0, 'B#': 0,
    'C#': 1, 'Db': 1,
    'D': 2,
    'D#': 3, 'Eb': 3,
    'E': 4, 'Fb': 4,
    'F': 5, 'E#': 5,
    'F#': 6, 'Gb': 6,
    'G': 7,
    'G#': 8, 'Ab': 8,
    'A': 9,
    'A#': 10, 'Bb': 10,
    'B': 11, 'Cb': 11
}

DEGREE_NOTE_TABLE = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def getTransposedPitch(note_name, octave, offset):
    degree = NOTE_DEGREE_TABLE[note_name]
    transposed_degree = degree + offset
    transposed_octave = octave + transposed_degree // 12
    transposed_degree %= 12
    return (DEGREE_NOTE_TABLE[transposed_degree], transposed_octave)

def getTransposeOffsetToC(key):
    degree = NOTE_DEGREE_TABLE[key]
    if degree <= 6:
        return -degree
    else:
        return 12 - degree

def generateBasicNote(note):
    if note.isRest():
        return '0'
    else:
        pitch = note.getPitch()
        (note_name, octave) = note.getPitch()

        keysig = note.getAttributes().getKeySignature()
        if keysig != 'C':
            offset = getTransposeOffsetToC(keysig)
            (note_name, octave) = getTransposedPitch(note_name, octave, offset)

        step = note_name[0:1] # C, D, E, F, G, A, B
        accidental = note_name[1:2] # sharp (#) and flat (b)
        if accidental == 'b':
            accidental = '$' # $ is used to notated flat in this format

        return stepToNumber(step) + accidental + generateOctaveMark(octave)

def generateNote(note):
    result = generateBasicNote(note)
    value = note.getTremolo()
    if value > 0:
        result += '"%s"' % ('/' * value)
    result += generateTimeSuffix(*getNoteDisplayedDuration(note))

    if note.isTieStart():
        result = '( ' + result
    if note.isTupletStart():
        result = '(y' + result
    if note.isTupletStop():
        result += ')'
    if note.isSlideStart():
        if note.isSlideUp():
            result += '&shy'
        else:
            result += '&xhy'
    if note.isTieStop():
        if '-' in result: # put ending tie before the first -
            idx = result.index('-')
            result = result[:idx] + ') ' + result[idx:]
        else:
            result = result + ' )'
    return result

def generateMeasure(measure):
    pieces = [generateNote(note) for note in measure]
    return ' '.join(pieces)

def generateRightBarline(measure):
    if measure.getRightBarlineType() == Measure.BARLINE_REPEAT:
        return ":|"
    elif measure.getRightBarlineType() == Measure.BARLINE_DOUBLE:
        return "||/"
    elif measure.getRightBarlineType() == Measure.BARLINE_FINAL:
        return "||"
    else:
        return "|"

def generateMeasures(measureList):
    pieces = []
    for i, measure in enumerate(measureList):
        if measure.getLeftBarlineType() == Measure.BARLINE_REPEAT:
            if i == 0:
                pieces.append("|:")
            else:
                pieces.append(":")

        if measure.isSegno():
            pieces.append("&hs")
        elif measure.isCoda():
            pieces.append("&ty")

        pieces.append(" ")
        pieces.append(generateMeasure(measure))
        pieces.append(" ")

        pieces.append(generateRightBarline(measure))
        if measure.isDalSegno():
            pieces.append("&ds")
        elif measure.isToCoda():
            pieces.append("&ty")

    return ''.join(pieces)

def generateBody(reader, max_measures_per_line=4):

    parts = reader.getPartIdList()

    part_measures = dict()
    for part in parts:
        part_measures[part] = list(reader.iterMeasures(part))

    lines = []

    measure_count = max(len(measures) for measures in part_measures.values())
    for i in range(0, measure_count, max_measures_per_line):
        begin = i
        end = min(i + max_measures_per_line, measure_count)
        for part_index, part in enumerate(parts):
            line = "Q%d: " % (part_index + 1)
            line += generateMeasures(part_measures[part][begin:end])
            lines.append(line)
        lines.append('') # empty line

    return '\n'.join(lines)

class WriterError(Exception):
    pass

class Jianpu99Writer:

    def generate(self, reader):
        return generateHeader(reader) + "\n" + generateBody(reader)
