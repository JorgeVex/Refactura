"""
Prueba rápida del módulo 1 (sin interfaz).

Uso:
    python herramientas/probar_lector.py "C:/ruta/carpeta_con_FEV"
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
from collections import Counter
from pathlib import Path

from app.config.aseguradoras import ASMET
from app.services.lector_fev import LectorFEV


def main(carpeta: str):
    carpeta = Path(carpeta)
    lector = LectorFEV(ASMET)
    pdfs = sorted(p for p in carpeta.iterdir() if p.suffix.lower() == ".pdf")
    print(f"PDFs encontrados: {len(pdfs)}\n")

    inicio = time.time()
    estados = Counter()
    for i, ruta in enumerate(pdfs, 1):
        f = lector.leer(ruta)
        estados[f.estado.value] += 1
        print(f"{i:>4}. [{f.estado.value:<11}] {f.consecutivo:<10} {f.tipo_doc:<3} "
              f"{f.num_doc:<12} {f.nombre}")
        for obs in f.observaciones:
            print(f"        -> {obs}")

    seg = time.time() - inicio
    print(f"\nResumen: {dict(estados)}  |  {seg:.1f} s  "
          f"({seg / max(len(pdfs), 1):.2f} s por factura)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
    else:
        main(sys.argv[1])
