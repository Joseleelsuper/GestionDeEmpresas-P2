"""Carga una instancia de entrada y prepara la respuesta del cálculo."""

from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..flowshop import calculate_flowshop
from ..instance import MAX_FILE_BYTES, parse_instance
from ..local_search import local_search
from ..sequence import parse_sequence


async def solve_instance(
    example: str,
    sequence: str,
    file: UploadFile | None,
    examples_dir: Path,
    algorithm: str = "calculate",
    objective: str = "cmax",
    strategy: str = "best",
    neighborhood: str = "swap",
    max_iterations: int = 100,
) -> dict:
    """Valida la fuente y calcula la matriz de finalización.

    Args:
        example (str): Nombre del ejemplo integrado seleccionado.
        sequence (str): Permutación opcional de órdenes.
        file (UploadFile | None): TXT cargado temporalmente por el usuario.
        examples_dir (Path): Directorio de los ejemplos integrados.
        algorithm (str): ``calculate`` para evaluar o ``local_search`` para buscar.
        objective (str): Medida que minimiza la búsqueda local.
        strategy (str): Submodo de selección del vecino.
        neighborhood (str): Movimiento usado para formar el vecindario.
        max_iterations (int): Máximo de mejoras aceptadas.

    Returns:
        dict: Datos de entrada, cálculo final y resumen opcional de búsqueda.

    Raises:
        HTTPException: Si la fuente, el archivo, la instancia o la secuencia son inválidos.
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
        raise HTTPException(413, f"El archivo supera el límite de {MAX_FILE_BYTES / (1024 * 1024)}MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "El archivo debe estar codificado en UTF-8.") from None

    try:
        processing = parse_instance(text)
        order = parse_sequence(sequence, len(processing))
        if algorithm == "local_search":
            result, search = local_search(
                processing, order, objective, strategy, neighborhood, max_iterations
            )
            return {"source": source, **result, "search": search}
        if algorithm != "calculate":
            raise ValueError("El algoritmo debe ser cálculo directo o búsqueda local.")
    except ValueError as error:
        raise HTTPException(400, str(error)) from None

    return {"source": source, **calculate_flowshop(processing, order)}
