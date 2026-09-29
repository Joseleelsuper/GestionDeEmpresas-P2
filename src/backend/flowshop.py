"""Cálculo de los tiempos de finalización de un flow shop permutacional."""


def calculate_flowshop(processing: list[list[int]], sequence: list[int]) -> dict:
    """Calcula F con la recurrencia de disponibilidad de órdenes y máquinas.

    Cada operación termina cuando ha acabado la operación anterior de su orden
    y la máquina está libre. Así, ``F[k,j] = max(F[k-1,j], F[k,j-1]) + d[k,j]``.
    Todas las órdenes llegan en cero, por lo que Fmáx coincide con Cmáx.

    Args:
        processing (list[list[int]]): Duraciones, indexadas por orden y máquina.
        sequence (list[int]): Permutación completa de identificadores desde 1.

    Returns:
        dict: Filas de duraciones y finalización, Cmáx y Fmáx.
    """
    machine_count = len(processing[0])
    rows = []
    previous = [0] * machine_count

    for job in sequence:
        durations = processing[job - 1]
        current = []
        for machine, duration in enumerate(durations):
            current.append(
                max(previous[machine], current[machine - 1] if machine else 0)
                + duration
            )
        rows.append({"job": job, "processing": durations, "completion": current})
        previous = current

    completion_times = [row["completion"][-1] for row in rows]
    cmax = max(completion_times)
    
    return {
        "jobs": len(processing),
        "machines": machine_count,
        "sequence": sequence,
        "rows": rows,
        "cmax": cmax,
        "fmax": round(sum(completion_times) / len(completion_times), 2),
    }
