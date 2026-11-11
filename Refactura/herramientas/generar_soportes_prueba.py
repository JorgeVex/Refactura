"""
Llena cada carpeta de <CARPETA PADRE> (salida de la Fase 1) con soportes de prueba
(ANE2.pdf, ENV.pdf, TRI.pdf...), simulando la descarga manual.

Uso:
    python herramientas/generar_soportes_prueba.py "SALIDA/ASMET EVENTO"
    python herramientas/generar_soportes_prueba.py "SALIDA/ASMET EVENTO" --semilla 5
    python herramientas/generar_soportes_prueba.py "SALIDA/ASMET EVENTO" --todo-completo
    python herramientas/generar_soportes_prueba.py "SALIDA/SUBSIDIADO" --aseguradora nueva_eps
    python herramientas/generar_soportes_prueba.py "SALIDA/SOAT PREVISORA" --aseguradora soat

Por defecto, para probar validaciones:
  - ~15% de carpetas con algún obligatorio faltante (según la aseguradora)
  - Opcionales al azar (según la aseguradora)
  - Algunos nombres en minúscula (ane2.pdf) y un archivo desconocido (OTRO.pdf)
  - 1 PDF dañado (TRI)
"""
import argparse
import random
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# aseguradora -> (obligatorios, {opcional: probabilidad}, ¿lleva EKG?)
CONFIG = {
    "asmet": (["ANE2", "ENV", "EST", "HC", "TRI"],
              {"ANE3": 0.4, "BIT": 0.3, "BIT1": 0.1, "RET": 0.1, "DIS": 0.1, "FIC": 0.2,
               "APL": 0.3, "REM": 0.15}, True),
    "sanitas": None,   # Se completa abajo: mismos soportes que Asmet
    "nueva_eps": (["ANE2", "ENV", "EST", "COD", "AUT", "HC", "TRI"],
                  {"ANE3": 0.4, "BIT": 0.3, "Tras": 0.1, "RET": 0.1, "DIS": 0.1, "FIC": 0.2,
                   "APL": 0.3, "REM": 0.15}, True),
    "soat": (["SOAT", "TP", "CC", "CM", "HC", "TRI"],
             {"CCPROP": 0.4, "BIT": 0.5, "Tras": 0.3, "RET": 0.1, "DIS": 0.1,
              "APL": 0.3, "REM": 0.15, "REM1": 0.05}, False),
}


CONFIG["sanitas"] = CONFIG["asmet"]


def pdf_soporte(ruta: Path, codigo: str, carpeta: str, paginas: int):
    c = canvas.Canvas(str(ruta), pagesize=letter)
    for p in range(1, paginas + 1):
        c.setFont("Helvetica-Bold", 60)
        c.drawCentredString(306, 450, codigo)
        c.setFont("Helvetica", 12)
        c.drawCentredString(306, 400, carpeta)
        c.drawCentredString(306, 380, f"Página {p} de {paginas} - SOPORTE DE PRUEBA")
        c.showPage()
    c.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta_padre")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--todo-completo", action="store_true")
    ap.add_argument("--aseguradora", choices=list(CONFIG), default="asmet")
    args = ap.parse_args()

    rng = random.Random(args.semilla)
    carpetas = sorted(p for p in Path(args.carpeta_padre).iterdir() if p.is_dir())
    raros = not args.todo_completo
    incompletas = 0
    OBLIGATORIOS, OPCIONALES, lleva_ekg = CONFIG[args.aseguradora]

    for i, carpeta in enumerate(carpetas):
        codigos = list(OBLIGATORIOS)
        if raros and rng.random() < 0.15:
            codigos.remove(rng.choice(OBLIGATORIOS))
            incompletas += 1
        codigos += [c for c, prob in OPCIONALES.items() if rng.random() < prob]
        r = rng.random() if lleva_ekg else 1
        if r < 0.15:
            codigos.append("EKG")
        elif r < 0.25:
            codigos += ["EKG1", "EKG2"]

        for codigo in codigos:
            nombre = codigo.lower() if raros and rng.random() < 0.05 else codigo
            pdf_soporte(carpeta / f"{nombre}.pdf", codigo, carpeta.name,
                        paginas=rng.randint(1, 3))

        if raros and i == 0:
            pdf_soporte(carpeta / "OTRO.pdf", "OTRO", carpeta.name, 1)
        if raros and i == 1:
            (carpeta / "TRI.pdf").write_bytes(b"esto no es un PDF")

    print(f"Soportes generados en {len(carpetas)} carpetas")
    if raros:
        print(f"  Carpetas con un obligatorio faltante: {incompletas}")
        print(f"  Archivo desconocido en: {carpetas[0].name}")
        print(f"  TRI.pdf dañado en:      {carpetas[1].name}")


if __name__ == "__main__":
    main()
