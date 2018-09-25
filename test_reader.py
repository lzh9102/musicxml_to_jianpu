#!/usr/bin/env python3

from unittest import TestCase
from unittest.mock import patch
from lxml import etree
from reader import *

class TestMeasure(TestCase):

    def setUp(self):
        measures = []
        prev_measure = None
        for measure_str in FAKE_MEASURES:
            measure = Measure(etree.fromstring(measure_str), prev_measure)
            measures.append(measure)
            prev_measure = measure

        self.measures = measures

    def test_firstMeasureNoAttribute(self):
        with self.assertRaises(MusicXMLParseError):
            # measure 2 has no attributes
            Measure(etree.fromstring(FAKE_MEASURES[1]), None)

    def test_measureNumber(self):
        self.assertEqual(self.measures[0].getMeasureNumber(), 1)
        self.assertEqual(self.measures[1].getMeasureNumber(), 2)
        self.assertEqual(self.measures[2].getMeasureNumber(), 3)
        self.assertEqual(self.measures[3].getMeasureNumber(), 4)

    def test_attributes(self):
        attributes = [m.getAttributes() for m in self.measures]

        # measure 1
        a1 = attributes[0]
        self.assertEqual(a1.getDivisions(), 2)
        self.assertEqual(a1.getKeySignature(), 'C')
        self.assertEqual(a1.getTimeSignature(), '4/4')

        # measure 2 should inherit attributes from measure 1
        a2 = attributes[1]
        self.assertEqual(a2.getDivisions(), 2)
        self.assertEqual(a2.getKeySignature(), 'C')
        self.assertEqual(a2.getTimeSignature(), '4/4')

        # measure 3: attribute update
        a3 = attributes[2]
        self.assertEqual(a3.getDivisions(), 4)
        self.assertEqual(a3.getKeySignature(), 'D')
        self.assertEqual(a3.getTimeSignature(), '6/8')

        # measure 4: partial attribute update (only key signature changes)
        a4 = attributes[3]
        self.assertEqual(a4.getDivisions(), 4)
        self.assertEqual(a4.getKeySignature(), 'A')
        self.assertEqual(a4.getTimeSignature(), '6/8')

    def test_iterNotes(self):
        measure1_notes = [note for note in self.measures[0]]
        self.assertEqual(len(measure1_notes), 5)
        measure2_notes = [note for note in self.measures[1]]
        self.assertEqual(len(measure2_notes), 6)
        measure3_notes = [note for note in self.measures[2]]
        self.assertEqual(len(measure3_notes), 4)
        measure4_notes = [note for note in self.measures[3]]
        self.assertEqual(len(measure4_notes), 5)

    def test_barlines(self):
        measure = Measure(etree.fromstring("""
        <measure number="1">
          <barline location="right">
            <bar-style>light-heavy</bar-style>
          </barline>
        </measure>
        """), prev_measure=self.measures[0])
        self.assertEqual(measure.getLeftBarlineType(), Measure.BARLINE_NORMAL)
        self.assertEqual(measure.getRightBarlineType(), Measure.BARLINE_FINAL)

        measure = Measure(etree.fromstring("""
        <measure number="1">
          <barline location="left">
            <bar-style>heavy-light</bar-style>
            <repeat direction="forward"/>
          </barline>
        </measure>
        """), prev_measure=self.measures[0])
        self.assertEqual(measure.getLeftBarlineType(), Measure.BARLINE_REPEAT)
        self.assertEqual(measure.getRightBarlineType(), Measure.BARLINE_NORMAL)

        measure = Measure(etree.fromstring("""
        <measure number="1">
          <barline location="right">
            <bar-style>light-heavy</bar-style>
            <repeat direction="backward"/>
          </barline>
        </measure>
        """), prev_measure=self.measures[0])
        self.assertEqual(measure.getLeftBarlineType(), Measure.BARLINE_NORMAL)
        self.assertEqual(measure.getRightBarlineType(), Measure.BARLINE_REPEAT)

        measure = Measure(etree.fromstring("""
        <measure number="1">
          <barline location="left">
            <bar-style>heavy-light</bar-style>
            <repeat direction="forward"/>
          </barline>
          <barline location="right">
            <bar-style>light-light</bar-style>
          </barline>
        </measure>
        """), prev_measure=self.measures[0])
        self.assertEqual(measure.getLeftBarlineType(), Measure.BARLINE_REPEAT)
        self.assertEqual(measure.getRightBarlineType(), Measure.BARLINE_DOUBLE)

