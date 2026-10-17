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
    """Evalúa un objetivo y corta el cálculo si un prefijo ya no puede mejorarlo.

    Args:
        processing (list[list[int]]): Duraciones por orden y máquina.
        sequence (list[int]): Permutación de órdenes identificadas desde 1.
        objective (str): Medida a calcular: ``cmax`` o ``fmax``.
        cutoff (float | None): Umbral para descartar un prefijo; si es ``None``,
            se completa la evaluación.

    Returns:
        float | None: Valor del objetivo o ``None`` si el prefijo alcanza el corte.
    """
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
        if cutoff is not None and objective == "cmax" and previous[-1] >= cutoff:
            return None
        if (
            cutoff is not None
            and objective == "fmax"
            and total_completion >= cutoff * len(sequence)
        ):
            return None

    if objective == "cmax":
        return previous[-1]
    return total_completion / len(sequence)


def _score(processing: list[list[int]], sequence: list[int], objective: str) -> float:
    """Calcula el valor de una solución completa para el objetivo indicado.

    Args:
        processing (list[list[int]]): Duraciones por orden y máquina.
        sequence (list[int]): Permutación completa de órdenes desde 1.
        objective (str): Medida que se calcula: ``cmax`` o ``fmax``.

    Returns:
        float: Valor del objetivo para la permutación completa.

    Raises:
        RuntimeError: Si la evaluación completa se descarta inesperadamente.
    """
    value = _objective_value(processing, sequence, objective)
    if value is None:
        raise RuntimeError("La evaluación completa no puede descartarse.")
    return value


def _pair_start(first: int, size: int) -> int:
    """Calcula el índice plano del primer par que empieza en una posición.

    Args:
        first (int): Primera posición del par.
        size (int): Cantidad de posiciones de la permutación.

    Returns:
        int: Índice lexicográfico plano del primer par con ese inicio.
    """
    return first * (2 * size - first - 1) // 2


def _pair_at(index: int, size: int) -> tuple[int, int]:
    """Convierte el índice plano de un par en sus dos posiciones.

    Args:
        index (int): Índice del par en el orden lexicográfico.
        size (int): Cantidad de posiciones de la permutación.

    Returns:
        tuple[int, int]: Posiciones del par ``(i, j)`` con ``i < j``.
    """
    low, high = 0, size - 1
    while low + 1 < high:
        middle = (low + high) // 2
        if _pair_start(middle, size) <= index:
            low = middle
        else:
            high = middle
    return low, low + 1 + index - _pair_start(low, size)


def _neighbor_pairs(size: int, max_neighbors: int) -> Iterator[tuple[int, int]]:
    """Genera todos los pares de posiciones o una muestra uniforme de ellos.

    Args:
        size (int): Cantidad de posiciones de la permutación.
        max_neighbors (int): Cantidad máxima de pares; 0 solicita todos.

    Returns:
        Iterator[tuple[int, int]]: Pares de índices ``(i, j)`` con ``i < j``.
    """
    total = size * (size - 1) // 2
    if max_neighbors == 0 or max_neighbors >= total:
        for first in range(size - 1):
            for second in range(first + 1, size):
                yield first, second
        return

    for index in sorted(random.sample(range(total), max_neighbors)):
        yield _pair_at(index, size)


def _move(sequence: list[int], first: int, second: int, neighborhood: str) -> None:
    """Aplica en el sitio un intercambio o una inversión entre dos posiciones.

    Args:
        sequence (list[int]): Secuencia que se modificará.
        first (int): Índice inicial del movimiento.
        second (int): Índice final del movimiento.
        neighborhood (str): ``swap`` intercambia extremos; ``2opt`` invierte
            el segmento inclusivo entre ambos índices.

    Returns:
        None: La secuencia recibida se modifica directamente.
    """
    if neighborhood == "swap":
        sequence[first], sequence[second] = sequence[second], sequence[first]
    else:
        sequence[first : second + 1] = reversed(sequence[first : second + 1])


def _should_select(
    strategy: str,
    candidate_value: float,
    selected_value: float,
    improving_neighbors: int,
) -> bool:
    """Decide si una mejora pasa a ser la vecina seleccionada.

    Args:
        strategy (str): Criterio ``first``, ``best`` o selección aleatoria.
        candidate_value (float): Valor de la nueva secuencia.
        selected_value (float): Valor de la mejor vecina seleccionada hasta ahora.
        improving_neighbors (int): Número de mejoras vistas, para el muestreo aleatorio.

    Returns:
        bool: ``True`` si debe conservarse la nueva secuencia.
    """
    if strategy == "first":
        return True
    if strategy == "best":
        return candidate_value < selected_value
    return random.randrange(improving_neighbors) == 0


def _select_neighbor(
    processing: list[list[int]],
    current: list[int],
    current_value: float,
    objective: str,
    strategy: str,
    neighborhood: str,
    max_neighbors: int,
) -> tuple[list[int] | None, float, int]:
    """Explora vecinos, conserva una mejora según la estrategia y cuenta evaluaciones.

    Args:
        processing (list[list[int]]): Duraciones por orden y máquina.
        current (list[int]): Permutación que se está explorando.
        current_value (float): Valor del objetivo de la permutación actual.
        objective (str): Medida a minimizar: ``cmax`` o ``fmax``.
        strategy (str): Criterio de selección: ``best``, ``first`` o ``random``.
        neighborhood (str): Movimiento ``swap`` o inversión ``2opt``.
        max_neighbors (int): Vecinos a evaluar; 0 recorre el vecindario completo.

    Returns:
        tuple[list[int] | None, float, int]: Vecina elegida o ``None``, su valor
            y el número de vecinos evaluados.
    """
    selected_sequence = None
    selected_value = current_value
    improving_neighbors = 0
    evaluated = 0

    for first, second in _neighbor_pairs(len(current), max_neighbors):
        _move(current, first, second, neighborhood)
        cutoff = selected_value if strategy == "best" else current_value
        candidate_value = _objective_value(processing, current, objective, cutoff)
        evaluated += 1
        if candidate_value is not None and candidate_value < current_value:
            improving_neighbors += 1
            if _should_select(
                strategy, candidate_value, selected_value, improving_neighbors
            ):
                selected_sequence = current.copy()
                selected_value = candidate_value

        _move(current, first, second, neighborhood)
        if strategy == "first" and selected_sequence is not None:
            break

    return selected_sequence, selected_value, evaluated


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
        raise ValueError(
            f"El máximo de iteraciones debe estar entre 1 y {MAX_ITERATIONS}."
        )
    if not 0 <= max_neighbors <= MAX_NEIGHBORS:
        raise ValueError(
            f"Los vecinos por iteración deben estar entre 0 y {MAX_NEIGHBORS}."
        )

    current = list(sequence)
    current_value = _score(processing, current, objective)
    initial_value = current_value
    initial_metrics = {
        "cmax": (
            current_value
            if objective == "cmax"
            else _score(processing, current, "cmax")
        ),
        "fmax": round(
            current_value
            if objective == "fmax"
            else _score(processing, current, "fmax"),
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
        selected_sequence, selected_value, evaluated = _select_neighbor(
            processing,
            current,
            current_value,
            objective,
            strategy,
            neighborhood,
            max_neighbors,
        )
        neighbors_evaluated += evaluated

        if selected_sequence is None:
            stop_reason = (
                "local_optimum" if full_neighborhood else "sample_no_improvement"
            )
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
