"""
Prueba de la Fase 3 por consola (sin interfaz).

Uso:
    python herramientas/probar_fase3.py "SALIDA/ASMET EVENTO"

Muestra el plan, pide confirmación y luego limpia:
  - En cada carpeta quedan solo FEV, PDE y HEV
  - El resto se mueve a "ASMET EVENTO_RESPALDO"
  - La carpeta se renombra al número del consecutivo
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collections import Counter

from app.config.aseguradoras import ASMET
from app.core.modelos import AccionFase3
from app.services.limpiador_carpetas import LimpiadorCarpetas


def barra(actual, total, mensaje):
    pct = actual * 100 // max(total, 1)
    print(f"\r[{'#' * (pct // 4):<25}] {pct:>3}%  {mensaje[:60]:<60}", end="", flush=True)


def main(carpeta_padre):
    limpiador = LimpiadorCarpetas(ASMET)
    plan = limpiador.planear(carpeta_padre)
    conteo = Counter(p.accion for p in plan)
    archivos = sum(len(p.respaldar) for p in plan if p.accion == AccionFase3.LIMPIAR)

    print("PLAN DE LIMPIEZA")
    print(f"  Se limpiarán y renombrarán: {conteo[AccionFase3.LIMPIAR]} carpetas "
          f"({archivos} archivos al respaldo)")
    print(f"  Ya estaban limpias:         {conteo[AccionFase3.YA_LIMPIA]}")
    print(f"  Se omitirán:                {conteo[AccionFase3.OMITIR]}")
    for p in plan:
        if p.accion == AccionFase3.OMITIR:
            print(f"     - {p.carpeta.name}: {p.motivo}")
    print(f"  Respaldo en: {limpiador.carpeta_respaldo(carpeta_padre)}")

    if input("\n¿Continuar? (s/n): ").strip().lower() != "s":
        print("Cancelado, no se modificó nada.")
        return

    resultado = limpiador.ejecutar(carpeta_padre, plan, progreso=barra)
    print(f"\n\n{resultado.resumen()}")
    print(f"Registro: {resultado.ruta_excel}")
    for it in resultado.items:
        if it.errores:
            print(f"  ERROR {it.plan.carpeta.name}: {'; '.join(it.errores)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        main(sys.argv[1])
