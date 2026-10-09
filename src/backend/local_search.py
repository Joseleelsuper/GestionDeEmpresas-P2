"""Búsqueda local para secuencias de un flow shop permutacional."""

import random
from collections.abc import Iterator

from .flowshop import calculate_flowshop

MAX_ITERATIONS = 1000
MAX_NEIGHBORS = 1000


def _objective_value(
    processing: list[list[int]],
    sequence: list[int],
    objective: str,
    cutoff: float | None = None,
) -> float | None:
    """Evalúa el objetivo y descarta prefijos que ya no pueden mejorarlo."""
    machine_count = len(processing[0])
    previous = [0] * machine_count
    current = [0] * machine_count
    total_completion = 0

    for job in sequence:
        for machine, duration in enumerate(processing[job - 1]):
            current[machine] = max(
                previous[machine], current[machine - 1] if machine else 0
            ) + duration
        previous, current = current, previous
        total_completion += previous[-1]
        if cutoff is not None:
            if objective == "cmax" and previous[-1] >= cutoff:
                return None
            if objective == "fmax" and total_completion >= cutoff * len(sequence):
                return None

    if objective == "cmax":
        return previous[-1]
    return total_completion / len(sequence)


def _pair_start(first: int, size: int) -> int:
    """Índice del primer par que empieza en ``first`` en el orden lexicográfico."""
    return first * (2 * size - first - 1) // 2


def _pair_at(index: int, size: int) -> tuple[int, int]:
    """Convierte un índice plano en una pareja de posiciones ``(i, j)``."""
    low, high = 0, size - 1
    while low + 1 < high:
        middle = (low + high) // 2
        if _pair_start(middle, size) <= index:
            low = middle
        else:
            high = middle
    return low, low + 1 + index - _pair_start(low, size)


def _neighbor_pairs(size: int, max_neighbors: int) -> Iterator[tuple[int, int]]:
    """Recorre todos los pares o una muestra uniforme de posiciones."""
    total = size * (size - 1) // 2
    if max_neighbors == 0 or max_neighbors >= total:
        for first in range(size - 1):
            for second in range(first + 1, size):
                yield first, second
        return

    for index in sorted(random.sample(range(total), max_neighbors)):
        yield _pair_at(index, size)


def local_search(
    processing: list[list[int]],
    sequence: list[int],
    objective: str = "cmax",
    strategy: str = "best",
    neighborhood: str = "swap",
    max_iterations: int = 100,
    max_neighbors: int = 100,
) -> tuple[dict, dict]:
    """Mejora una permutación evaluando una muestra configurable de vecinos.

    Args:
        processing (list[list[int]]): Duraciones por orden y máquina.
        sequence (list[int]): Secuencia inicial completa, con identificadores desde 1.
        objective (str): Medida a minimizar: ``cmax`` o ``fmax``.
        strategy (str): Selección del vecino: ``best``, ``first`` o ``random``.
        neighborhood (str): Movimiento ``swap`` o inversión ``2opt``.
        max_iterations (int): Máximo de exploraciones del vecindario, entre 1 y 1000.
        max_neighbors (int): Vecinos evaluados por iteración; 0 recorre todos.

    Returns:
        tuple[dict, dict]: Resultado de la secuencia final y resumen de búsqueda.

    Raises:
        ValueError: Si una opción no es válida o excede sus límites.
    """
    if objective not in {"cmax", "fmax"}:
        raise ValueError("El objetivo debe ser Cmáx o Fmáx.")
    if strategy not in {"best", "first", "random"}:
        raise ValueError("El submodo debe ser mejor, primer mejor o aleatorio.")
    if neighborhood not in {"swap", "2opt"}:
        raise ValueError("El vecindario debe ser intercambio o inversión 2-opt.")
    if not 1 <= max_iterations <= MAX_ITERATIONS:
        raise ValueError(f"El máximo de iteraciones debe estar entre 1 y {MAX_ITERATIONS}.")
    if not 0 <= max_neighbors <= MAX_NEIGHBORS:
        raise ValueError(
            f"Los vecinos por iteración deben estar entre 0 y {MAX_NEIGHBORS}."
        )

    current = list(sequence)
    current_value = _objective_value(processing, current, objective)
    initial_value = current_value
    initial_metrics = {
        "cmax": current_value if objective == "cmax" else _objective_value(processing, current, "cmax"),
        "fmax": round(
            current_value if objective == "fmax" else _objective_value(processing, current, "fmax"),
            2,
        ),
    }
    total_neighbors = len(current) * (len(current) - 1) // 2
    full_neighborhood = max_neighbors == 0 or max_neighbors >= total_neighbors
    iterations = 0
    neighbors_evaluated = 0
    stop_reason = "max_iterations"

    for _ in range(max_iterations):
        iterations += 1
        selected_sequence = None
        selected_value = current_value
        improving_neighbors = 0

        for first, second in _neighbor_pairs(len(current), max_neighbors):
            if neighborhood == "swap":
                current[first], current[second] = current[second], current[first]
            else:
                current[first : second + 1] = reversed(current[first : second + 1])

            cutoff = selected_value if strategy == "best" else current_value
            candidate_value = _objective_value(processing, current, objective, cutoff)
            neighbors_evaluated += 1
            if candidate_value is not None and candidate_value < current_value:
                improving_neighbors += 1
                if strategy == "first":
                    selected_sequence = current.copy()
                    selected_value = candidate_value
                elif strategy == "best":
                    if selected_sequence is None or candidate_value < selected_value:
                        selected_sequence = current.copy()
                        selected_value = candidate_value
                elif random.randrange(improving_neighbors) == 0:
                    selected_sequence = current.copy()
                    selected_value = candidate_value

            if neighborhood == "swap":
                current[first], current[second] = current[second], current[first]
            else:
                current[first : second + 1] = reversed(current[first : second + 1])

            if strategy == "first" and selected_sequence is not None:
                break

        if selected_sequence is None:
            stop_reason = "local_optimum" if full_neighborhood else "sample_no_improvement"
            break

        current = selected_sequence
        current_value = selected_value

    result = calculate_flowshop(processing, current)
    return result, {
        "method": "local_search",
        "objective": objective,
        "strategy": strategy,
        "neighborhood": neighborhood,
        "iterations": iterations,
        "max_iterations": max_iterations,
        "max_neighbors": max_neighbors,
        "neighbors_evaluated": neighbors_evaluated,
        "evaluations": neighbors_evaluated,
        "evaluation_label": "vecinos",
        "initial_value": initial_value,
        "final_value": current_value,
        "initial_metrics": initial_metrics,
        "final_metrics": {"cmax": result["cmax"], "fmax": result["fmax"]},
        "stop_reason": stop_reason,
    }
