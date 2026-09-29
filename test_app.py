"""Comprobaciones del parser y del cálculo de la matriz F."""

import unittest
from pathlib import Path
from zipfile import ZipFile

from app import EXAMPLES, list_examples
from src.backend.flowshop import calculate_flowshop
from src.backend.instance import parse_instance
from src.backend.sequence import parse_sequence

ROOT = Path(__file__).resolve().parent


class FlowShopTests(unittest.TestCase):
    def test_extracted_examples_match_archive(self):
        with ZipFile(ROOT / "docs" / "ProblemasFlowShopPermutacional.zip") as archive:
            examples = [name for name in archive.namelist() if name.lower().endswith(".txt")]
            self.assertEqual(len(list_examples()), 13)
            for name in examples:
                self.assertEqual((EXAMPLES / name).read_bytes(), archive.read(name))
                parse_instance((EXAMPLES / name).read_text(encoding="utf-8-sig"))

    def test_first_class_example(self):
        processing = parse_instance((EXAMPLES / "ejem_clase1.txt").read_text())
        result = calculate_flowshop(processing, [4, 2, 5, 1, 3])
        self.assertEqual([row["completion"] for row in result["rows"]], [[0, 6], [2, 13], [10, 17], [15, 20], [24, 25]])
        self.assertEqual(result["cmax"], 25)
        self.assertEqual(result["fmax"], 25)

    def test_second_class_example(self):
        processing = parse_instance((EXAMPLES / "ejem_clase2.txt").read_text())
        result = calculate_flowshop(processing, [1, 3, 4, 2, 5])
        self.assertEqual(result["cmax"], 41)

    def test_sequence_validation_and_random_order(self):
        self.assertEqual(parse_sequence("4, 2 5,1,3", 5), [4, 2, 5, 1, 3])
        self.assertEqual(sorted(parse_sequence("", 5)), [1, 2, 3, 4, 5])
        for value in ("1 2 3 4 4", "1 2 3", "1 2 3 4 6", "a b c d e"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_sequence(value, 5)

    def test_invalid_instances_are_rejected(self):
        for text in (
            "0 2",
            "2 2\n0 1 1 2",
            "1 2\n0 1 0 2",
            "1 1\n0 -1",
            "10001 1",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_instance(text)


if __name__ == "__main__":
    unittest.main()
