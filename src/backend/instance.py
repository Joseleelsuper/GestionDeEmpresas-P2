"""Lectura y validación de instancias flow shop en formato TXT."""

MAX_FILE_BYTES = 1_048_576
MAX_OPERATIONS = 10_000


def _parse_header(fields: list[str]) -> tuple[int, int]:
    """Convierte los dos campos de la cabecera en órdenes y máquinas.

    Args:
        fields (list[str]): Tokens de la primera línea de la instancia.

    Returns:
        tuple[int, int]: Número de órdenes y número de máquinas.

    Raises:
        ValueError: Si la cabecera no contiene exactamente dos enteros.
    """
    try:
        if len(fields) != 2:
            raise ValueError
        jobs, machines = map(int, fields)
        return jobs, machines
    except ValueError:
        raise ValueError(
            "La primera línea debe contener el número de órdenes y máquinas."
        ) from None


def parse_instance(text: str) -> list[list[int]]:
    """Lee una instancia TXT y obtiene sus duraciones por orden y máquina.

    Args:
        text (str): Cabecera ``n m`` y filas de pares ``máquina duración``; admite
            hasta ``MAX_FILE_BYTES`` bytes y ``MAX_OPERATIONS`` operaciones.

    Returns:
        list[list[int]]: Duraciones en el orden en que aparecen en el TXT.

    Raises:
        ValueError: Si el contenido no cumple el formato o los límites admitidos.
    """
    lines = [
        line.split() for line in text.lstrip("\ufeff").splitlines() if line.strip()
    ]
    if not lines:
        raise ValueError("El archivo está vacío.")

    jobs, machines = _parse_header(lines[0])

    if jobs < 1 or machines < 1:
        raise ValueError("La instancia debe tener al menos una orden y una máquina.")
    if jobs * machines > MAX_OPERATIONS:
        raise ValueError(
            f"La instancia supera el límite de {MAX_OPERATIONS} operaciones."
        )
    if len(lines) != jobs + 1:
        raise ValueError(
            f"Se esperaban {jobs} filas de operaciones "
            f"y se recibieron {len(lines) - 1}."
        )

    processing = []
    for job, fields in enumerate(lines[1:], start=1):
        if len(fields) != machines * 2:
            raise ValueError(
                f"La orden {job} debe contener {machines} pares máquina-tiempo."
            )
        try:
            values = list(map(int, fields))
        except ValueError:
            raise ValueError(
                f"La orden {job} contiene un valor que no es entero."
            ) from None
        if values[::2] != list(range(machines)):
            raise ValueError(
                f"La orden {job} debe listar las máquinas "
                f"en orden de 0 a {machines - 1}."
            )
        durations = values[1::2]
        if any(duration < 0 for duration in durations):
            raise ValueError(f"La orden {job} contiene una duración negativa.")
        processing.append(durations)
    return processing
