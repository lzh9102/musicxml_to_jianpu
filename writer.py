#!/usr/bin/env python

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

def appendForTie(text, char):
    if '-' in text:  # put char before the first -
        idx = text.index('-')
        text = f'{text[:idx]}{char} {text[idx:]}'
    else:
        text = f'{text} {char}'
    return text

class WriterError(Exception):
    pass

class WriterOptions:

    def __init__(self):
        self.ignore_key = False
        self.max_measures_per_line = 4

class WriterDict:

    def __init__(self):
        self.sharp = '#'
        self.flat = 'b'
        self.tuplet = ('', '')
        self.line_suffix = ''

class BaseWriter:

    def __init__(self, **kwds):
        self._options = WriterOptions()
        self._dict = WriterDict()
        for key, value in kwds.items():
            if value is None:
                pass
            if hasattr(self._options, key):
                setattr(self._options, key, value)
            if hasattr(self._dict, key):
                setattr(self._dict, key, value)

    def toHeader(self, title, key, beats, beat_type, tempo, composer):
        raise NotImplementedError()

    def toLinePrefix(self, part_index, num_parts):
        return ''

    def toNote(self, step, accidental, octave_mark):
        raise NotImplementedError()

    def toTremolo(self, tremolo):
        return ''

    def toSlide(self, text, slide_up):
        return ''

    def toTieStart(self, text):
        return f'( {text}'

    def generate(self, reader):
        return self.generateHeader(reader) + '\n' + self.generateBody(reader)

    def generateHeader(self, reader):
        title = reader.getWorkTitle()
        if self._options.ignore_key:
            key = 'C'
        else:
            key = reader.getInitialKeySignature().replace(
                '#', self._dict.sharp).replace('b', self._dict.flat)
        beats, beat_type = reader.getInitialTime()
        tempo = reader.getInitialTempo()
        pickup = reader.getPickup()
        composer = reader.getComposer()
        return self.toHeader(title, key, beats, beat_type, tempo, pickup, composer)

    def generateBody(self, reader):
        parts = reader.getPartIdList()

        part_measures = dict()
        for part in parts:
            part_measures[part] = list(reader.iterMeasures(part))

        lines = []

        measure_count = max(len(measures) for measures in part_measures.values())
        for i in range(0, measure_count, self._options.max_measures_per_line):
            begin = i
            end = min(i + self._options.max_measures_per_line, measure_count)
            for part_index, part in enumerate(parts):
                line = self.toLinePrefix(part_index, len(parts))
                line += self.generateMeasures(part_measures[part][begin:end])
                line += self._dict.line_suffix
                lines.append(line)
            lines.append('') # empty line

        return '\n'.join(lines)

    def generateMeasures(self, measureList):
        result = ''
        for i, measure in enumerate(measureList):
            result += self.toLeftBarline(i, measure)
            result += ' '
            result += self.generateMeasure(measure)
            result += ' '
            result += self.toRightBarline(measure)
        return result

    def generateMeasure(self, measure):
        pieces = [self.generateNote(note) for note in measure]
        return ' '.join(pieces)

    def generateNote(self, note):
        result = self.generateBasicNote(note)
        tremolo = note.getTremolo()
        if tremolo > 0:
            result += self.toTremolo(tremolo)
        prefix, suffix = self.generateTimePrefixAndSuffix(*note.getDisplayedDuration())
        result = prefix + result + suffix

        if note.isTieStart():
            result = self.toTieStart(result)
        if note.isTupletStart():
            result = self._dict.tuplet[0] + result
        if note.isTupletStop():
            result += self._dict.tuplet[1]
        if note.isSlideStart():
            result = self.toSlide(result, note.isSlideUp())
        if note.isTieStop():
            result = appendForTie(result, ')')
        return result

    def generateBasicNote(self, note):
        if note.isRest():
            return '0'
        else:
            pitch = note.getPitch()
            (note_name, octave) = note.getPitch()

            if not self._options.ignore_key:
                keysig = note.getAttributes().getKeySignature()
                if keysig != 'C':
                    offset = getTransposeOffsetToC(keysig)
                    (note_name, octave) = getTransposedPitch(note_name, octave, offset)

            step = note_name[0:1] # C, D, E, F, G, A, B
            accidental = note_name[1:2] # sharp (#) and flat (b)
            if accidental == '#':
                accidental = self._dict.sharp
            elif accidental == 'b':
                accidental = self._dict.flat

            return self.toNote(stepToNumber(step), accidental, generateOctaveMark(octave))

    def generateTimePrefixAndSuffix(self, duration, divisions, prefix=''):
        if duration < divisions: # less than quarter notes: add / and continue
            return self.toShortTimePrefixAndSuffix(duration, divisions, prefix)
        elif duration == divisions: # quarter notes
            return prefix, ''
        elif duration * 2 == divisions * 3: # syncopated notes
            return prefix, '.'
        else: # sustained more than 1.5 quarter notes: add - and continue
            prefix, suffix = self.generateTimePrefixAndSuffix(duration - divisions, divisions)
            return prefix, ' -' + suffix

