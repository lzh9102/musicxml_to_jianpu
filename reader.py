#!/usr/bin/env python

from lxml import etree
import zipfile

MUSICXML_FIFTHS_TABLE = {
    0: 'C',
    # sharps
    1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#',
    # flats
    -1: 'F', -2: 'Bb', -3: 'Eb', -4: 'Ab', -5: 'Db', -6: 'Gb',
}

class MusicXMLParseError(Exception):
    pass

class Attributes:

    def __init__(self, elem, prev_attributes=None):
        if elem is None:
            raise MusicXMLParseError("attribute not found")
        assert(elem.tag == 'attributes')
        self._elem = elem
        self._cache = {
            'keysig': self._getKeySignature(prev_attributes),
            'time' : self._getTime(prev_attributes),
            'divisions': self._getDivisions(prev_attributes),
            'staves': self._getStaves(prev_attributes),
        }

    def _getDivisions(self, prev_attributes):
        divisions = self._elem.find('divisions')
        if divisions is None:
            if prev_attributes:
                return prev_attributes.getDivisions()
            raise MusicXMLParseError("divisions not found in attribute")
        return int(divisions.text)

    def _getKeySignature(self, prev_attributes):
        fifths = self._elem.find('key/fifths')
        if fifths is None:
            if prev_attributes:
                return prev_attributes.getKeySignature()
            raise MusicXMLParseError("fifths not found in attribute")
        return MUSICXML_FIFTHS_TABLE[int(fifths.text)]

    def _getTime(self, prev_attributes):
        beats = self._elem.find('time/beats')
        beat_type = self._elem.find('time/beat-type')
        if beats is None or beat_type is None:
            if prev_attributes:
                return prev_attributes.getTime()
            raise MusicXMLParseError("time not found in attribute")
        return int(beats.text), int(beat_type.text)
 
    def _getStaves(self, prev_attributes):
        staves = self._elem.find('staves')
        if staves is None:
            if prev_attributes:
                return prev_attributes.getStaves()
            return 1  # default value
        return int(staves.text)

    def getDivisions(self):
        return self._cache['divisions']

    def getKeySignature(self):
        return self._cache['keysig']

    def getTime(self):
        return self._cache['time']

    def getStaves(self):
        return self._cache['staves']

ACCIDENTAL_TABLE = {
    'C':  ('#', []),
    'G':  ('#', ['F']),
    'D':  ('#', ['F', 'C']),
    'A':  ('#', ['F', 'C', 'G']),
    'E':  ('#', ['F', 'C', 'G', 'D']),
    'B':  ('#', ['F', 'C', 'G', 'D', 'A']),
    'F#': ('#', ['F', 'C', 'G', 'D', 'A', 'E']),
    'F':  ('b', ['B']),
    'Bb': ('b', ['B', 'E']),
    'Eb': ('b', ['B', 'E', 'A']),
    'Ab': ('b', ['B', 'E', 'A', 'D']),
    'Db': ('b', ['B', 'E', 'A', 'D', 'G']),
    'Gb': ('b', ['B', 'E', 'A', 'D', 'G', 'C']),
}

class Base:

    def __init__(self, elem):
        self._elem = elem

    def _get_int(self, path, default=None):
        return int(self._get_text(path, str(default)))

    def _get_float(self, path, default=None):
        return float(self._get_text(path, str(default)))

    def _get_bool(self, path):
        return bool(self._elem.xpath(path))

    def _get_text(self, path, default=None):
        if not path.split('/')[-1].startswith('@'):
            path += '/text()'
        results = self._elem.xpath(path)
        if results:
            return results[0]
        return default

