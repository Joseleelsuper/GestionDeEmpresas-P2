"""Algoritmo genético con operadores válidos para secuencias permutacionales."""

import math
import random
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass

from .flowshop import calculate_flowshop
from .local_search import _score

MAX_GENETIC_EVALUATIONS = 10_000
MAX_GENETIC_OPERATIONS = 20_000_000


@dataclass(frozen=True)
class GeneticOptions:
    """Parámetros de población, operadores, reemplazo y parada."""

    population_size: int = 40
    generations: int = 100
    selection: str = "tournament"
    tournament_size: int = 3
    truncation_fraction: float = 0.5
    crossover: str = "ox"
    crossover_probability: float = 0.8
    mutation: str = "swap"
    mutation_probability: float = 0.1
    replacement: str = "generational"
    elite_count: int = 1
    stagnation_generations: int = 20
    time_limit_seconds: float = 10
    target_value: float | None = None


@dataclass
class _EvolutionState:
    """Estado mutable de la población y del criterio de parada."""

    population: list[tuple[list[int], float]]
    best_sequence: list[int]
    best_value: float
    generations_run: int = 0
    stagnant: int = 0
    stop_reason: str = "max_generations"


def _validate_population(options: GeneticOptions, jobs: int, machines: int) -> None:
    """Valida el tamaño, la duración y el coste máximo de la evolución.

    Args:
        options (GeneticOptions): Configuración que contiene población y generaciones.
        jobs (int): Número de órdenes de la instancia.
        machines (int): Número de máquinas de la instancia.

    Returns:
        None: Termina sin resultado si se respetan los límites.

    Raises:
        ValueError: Si un parámetro o el presupuesto de cálculo queda fuera de rango.
    """
    if not 2 <= options.population_size <= 200:
        raise ValueError("La población debe tener entre 2 y 200 individuos.")
    if not 1 <= options.generations <= 1000:
        raise ValueError("Las generaciones deben estar entre 1 y 1000.")
    if options.replacement not in {"generational", "steady"}:
        raise ValueError("El reemplazo debe ser generacional o estacionario.")
    if not 0 <= options.elite_count < options.population_size:
        raise ValueError("La élite debe ser menor que la población y no negativa.")
    offspring = options.population_size - options.elite_count if options.replacement == "generational" else options.population_size
    evaluations = options.population_size + offspring * options.generations
    if evaluations > MAX_GENETIC_EVALUATIONS or evaluations * jobs * machines > MAX_GENETIC_OPERATIONS:
        raise ValueError("La población y las generaciones superan el límite de cálculo; reduce uno de los dos valores.")


def _validate_selection(options: GeneticOptions) -> None:
    """Valida el método de selección y los parámetros que utiliza.

    Args:
        options (GeneticOptions): Configuración de selección de la población.

    Returns:
        None: Termina sin resultado si la selección es válida.

    Raises:
        ValueError: Si el método o el tamaño del torneo o la fracción son inválidos.
    """
    if options.selection not in {"tournament", "roulette", "average", "truncation"}:
        raise ValueError("Elige torneo, ruleta, media o truncamiento para la selección.")
    if options.selection == "tournament" and not 2 <= options.tournament_size <= options.population_size:
        raise ValueError("El tamaño del torneo debe estar entre 2 y el tamaño de la población.")
    if not math.isfinite(options.truncation_fraction) or not 0 < options.truncation_fraction <= 1:
        raise ValueError("La fracción de truncamiento debe ser mayor que 0 y como máximo 1.")


