#!/usr/bin/env python

from lxml import etree

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
            'timesig': self._getTimeSignature(prev_attributes),
            'divisions': self._getDivisions(prev_attributes)
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

    def _getTimeSignature(self, prev_attributes):
        beats = self._elem.find('time/beats')
        beat_type = self._elem.find('time/beat-type')
        if beats is None or beat_type is None:
            if prev_attributes:
                return prev_attributes.getTimeSignature()
            raise MusicXMLParseError("time not found in attribute")
        return "%s/%s" % (beats.text, beat_type.text)

    def getDivisions(self):
        return self._cache['divisions']

    def getKeySignature(self):
        return self._cache['keysig']

    def getTimeSignature(self):
        return self._cache['timesig']

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

class Note:

    def __init__(self, elem, attributes):
        assert(elem.tag == 'note')
        self._elem = elem
        self._attributes = attributes

    def _get_int(self, path):
        return int(self._elem.find(path).text)

    def _get_text(self, path):
        elem = self._elem.find(path)
        if elem is None:
            return None
        else:
            return elem.text

    def isRest(self):
        return bool(self._elem.xpath('rest'))

    def isTieStart(self):
        return bool(self._elem.xpath("tie[@type='start']"))

    def isTieStop(self):
        return bool(self._elem.xpath("tie[@type='stop']"))

    def isTuplet(self):
        return bool(self._elem.xpath("time-modification"))

    def isTupletStart(self):
        return self.isTuplet() and bool(self._elem.xpath("notations/tuplet[@type='start']"))

    def isTupletStop(self):
        return self.isTuplet() and bool(self._elem.xpath("notations/tuplet[@type='stop']"))

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
        notated_accidental = self._get_text('accidental')

        notated_sharp = notated_accidental == 'sharp'
        notated_flat = notated_accidental == 'flat'
        notated_natural = notated_accidental == 'natural'

        key = self._attributes.getKeySignature()
        key_accidental_char, key_accidental_list = ACCIDENTAL_TABLE[key]
        if not notated_natural and note_name in key_accidental_list:
            note_name += key_accidental_char
        elif notated_sharp:
            note_name += '#'
        elif notated_flat:
            note_name += 'b'

        return (note_name, octave)

class Measure:

    BARLINE_NORMAL = "NORMAL"
    BARLINE_DOUBLE = "DOUBLE"
    BARLINE_FINAL = "FINAL"
    BARLINE_REPEAT = "REPEAT"

    def __init__(self, elem, prev_measure=None):
        assert(elem.tag == 'measure')
        assert(not prev_measure or isinstance(prev_measure, Measure))
        self._elem = elem

        prev_attributes = prev_measure.getAttributes() if prev_measure else None
        attributes_elem = self._elem.find('attributes')

        if not prev_attributes and attributes_elem is None:
            raise MusicXMLParseError("attribute tag not found in first measure")

        if attributes_elem is not None: # this measure contains attribute tag
            self._attributes = Attributes(attributes_elem, prev_attributes)
        else: # no attribute tag; inherit from previous measure
            self._attributes = prev_attributes

        assert(self._attributes is not None)

    def getMeasureNumber(self):
        return int(self._elem.get('number'))

    def getAttributes(self):
        return self._attributes

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
        for elem in self._elem.xpath('note'):
            yield Note(elem, self.getAttributes())

class MusicXMLReader:

    def __init__(self, filename):
        self._root = etree.parse(filename).getroot()
        if self._root.tag != 'score-partwise':
            raise MusicXMLParseError("error: unsupported root element: %s" % self._root.tag)
        self._parts = [x.attrib.get('id')
                       for x in self._root.xpath('part-list/score-part')]

    def _get_text(self, xpath):
        nodes = self._root.xpath(xpath)
        if nodes:
            return nodes[0].text
        else:
            return None

    def _getFirstMeasure(self):
        return next(self.iterMeasures(self._parts[0]))

    def getWorkTitle(self):
        return self._get_text('work/work-title')

    def getComposer(self):
        return self._get_text("identification/creator[@type='composer']")

    def getInitialKeySignature(self):
        return self._getFirstMeasure().getAttributes().getKeySignature()

    def getInitialTimeSignature(self):
        return self._getFirstMeasure().getAttributes().getTimeSignature()

    def getPartIdList(self):
        return self._parts

    def iterMeasures(self, partId):
        prev_measure = None
        for elem in self._root.xpath("part[@id='%s']/measure" % partId):
            measure = Measure(elem, prev_measure)
            yield measure
            prev_measure = measure
