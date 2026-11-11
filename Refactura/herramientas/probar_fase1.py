"""
Prueba de la Fase 1 por consola (sin interfaz).

Uso:
    python herramientas/probar_fase1.py <carpeta_con_FEV> <carpeta_destino>
    python herramientas/probar_fase1.py FEV_PRUEBA SALIDA

Crea <destino>/ASMET EVENTO/<NOMBRE CONSECUTIVO>/FEV_...pdf
y   <destino>/ASMET EVENTO - PACIENTES.xlsx
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time

from app.config.aseguradoras import ASMET
from app.services.organizador_fev import OrganizadorFEV


def barra(actual, total, mensaje):
    pct = actual * 100 // max(total, 1)
    print(f"\r[{'#' * (pct // 4):<25}] {pct:>3}%  {mensaje[:60]:<60}", end="", flush=True)


def main(origen, destino):
    inicio = time.time()
    resultado = OrganizadorFEV(ASMET).ejecutar(origen, destino, progreso=barra)
    print(f"\n\n{resultado.resumen()}")
    print(f"Carpeta padre: {resultado.carpeta_padre}")
    print(f"Excel:         {resultado.ruta_excel}")
    print(f"Tiempo:        {time.time() - inicio:.1f} s")

    if resultado.con_novedad:
        print("\nNovedades:")
        for item in resultado.con_novedad:
            f = item.factura
            print(f"  - {f.ruta.name}: {item.accion.value} | {'; '.join(f.observaciones)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
    else:
        main(sys.argv[1], sys.argv[2])
