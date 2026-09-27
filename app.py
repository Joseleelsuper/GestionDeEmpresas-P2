"""Punto de entrada FastAPI y definición de rutas HTTP."""

from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.backend.endpoints.list_examples import get_example_names
from src.backend.endpoints.solve import solve_instance

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


@app.post("/api/solve")
async def solve(
    example: str = Form(default=""),
    sequence: str = Form(default=""),
    file: UploadFile | None = File(default=None),
) -> dict:
    """Calcula la matriz F para un ejemplo o un TXT subido.

    Args:
        example (str): Nombre de un ejemplo integrado, si no se sube archivo.
        sequence (str): Permutación opcional de órdenes desde 1.
        file (UploadFile | None): TXT temporal enviado por el usuario.

    Returns:
        dict: Instancia, secuencia, filas de cálculo y medidas de eficiencia.

    Raises:
        HTTPException: Si la instancia, el archivo o la secuencia no son válidos.
    """
    return await solve_instance(example, sequence, file, EXAMPLES)