class Jianpu99Writer(BaseWriter):

    def __init__(self, *args, **kwds):
        kwds.update(dict(
            flat = '$',  # flat is represented by '$' in this format
            tuplet = ('(y', ')'),
        ))
        BaseWriter.__init__(self, *args, **kwds)

    def toHeader(self, title, key, beats, beat_type, tempo, pickup, composer):
        header = 'V: 1.0\n'  # jianpu99 version number
        if title is not None:
            header += f'B: {title}\n'
        header += f'D: {key}\n'
        header += f'P: {beats}/{beat_type}\n'
        if tempo > 0.01:
            bpm = round(float(tempo) * beat_type / 4)
            header += f'J: {bpm}\n'
        if composer is not None:
            header += f'Z: {composer}\n'
        return header

    def toLinePrefix(self, part_index, num_parts):
        prefix = ''
        if num_parts > 1:
             prefix = str(part_index + 1)
        return f'Q{prefix}: '

    def toNote(self, step, accidental, octave_mark):
        return step + accidental + octave_mark

    def toTremolo(self, tremolo):
        return '"%s"' % ('/' * tremolo)

    def toSlide(self, text, slide_up):
        if slide_up:
            return f'{text}&shy'
        else:
            return f'{text}&xhy'

    def toShortTimePrefixAndSuffix(self, duration, divisions, prefix):
        assert(duration < divisions)
        prefix, suffix = self.generateTimePrefixAndSuffix(duration * 2, divisions, prefix)
        return prefix, suffix + '/'

    def toLeftBarline(self, index, measure):
        result = ''
        if measure.getLeftBarlineType() == Measure.BARLINE_REPEAT:
            if index == 0:
                result = '|:'
            else:
                result = ':'

        if measure.isSegno():
            result += '&hs'
        elif measure.isCoda():
            result += '&ty'
        return result

    def toRightBarline(self, measure):
        if measure.getRightBarlineType() == Measure.BARLINE_REPEAT:
            result = ':|'
        elif measure.getRightBarlineType() == Measure.BARLINE_DOUBLE:
            result = '||/'
        elif measure.getRightBarlineType() == Measure.BARLINE_FINAL:
            result = '||'
        else:
            result = '|'

        if measure.isDalSegno():
            result += '&ds'
        elif measure.isToCoda():
            result += '&ty'
        return result

LY_TIME_PREFIXES = ('', 'q', 's', 'd', 'h')
ANAC_TABLE = {  # jianpu-ly only has limited support to anac
    1: '64', 2: '32', 3: '32.', 4: '16', 6: '16.', 8: '8', 12: '8.',
    16: '4', 24: '4.', 32: '2', 48: '2.'
}

def wrapLy(s):
    if not s:
        return ''
    if type(s) in (list, tuple):
        s = '\n'.join(s)
    return f'\nLP:\n{s}\n:LP\n'

def wrapLyMark(s, raw=False, down=False):
    result = r'\mark \markup { \sans \bold \fontsize #-4 {%s} }' % s
    if down:
        result = r'\once \override Score.RehearsalMark.direction = #DOWN ' + result
    if not raw:
        result = wrapLy(result)
    return result

