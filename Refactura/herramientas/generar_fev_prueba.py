"""
Genera FEV de prueba (PDF) con el mismo formato de texto que las facturas CNT,
para probar el lector y las fases sin usar datos reales.

Uso:
    python herramientas/generar_fev_prueba.py                       # 50 FEV en ./FEV_PRUEBA
    python herramientas/generar_fev_prueba.py -n 1000 -o C:/pruebas/FEV_MIL
    python herramientas/generar_fev_prueba.py --sin-casos-raros     # solo Asmet, todo limpio
    python herramientas/generar_fev_prueba.py --semilla 7           # mismos datos cada vez
    python herramientas/generar_fev_prueba.py --aseguradora nueva_eps -o FEV_NEPS
    python herramientas/generar_fev_prueba.py --aseguradora soat -o FEV_SOAT

Por defecto incluye casos para probar validaciones:
  - ~20% de pacientes con 2 o 3 facturas (mismo nombre, distinto consecutivo)
  - 2 facturas de otra administradora (deben salir en ADVERTENCIA)
  - 1 archivo cuyo nombre no coincide con el consecutivo del PDF (ADVERTENCIA)
"""
import argparse
import random
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

NIT_IPS = "813003431"

NOMBRES = ["JUAN", "CARLOS", "ANDRES", "LUIS", "JOSE", "MIGUEL", "JORGE", "DIEGO",
           "MARIA", "ANA", "LAURA", "PAULA", "SANDRA", "YULI", "KAREN", "DIANA",
           "CAMILO", "SEBASTIAN", "VALENTINA", "SOFIA", "ESPERANZA", "ESTEFANY",
           "NICOLAS", "DANIELA", "ALEJANDRO", "MARTHA", "GLORIA", "EDWIN"]
APELLIDOS = ["PEREZ", "GOMEZ", "RODRIGUEZ", "MARTINEZ", "GARCIA", "LOPEZ", "CASTRO",
             "RAMIREZ", "TORRES", "VARGAS", "MUÑOZ", "ROJAS", "DIAZ", "MORENO",
             "PARRA", "ESPINOSA", "REYES", "BAUTISTA", "CUELLAR", "TOVAR", "PEÑA",
             "SUAREZ", "OSPINA", "CHARRY", "CEDEÑO", "POLANIA", "TRUJILLO"]
TIPOS_DOC = [("CC", 70), ("TI", 15), ("RC", 10), ("CE", 3), ("PT", 2)]
TIPOS_USUARIO = ["Subsidiado", "Contributivo"]

ASMET = ("ASMET SALUD EPS SAS", "900935126 - 7", "EVENTOSUB")
NUEVA_EPS = ("NUEVA EPS S.A", "900156264 - 2", "EVENTOSUB")
PREVISORA = ("LA PREVISORA S.A cia Seguros", "860002400 - 2", "EVENTO2009")
MUNDIAL = ("COMPAÑIA MUNDIAL DE SEGUROS SOAT", "860037013 - 6", "EVENTO2009")
SANITAS = ("EPS SANITAS S.A.S.", "800251440 - 6", "EVENTOSUB")

# aseguradora -> (administradora principal, otras para casos raros, formato por defecto)
CONFIG = {
    "asmet": (ASMET, [NUEVA_EPS, MUNDIAL], "B"),
    "nueva_eps": (NUEVA_EPS, [ASMET, PREVISORA], "A"),
    "sanitas": (SANITAS, [NUEVA_EPS, ASMET], "A"),
    "soat": (PREVISORA, [MUNDIAL, ASMET], "B"),
}
PLAN_SOAT = "Cobertura Póliza SOAT"
PLAN_EPS = "Plan de beneficios en sal"

SERVICIOS = [("890701", "39145 Consulta de urgencias", 103500),
             ("19942777-12", "Dexametasona (acetato)Amp8 mg / mL d", 1638),
             ("20067651-02", "Diclofenaco sódicoAmp75 mg / 3 mL", 1620),
             ("19942561-03", "Ringer lactato (Solución Hartman) bol. 5", 9703),
             ("MDX066", "JERINGA 5 ML", 778),
             ("MMQ017", "EQUIPO MACROGOTEO", 3771),
             ("MMQ072", "CATETER NO 20", 4195),
             ("890601", "Atencion diaria intrahospitalaria por el m", 71600),
             ("5DSB01", "38915 Sala de observación", 107200)]


# --------------------------------------------------------------- datos
def paciente_aleatorio(rng):
    tipo = rng.choices([t for t, _ in TIPOS_DOC], [w for _, w in TIPOS_DOC])[0]
    largo = {"CC": rng.choice([8, 10]), "TI": 10, "RC": 10, "CE": 7, "PT": 7}[tipo]
    doc = str(rng.randint(10 ** (largo - 1), 10 ** largo - 1))
    nombre = " ".join([rng.choice(APELLIDOS), rng.choice(APELLIDOS),
                       *rng.sample(NOMBRES, rng.choice([1, 2]))])
    return tipo, doc, nombre, rng.choice(TIPOS_USUARIO)


