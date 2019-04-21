#!/usr/bin/env python3

from unittest import TestCase
from unittest.mock import patch
from writer import *

class TestGenerateNote(TestCase):

    @patch('reader.Note')
    @patch('reader.Attributes')
    def setUp(self, MockNote, MockAttributes):
        attributes = MockAttributes()
        attributes.getKeySignature.return_value = 'C'

        note = MockNote()
        note.isRest.return_value = False
        note.getPitch.return_value = ('C', 4)
        note.getDuration.return_value = (2, 2)
        note.getDisplayedDuration.return_value = (2, 2)
        note.isTuplet.return_value = False
        note.isTupletStart.return_value = False
        note.isTupletStop.return_value = False
        note.isTieStart.return_value = False
        note.isTieStop.return_value = False
        note.getAttributes.return_value = attributes
        self.note = note

    def test_pitches(self):
        note = self.note

        note.getPitch.return_value = ('C', 4)
        self.assertEqual(generateNote(note), "1")
        note.getPitch.return_value = ('D', 4)
        self.assertEqual(generateNote(note), "2")
        note.getPitch.return_value = ('E', 4)
        self.assertEqual(generateNote(note), "3")
        note.getPitch.return_value = ('F', 4)
        self.assertEqual(generateNote(note), "4")
        note.getPitch.return_value = ('G', 4)
        self.assertEqual(generateNote(note), "5")
        note.getPitch.return_value = ('A', 4)
        self.assertEqual(generateNote(note), "6")
        note.getPitch.return_value = ('B', 4)
        self.assertEqual(generateNote(note), "7")
        note.getPitch.return_value = ('C', 5)

        # dot over note
        self.assertEqual(generateNote(note), "1'")
        note.getPitch.return_value = ('D', 5)
        self.assertEqual(generateNote(note), "2'")
        note.getPitch.return_value = ('E', 5)
        self.assertEqual(generateNote(note), "3'")
        note.getPitch.return_value = ('C', 6)
        self.assertEqual(generateNote(note), "1''")

        # dot under note
        note.getPitch.return_value = ('B', 3)
        self.assertEqual(generateNote(note), "7,")
        note.getPitch.return_value = ('A', 3)
        self.assertEqual(generateNote(note), "6,")

    def test_accidentals(self):
        note = self.note

        note.getPitch.return_value = ('A#', 5)
        self.assertEqual(generateNote(note), "6#'")
        note.getPitch.return_value = ('Eb', 3)
        self.assertEqual(generateNote(note), "3$,")

    def test_durations(self):
        note = self.note

        note.getDuration.return_value = (2, 2)
        self.assertEqual(generateNote(note), "1")

        note.getDuration.return_value = (4, 2)
        self.assertEqual(generateNote(note), "1 -")

        note.getDuration.return_value = (6, 2)
        self.assertEqual(generateNote(note), "1 - -")

        note.getDuration.return_value = (8, 2)
        self.assertEqual(generateNote(note), "1 - - -")

        note.getDuration.return_value = (1, 2)
        self.assertEqual(generateNote(note), "1/")

        note.getDuration.return_value = (1, 4)
        self.assertEqual(generateNote(note), "1//")

        note.getDuration.return_value = (1, 8)
        self.assertEqual(generateNote(note), "1///")

        # syncopated notes

        note.getDuration.return_value = (3, 2)
        self.assertEqual(generateNote(note), "1.")

        note.getDuration.return_value = (3, 4)
        self.assertEqual(generateNote(note), "1./")

    def test_rest(self):
        note = self.note

        note.isRest.return_value = True
        self.assertEqual(generateNote(note), "0")

        note.getDuration.return_value = (4, 2)
        self.assertEqual(generateNote(note), "0 -")

        note.getDuration.return_value = (1, 2)
        self.assertEqual(generateNote(note), "0/")

    def test_tie(self):
        note = self.note
        note.getDuration.return_value = (6, 6)

        note.isTieStart.return_value = True
        self.assertEqual(generateNote(note), "( 1")

        note.isTieStart.return_value = False
        note.isTieStop.return_value = True
        self.assertEqual(generateNote(note), "1 )")

        note.getDuration.return_value = (12, 6)
        self.assertEqual(generateNote(note), "1 ) -")

    def test_tuplet(self):
        note = self.note

        note.isTuplet.return_value = True
        note.getDuration.return_value = (2, 6) # 3 notes in 1 beats
        note.getDisplayedDuration.return_value = (3, 6)

        # tuplet start
        note.isTupletStart.return_value = True
        note.isTupletStop.return_value = False
        self.assertEqual(generateNote(note), "(y1/")

        # tuplet middle notes
        note.isTupletStart.return_value = False
        note.isTupletStop.return_value = False
        self.assertEqual(generateNote(note), "1/")

        # tuplet stop
        note.isTupletStart.return_value = False
        note.isTupletStop.return_value = True
        self.assertEqual(generateNote(note), "1/)")

        # 3 notes in 2 beats, should be displayed as quarter notes
        note.getDuration.return_value = (4, 6)
        note.getDisplayedDuration.return_value = (6, 6)
        note.isTupletStart.return_value = False
        note.isTupletStop.return_value = False
        self.assertEqual(generateNote(note), "1")

class TestTranspose(TestCase):

    def test_transpose_pitch(self):
        self.assertEqual(getTransposedPitch('C', 4, offset=3), ('D#', 4))
        self.assertEqual(getTransposedPitch('D', 4, offset=-3), ('B', 3))
        self.assertEqual(getTransposedPitch('Bb', 4, offset=2), ('C', 5))

    def test_transpose_offset(self):
        self.assertEqual(getTransposeOffsetToC('F'), -5)
        self.assertEqual(getTransposeOffsetToC('C'), 0)
        self.assertEqual(getTransposeOffsetToC('G'), 5)
        self.assertEqual(getTransposeOffsetToC('F#'), -6)