class JianpuLyWriter(BaseWriter):

    def __init__(self, *args, **kwds):
        kwds.update(dict(
            tuplet = ('3[ ', ' ]'),
            line_suffix = r'\break',
        ))
        BaseWriter.__init__(self, *args, **kwds)
        self.right_after_final_bar = False

    def toHeader(self, title, key, beats, beat_type, tempo, pickup, composer):
        header = ''
        if tempo > 0.01:
            header = f'%% tempo: {beat_type}={round(tempo)}\n'
        if title is not None:
            header += f'title={title}\n'
        header += f'1={key}\n'

        anac = ''
        if pickup < beats - .01:
            index = round(pickup * 64 / beat_type)
            if index in ANAC_TABLE:
                anac = ',' + ANAC_TABLE[index]
        header += f'{beats}/{beat_type}{anac}\n'

        if composer is not None:
            header += f'composer={composer}\n'

        ly_lines = [
            r'\set Score.barNumberVisibility = #all-bar-numbers-visible',
            r'\override Score.BarNumber.break-visibility = #end-of-line-invisible',
            r'\override Score.RehearsalMark.break-visibility = #begin-of-line-invisible',
        ]
        if anac:
            ly_lines.append(r'\set Score.currentBarNumber = #2')
        header += wrapLy(ly_lines)
        return header

    def toNote(self, step, accidental, octave_mark):
        return accidental + step + octave_mark

    def toTremolo(self, tremolo):
        return wrapLy(fr"-\tweak #'Y-offset #-4.8 -\tweak #'X-offset #0.6 :{4 * 2 ** tremolo}")

    def toSlide(self, text, slide_up):
        y = [2, -1]
        if slide_up:
            y.reverse()
        return wrapLy(r'\once \override Glissando.bound-details.left.Y = #%d '
                      r'\once \override Glissando.bound-details.right.Y = #%d '
                      % (y[0], y[1])) + text + ' \glissando '

    def toTieStart(self, text):
        return appendForTie(text, '(')

    def toShortTimePrefixAndSuffix(self, duration, divisions, prefix):
        assert(duration < divisions)
        for i in range(len(LY_TIME_PREFIXES) - 1):
            if prefix == LY_TIME_PREFIXES[i]:
                return self.generateTimePrefixAndSuffix(
                    duration * 2, divisions, LY_TIME_PREFIXES[i + 1])
        raise ValueError('Too short a note duration')

    def toLeftBarline(self, index, measure):
        result = ''
        ly_lines = []
        if measure.getLeftBarlineType() == Measure.BARLINE_REPEAT:
            ly_lines.append(r'\bar ".|:"')

        if self.right_after_final_bar:  # add an invisible measure
            ly_lines = [
                r'\override Voice.Rest.color = "white"',
                r'\once \override Score.BarNumber.break-visibility = ##(#f #f #f)',
            ] + ly_lines
            beats, beat_type = measure.getAttributes().getTime()
            result += wrapLy(ly_lines) + ' 0 ' + '- ' * (beats * 4 // beat_type - 1)
            ly_lines = [
                r'\bar "|"',
                r'\revert Voice.Rest.color',
                fr'\set Score.currentBarNumber = #{measure.getMeasureNumber()}',
            ]
            self.right_after_final_bar = False

        if measure.isSegno():
            ly_lines.append(wrapLyMark(r'\musicglyph #"scripts.segno"', raw=True))
        elif measure.isCoda():
            ly_lines.append(wrapLyMark(r'\musicglyph #"scripts.coda"', raw=True))
        return result + wrapLy(ly_lines)

    def toRightBarline(self, measure):
        ly_lines = []
        if measure.getRightBarlineType() == Measure.BARLINE_REPEAT:
            ly_lines.append(r'\bar ":|."')
        elif measure.getRightBarlineType() == Measure.BARLINE_DOUBLE:
            ly_lines.append(r'\bar "||"')
        elif measure.getRightBarlineType() == Measure.BARLINE_FINAL:
            self.right_after_final_bar = True
            ly_lines.append(r'\bar "|."')
        # else: use auto barline

        if measure.isDalSegno():
            ly_lines.insert(0, wrapLyMark(measure.getDalSegno(), raw=True, down=True))
        elif measure.isToCoda():
            ly_lines.insert(0, wrapLyMark('To \musicglyph #"scripts.coda"', raw=True))
        return wrapLy(ly_lines)

def getGrammars():
    return 'jianpu99', 'jianpu-ly'

def createWriter(grammar, *args, **kwds):
    if grammar == 'jianpu-ly':
        return JianpuLyWriter(*args, **kwds)
    return Jianpu99Writer(*args, **kwds)