def armar_lista(n, rng, casos_raros, principal=ASMET, otras=(NUEVA_EPS, MUNDIAL)):
    consecutivos = rng.sample(range(140000, 160000), n)
    facturas, i = [], 0
    while i < n:
        pac = paciente_aleatorio(rng)
        repeticiones = rng.choice([2, 3]) if casos_raros and rng.random() < 0.2 else 1
        for _ in range(min(repeticiones, n - i)):
            facturas.append({"paciente": pac, "numero": consecutivos[i],
                             "admin": principal, "nombre_archivo": None})
            i += 1
    rng.shuffle(facturas)

    if casos_raros and n >= 5:
        for f, otra in zip(facturas[:2], otras):            # otra administradora
            f["admin"] = otra
        f = facturas[2]                                     # archivo mal nombrado
        f["nombre_archivo"] = f"FEV_{NIT_IPS}_LPG{f['numero'] + 1}.pdf"
    return facturas


# --------------------------------------------------------------- PDF
def _es_soat(admin_tupla):
    return admin_tupla in (PREVISORA, MUNDIAL)


def dibujar_fev(ruta, fac, rng, formato="A"):
    tipo, doc, nombre, tipo_usuario = fac["paciente"]
    admin, nit_admin, convenio = fac["admin"]
    if _es_soat(fac["admin"]):
        tipo_usuario = "Tomador/Amparado SOAT"
    fac["paciente"] = (tipo, doc, nombre, tipo_usuario)
    consecutivo = f"LPG{fac['numero']}"
    f_fact = date(2026, 9, 1) + timedelta(days=rng.randint(0, 40))
    f_aten = f_fact - timedelta(days=rng.randint(10, 90))

    c = canvas.Canvas(str(ruta), pagesize=letter)
    w, h = letter
    y = h - 40

    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "EMPRESA SOCIAL DEL ESTADO LAURA PERDOMO")
    c.drawString(330, y, f"FACTURA ELECTRÓNICA DE VENTA No. {consecutivo}")
    c.drawString(110, y - 12, "DE GARCIA")
    c.setFont("Helvetica", 8)
    filas_der = [("Fecha Factura:", f_fact.strftime("%d/%m/%Y")),
                 ("Fecha Vencimiento:", (f_fact + timedelta(30)).strftime("%d/%m/%Y")),
                 ("Fecha Validación DIAN:", f_fact.strftime("%d/%m/%Y") + " 15:44:00"),
                 ("Fecha Inicial:", "01/01/2026"),
                 ("Fecha Final:", f_fact.strftime("%d/%m/%Y"))]
    filas_izq = [f"NIT {NIT_IPS}", "Cr 8 n 7-29 YAGUARA - HUILA", "Telefono 8383567", "Cod. IPS:", ""]
    for k, ((lbl, val), izq) in enumerate(zip(filas_der, filas_izq)):
        yy = y - 26 - k * 12
        c.drawString(160, yy, izq)
        c.drawString(330, yy, lbl)
        c.drawString(440, yy, val)

    y -= 100
    c.drawString(40, y, "CUFE: " + "".join(rng.choices("0123456789abcdef", k=96)))
    c.drawString(40, y - 12, "Elaborado por: JORGE HERNAN VELAZCO GOMEZ")
    c.drawString(520, y - 12, "Página 1 de 1")

    y -= 34
    if formato == "B":
        y = _bloque_formato_b(c, y, fac, rng)
    else:
        c.setFont("Helvetica-Bold", 9)
        for k, (lbl, val) in enumerate([("Administradora:", admin), ("Nit:", nit_admin),
                                        ("Convenio:", f"{convenio} - {rng.getrandbits(80):x}"),
                                        ("Fecha Convenio:", "25/02/2010 A 31/12/2026"),
                                        ("Contratacion:", "Pago por evento")]):
            c.setFont("Helvetica-Bold", 9); c.drawString(40, y - k * 13, lbl)
            c.setFont("Helvetica", 9); c.drawString(120, y - k * 13, val)
        c.drawString(380, y - 13, "Forma pago: Crédito")
        c.drawString(380, y - 26, "Plazo (Días): 30")

        y -= 80
        c.setFont("Helvetica", 8)
        c.drawString(40, y, tipo)
        c.drawString(65, y, doc)
        c.drawString(140, y, nombre)
        c.drawString(390, y, f"Tipo Usuario: {tipo_usuario}")

    y -= 18
    c.setFont("Helvetica-Bold", 7)
    c.drawString(40, y, "Orden   Fecha   Código   CUM   AUTOR.   Descripción   Cant.   Vl Unit   Vl Total   Copago   Saldo")
    c.setFont("Helvetica", 7)
    orden, total = rng.randint(700000, 900000), 0
    for cod, desc, valor in [SERVICIOS[0]] + rng.sample(SERVICIOS[1:], rng.randint(1, 5)):
        y -= 11
        cant = 1 if valor > 5000 else rng.choice([1, 2])
        sub = valor * cant
        total += sub
        c.drawString(40, y, f"{orden}  {f_aten.strftime('%d/%m/%Y')}  {cod}")
        c.drawString(230, y, desc)
        c.drawString(420, y, f"{cant:.2f}  {valor:,.2f}  {sub:,}  0  {sub:,}")
    y -= 14
    c.drawString(330, y, f"Total Paciente {total:,} 0 {total:,}")

    y -= 30
    c.setFont("Helvetica-Bold", 8)
    c.drawString(40, y, "OBSERVACIONES:")
    c.drawString(330, y, f"TOTAL CARGOS {total:,}")
    c.drawString(330, y - 14, f"SALDO ADMINISTRADORA {total:,}")
    c.setFont("Helvetica", 7)
    c.drawString(40, y - 50, "Impreso por: CNT Sistemas de Información SAS, NIT. 800031148-6, Software PACIENTES")
    c.drawString(40, y - 80, "DOCUMENTO DE PRUEBA - DATOS FICTICIOS")
    c.save()


