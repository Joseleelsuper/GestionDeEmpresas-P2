"""Búsqueda aleatoria y recocido simulado para flow shop permutacional."""

import math
import random

from .flowshop import calculate_flowshop
from .local_search import _objective_value

MAX_RANDOM_ITERATIONS = 10_000
MAX_ANNEALING_EVALUATIONS = 10_000


def _score(processing: list[list[int]], sequence: list[int], objective: str) -> float:
    value = _objective_value(processing, sequence, objective)
    if value is None:
        raise RuntimeError("La evaluación completa no puede descartarse.")
    return value


def _metrics(result: dict) -> dict[str, int | float]:
    return {"cmax": result["cmax"], "fmax": result["fmax"]}


def _validate_objective(objective: str) -> None:
    if objective not in {"cmax", "fmax"}:
        raise ValueError("El objetivo debe ser Cmáx o Fmáx.")


def random_search(
    processing: list[list[int]],
    sequence: list[int],
    objective: str = "cmax",
    iterations: int = 1000,
) -> tuple[dict, dict]:
    """Muestrea permutaciones aleatorias y conserva la mejor encontrada."""
    _validate_objective(objective)
    if not 1 <= iterations <= MAX_RANDOM_ITERATIONS:
        raise ValueError(
            f"Las iteraciones aleatorias deben estar entre 1 y {MAX_RANDOM_ITERATIONS}."
        )

    initial_sequence = list(sequence)
    initial_result = calculate_flowshop(processing, initial_sequence)
    initial_value = _score(processing, initial_sequence, objective)
    best_sequence = initial_sequence
    best_value = initial_value

    for _ in range(iterations):
        candidate = random.sample(range(1, len(processing) + 1), len(processing))
        candidate_value = _score(processing, candidate, objective)
        if candidate_value < best_value:
            best_sequence = candidate
            best_value = candidate_value

    result = (
        initial_result
        if best_sequence == initial_sequence
        else calculate_flowshop(processing, best_sequence)
    )
    return result, {
        "method": "random_search",
        "objective": objective,
        "iterations": iterations,
        "max_iterations": iterations,
        "evaluations": iterations,
        "evaluation_label": "soluciones",
        "initial_value": initial_value,
        "final_value": best_value,
        "initial_metrics": _metrics(initial_result),
        "final_metrics": _metrics(result),
        "stop_reason": "iterations_complete",
    }


def simulated_annealing(
    processing: list[list[int]],
    sequence: list[int],
    objective: str = "cmax",
    neighborhood: str = "swap",
    initial_temperature: float = 1000,
    cooling_rate: float = 0.9,
    iterations_per_temperature: int = 50,
    final_temperature: float = 1,
) -> tuple[dict, dict]:
    """Aplica recocido simulado y devuelve la mejor solución visitada."""
    _validate_objective(objective)
    if neighborhood not in {"swap", "2opt"}:
        raise ValueError("El movimiento debe ser intercambio o inversión 2-opt.")
    if not math.isfinite(initial_temperature) or initial_temperature <= 0:
        raise ValueError("La temperatura inicial debe ser un número positivo finito.")
    if not math.isfinite(final_temperature) or final_temperature <= 0:
        raise ValueError("La temperatura final debe ser un número positivo finito.")
    if initial_temperature < final_temperature:
        raise ValueError("La temperatura inicial debe ser mayor o igual que la final.")
    if not math.isfinite(cooling_rate) or not 0 < cooling_rate < 1:
        raise ValueError("α debe estar entre 0 y 1, sin incluirlos.")
    if not 1 <= iterations_per_temperature <= MAX_ANNEALING_EVALUATIONS:
        raise ValueError(
            f"L(T) debe estar entre 1 y {MAX_ANNEALING_EVALUATIONS}."
        )

    temperature_levels = 0
    temperature = initial_temperature
    while temperature >= final_temperature:
        temperature_levels += 1
        if temperature_levels * iterations_per_temperature > MAX_ANNEALING_EVALUATIONS:
            raise ValueError(
                "La combinación de temperaturas y L(T) supera el límite de "
                f"{MAX_ANNEALING_EVALUATIONS} evaluaciones."
            )
        temperature *= cooling_rate

    current = list(sequence)
    initial_result = calculate_flowshop(processing, current)
    current_value = _score(processing, current, objective)
    initial_value = current_value
    best_sequence = current.copy()
    best_value = current_value
    iterations = 0
    stop_reason = "final_temperature"

    if len(current) < 2:
        stop_reason = "empty_neighborhood"
    else:
        temperature = initial_temperature
        for _ in range(temperature_levels):
            for _ in range(iterations_per_temperature):
                first, second = sorted(random.sample(range(len(current)), 2))
                candidate = current.copy()
                if neighborhood == "swap":
                    candidate[first], candidate[second] = candidate[second], candidate[first]
                else:
                    candidate[first : second + 1] = reversed(candidate[first : second + 1])

                candidate_value = _score(processing, candidate, objective)
                iterations += 1
                delta = candidate_value - current_value
                if delta < 0 or random.random() < math.exp(-delta / temperature):
                    current = candidate
                    current_value = candidate_value
                    if current_value < best_value:
                        best_sequence = current.copy()
                        best_value = current_value
            temperature *= cooling_rate

    result = (
        initial_result
        if best_sequence == sequence
        else calculate_flowshop(processing, best_sequence)
    )
    return result, {
        "method": "simulated_annealing",
        "objective": objective,
        "neighborhood": neighborhood,
        "initial_temperature": initial_temperature,
        "cooling_rate": cooling_rate,
        "iterations_per_temperature": iterations_per_temperature,
        "final_temperature": final_temperature,
        "temperature_levels": temperature_levels,
        "iterations": iterations,
        "max_iterations": temperature_levels * iterations_per_temperature,
        "evaluations": iterations,
        "evaluation_label": "propuestas",
        "initial_value": initial_value,
        "final_value": best_value,
        "initial_metrics": _metrics(initial_result),
        "final_metrics": _metrics(result),
        "stop_reason": stop_reason,
    }
