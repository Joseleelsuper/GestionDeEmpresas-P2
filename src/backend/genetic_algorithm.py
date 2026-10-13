"""Algoritmo genético con operadores válidos para secuencias permutacionales."""

import math
import random
import time
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


def _validate(options: GeneticOptions, jobs: int, machines: int) -> None:
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
    if options.selection not in {"tournament", "roulette", "average", "truncation"}:
        raise ValueError("Elige torneo, ruleta, media o truncamiento para la selección.")
    if options.selection == "tournament" and not 2 <= options.tournament_size <= options.population_size:
        raise ValueError("El tamaño del torneo debe estar entre 2 y el tamaño de la población.")
    if not math.isfinite(options.truncation_fraction) or not 0 < options.truncation_fraction <= 1:
        raise ValueError("La fracción de truncamiento debe ser mayor que 0 y como máximo 1.")
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
    if not 0 <= options.stagnation_generations <= 1000:
        raise ValueError("Las generaciones sin mejora deben estar entre 0 y 1000.")
    if not math.isfinite(options.time_limit_seconds) or not 0 <= options.time_limit_seconds <= 60:
        raise ValueError("El límite de tiempo debe estar entre 0 y 60 segundos.")
    if options.target_value is not None and (
        not math.isfinite(options.target_value) or options.target_value < 0
    ):
        raise ValueError("El objetivo conocido debe ser un número finito no negativo.")


def _select(population: list[tuple[list[int], float]], options: GeneticOptions) -> list[int]:
    """Selecciona un padre usando la presión indicada sobre costes mínimos."""
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
    """Conserva un segmento y rellena el resto en el orden del otro padre."""
    child = [0] * len(parent)
    child[start:end] = parent[start:end]
    segment = set(parent[start:end])
    remaining = (gene for gene in donor if gene not in segment)
    for index in list(range(end, len(parent))) + list(range(start)):
        child[index] = next(remaining)
    return child


def _pmx(parent: list[int], donor: list[int], start: int, end: int) -> list[int]:
    """Resuelve duplicados mediante la correspondencia del segmento PMX."""
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
    """Copia ciclos completos de cada padre y genera hijos complementarios."""
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
    if len(first) < 2:
        return first.copy(), second.copy()
    if method == "cx":
        return _cx(first, second)
    start, last = sorted(random.sample(range(len(first)), 2))
    operator = _ox if method == "ox" else _pmx
    return operator(first, second, start, last + 1), operator(second, first, start, last + 1)


def _mutate(sequence: list[int], method: str) -> None:
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


def genetic_algorithm(
    processing: list[list[int]],
    sequence: list[int],
    objective: str = "cmax",
    options: GeneticOptions | None = None,
) -> tuple[dict, dict]:
    """Evoluciona permutaciones y devuelve la mejor secuencia visitada."""
    options = options or GeneticOptions()
    if objective not in {"cmax", "fmax"}:
        raise ValueError("El objetivo debe ser Cmáx o Fmáx.")
    _validate(options, len(processing), len(processing[0]))

    cache: dict[tuple[int, ...], float] = {}

    def evaluate(candidate: list[int]) -> float:
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
    best_sequence = best_sequence.copy()
    generations_run = 0
    stagnant = 0
    stop_reason = "max_generations"
    deadline = time.monotonic() + options.time_limit_seconds if options.time_limit_seconds else None
    elite_count = options.elite_count if options.replacement == "generational" else 0

    if options.target_value is not None and best_value <= options.target_value:
        stop_reason = "target_reached"
    else:
        for _ in range(options.generations):
            if deadline is not None and time.monotonic() >= deadline:
                stop_reason = "time_limit"
                break
            generations_run += 1
            improved = False
            next_population = sorted(population, key=lambda item: item[1])[:elite_count]
            needed = options.population_size - elite_count
            produced = 0
            while produced < needed:
                if deadline is not None and time.monotonic() >= deadline:
                    stop_reason = "time_limit"
                    break
                first = _select(population, options)
                second = _select(population, options)
                children = (
                    _crossover(first, second, options.crossover)
                    if random.random() < options.crossover_probability
                    else (first.copy(), second.copy())
                )
                for child in children[: needed - produced]:
                    if random.random() < options.mutation_probability:
                        _mutate(child, options.mutation)
                    value = evaluate(child)
                    produced += 1
                    if value < best_value:
                        best_sequence, best_value = child.copy(), value
                        improved = True
                    if options.replacement == "generational":
                        next_population.append((child, value))
                    else:
                        ranked = sorted(range(len(population)), key=lambda index: population[index][1])
                        population[ranked[-1]] = (child, value)
                    if options.target_value is not None and best_value <= options.target_value:
                        stop_reason = "target_reached"
                        break
                if stop_reason != "max_generations":
                    break
            if stop_reason != "max_generations":
                break
            if options.replacement == "generational":
                population = next_population
            stagnant = 0 if improved else stagnant + 1
            if options.stagnation_generations and stagnant >= options.stagnation_generations:
                stop_reason = "stagnation"
                break

    result = calculate_flowshop(processing, best_sequence)
    return result, {
        "method": "genetic_algorithm",
        "objective": objective,
        **asdict(options),
        "elite_count": elite_count,
        "iterations": generations_run,
        "max_iterations": options.generations,
        "evaluations": len(cache),
        "evaluation_label": "evaluaciones únicas",
        "initial_value": initial_value,
        "final_value": best_value,
        "initial_metrics": {"cmax": initial_result["cmax"], "fmax": initial_result["fmax"]},
        "final_metrics": {"cmax": result["cmax"], "fmax": result["fmax"]},
        "stop_reason": stop_reason,
    }
