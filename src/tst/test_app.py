"""Comprobaciones del parser y del cálculo de la matriz F."""

import unittest

from app import EXAMPLES, list_examples
from src.backend.flowshop import calculate_flowshop
from src.backend.instance import parse_instance
from src.backend.sequence import parse_sequence
from src.tst.flow_shop_test import DOC1, DOC2, EJEM_CLASE1

REFERENCE_EXAMPLES = (
    ("ejem_clase1.txt", EJEM_CLASE1),
    ("Doc1.txt", DOC1),
    ("Doc2.txt", DOC2),
)


class FlowShopTests(unittest.TestCase):
    def test_extracted_examples_are_available_and_parseable(self):
        example_files = sorted(EXAMPLES.glob("*.txt"))
        self.assertEqual(len(example_files), 13)
        self.assertEqual(set(list_examples()), {path.name for path in example_files})
        for path in example_files:
            with self.subTest(example=path.name):
                parse_instance(path.read_text(encoding="utf-8-sig"))

    def test_reference_examples_match_completion_matrices_and_metrics(self):
        for filename, (sequence, expected_completion) in REFERENCE_EXAMPLES:
            with self.subTest(example=filename):
                processing = parse_instance(
                    (EXAMPLES / filename).read_text(encoding="utf-8-sig")
                )
                result = calculate_flowshop(processing, sequence)
                self.assertEqual([row["job"] for row in result["rows"]], sequence)
                ordered_rows = sorted(result["rows"], key=lambda row: row["job"])
                self.assertEqual(
                    [row["completion"] for row in ordered_rows], expected_completion
                )
                end_times = [row[-1] for row in expected_completion]
                self.assertEqual(result["cmax"], max(end_times))
                self.assertAlmostEqual(
                    result["fmax"], sum(end_times) / len(end_times), places=2
                )

    def test_first_class_example(self):
        processing = parse_instance((EXAMPLES / "ejem_clase1.txt").read_text())
        result = calculate_flowshop(processing, [4, 2, 5, 1, 3])
        self.assertEqual([row["completion"] for row in result["rows"]], [[0, 6], [2, 13], [10, 17], [15, 20], [24, 25]])
        self.assertEqual(result["cmax"], 25)
        self.assertEqual(result["fmax"], 16.2)

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