class TestNote(TestCase):

    @patch('reader.Attributes')
    def setUp(self, MockAttributes):
        attributes = MockAttributes()
        attributes.getDivisions.return_value = 2
        attributes.getKeySignature.return_value = 'C'
        attributes.getTimeSignature.return_value = "4/4"
        self.attributes = attributes

    def test_simpleNote(self):
        note = Note(etree.fromstring(
            """
            <note>
                <pitch>
                    <step>E</step>
                    <octave>4</octave>
                </pitch>
                <duration>2</duration>
            </note>
            """), self.attributes)
        self.assertFalse(note.isRest())
        self.assertEqual(note.getPitch(), ('E', 4))
        self.assertEqual(note.getDuration(), (2, 2))
        self.assertFalse(note.isTieStart())
        self.assertFalse(note.isTieStop())
        self.assertFalse(note.isTupletStart())
        self.assertFalse(note.isTupletStop())
        self.assertFalse(note.isTuplet())
        self.assertEqual(note.getAttributes(), self.attributes)

    def test_pitch(self):
        note = Note(etree.fromstring(
            """
            <note>
                <pitch>
                    <step>C</step>
                    <octave>5</octave>
                </pitch>
                <duration>2</duration>
            </note>
            """), self.attributes)
        self.assertEqual(note.getPitch(), ('C', 5))

        # sharp
        note = Note(etree.fromstring(
            """
            <note>
                <pitch>
                    <step>D</step>
                    <octave>4</octave>
                </pitch>
                <accidental>sharp</accidental>
                <duration>2</duration>
            </note>
            """), self.attributes)
        self.assertEqual(note.getPitch(), ('D#', 4))

        # flat
        note = Note(etree.fromstring(
            """
            <note>
                <pitch>
                    <step>D</step>
                    <octave>4</octave>
                </pitch>
                <accidental>flat</accidental>
                <duration>2</duration>
            </note>
            """), self.attributes)
        self.assertEqual(note.getPitch(), ('Db', 4))

        # Notated C should be C# in the key of A
        self.attributes.getKeySignature.return_value = 'A'
        note = Note(etree.fromstring(
            """
            <note>
                <pitch>
                    <step>C</step>
                    <octave>5</octave>
                </pitch>
                <duration>2</duration>
            </note>
            """), self.attributes)
        self.assertEqual(note.getPitch(), ('C#', 5))

        # Natural C in the key of A
        self.attributes.getKeySignature.return_value = 'A'
        note = Note(etree.fromstring(
            """
            <note>
                <pitch>
                    <step>C</step>
                    <octave>5</octave>
                </pitch>
                <accidental>natural</accidental>
                <duration>2</duration>
            </note>
            """), self.attributes)
        self.assertEqual(note.getPitch(), ('C', 5))


    def test_rest(self):
        note = Note(etree.fromstring(
            """
            <note>
                <rest/>
                <duration>2</duration>
            </note>
            """), self.attributes)
        self.assertTrue(note.isRest())
        with self.assertRaises(MusicXMLParseError):
            note.getPitch()
        self.assertEqual(note.getDuration(), (2, 2))
        self.assertFalse(note.isTieStart())
        self.assertFalse(note.isTieStop())

    def test_tie(self):
        note = Note(etree.fromstring(
            """
            <note>
                <pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
                <tie type="start"/>
            </note>
            """), self.attributes)
        self.assertTrue(note.isTieStart())
        self.assertFalse(note.isTieStop())

        note = Note(etree.fromstring(
            """
            <note>
                <pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
                <tie type="stop"/>
            </note>
            """), self.attributes)
        self.assertFalse(note.isTieStart())
        self.assertTrue(note.isTieStop())

        note = Note(etree.fromstring(
            """
            <note>
                <pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
                <tie type="start"/>
                <tie type="stop"/>
            </note>
            """), self.attributes)
        self.assertTrue(note.isTieStart())
        self.assertTrue(note.isTieStop())

    def test_tuplet(self):
        self.attributes.getDivisions.return_value = 6

        note1 = Note(etree.fromstring(
            """
            <note>
                <pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
                <time-modification>
                  <actual-notes>3</actual-notes>
                  <normal-notes>2</normal-notes>
                </time-modification>
                <notations>
                  <tuplet type="start" bracket="yes"/>
                </notations>
            </note>
            """), self.attributes)
        note2 = Note(etree.fromstring(
            """
            <note>
                <pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
                <time-modification>
                  <actual-notes>3</actual-notes>
                  <normal-notes>2</normal-notes>
                </time-modification>
            </note>
            """), self.attributes)
        note3 = Note(etree.fromstring(
            """
            <note>
                <pitch><step>E</step><octave>4</octave></pitch><duration>2</duration>
                <time-modification>
                  <actual-notes>3</actual-notes>
                  <normal-notes>2</normal-notes>
                </time-modification>
                <notations>
                  <tuplet type="stop"/>
                </notations>
            </note>
            """), self.attributes)

        self.assertTrue(note1.isTuplet())
        self.assertTrue(note2.isTuplet())
        self.assertTrue(note3.isTuplet())

        self.assertTrue(note1.isTupletStart())
        self.assertFalse(note1.isTupletStop())
        self.assertFalse(note2.isTupletStart())
        self.assertFalse(note2.isTupletStop())
        self.assertFalse(note3.isTupletStart())
        self.assertTrue(note3.isTupletStop())

        self.assertEqual(note1.getDisplayedDuration(), (3, 6))