def _validate_operators(options: GeneticOptions) -> None:
    """Valida los operadores de cruce y mutación y sus probabilidades.

    Args:
        options (GeneticOptions): Configuración de cruce y mutación.

    Returns:
        None: Termina sin resultado si los operadores son válidos.

    Raises:
        ValueError: Si un operador no está admitido o una probabilidad queda fuera de
            ``[0, 1]``.
    """
    if options.crossover not in {"ox", "pmx", "cx"}:
        raise ValueError("El cruce debe ser OX, PMX o CX.")
    if options.mutation not in {"swap", "insert", "invert"}:
        raise ValueError("La mutación debe ser intercambio, inserción o inversión.")
    for value, label in (
        (options.crossover_probability, "La probabilidad de cruce"),
        (options.mutation_probability, "La probabilidad de mutación"),
    ):
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{label} debe estar entre 0 y 1.")


def _validate_stopping(options: GeneticOptions) -> None:
    """Valida los límites de parada por estancamiento, tiempo y valor objetivo.

    Args:
        options (GeneticOptions): Configuración de los criterios de parada.

    Returns:
        None: Termina sin resultado si los límites son válidos.

    Raises:
        ValueError: Si un límite no es finito o queda fuera de su rango permitido.
    """
    if not 0 <= options.stagnation_generations <= 1000:
        raise ValueError("Las generaciones sin mejora deben estar entre 0 y 1000.")
    if not math.isfinite(options.time_limit_seconds) or not 0 <= options.time_limit_seconds <= 60:
        raise ValueError("El límite de tiempo debe estar entre 0 y 60 segundos.")
    if options.target_value is not None and (
        not math.isfinite(options.target_value) or options.target_value < 0
    ):
        raise ValueError("El objetivo conocido debe ser un número finito no negativo.")


def _validate(options: GeneticOptions, jobs: int, machines: int) -> None:
    """Valida la configuración completa antes de evaluar individuos.

    Args:
        options (GeneticOptions): Opciones de evolución y de parada.
        jobs (int): Número de órdenes de la instancia.
        machines (int): Número de máquinas de la instancia.

    Returns:
        None: Termina sin resultado si todos los grupos de opciones son válidos.

    Raises:
        ValueError: Si cualquiera de los parámetros genéticos no es válido.
    """
    _validate_population(options, jobs, machines)
    _validate_selection(options)
    _validate_operators(options)
    _validate_stopping(options)


def _select(population: list[tuple[list[int], float]], options: GeneticOptions) -> list[int]:
    """Selecciona una secuencia progenitora según el método configurado.

    Args:
        population (list[tuple[list[int], float]]): Individuos y sus costes.
        options (GeneticOptions): Método y parámetros de selección.

    Returns:
        list[int]: Secuencia seleccionada como padre.
    """
    if options.selection == "tournament":
        return min(random.sample(population, options.tournament_size), key=lambda item: item[1])[0]
    ranked = sorted(population, key=lambda item: item[1])
    if options.selection == "roulette":
        return random.choices(ranked, weights=range(len(ranked), 0, -1))[0][0]
    if options.selection == "average":
        average = sum(value for _, value in population) / len(population)
        return random.choice([item for item in population if item[1] <= average])[0]
    count = max(1, math.ceil(len(ranked) * options.truncation_fraction))
    return random.choice(ranked[:count])[0]


def _ox(parent: list[int], donor: list[int], start: int, end: int) -> list[int]:
    """Aplica el cruce OX conservando un segmento y el orden del padre donante.

    Args:
        parent (list[int]): Padre del que se copia el segmento.
        donor (list[int]): Padre que determina el orden de los genes restantes.
        start (int): Índice inicial inclusivo del segmento.
        end (int): Índice final exclusivo del segmento.

    Returns:
        list[int]: Permutación hija producida por el operador OX.
    """
    child = [0] * len(parent)
    child[start:end] = parent[start:end]
    segment = set(parent[start:end])
    remaining = (gene for gene in donor if gene not in segment)
    for index in list(range(end, len(parent))) + list(range(start)):
        child[index] = next(remaining)
    return child


