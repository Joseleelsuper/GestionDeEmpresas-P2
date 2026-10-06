"""Búsqueda local para secuencias de un flow shop permutacional."""

import random

from .flowshop import calculate_flowshop

MAX_ITERATIONS = 1000


def local_search(
    processing: list[list[int]],
    sequence: list[int],
    objective: str = "cmax",
    strategy: str = "best",
    neighborhood: str = "swap",
    max_iterations: int = 100,
) -> tuple[dict, dict]:
    """Mejora una permutación mientras encuentre vecinos estrictamente mejores.

    Args:
        processing (list[list[int]]): Duraciones por orden y máquina.
        sequence (list[int]): Secuencia inicial completa, con identificadores desde 1.
        objective (str): Medida a minimizar: ``cmax`` o ``fmax``.
        strategy (str): Selección del vecino: ``best``, ``first`` o ``random``.
        neighborhood (str): Movimiento ``swap`` o inversión ``2opt``.
        max_iterations (int): Máximo de movimientos aceptados, entre 1 y 1000.

    Returns:
        tuple[dict, dict]: Resultado de la secuencia final y resumen de búsqueda.

    Raises:
        ValueError: Si una opción no es válida o el límite de iteraciones excede 1000.
    """
    if objective not in {"cmax", "fmax"}:
        raise ValueError("El objetivo debe ser Cmáx o Fmáx.")
    if strategy not in {"best", "first", "random"}:
        raise ValueError("El submodo debe ser mejor, primer mejor o aleatorio.")
    if neighborhood not in {"swap", "2opt"}:
        raise ValueError("El vecindario debe ser intercambio o inversión 2-opt.")
    if not 1 <= max_iterations <= MAX_ITERATIONS:
        raise ValueError(f"El máximo de iteraciones debe estar entre 1 y {MAX_ITERATIONS}.")

    current = list(sequence)
    current_result = calculate_flowshop(processing, current)

    def measure(result: dict) -> float:
        if objective == "cmax":
            return result["cmax"]
        return sum(row["completion"][-1] for row in result["rows"]) / result["jobs"]

    current_value = measure(current_result)
    initial_value = current_value
    iterations = 0
    stop_reason = "max_iterations"

    for _ in range(max_iterations):
        selected_result = None
        selected_value = current_value
        improving_neighbors = 0

        for first in range(len(current) - 1):
            for second in range(first + 1, len(current)):
                neighbor = current.copy()
                if neighborhood == "swap":
                    neighbor[first], neighbor[second] = neighbor[second], neighbor[first]
                else:
                    neighbor[first : second + 1] = neighbor[first : second + 1][::-1]

                candidate_result = calculate_flowshop(processing, neighbor)
                candidate_value = measure(candidate_result)
                if candidate_value >= current_value:
                    continue

                if strategy == "first":
                    selected_result, selected_value = candidate_result, candidate_value
                    break
                if strategy == "best":
                    if selected_result is None or candidate_value < selected_value:
                        selected_result, selected_value = candidate_result, candidate_value
                else:
                    improving_neighbors += 1
                    if random.randrange(improving_neighbors) == 0:
                        selected_result, selected_value = candidate_result, candidate_value

            if strategy == "first" and selected_result is not None:
                break

        if selected_result is None:
            stop_reason = "local_optimum"
            break

        current_result = selected_result
        current = current_result["sequence"]
        current_value = selected_value
        iterations += 1

    return current_result, {
        "objective": objective,
        "strategy": strategy,
        "neighborhood": neighborhood,
        "iterations": iterations,
        "max_iterations": max_iterations,
        "initial_value": initial_value,
        "final_value": current_value,
        "stop_reason": stop_reason,
    }
