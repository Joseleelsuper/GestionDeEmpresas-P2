"""Regresiones de los algoritmos y del despacho de búsqueda."""

import random
import unittest
from dataclasses import replace

from fastapi import HTTPException

from app import EXAMPLES
from src.backend.endpoints.solve import SearchOptions, solve_instance
from src.backend.flowshop import calculate_flowshop
from src.backend.instance import parse_instance
from src.backend.local_search import local_search
from src.backend.metaheuristics import simulated_annealing


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Carga una instancia y una secuencia compartidas por las pruebas."""
        cls.processing = parse_instance((EXAMPLES / "ejem_clase1.txt").read_text())
        cls.sequence = [1, 2, 3, 4, 5]

    def test_full_local_search_stops_at_a_local_optimum(self):
        """Comprueba que cada estrategia termina en un óptimo del vecindario completo."""
        original = calculate_flowshop(self.processing, self.sequence)["cmax"]
        for strategy in ("best", "first", "random"):
            for neighborhood in ("swap", "2opt"):
                with self.subTest(strategy=strategy, neighborhood=neighborhood):
                    random.seed(7)
                    result, search = local_search(
                        self.processing,
                        self.sequence,
                        "cmax",
                        strategy,
                        neighborhood,
                        10,
                        0,
                    )
                    self.assertEqual(self.sequence, [1, 2, 3, 4, 5])
                    self.assertLessEqual(result["cmax"], original)
                    self.assertEqual(search["stop_reason"], "local_optimum")
                    self.assertEqual(search["final_value"], result["cmax"])

                    for first in range(len(self.sequence) - 1):
                        for second in range(first + 1, len(self.sequence)):
                            neighbor = result["sequence"].copy()
                            if neighborhood == "swap":
                                neighbor[first], neighbor[second] = (
                                    neighbor[second], neighbor[first]
                                )
                            else:
                                neighbor[first : second + 1] = reversed(
                                    neighbor[first : second + 1]
                                )
                            self.assertGreaterEqual(
                                calculate_flowshop(self.processing, neighbor)["cmax"],
                                result["cmax"],
                            )

    def test_annealing_keeps_best_solution_and_counts_proposals(self):
        """Comprueba que el recocido devuelve su mejor visita y cuenta propuestas."""
        original = calculate_flowshop(self.processing, self.sequence)["cmax"]
        for neighborhood in ("swap", "2opt"):
            with self.subTest(neighborhood=neighborhood):
                random.seed(7)
                result, search = simulated_annealing(
                    self.processing, self.sequence, "cmax", neighborhood, 10, 0.5, 3, 1
                )
                self.assertEqual(self.sequence, [1, 2, 3, 4, 5])
                self.assertLessEqual(result["cmax"], original)
                self.assertEqual(search["temperature_levels"], 4)
                self.assertEqual(search["evaluations"], 12)
                self.assertEqual(search["final_value"], result["cmax"])

    def test_fmax_local_search_keeps_numeric_metrics(self):
        """Comprueba que búsqueda local conserva métricas numéricas para Fmáx."""
        result, search = local_search(
            self.processing, self.sequence, "fmax", "best", "2opt", 10, 0
        )
        self.assertIsInstance(search["initial_metrics"]["fmax"], float)
        self.assertLessEqual(search["final_value"], search["initial_value"])
        self.assertEqual(round(search["final_value"], 2), result["fmax"])

    def test_annealing_handles_empty_neighborhood_and_rejects_large_schedule(self):
        """Comprueba el vecindario vacío y el rechazo de un calendario excesivo."""
        result, search = simulated_annealing(
            [[4]], [1], initial_temperature=1, final_temperature=1
        )
        self.assertEqual(result["sequence"], [1])
        self.assertEqual(search["evaluations"], 0)
        self.assertEqual(search["stop_reason"], "empty_neighborhood")
        with self.assertRaisesRegex(ValueError, "supera el límite"):
            simulated_annealing(
                self.processing, self.sequence, iterations_per_temperature=10_000
            )


class SolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_options_preserve_dispatch_and_refinement(self):
        """Comprueba el cálculo directo, el despacho y el refinamiento de búsqueda."""
        options = SearchOptions(
            "calculate", "cmax", "best", "swap", 10, 0, 5, 10, 0.5, 3, 1, False
        )
        direct = await solve_instance(
            "ejem_clase1.txt", "1,2,3,4,5", None, EXAMPLES, options
        )
        self.assertNotIn("search", direct)

        random.seed(7)
        annealed = await solve_instance(
            "ejem_clase1.txt",
            "1,2,3,4,5",
            None,
            EXAMPLES,
            replace(
                options, algorithm="simulated_annealing", refine_with_local_search=True
            ),
        )
        self.assertEqual(annealed["search"]["method"], "simulated_annealing")
        self.assertTrue(annealed["search"]["refined_with_local_search"])
        self.assertEqual(annealed["search"]["final_value"], annealed["cmax"])

        with self.assertRaises(HTTPException) as error:
            await solve_instance(
                "ejem_clase1.txt", "1,2,3,4,5", None, EXAMPLES,
                replace(options, algorithm="unknown"),
            )
        self.assertEqual(error.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
