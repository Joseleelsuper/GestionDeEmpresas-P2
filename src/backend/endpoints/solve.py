"""Carga una instancia de entrada y prepara la respuesta del cálculo."""

from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..flowshop import calculate_flowshop
from ..genetic_algorithm import GeneticOptions, genetic_algorithm
from ..instance import MAX_FILE_BYTES, parse_instance
from ..local_search import local_search
from ..metaheuristics import random_search, simulated_annealing
from ..sequence import parse_sequence


@dataclass(frozen=True)
class SearchOptions:
    """Opciones del algoritmo recibidas en el formulario HTTP."""

    algorithm: str
    objective: str
    strategy: str
    neighborhood: str
    max_iterations: int
    max_neighbors: int
    random_iterations: int
    initial_temperature: float
    cooling_rate: float
    iterations_per_temperature: int
    final_temperature: float
    refine_with_local_search: bool
    genetic: GeneticOptions = field(default_factory=GeneticOptions)


def _run_search(
    processing: list[list[int]], order: list[int], options: SearchOptions
) -> tuple[dict, dict]:
    """Despacha la búsqueda y aplica el refinamiento solicitado."""
    if options.algorithm == "local_search":
        return local_search(
            processing,
            order,
            options.objective,
            options.strategy,
            options.neighborhood,
            options.max_iterations,
            options.max_neighbors,
        )
    if options.algorithm == "random_search":
        return random_search(
            processing, order, options.objective, options.random_iterations
        )
    if options.algorithm == "genetic_algorithm":
        return genetic_algorithm(processing, order, options.objective, options.genetic)
    if options.algorithm != "simulated_annealing":
        raise ValueError(
            "Elige cálculo directo, búsqueda local, aleatoria, recocido o algoritmo genético."
        )

    result, search = simulated_annealing(
        processing,
        order,
        options.objective,
        options.neighborhood,
        options.initial_temperature,
        options.cooling_rate,
        options.iterations_per_temperature,
        options.final_temperature,
    )
    if options.refine_with_local_search:
        result, refinement = local_search(
            processing,
            result["sequence"],
            options.objective,
            options.strategy,
            options.neighborhood,
            options.max_iterations,
            options.max_neighbors,
        )
        search["refined_with_local_search"] = True
        search["refinement"] = {
            key: refinement[key]
            for key in ("strategy", "iterations", "neighbors_evaluated", "stop_reason")
        }
        search["final_value"] = refinement["final_value"]
        search["final_metrics"] = refinement["final_metrics"]
    return result, search


async def solve_instance(
    example: str,
    sequence: str,
    file: UploadFile | None,
    examples_dir: Path,
    options: SearchOptions,
) -> dict:
    """Valida la fuente y calcula la matriz de finalización.

    Args:
        example (str): Nombre del ejemplo integrado seleccionado.
        sequence (str): Permutación opcional de órdenes.
        file (UploadFile | None): TXT cargado temporalmente por el usuario.
        examples_dir (Path): Directorio de los ejemplos integrados.
        options (SearchOptions): Algoritmo y parámetros de búsqueda.

    Returns:
        dict: Datos de entrada, cálculo final y resumen opcional de búsqueda.

    Raises:
        HTTPException: Si la fuente, el archivo, la instancia o la secuencia
            son inválidos.
    """
    if bool(example) == bool(file):
        raise HTTPException(400, "Selecciona un ejemplo o sube un TXT, pero no ambos.")

    if file:
        content = await file.read(MAX_FILE_BYTES + 1)
        source = file.filename or "archivo.txt"
    else:
        if Path(example).name != example or Path(example).suffix.lower() != ".txt":
            raise HTTPException(404, "El ejemplo solicitado no existe.")
        path = examples_dir / example
        if not path.is_file():
            raise HTTPException(404, "El ejemplo solicitado no existe.")
        content = path.read_bytes()
        source = example

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            413, f"El archivo supera el límite de {MAX_FILE_BYTES / (1024 * 1024)}MB."
        )
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "El archivo debe estar codificado en UTF-8.") from None

    try:
        processing = parse_instance(text)
        order = parse_sequence(sequence, len(processing))
        if options.algorithm == "calculate":
            return {"source": source, **calculate_flowshop(processing, order)}
        result, search = _run_search(processing, order, options)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None

    return {"source": source, **result, "search": search}
