"""
Prueba de la Fase 2 por consola (sin interfaz).

Uso:
    python herramientas/probar_fase2.py "SALIDA/ASMET EVENTO"

Arma PDE_813003431_LPG#####.pdf y HEV_813003431_LPG#####.pdf en cada carpeta
y genera "<CARPETA PADRE> - REPORTE SOPORTES.xlsx" al lado.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time

from app.config.aseguradoras import ASMET
from app.services.armador_paquetes import ArmadorPaquetes


def barra(actual, total, mensaje):
    pct = actual * 100 // max(total, 1)
    print(f"\r[{'#' * (pct // 4):<25}] {pct:>3}%  {mensaje[:60]:<60}", end="", flush=True)


def main(carpeta_padre):
    inicio = time.time()
    resultado = ArmadorPaquetes(ASMET).ejecutar(carpeta_padre, progreso=barra)
    print(f"\n\n{resultado.resumen()}")
    print(f"Reporte: {resultado.ruta_excel}")
    print(f"Tiempo:  {time.time() - inicio:.1f} s")

    if resultado.incompletos:
        print("\nIncompletas:")
        for it in resultado.incompletos:
            detalle = ", ".join(it.faltantes) or "; ".join(
                it.observaciones + (it.pde.errores if it.pde else []) +
                (it.hev.errores if it.hev else []))
            print(f"  - {it.carpeta.name}: {detalle}")

    print("\n>>> Verifica que los soportes tengan todos los documentos antes de limpiar.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        main(sys.argv[1])