def _pmx(parent: list[int], donor: list[int], start: int, end: int) -> list[int]:
    """Aplica PMX y resuelve duplicados con la correspondencia del segmento.

    Args:
        parent (list[int]): Padre cuya permutación se copia inicialmente.
        donor (list[int]): Padre que aporta el segmento de cruce.
        start (int): Índice inicial inclusivo del segmento.
        end (int): Índice final exclusivo del segmento.

    Returns:
        list[int]: Permutación hija producida por el operador PMX.
    """
    child = parent.copy()
    segment = set(parent[start:end])
    correspondence = dict(zip(parent[start:end], donor[start:end]))
    for index in list(range(start)) + list(range(end, len(parent))):
        gene = donor[index]
        while gene in segment:
            gene = correspondence[gene]
        child[index] = gene
    return child


def _cx(first: list[int], second: list[int]) -> tuple[list[int], list[int]]:
    """Aplica cruce por ciclos y construye dos permutaciones hijas complementarias.

    Args:
        first (list[int]): Primera permutación progenitora.
        second (list[int]): Segunda permutación progenitora.

    Returns:
        tuple[list[int], list[int]]: Dos hijos que heredan ciclos de los padres.
    """
    positions = {gene: index for index, gene in enumerate(first)}
    children = ([0] * len(first), [0] * len(first))
    visited = set()
    for start in range(len(first)):
        if start in visited:
            continue
        source, other = (first, second) if random.getrandbits(1) else (second, first)
        index = start
        while index not in visited:
            visited.add(index)
            children[0][index] = source[index]
            children[1][index] = other[index]
            index = positions[second[index]]
    return children


def _crossover(first: list[int], second: list[int], method: str) -> tuple[list[int], list[int]]:
    """Aplica el operador de cruce indicado a dos permutaciones progenitoras.

    Args:
        first (list[int]): Primera secuencia progenitora.
        second (list[int]): Segunda secuencia progenitora.
        method (str): Operador ``ox``, ``pmx`` o ``cx``.

    Returns:
        tuple[list[int], list[int]]: Dos secuencias hijas; para menos de dos genes,
            devuelve copias de los padres.
    """
    if len(first) < 2:
        return first.copy(), second.copy()
    if method == "cx":
        return _cx(first, second)
    start, last = sorted(random.sample(range(len(first)), 2))
    operator = _ox if method == "ox" else _pmx
    return operator(first, second, start, last + 1), operator(second, first, start, last + 1)


def _mutate(sequence: list[int], method: str) -> None:
    """Aplica una mutación de intercambio, inserción o inversión en el sitio.

    Args:
        sequence (list[int]): Permutación que se modificará.
        method (str): Mutación ``swap``, ``insert`` o ``invert``.

    Returns:
        None: La secuencia se modifica directamente; si tiene menos de dos genes,
            no se modifica.
    """
    if len(sequence) < 2:
        return
    first, second = random.sample(range(len(sequence)), 2)
    if method == "swap":
        sequence[first], sequence[second] = sequence[second], sequence[first]
    elif method == "insert":
        sequence.insert(second, sequence.pop(first))
    else:
        first, second = sorted((first, second))
        sequence[first : second + 1] = reversed(sequence[first : second + 1])


def _make_children(
    population: list[tuple[list[int], float]], options: GeneticOptions
) -> tuple[list[int], list[int]]:
    """Selecciona dos padres y genera dos hijos mediante cruce o copia.

    Args:
        population (list[tuple[list[int], float]]): Individuos y costes actuales.
        options (GeneticOptions): Métodos y probabilidad de cruce.

    Returns:
        tuple[list[int], list[int]]: Dos hijos, cruzados o copiados de los padres.
    """
    first = _select(population, options)
    second = _select(population, options)
    if random.random() < options.crossover_probability:
        return _crossover(first, second, options.crossover)
    return first.copy(), second.copy()