def _bloque_formato_b(c, y, fac, rng):
    """Bloque del paciente con etiquetas (diseño real de las FEV de Asmet Salud)."""
    tipo, doc, nombre, tipo_usuario = fac["paciente"]
    admin, nit_admin, convenio = fac["admin"]
    filas = [("Paciente:", nombre, "Forma pago:", "Crédito"),
             ("Documento:", f"{tipo}    {doc}", "Plazo (Días):", "30"),
             ("Dirección:", rng.choice(["NO", "VEREDA MALU", "CENTRO"]), "", ""),
             ("Empresa:", f"{nit_admin}    {admin}", "Teléfono:", f"31{rng.randint(10**7, 10**8 - 1)}"),
             ("Convenio:", f"{convenio}ASISTE - HUI-599-S22", "Plan Beneficio:",
              PLAN_SOAT if _es_soat(fac["admin"]) else PLAN_EPS),
             ("Fecha Convenio:", "16/12/2010 A 31/12/2026", "Tipo Usuario:", tipo_usuario),
             ("Contratacion:", "Pago por evento", "", "")]
    for k, (l1, v1, l2, v2) in enumerate(filas):
        yy = y - k * 13
        c.setFont("Helvetica-Bold", 9); c.drawString(40, yy, l1)
        c.setFont("Helvetica", 9); c.drawString(130, yy, v1)
        if l2:
            c.setFont("Helvetica-Bold", 9); c.drawString(380, yy, l2)
            c.setFont("Helvetica", 9); c.drawString(470, yy, v2)
    return y - len(filas) * 13 - 10


# --------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Genera FEV de prueba")
    ap.add_argument("-n", "--cantidad", type=int, default=50)
    ap.add_argument("-o", "--salida", default="FEV_PRUEBA")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--sin-casos-raros", action="store_true")
    ap.add_argument("--aseguradora", choices=list(CONFIG), default="asmet",
                    help="asmet (defecto), nueva_eps o sanitas (mezcla Subsidiado/Contributivo), soat (Previsora)")
    ap.add_argument("--formato", choices=["A", "B", "mixto"], default=None,
                    help="A = línea del paciente, B = campos con etiqueta (Asmet real), "
                         "mixto = mitad y mitad")
    args = ap.parse_args()

    rng = random.Random(args.semilla)
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    principal, otras, formato_def = CONFIG[args.aseguradora]
    args.formato = args.formato or formato_def
    facturas = armar_lista(args.cantidad, rng, not args.sin_casos_raros, principal, otras)
    for fac in facturas:
        nombre = fac["nombre_archivo"] or f"FEV_{NIT_IPS}_LPG{fac['numero']}.pdf"
        formato = args.formato if args.formato != "mixto" else rng.choice("AB")
        dibujar_fev(salida / nombre, fac, rng, formato)

    repetidos = len(facturas) - len({f["paciente"] for f in facturas})
    print(f"{len(facturas)} FEV generadas en: {salida.resolve()}")
    print(f"  Facturas de pacientes repetidos: {repetidos}")
    if not args.sin_casos_raros:
        print("  Casos raros: 2 de otra administradora + 1 con nombre de archivo errado")


if __name__ == "__main__":
    main()
