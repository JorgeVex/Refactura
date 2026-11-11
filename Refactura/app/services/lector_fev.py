"""
Lector de facturas FEV (formato CNT - Software PACIENTES).

Saca del PDF: consecutivo, nombre, tipo y número de documento,
administradora y fecha de factura.

Soporta los dos diseños de factura que genera CNT:

  Formato A (línea del paciente):
      Administradora: NUEVA EPS S.A
      CC 40422190 PARRA ESPINOSA YULI ESPERANZA Tipo Usuario: Subsidiado

  Formato B (campos con etiqueta, ej. convenio Asmet Salud):
      Paciente: PEÑA RAMIREZ CARMEN            Forma pago: Crédito
      Documento: CC 26511751                   Plazo (Días): 30
      Empresa: 900935126 - 7 ASMET SALUD EPS SAS   Teléfono: 3186933264
"""
import re
from pathlib import Path

import pdfplumber

from app.config.constantes import PATRON_ARCHIVO_FEV
from app.config.aseguradoras import PerfilAseguradora
from app.core.modelos import Factura, EstadoLectura

TIPOS_DOC = r"CC|TI|RC|CE|PA|PE|PT|PPT|MS|AS|CN|SC|DE|CD|SI"

# "CC 40422190 PARRA ESPINOSA YULI ESPERANZA Tipo Usuario: Subsidiado"
RE_PACIENTE = re.compile(
    # [ \t] en vez de \s para no saltar de línea; el documento debe empezar con dígito
    rf"^[ \t]*({TIPOS_DOC})[ \t]+(\d[0-9A-Z]*)[ \t]+(.+?)(?:[ \t]+Tipo[ \t]+Usuario:.*)?$",
    re.MULTILINE,
)
RE_CONSECUTIVO = re.compile(r"VENTA\s+No\.?\s*(LPG\d+)", re.IGNORECASE)
RE_ADMINISTRADORA = re.compile(r"Administradora:[ \t]*(.+)")
RE_FECHA_FACTURA = re.compile(r"Fecha\s+Factura:\s*(\d{2}/\d{2}/\d{4})")
RE_TIPO_USUARIO = re.compile(r"Tipo\s+Usuario:[ \t]*([^\n]+)", re.IGNORECASE)

# ---- Formato B: campos con etiqueta ------------------------------------------
RE_B_PACIENTE = re.compile(r"Paciente:[ \t]*(.+)", re.IGNORECASE)
RE_B_DOCUMENTO = re.compile(rf"Documento:[ \t]*({TIPOS_DOC})[ \t]+(\d[0-9A-Z]*)", re.IGNORECASE)
RE_B_EMPRESA = re.compile(r"Empresa:[ \t]*(.+)", re.IGNORECASE)
RE_NIT_INICIAL = re.compile(r"^\d[\d.]*\s*-\s*\d\s+")      # "900935126 - 7 "

# Etiquetas de la columna derecha que pdfplumber deja en la misma línea
# (aunque vengan pegadas: "...EPS SASTeléfono: 318..."). Exigir los ":" evita
# cortar un apellido que coincida con una palabra.
RE_ETIQUETA_DERECHA = re.compile(
    r"\s*(Forma\s+pago|Plazo\s*\(D[ií]as\)|Tel[eé]fono|Plan\s+Beneficio|Tipo\s+Usuario"
    r"|Direcci[oó]n)\s*:.*$",
    re.IGNORECASE)


def _limpiar_valor(texto: str) -> str:
    """Quita lo que pertenece a la columna derecha: 'PEÑA CARMEN Forma pago: Crédito' -> 'PEÑA CARMEN'."""
    return RE_ETIQUETA_DERECHA.sub("", texto).strip()


