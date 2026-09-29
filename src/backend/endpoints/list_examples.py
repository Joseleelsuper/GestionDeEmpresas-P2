"""Acceso a los ejemplos TXT integrados."""

import re
from pathlib import Path


def get_example_names(examples_dir: Path) -> list[str]:
    """Lista los TXT disponibles y mantiene su orden natural.

    Args:
        examples_dir (Path): Directorio que contiene los ejemplos.

    Returns:
        list[str]: Nombres de los archivos TXT ordenados por su sufijo numérico.
    """

    def order_key(path: Path) -> tuple[str, int]:
        """Crea la clave de ordenación de un nombre de ejemplo.

        Args:
            path (Path): Archivo TXT que se va a ordenar.

        Returns:
            tuple[str, int]: Prefijo textual y primer número del nombre.
        """
        match = re.search(r"\d+", path.stem)
        return path.stem.rstrip("0123456789"), int(match.group()) if match else 0

    return [
        path.name
        for path in sorted(examples_dir.glob("*.txt"), key=order_key)
        if path.is_file()
    ]