def _process_child(
    child: list[int],
    options: GeneticOptions,
    state: _EvolutionState,
    evaluate: Callable[[list[int]], float],
    next_population: list[tuple[list[int], float]],
) -> bool:
    """Muta y evalúa un hijo, actualiza estado y población, e informa de su mejora.

    Args:
        child (list[int]): Secuencia hija que se incorporará.
        options (GeneticOptions): Probabilidad de mutación y tipo de reemplazo.
        state (_EvolutionState): Población y mejor individuo conocidos.
        evaluate (Callable[[list[int]], float]): Función que calcula el coste del hijo.
        next_population (list[tuple[list[int], float]]): Nueva población generacional.

    Returns:
        bool: ``True`` si el hijo mejora el mejor coste encontrado hasta ahora.
    """
    if random.random() < options.mutation_probability:
        _mutate(child, options.mutation)
    value = evaluate(child)
    improved = value < state.best_value
    if improved:
        state.best_sequence, state.best_value = child.copy(), value
    if options.replacement == "generational":
        next_population.append((child, value))
    else:
        ranked = sorted(
            range(len(state.population)),
            key=lambda index: state.population[index][1],
        )
        state.population[ranked[-1]] = (child, value)
    if options.target_value is not None and state.best_value <= options.target_value:
        state.stop_reason = "target_reached"
    return improved


def _add_offspring(
    children: tuple[list[int], ...],
    options: GeneticOptions,
    state: _EvolutionState,
    evaluate: Callable[[list[int]], float],
    next_population: list[tuple[list[int], float]],
) -> tuple[int, bool]:
    """Incorpora hijos hasta completar el lote o alcanzar un criterio de parada.

    Args:
        children (tuple[list[int], ...]): Hijos disponibles para incorporar.
        options (GeneticOptions): Configuración del reemplazo y del objetivo.
        state (_EvolutionState): Estado que se actualiza con cada hijo.
        evaluate (Callable[[list[int]], float]): Función que calcula el coste.
        next_population (list[tuple[list[int], float]]): Población de la generación.

    Returns:
        tuple[int, bool]: Número de hijos procesados y si alguno mejoró el mejor coste.
    """
    produced = 0
    improved = False
    for child in children:
        if _process_child(child, options, state, evaluate, next_population):
            improved = True
        produced += 1
        if state.stop_reason != "max_generations":
            break
    return produced, improved


def _run_generation(
    options: GeneticOptions,
    state: _EvolutionState,
    evaluate: Callable[[list[int]], float],
    deadline: float | None,
    elite_count: int,
) -> bool:
    """Construye una generación y detiene la producción si vence el plazo.

    Args:
        options (GeneticOptions): Tamaño, reemplazo y criterios de evolución.
        state (_EvolutionState): Población y métricas que se actualizarán.
        evaluate (Callable[[list[int]], float]): Función que calcula el coste.
        deadline (float | None): Instante límite de ``time.monotonic`` o ``None``.
        elite_count (int): Individuos de élite que pasan sin cambios a la generación.

    Returns:
        bool: ``True`` si esta generación encontró una mejora del mejor coste.
    """
    next_population = sorted(state.population, key=lambda item: item[1])[:elite_count]
    needed = options.population_size - elite_count
    produced = 0
    improved = False
    while produced < needed:
        if deadline is not None and time.monotonic() >= deadline:
            state.stop_reason = "time_limit"
            break
        children = _make_children(state.population, options)
        added, better = _add_offspring(
            children[: needed - produced], options, state, evaluate, next_population
        )
        produced += added
        improved = improved or better
        if state.stop_reason != "max_generations":
            break
    if state.stop_reason == "max_generations" and options.replacement == "generational":
        state.population = next_population
    return improved