class LectorFEV:

    def __init__(self, perfil: PerfilAseguradora = None):
        self.perfil = perfil
        self._re_archivo = re.compile(PATRON_ARCHIVO_FEV, re.IGNORECASE)

    # ------------------------------------------------------------------ API
    def es_archivo_fev(self, ruta: Path) -> bool:
        return self._re_archivo.match(ruta.name) is not None

    def leer(self, ruta) -> Factura:
        ruta = Path(ruta)
        factura = Factura(ruta=ruta)

        # 1) Consecutivo desde el nombre del archivo (fuente principal)
        m = self._re_archivo.match(ruta.name)
        if m:
            factura.consecutivo, factura.numero = m.group(1).upper(), m.group(2)
        else:
            factura.agregar_obs("Nombre de archivo no cumple FEV_813003431_LPG#####")

        # 2) Texto del PDF
        try:
            texto = self._extraer_texto(ruta)
        except Exception as e:
            factura.agregar_obs(f"No se pudo abrir el PDF: {e}", EstadoLectura.ERROR)
            return factura

        if not texto.strip():
            factura.agregar_obs("PDF sin texto (¿escaneado?)", EstadoLectura.ERROR)
            return factura

        self._leer_consecutivo(texto, factura)
        self._leer_paciente(texto, factura)
        self._leer_administradora(texto, factura)

        m = RE_FECHA_FACTURA.search(texto)
        if m:
            factura.fecha_factura = m.group(1)

        m = RE_TIPO_USUARIO.search(texto)
        if m:
            factura.tipo_usuario = m.group(1).strip()
        self._validar_regimen(factura)

        return factura

    # ------------------------------------------------------------ internos
    @staticmethod
    def _extraer_texto(ruta: Path) -> str:
        # La info que necesitamos siempre está en la primera página
        with pdfplumber.open(ruta) as pdf:
            return pdf.pages[0].extract_text() or ""

    @staticmethod
    def _leer_consecutivo(texto: str, f: Factura):
        m = RE_CONSECUTIVO.search(texto)
        if not m:
            if not f.consecutivo:
                f.agregar_obs("No se encontró el consecutivo", EstadoLectura.ERROR)
            return
        del_pdf = m.group(1).upper()
        if f.consecutivo and del_pdf != f.consecutivo:
            f.agregar_obs(f"Nombre de archivo ({f.consecutivo}) no coincide con el PDF "
                          f"({del_pdf}); se usa el del PDF")
        # El contenido del PDF es la fuente de verdad
        f.consecutivo, f.numero = del_pdf, del_pdf[3:]

    @staticmethod
    def _leer_paciente(texto: str, f: Factura):
        # Formato B: "Paciente:" + "Documento: CC 123"
        m_doc = RE_B_DOCUMENTO.search(texto)
        m_pac = RE_B_PACIENTE.search(texto)
        if m_doc and m_pac and _limpiar_valor(m_pac.group(1)):
            f.tipo_doc, f.num_doc = m_doc.group(1).upper(), m_doc.group(2)
            f.nombre = _limpiar_valor(m_pac.group(1))
            return

        # Formato A: "CC 40422190 NOMBRE Tipo Usuario: ..."
        m = RE_PACIENTE.search(texto)
        if m:
            f.tipo_doc, f.num_doc = m.group(1), m.group(2)
            f.nombre = _limpiar_valor(m.group(3))
            return

        f.agregar_obs("No se encontraron los datos del paciente", EstadoLectura.ERROR)

    def _leer_administradora(self, texto: str, f: Factura):
        m = RE_ADMINISTRADORA.search(texto)
        if m:
            f.administradora = _limpiar_valor(m.group(1))
        else:
            m = RE_B_EMPRESA.search(texto)
            if m:
                f.administradora = RE_NIT_INICIAL.sub("", _limpiar_valor(m.group(1))).strip()

        if not self.perfil:
            return

        # Perfiles que se reconocen por el texto (SOAT: "Cobertura Póliza SOAT")
        if self.perfil.palabras_texto:
            if not any(p in texto.upper() for p in self.perfil.palabras_texto):
                f.otra_aseguradora = True
                f.agregar_obs(f"La factura no es de {self.perfil.nombre} "
                              f"(administradora: {f.administradora or 'no encontrada'})")
            return

        if not self.perfil.palabras_administradora:
            return
        if not f.administradora:
            # No se pudo leer: se incluye, pero se avisa (no se excluye a ciegas)
            f.agregar_obs("No se encontró la administradora; verifica que sea "
                          f"{self.perfil.nombre}")
            return
        adm = f.administradora.upper()
        if not any(p in adm for p in self.perfil.palabras_administradora):
            f.otra_aseguradora = True
            f.agregar_obs(f"Administradora '{f.administradora}' no es {self.perfil.nombre}")

    def _validar_regimen(self, f: Factura):
        """Nueva EPS: el 'Tipo Usuario' debe coincidir con el régimen escogido."""
        if not (self.perfil and self.perfil.regimen) or f.otra_aseguradora:
            return
        if not f.tipo_usuario:
            f.agregar_obs(f"No se encontró el Tipo Usuario; verifica que sea "
                          f"{self.perfil.regimen.capitalize()}")
            return
        if self.perfil.regimen.upper() not in f.tipo_usuario.upper():
            f.otro_regimen = True
            f.agregar_obs(f"Tipo Usuario '{f.tipo_usuario}' no es "
                          f"{self.perfil.regimen.capitalize()}")
