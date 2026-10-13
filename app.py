"""Punto de entrada FastAPI y definición de rutas HTTP."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.backend.endpoints.list_examples import get_example_names
from src.backend.endpoints.solve import SearchOptions, solve_instance
from src.backend.genetic_algorithm import GeneticOptions

ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "data" / "examples"
FRONTEND = ROOT / "src" / "frontend"

app = FastAPI(title="Flow shop permutacional")
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Sirve la página principal.

    Returns:
        FileResponse: Documento HTML de la aplicación.
    """
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/examples")
def list_examples() -> list[str]:
    """Lista los TXT integrados en la aplicación.

    Returns:
        list[str]: Nombres de archivo disponibles en ``data/examples``.
    """
    return get_example_names(EXAMPLES)


def _search_options(
    algorithm: str = Form(default="calculate"),
    objective: str = Form(default="cmax"),
    strategy: str = Form(default="best"),
    neighborhood: str = Form(default="swap"),
    max_iterations: int = Form(default=100),
    max_neighbors: int = Form(default=100),
    random_iterations: int = Form(default=1000),
    initial_temperature: float = Form(default=1000),
    cooling_rate: float = Form(default=0.9),
    iterations_per_temperature: int = Form(default=50),
    final_temperature: float = Form(default=1),
    refine_with_local_search: bool = Form(default=False),
    ga_population_size: int = Form(default=40),
    ga_generations: int = Form(default=100),
    ga_selection: str = Form(default="tournament"),
    ga_tournament_size: int = Form(default=3),
    ga_truncation_fraction: float = Form(default=0.5),
    ga_crossover: str = Form(default="ox"),
    ga_crossover_probability: float = Form(default=0.8),
    ga_mutation: str = Form(default="swap"),
    ga_mutation_probability: float = Form(default=0.1),
    ga_replacement: str = Form(default="generational"),
    ga_elite_count: int = Form(default=1),
    ga_stagnation_generations: int = Form(default=20),
    ga_time_limit_seconds: float = Form(default=10),
    ga_target_value: float | None = Form(default=None),
) -> SearchOptions:
    """Agrupa los parámetros de búsqueda recibidos como campos del formulario."""
    return SearchOptions(
        algorithm=algorithm,
        objective=objective,
        strategy=strategy,
        neighborhood=neighborhood,
        max_iterations=max_iterations,
        max_neighbors=max_neighbors,
        random_iterations=random_iterations,
        initial_temperature=initial_temperature,
        cooling_rate=cooling_rate,
        iterations_per_temperature=iterations_per_temperature,
        final_temperature=final_temperature,
        refine_with_local_search=refine_with_local_search,
        genetic=GeneticOptions(
            population_size=ga_population_size,
            generations=ga_generations,
            selection=ga_selection,
            tournament_size=ga_tournament_size,
            truncation_fraction=ga_truncation_fraction,
            crossover=ga_crossover,
            crossover_probability=ga_crossover_probability,
            mutation=ga_mutation,
            mutation_probability=ga_mutation_probability,
            replacement=ga_replacement,
            elite_count=ga_elite_count,
            stagnation_generations=ga_stagnation_generations,
            time_limit_seconds=ga_time_limit_seconds,
            target_value=ga_target_value,
        ),
    )


@app.post("/api/solve")
async def solve(
    options: Annotated[SearchOptions, Depends(_search_options)],
    example: str = Form(default=""),
    sequence: str = Form(default=""),
    file: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """Calcula la matriz F o ejecuta un algoritmo de búsqueda para un ejemplo o TXT.

    Args:
        example (str): Nombre de un ejemplo integrado, si no se sube archivo.
        sequence (str): Permutación opcional de órdenes desde 1.
        file (UploadFile | None): TXT temporal enviado por el usuario.
        options (SearchOptions): Algoritmo y parámetros de búsqueda.

    Returns:
        dict: Instancia, cálculo final y resumen opcional de búsqueda.

    Raises:
        HTTPException: Si la instancia, el archivo o la secuencia no son válidos.
    """
    return await solve_instance(example, sequence, file, EXAMPLES, options)
