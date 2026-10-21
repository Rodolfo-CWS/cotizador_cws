"""Conversión de filas de psycopg2 a dict, independiente del tipo de cursor.

La conexión de SupabaseManager usa RealDictCursor: ``fetchone()`` devuelve un
mapping. Iterarlo produce las llaves (nombres de columna), así que
``dict(zip(colnames, row))`` termina como
``{'id': 'id', 'is_internal': 'is_internal'}``. Un cursor normal devuelve una
tupla (o un DictRow, que es una lista) de valores, y ahí ``zip`` sí es correcto.
"""
from collections.abc import Mapping


def row_to_dict(row, colnames=None):
    """Devuelve un dict columna→valor, sea la fila un mapping o una secuencia.

    ``colnames`` se usa para las secuencias (tupla / DictRow). En un mapping se
    leen los valores por nombre: si se pasan ``colnames``, solo esas columnas.
    """
    if row is None:
        return None
    if isinstance(row, Mapping):
        if colnames is not None:
            return {name: row[name] for name in colnames}
        return dict(row)
    if colnames is None:
        raise TypeError("colnames es obligatorio cuando la fila no es un mapping")
    return dict(zip(colnames, row))


def row_scalar(row):
    """Primer valor de una fila (``COUNT(*)``, ``RETURNING`` de una columna)."""
    if row is None:
        return None
    if isinstance(row, Mapping):
        return next(iter(row.values()))
    return row[0]
