"""Validación y generación de secuencias de órdenes."""

import random
import re


def parse_sequence(value: str, jobs: int) -> list[int]:
    """Valida una permutación de órdenes o genera una aleatoria.

    Args:
        value (str): Órdenes separadas por espacios o comas; vacío para aleatorizar.
        jobs (int): Número de órdenes de la instancia.

    Returns:
        list[int]: Permutación completa con identificadores desde 1 hasta ``jobs``.

    Raises:
        ValueError: Si faltan órdenes, hay duplicados o un identificador no es válido.
    """
    if not value.strip():
        return random.sample(range(1, jobs + 1), jobs)
    try:
        sequence = [int(item) for item in re.split(r"[\s,]+", value.strip())]
    except ValueError:
        raise ValueError(
            "La secuencia solo puede contener números separados por espacios o comas."
        ) from None
    if len(sequence) != jobs or set(sequence) != set(range(1, jobs + 1)):
        raise ValueError(
            f"La secuencia debe incluir una vez cada orden del 1 al {jobs}."
        )
    return sequence
