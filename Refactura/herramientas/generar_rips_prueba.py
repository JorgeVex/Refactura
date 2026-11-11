"""
Genera una carpeta padre de RIPS de prueba (como RIPS ATRASADOS/NUEVA. SUB),
con una subcarpeta por factura, para probar el Limpiador de RIPS.

Uso:
    python herramientas/generar_rips_prueba.py                      # 30 carpetas en ./RIPS_PRUEBA
    python herramientas/generar_rips_prueba.py -n 200 -o RIPS_MIL --semilla 4

Cada carpeta trae, como en la vida real:
    152460.json
    ad0813003431000000262538C.xml
    ResultadosLocales_LPG152460.txt                 <- se elimina
    ResultadosMSPS_LPG152460_ID0_R.txt              <- se elimina
    ResultadosMSPS_LPG152460_ID329310568_A_CUV.txt  <- se conserva

Casos raros (por defecto): carpetas sin CUV (rechazadas), sin XML, ya limpias,
con un archivo extra (.pdf) y una vacía.
"""
import argparse
import json
import random
from pathlib import Path


def crear_carpeta(base: Path, numero: int, rng, caso: str):
    c = base / str(numero)
    c.mkdir(parents=True, exist_ok=True)
    if caso == "vacia":
        return
    (c / f"{numero}.json").write_text(json.dumps(
        {"numFactura": f"LPG{numero}", "tipoNota": None, "usuarios": [{"tipoDocumentoIdentificacion": "CC"}]},
        indent=2), encoding="utf-8")
    if caso != "sin_xml":
        (c / f"ad0813003431000000{rng.randint(100000, 999999)}C.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<AttachedDocument></AttachedDocument>', encoding="utf-8")
    if caso == "ya_limpia":
        (c / f"ResultadosMSPS_LPG{numero}_ID{rng.randint(10**8, 10**9)}_A_CUV.txt").write_text("CUV ...")
        return
    (c / f"ResultadosLocales_LPG{numero}.txt").write_text('{"ResultadosValidacion": []}')
    (c / f"ResultadosMSPS_LPG{numero}_ID0_R.txt").write_text('{"ResultState": false}')
    if caso != "sin_cuv":
        (c / f"ResultadosMSPS_LPG{numero}_ID{rng.randint(10**8, 10**9)}_A_CUV.txt").write_text("CUV ...")
    if caso == "extra":
        (c / "soporte_suelto.pdf").write_bytes(b"%PDF-1.4 prueba")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--cantidad", type=int, default=30)
    ap.add_argument("-o", "--salida", default="RIPS_PRUEBA")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--sin-casos-raros", action="store_true")
    args = ap.parse_args()

    rng = random.Random(args.semilla)
    base = Path(args.salida)
    numeros = sorted(rng.sample(range(150000, 160000), args.cantidad))
    raros = ["sin_cuv", "sin_cuv", "sin_xml", "ya_limpia", "extra", "vacia"]
    casos = {}
    for i, n in enumerate(numeros):
        caso = raros[i] if (not args.sin_casos_raros and i < len(raros)) else "normal"
        crear_carpeta(base, n, rng, caso)
        casos[caso] = casos.get(caso, 0) + 1
    print(f"{len(numeros)} carpetas de RIPS en: {base.resolve()}")
    print("  Casos:", casos)


if __name__ == "__main__":
    main()
