"""
Prueba del Limpiador de RIPS por consola (sin interfaz).

Uso:
    python herramientas/probar_rips.py "C:/cntsiste.cnt/RIPS ATRASADOS/NUEVA. SUB"

Muestra el plan, pide confirmación y ELIMINA DEFINITIVAMENTE los archivos que no son
CUV, JSON ni XML. Las carpetas sin CUV no se tocan.
"""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.limpiador_rips import EstadoRIPS, LimpiadorRIPS


def main(carpeta_padre):
    limpiador = LimpiadorRIPS()
    plan = limpiador.planear(carpeta_padre)
    conteo = Counter(p.estado for p in plan)
    a_eliminar = sum(len(p.eliminar) for p in plan if p.estado == EstadoRIPS.LIMPIAR)

    print("PLAN DE LIMPIEZA DE RIPS")
    print(f"  Carpetas a limpiar:   {conteo[EstadoRIPS.LIMPIAR]}  ({a_eliminar} archivos a eliminar)")
    print(f"  Ya limpias:           {conteo[EstadoRIPS.YA_LIMPIA]}")
    print(f"  Sin CUV (no se tocan): {conteo[EstadoRIPS.SIN_CUV]}")
    for p in plan:
        if p.estado == EstadoRIPS.SIN_CUV:
            print(f"     - {p.carpeta.name}")

    if not a_eliminar:
        print("\nNada que eliminar.")
        return
    if input("\n¿Eliminar DEFINITIVAMENTE? (s/n): ").strip().lower() != "s":
        print("Cancelado, no se modificó nada.")
        return
    r = limpiador.ejecutar(carpeta_padre, plan)
    print(f"\n{r.resumen()}\nReporte: {r.ruta_excel}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        main(sys.argv[1])