def _evolve(
    options: GeneticOptions,
    state: _EvolutionState,
    evaluate: Callable[[list[int]], float],
    deadline: float | None,
    elite_count: int,
) -> None:
    """Evoluciona la población hasta alcanzar un criterio de parada.

    Args:
        options (GeneticOptions): Límites de generaciones y condiciones de parada.
        state (_EvolutionState): Población y estado de búsqueda que se actualizarán.
        evaluate (Callable[[list[int]], float]): Función que calcula el coste.
        deadline (float | None): Instante límite de ``time.monotonic`` o ``None``.
        elite_count (int): Individuos de élite conservados en cada generación.

    Returns:
        None: Actualiza el estado, incluido el número de generaciones y el motivo
            de parada.
    """
    if options.target_value is not None and state.best_value <= options.target_value:
        state.stop_reason = "target_reached"
        return
    for _ in range(options.generations):
        if deadline is not None and time.monotonic() >= deadline:
            state.stop_reason = "time_limit"
            break
        state.generations_run += 1
        improved = _run_generation(options, state, evaluate, deadline, elite_count)
        if state.stop_reason != "max_generations":
            break
        state.stagnant = 0 if improved else state.stagnant + 1
        if (
            options.stagnation_generations
            and state.stagnant >= options.stagnation_generations
        ):
            state.stop_reason = "stagnation"
            break


def genetic_algorithm(
    processing: list[list[int]],
    sequence: list[int],
    objective: str = "cmax",
    options: GeneticOptions | None = None,
) -> tuple[dict, dict]:
    """Optimiza una permutación con un algoritmo genético configurable.

    Args:
        processing (list[list[int]]): Duraciones por orden y máquina.
        sequence (list[int]): Secuencia inicial completa, con identificadores desde 1.
        objective (str): Medida a minimizar: ``cmax`` o ``fmax``.
        options (GeneticOptions | None): Parámetros de población, operadores y parada;
            si se omite, se utilizan los valores predeterminados.

    Returns:
        tuple[dict, dict]: Resultado de la mejor secuencia y resumen de la evolución.

    Raises:
        ValueError: Si el objetivo o alguno de los parámetros genéticos no es válido.
    """
    options = options or GeneticOptions()
    if objective not in {"cmax", "fmax"}:
        raise ValueError("El objetivo debe ser Cmáx o Fmáx.")
    _validate(options, len(processing), len(processing[0]))

    cache: dict[tuple[int, ...], float] = {}

    def evaluate(candidate: list[int]) -> float:
        """Evalúa una permutación y reutiliza costes ya calculados.

        Args:
            candidate (list[int]): Permutación de órdenes que se va a evaluar.

        Returns:
            float: Valor del objetivo para la permutación.
        """
        key = tuple(candidate)
        if key not in cache:
            cache[key] = _score(processing, candidate, objective)
        return cache[key]

    initial_result = calculate_flowshop(processing, sequence)
    initial_value = evaluate(sequence)
    sequences = [list(sequence)] + [
        random.sample(range(1, len(processing) + 1), len(processing))
        for _ in range(options.population_size - 1)
    ]
    population = [(candidate, evaluate(candidate)) for candidate in sequences]
    best_sequence, best_value = min(population, key=lambda item: item[1])
    state = _EvolutionState(population, best_sequence.copy(), best_value)
    deadline = time.monotonic() + options.time_limit_seconds if options.time_limit_seconds else None
    elite_count = options.elite_count if options.replacement == "generational" else 0
    _evolve(options, state, evaluate, deadline, elite_count)

    result = calculate_flowshop(processing, state.best_sequence)
    return result, {
        "method": "genetic_algorithm",
        "objective": objective,
        **asdict(options),
        "elite_count": elite_count,
        "iterations": state.generations_run,
        "max_iterations": options.generations,
        "evaluations": len(cache),
        "evaluation_label": "evaluaciones únicas",
        "initial_value": initial_value,
        "final_value": state.best_value,
        "initial_metrics": {"cmax": initial_result["cmax"], "fmax": initial_result["fmax"]},
        "final_metrics": {"cmax": result["cmax"], "fmax": result["fmax"]},
        "stop_reason": state.stop_reason,
    }
