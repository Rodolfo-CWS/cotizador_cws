#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test unitario para el fix de la "doble fuente de verdad" en revisiones.

Verifica que preparar_datos_nueva_revision() derive el siguiente número de
revisión a partir del FOLIO (-R#- dentro de numeroCotizacion) y NO del campo
'datosGenerales.revision', que históricamente se desincroniza (p. ej. la R2 de
BMW-CWS-FM-019 quedó guardada con revision=1).

Uso:
    python3 test_revision_folio_source.py

No requiere conexión a Supabase: reemplaza db_manager por un stub.
"""
import sys
import os
import types

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# En entornos sin las librerías de sistema de WeasyPrint (pango/gobject/cairo),
# `import weasyprint` lanza OSError (no ImportError) y cotizador/_compat.py no lo
# atrapa. Para probar SOLO la lógica de revisiones no necesitamos WeasyPrint:
# instalamos un stub en sys.modules para que el import de la app no falle.
if "weasyprint" not in sys.modules:
    try:
        import weasyprint  # noqa: F401
    except Exception:
        _stub = types.ModuleType("weasyprint")
        sys.modules["weasyprint"] = _stub

import app as app_module


class FakeDB:
    """Stub de SupabaseManager: solo implementa lo que usa preparar_datos_nueva_revision."""

    def generar_numero_revision(self, numero, nueva_revision):
        import re
        return re.sub(r'-R\d+', f'-R{nueva_revision}', numero, count=1)

    def generar_numero_cotizacion(self, cliente, vendedor, proyecto, revision):
        return f"{cliente}-CWS-XX-001-R{revision}-{proyecto}"


def _run(descripcion, cotizacion, espera_revision, espera_r_en_folio):
    app_module.db_manager = FakeDB()
    resultado = app_module.preparar_datos_nueva_revision(cotizacion)
    assert resultado is not None, f"preparar_datos_nueva_revision devolvió None: {descripcion}"
    dg = resultado["datosGenerales"]
    revision = dg.get("revision")
    folio = dg.get("numeroCotizacion")
    ok = (str(revision) == str(espera_revision)
          and espera_r_en_folio in (folio or ""))
    print(f"{'PASS' if ok else 'FAIL'}  {descripcion}")
    print(f"         revision={revision!r}  folio={folio!r}")
    return ok


def main():
    todos_ok = True

    # Caso 1 (el bug): folio dice R4 pero el campo revision quedó en "1" (desincronizado).
    todos_ok &= _run(
        "folio R4 + campo revision desincronizado (=1) -> debe dar R5",
        {
            "datosGenerales": {
                "numeroCotizacion": "BMW-CWS-FM-019-R4-TKB UNIVERSAL CONTAINERS TENDER",
                "revision": "1",
                "cliente": "BMW",
                "vendedor": "FM",
                "proyecto": "TKB Universal CONTAINERS TENDER",
            },
            "items": [],
        },
        espera_revision=5,
        espera_r_en_folio="-R5-",
    )

    # Caso 2 (normal): folio y campo coinciden -> comportamiento sin cambios.
    todos_ok &= _run(
        "folio R4 + campo revision correcto (=4) -> debe dar R5",
        {
            "datosGenerales": {
                "numeroCotizacion": "BMW-CWS-FM-019-R4-TKB UNIVERSAL CONTAINERS TENDER",
                "revision": "4",
                "cliente": "BMW",
                "vendedor": "FM",
                "proyecto": "TKB Universal CONTAINERS TENDER",
            },
            "items": [],
        },
        espera_revision=5,
        espera_r_en_folio="-R5-",
    )

    # Caso 3 (fallback): sin folio -> usa el campo.
    todos_ok &= _run(
        "sin folio -> fallback al campo (3 -> 4)",
        {
            "datosGenerales": {
                "numeroCotizacion": "",
                "revision": "3",
                "cliente": "BMW",
                "vendedor": "FM",
                "proyecto": "TKB",
            },
            "items": [],
        },
        espera_revision=4,
        espera_r_en_folio="-R4-",
    )

    # Caso 4: folio sin proyecto al final (GEN-123-R4).
    todos_ok &= _run(
        "folio sin proyecto (-R4 al final) -> debe dar R5",
        {
            "datosGenerales": {
                "numeroCotizacion": "GEN-CWS-XX-123-R4",
                "revision": "4",
                "cliente": "GEN",
                "vendedor": "XX",
                "proyecto": "",
            },
            "items": [],
        },
        espera_revision=5,
        espera_r_en_folio="-R5",
    )

    print("\n" + ("=" * 60))
    print("RESULTADO:", "TODO OK" if todos_ok else "HUBO FALLOS")
    print("=" * 60)
    return 0 if todos_ok else 1


if __name__ == "__main__":
    sys.exit(main())