# ------------- TEST DATA -------------

FAKE_MEASURES = [
    """
    <measure number="1" width="319.79">
      <print>
        <system-layout>
          <system-margins>
            <left-margin>0.00</left-margin>
            <right-margin>0.00</right-margin>
            </system-margins>
          <top-system-distance>170.00</top-system-distance>
          </system-layout>
        </print>
      <attributes>
        <divisions>2</divisions>
        <key>
          <fifths>0</fifths>
          </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
          </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
          </clef>
        </attributes>
      <note default-x="75.17" default-y="-40.00">
        <pitch>
          <step>E</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      <note default-x="132.35" default-y="-40.00">
        <pitch>
          <step>E</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">begin</beam>
        <notations>
          <slur type="start" number="1"/>
          </notations>
        </note>
      <note default-x="168.09" default-y="-35.00">
        <pitch>
          <step>F</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">end</beam>
        <notations>
          <slur type="stop" number="1"/>
          </notations>
        </note>
      <note default-x="203.83" default-y="-30.00">
        <pitch>
          <step>G</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      <note default-x="261.01" default-y="-40.00">
        <pitch>
          <step>E</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      </measure>
      """
      ,
      """
    <measure number="2" width="278.96">
      <note default-x="12.00" default-y="-45.00">
        <pitch>
          <step>D</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">begin</beam>
        </note>
      <note default-x="48.86" default-y="-40.00">
        <pitch>
          <step>E</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">continue</beam>
        </note>
      <note default-x="85.71" default-y="-35.00">
        <pitch>
          <step>F</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">continue</beam>
        </note>
      <note default-x="122.57" default-y="-45.00">
        <pitch>
          <step>D</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <tie type="start"/>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">end</beam>
        <notations>
          <tied type="start"/>
          </notations>
        </note>
      <note default-x="159.42" default-y="-45.00">
        <pitch>
          <step>D</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <tie type="stop"/>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        <notations>
          <tied type="stop"/>
          </notations>
        </note>
      <note>
        <rest/>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        </note>
      </measure>
      """
      ,
"""
    <measure number="3" width="249.35">
      <attributes>
        <divisions>4</divisions>
        <key>
          <fifths>2</fifths>
          </key>
        <time>
          <beats>6</beats>
          <beat-type>8</beat-type>
          </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
          </clef>
        </attributes>
      <note default-x="12.00" default-y="-35.00">
        <pitch>
          <step>F</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      <note default-x="70.94" default-y="-45.00">
        <pitch>
          <step>D</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      <note default-x="129.87" default-y="-30.00">
        <pitch>
          <step>G</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      <note default-x="188.81" default-y="-35.00">
        <pitch>
          <step>F</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      </measure>
      """
      ,
      """
    <measure number="4" width="262.51">
      <attributes>
        <key>
          <fifths>3</fifths>
          </key>
        </attributes>
      <note default-x="12.00" default-y="-40.00">
        <pitch>
          <step>E</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      <note default-x="70.57" default-y="-40.00">
        <pitch>
          <step>E</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">begin</beam>
        </note>
      <note default-x="107.17" default-y="-35.00">
        <pitch>
          <step>F</step>
          <octave>4</octave>
          </pitch>
        <duration>1</duration>
        <voice>1</voice>
        <type>eighth</type>
        <stem>up</stem>
        <beam number="1">end</beam>
        </note>
      <note default-x="143.78" default-y="-30.00">
        <pitch>
          <step>G</step>
          <octave>4</octave>
          </pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <stem>up</stem>
        </note>
      <note>
        <rest/>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        </note>
      </measure>
      """
      ]