class Note(Base):

    def __init__(self, elem, attributes):
        assert(elem.tag == 'note')
        Base.__init__(self, elem)
        self._attributes = attributes

    def isRest(self):
        return self._get_bool('rest')

    def isTieStart(self):
        return self._get_bool("tie[@type='start']")

    def isTieStop(self):
        return self._get_bool("tie[@type='stop']")

    def isTuplet(self):
        return self._get_bool('time-modification')

    def isTupletStart(self):
        return self.isTuplet() and self._get_bool("notations/tuplet[@type='start']")

    def isTupletStop(self):
        return self.isTuplet() and self._get_bool("notations/tuplet[@type='stop']")

    def isSlide(self):
        return self._get_bool('notations/slide')

    def isSlideStart(self):
        return self.isSlide() and self._get_bool("notations/slide[@type='start']")

    def isSlideStop(self):
        return self.isSlide() and self._get_bool("notations/slide[@type='stop']")

    def isSlideUp(self):
        y = self._get_float('notations/slide/@default-y', default=0)
        y0 = self._get_float('@default-y', default=0)
        return y < y0

    def isChord(self):
        return self._get_bool('chord')

    def getDisplayedDuration(self):
        if not self.isTuplet():
            return self.getDuration()
        actual_notes = self._get_int("time-modification/actual-notes")
        normal_notes = self._get_int("time-modification/normal-notes")
        (duration, divisions) = self.getDuration()
        return (duration * actual_notes // normal_notes, divisions)

    def getDuration(self):
        """ return a tuple (note divisions, divisions per quarternote) """
        return (self._get_int('duration'), self._attributes.getDivisions())

    def getPitch(self):
        """ return a tuple (note_name, octave) """
        step = self._elem.find('pitch/step')
        octave = self._elem.find('pitch/octave')
        if step is None or octave is None:
            raise MusicXMLParseError("this note does not have pitch")

        note_name = step.text
        octave = int(octave.text)

        alter = self._get_text('pitch/alter')
        if alter is not None:
            notated_sharp = alter == '1'
            notated_flat = alter == '-1'
            notated_natural = alter == '0'
        else:
            accidental = self._get_text('accidental')
            notated_sharp = accidental == 'sharp'
            notated_flat = accidental == 'flat'
            notated_natural = accidental == 'natural'

        key = self._attributes.getKeySignature()
        key_accidental_char, key_accidental_list = ACCIDENTAL_TABLE[key]
        if not notated_natural and note_name in key_accidental_list:
            note_name += key_accidental_char
        elif notated_sharp:
            note_name += '#'
        elif notated_flat:
            note_name += 'b'

        return (note_name, octave)

    def getAttributes(self):
        return self._attributes

    def getStaff(self):
        return self._get_int('staff', default=1)

    def getVoice(self):
        return self._get_int('voice', default=1)

    def getTremolo(self):
        return self._get_int('notations/ornaments/tremolo', default=0)

def chooseChordTonic(chord):
    # Note: only support tablature notation for now.
    return min(chord, key=lambda note:
        note._get_int('notations/technical/string', default=1000))

class ReaderOptions:

    def __init__(self):
        self.staff = 1
        self.keep_chords = False

class Measure(Base):

    BARLINE_NORMAL = 'NORMAL'
    BARLINE_DOUBLE = 'DOUBLE'
    BARLINE_FINAL = 'FINAL'
    BARLINE_REPEAT = 'REPEAT'

    _default_options = ReaderOptions()

    def __init__(self, elem, prev_measure=None, options = None):
        assert(elem.tag == 'measure')
        assert(not prev_measure or isinstance(prev_measure, Measure))
        Base.__init__(self, elem)

        if options is None:
            options = Measure._default_options

        prev_attributes = prev_measure.getAttributes() if prev_measure else None
        attributes_elem = self._elem.find('attributes')
        if not prev_attributes and attributes_elem is None:
            raise MusicXMLParseError("attribute tag not found in first measure")

        if attributes_elem is not None: # this measure contains attribute tag
            self._attributes = Attributes(attributes_elem, prev_attributes)
        else: # no attribute tag; inherit from previous measure
            self._attributes = prev_attributes
        assert(self._attributes is not None)

        chords = []
        for note_elem in self._elem.xpath('note'):
            note = Note(note_elem, self._attributes)
            if note.getStaff() != options.staff:
                continue  # filter out notes of other staffs
            if note.isChord():
                assert(chords)
                chords[-1].append(note)
            else:
                chords.append([note])
        if options.keep_chords:
            self._notes = chords
        else:
            self._notes = [chooseChordTonic(chord) for chord in chords]

    def isSegno(self):
        return self._get_bool('direction/sound[@segno]')

    def isDalSegno(self):
        return self._get_bool('direction/sound[@dalsegno]')

    def isCoda(self):
        return self._get_bool('direction/sound[@coda]')

    def isToCoda(self):
        return self._get_bool('direction/sound[@tocoda]')

    def getMeasureNumber(self):
        return int(self._elem.get('number'))

    def getTempo(self):
        return self._get_float('direction/sound/@tempo', default=0)

    def getDalSegno(self):
        return self._get_text('direction[sound[@dalsegno]]/direction-type/words')

    def getAttributes(self):
        return self._attributes

    def getNotes(self):
        return self._notes

    def _getBarLine(self, location):
        bar_style = self._elem.xpath('barline[@location="%s"]/bar-style' % location)
        repeat = self._elem.xpath('barline[@location="%s"]/repeat' % location)
        if not bar_style:
            return Measure.BARLINE_NORMAL
        elif repeat:
            return Measure.BARLINE_REPEAT
        elif bar_style[0].text == 'light-light':
            return Measure.BARLINE_DOUBLE
        elif bar_style[0].text == 'light-heavy':
            return Measure.BARLINE_FINAL
        else:
            return Measure.BARLINE_NORMAL

    def getLeftBarlineType(self):
        return self._getBarLine('left')

    def getRightBarlineType(self):
        return self._getBarLine('right')

    def __iter__(self):
        for note in self._notes:
            yield note

def readCompressedMusicXML(filename):
    archive = zipfile.ZipFile(filename)
    try:
        container_xml = archive.read('META-INF/container.xml')
        container_root = etree.fromstring(container_xml)
        musicxml_filename = container_root.xpath('rootfiles/rootfile')[0].attrib.get('full-path')
        return archive.read(musicxml_filename)
    except:
        raise MusicXMLParseError("failed to read compressed MusicXML")

class MusicXMLReader(Base):

    def __init__(self, filename, staff=None, keep_chords=None):
        if zipfile.is_zipfile(filename):
            root = etree.fromstring(readCompressedMusicXML(filename))
        else:
            root = etree.parse(filename).getroot()
        if root.tag != 'score-partwise':
            raise MusicXMLParseError(f'unsupported root element: {root.tag}')

        Base.__init__(self, root)
        self._options = ReaderOptions()
        if staff is not None:
            self._options.staff = max(staff, 1)  # minimal staff value is 1
        if keep_chords is not None:
            self._options.keep_cords = keep_chords

        self._parts = [x.attrib.get('id')
                       for x in root.xpath('part-list/score-part')]

        first_measure = next(self.iterMeasures(self._parts[0]))
        self._initial_attributes = first_measure.getAttributes()
        self._initial_tempo = first_measure.getTempo()

        self._pickup = 0
        for note in first_measure.getNotes():
            nom, denom = note.getDisplayedDuration()
            self._pickup += nom / denom

        staves = self._initial_attributes.getStaves()
        if staff > staves:  # maximal staff value is staves
            raise ValueError(f'staff exceeds staves: {staff} vs {staves}')

    def getWorkTitle(self):
        return self._get_text('work/work-title')

    def getComposer(self):
        return self._get_text("identification/creator[@type='composer']")

    def getInitialKeySignature(self):
        return self._initial_attributes.getKeySignature()

    def getInitialTime(self):
        return self._initial_attributes.getTime()

    def getInitialTempo(self):
        return self._initial_tempo

    def getPickup(self):
        return self._pickup

    def getPartIdList(self):
        return self._parts

    def iterMeasures(self, partId):
        prev_measure = None
        for elem in self._elem.xpath(f"part[@id='{partId}']/measure"):
            measure = Measure(elem, prev_measure, self._options)
            yield measure
            prev_measure = measure
