"""Lectura y validación de instancias flow shop en formato TXT."""

MAX_FILE_BYTES = 1_048_576
MAX_OPERATIONS = 10_000


def parse_instance(text: str) -> list[list[int]]:
    """Lee una instancia TXT y obtiene sus duraciones por orden y máquina.

    Args:
        text (str): Cabecera ``n m`` y filas de pares ``máquina duración``.

    Returns:
        list[list[int]]: Duraciones en el orden en que aparecen en el TXT.

    Raises:
        ValueError: Si el contenido no cumple el formato o los límites admitidos.
    """
    lines = [line.split() for line in text.lstrip("\ufeff").splitlines() if line.strip()]
    if not lines:
        raise ValueError("El archivo está vacío.")

    try:
        if len(lines[0]) != 2:
            raise ValueError
        jobs, machines = map(int, lines[0])
    except ValueError:
        raise ValueError("La primera línea debe contener el número de órdenes y máquinas.") from None

    if jobs < 1 or machines < 1:
        raise ValueError("La instancia debe tener al menos una orden y una máquina.")
    if jobs * machines > MAX_OPERATIONS:
        raise ValueError(f"La instancia supera el límite de {MAX_OPERATIONS} operaciones.")
    if len(lines) != jobs + 1:
        raise ValueError(f"Se esperaban {jobs} filas de operaciones y se recibieron {len(lines) - 1}.")

    processing = []
    for job, fields in enumerate(lines[1:], start=1):
        if len(fields) != machines * 2:
            raise ValueError(f"La orden {job} debe contener {machines} pares máquina-tiempo.")
        try:
            values = list(map(int, fields))
        except ValueError:
            raise ValueError(f"La orden {job} contiene un valor que no es entero.") from None
        if values[::2] != list(range(machines)):
            raise ValueError(f"La orden {job} debe listar las máquinas en orden de 0 a {machines - 1}.")
        durations = values[1::2]
        if any(duration < 0 for duration in durations):
            raise ValueError(f"La orden {job} contiene una duración negativa.")
        processing.append(durations)
    return processing
