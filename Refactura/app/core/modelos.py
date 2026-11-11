"""Modelos de dominio."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.config.constantes import nombre_paquete, PREFIJO_FEV
from app.utils.nombres import nombre_carpeta_seguro


class EstadoLectura(str, Enum):
    OK = "OK"
    ADVERTENCIA = "ADVERTENCIA"   # Se leyó, pero algo no cuadra (ej. otra aseguradora)
    ERROR = "ERROR"               # No se pudo leer


@dataclass
class Factura:
    ruta: Path
    consecutivo: str = ""          # LPG146513
    numero: str = ""               # 146513
    tipo_doc: str = ""             # CC
    num_doc: str = ""              # 40422190
    nombre: str = ""               # PARRA ESPINOSA YULI ESPERANZA
    administradora: str = ""
    fecha_factura: str = ""
    estado: EstadoLectura = EstadoLectura.OK
    observaciones: list = field(default_factory=list)
    tipo_usuario: str = ""           # "Subsidiado", "Contributivo", "Tomador/Amparado SOAT"...
    otra_aseguradora: bool = False   # True = la FEV no es de la aseguradora seleccionada
    otro_regimen: bool = False       # True = el régimen no coincide con el escogido

    # -- helpers ------------------------------------------------------------
    def agregar_obs(self, texto: str, estado: EstadoLectura = EstadoLectura.ADVERTENCIA):
        self.observaciones.append(texto)
        # El estado solo empeora: OK -> ADVERTENCIA -> ERROR
        orden = [EstadoLectura.OK, EstadoLectura.ADVERTENCIA, EstadoLectura.ERROR]
        if orden.index(estado) > orden.index(self.estado):
            self.estado = estado

    @property
    def es_valida(self) -> bool:
        return self.estado != EstadoLectura.ERROR

    @property
    def nombre_carpeta(self) -> str:
        """Carpeta inicial del paciente: 'PARRA ESPINOSA YULI ESPERANZA 146513'."""
        return nombre_carpeta_seguro(f"{self.nombre} {self.numero}")

    @property
    def nombre_carpeta_final(self) -> str:
        """Carpeta después de la limpieza: solo el número."""
        return self.numero

    @property
    def nombre_fev(self) -> str:
        return nombre_paquete(PREFIJO_FEV, self.consecutivo)

    def como_fila_excel(self) -> dict:
        return {
            "Nombre": self.nombre,
            "Tipo documento": self.tipo_doc,
            "N° documento": self.num_doc,
            "Consecutivo": self.consecutivo,
            "Fecha factura": self.fecha_factura,
            "Administradora": self.administradora,
            "Estado": self.estado.value,
            "Observaciones": "; ".join(self.observaciones),
        }


# ---------------------------------------------------------------------------
# Fase 1
# ---------------------------------------------------------------------------
class AccionFase1(str, Enum):
    COPIADA = "Copiada"
    YA_EXISTIA = "Ya existía (no se copió de nuevo)"
    EXCLUIDA_OTRA_ASEGURADORA = "Excluida: otra aseguradora"
    EXCLUIDA_OTRO_REGIMEN = "Excluida: régimen distinto al escogido"
    EXCLUIDA_DUPLICADA = "Excluida: consecutivo duplicado"
    EXCLUIDA_ERROR = "Excluida: error de lectura"


@dataclass
class ItemFase1:
    factura: Factura
    accion: AccionFase1
    ruta_destino: Path = None

    @property
    def incluida(self) -> bool:
        return self.accion in (AccionFase1.COPIADA, AccionFase1.YA_EXISTIA)


@dataclass
class ResultadoFase1:
    carpeta_padre: Path
    items: list = field(default_factory=list)
    ruta_excel: Path = None
    cancelado: bool = False

    @property
    def incluidas(self):
        return [i for i in self.items if i.incluida]

    @property
    def excluidas(self):
        return [i for i in self.items if not i.incluida]

    @property
    def con_novedad(self):
        """Excluidas + incluidas con advertencias: lo que el usuario debe revisar."""
        return [i for i in self.items
                if not i.incluida or i.factura.estado != EstadoLectura.OK]

    def resumen(self) -> str:
        pacientes = {(i.factura.tipo_doc, i.factura.num_doc) for i in self.incluidas}
        return (f"Facturas organizadas: {len(self.incluidas)} "
                f"({len(pacientes)} pacientes) | Excluidas: {len(self.excluidas)} | "
                f"Con novedad: {len(self.con_novedad)}")


# ---------------------------------------------------------------------------
# Fase 2
# ---------------------------------------------------------------------------
@dataclass
class ResultadoPaquete:
    prefijo: str                                      # "PDE" / "HEV"
    ruta: Path = None                                 # None = no se armó
    incluidos: list = field(default_factory=list)     # Códigos unidos, en orden
    faltantes: list = field(default_factory=list)     # Obligatorios que no estaban
    errores: list = field(default_factory=list)       # PDFs dañados, etc.

    @property
    def armado(self) -> bool:
        return self.ruta is not None

    @property
    def completo(self) -> bool:
        return self.armado and not self.faltantes and not self.errores


@dataclass
class ResultadoCarpeta:
    carpeta: Path
    consecutivo: str = ""
    fev: Path = None
    pde: ResultadoPaquete = None
    hev: ResultadoPaquete = None
    no_reconocidos: list = field(default_factory=list)   # Nombres de archivos
    observaciones: list = field(default_factory=list)

    @property
    def completo(self) -> bool:
        return (self.fev is not None and not self.observaciones
                and all(p and p.completo for p in (self.pde, self.hev)))

    @property
    def faltantes(self) -> list:
        f = [] if self.fev else ["FEV"]
        for p in (self.pde, self.hev):
            if p:
                f += [f"{c} ({p.prefijo})" for c in p.faltantes]
        return f

    def que_hacer(self) -> str:
        """Instrucción en lenguaje sencillo para el usuario (columna 'Qué hacer')."""
        pasos, correr_fase2 = [], False

        if not self.consecutivo:
            return ("Revisa la carpeta: no tiene FEV y su nombre no termina en el número "
                    "del consecutivo.")
        if self.fev is None:
            fev = _sin_pdf(nombre_paquete(PREFIJO_FEV, self.consecutivo))
            pasos.append(f"Copiar la factura {fev} (de la carpeta original de FEV) "
                         f"en esta carpeta")
            correr_fase2 = True
        if any(o.startswith("Hay ") and "FEV" in o for o in self.observaciones):
            pasos.append("Dejar solo la FEV que corresponde a esta carpeta (hay más de una)")
            correr_fase2 = True

        soportes = [c for p in (self.pde, self.hev) if p for c in p.faltantes]
        if soportes:
            pasos.append(f"Descargar {_enumerar(soportes)}")
            correr_fase2 = True

        danados = [_sin_pdf(e.split(" dañado")[0]) for p in (self.pde, self.hev) if p
                   for e in p.errores if " dañado" in e]
        if danados:
            if len(danados) == 1:
                pasos.append(f"Volver a descargar {danados[0]} (está dañado) y reemplazarlo")
            else:
                pasos.append(f"Volver a descargar {_enumerar(danados)} (están dañados) "
                             f"y reemplazarlos")
            correr_fase2 = True

        if self.no_reconocidos:
            otros = [_sin_pdf(n) for n in self.no_reconocidos]
            pasos.append(f"Revisar {_enumerar(otros)}: si es un soporte, renombrarlo con su "
                         f"código (ej. ANE2); si no, se puede dejar")
            correr_fase2 = correr_fase2 or not self.completo

        if not pasos:
            return "Listo para limpiar" if self.completo else "Revisar la carpeta manualmente"
        if correr_fase2:
            pasos.append("Correr de nuevo la Fase 2")
        if len(pasos) == 1:
            return pasos[0]
        return " ".join(f"{n}) {p}." for n, p in enumerate(pasos, 1))


@dataclass
class ResultadoFase2:
    carpeta_padre: Path
    items: list = field(default_factory=list)
    ruta_excel: Path = None
    cancelado: bool = False

    @property
    def completos(self):
        return [i for i in self.items if i.completo]

    @property
    def incompletos(self):
        return [i for i in self.items if not i.completo]

    def resumen(self) -> str:
        return (f"Carpetas procesadas: {len(self.items)} | Completas: {len(self.completos)} "
                f"| Incompletas: {len(self.incompletos)}")


# ---------------------------------------------------------------------------
# Fase 3
# ---------------------------------------------------------------------------
class AccionFase3(str, Enum):
    LIMPIAR = "Limpiar y renombrar"
    YA_LIMPIA = "Ya estaba limpia"
    OMITIR = "Omitida"
    LIMPIADA = "Limpiada"
    ERROR = "Error"


@dataclass
class PlanCarpeta:
    """Lo que se hará con una carpeta (se calcula antes de tocar nada)."""
    carpeta: Path
    numero: str = ""                                   # Nombre final: "146513"
    conservar: list = field(default_factory=list)      # FEV, PDE, HEV
    respaldar: list = field(default_factory=list)      # Todo lo demás
    accion: AccionFase3 = AccionFase3.LIMPIAR
    motivo: str = ""


@dataclass
class ResultadoLimpieza:
    plan: PlanCarpeta
    carpeta_final: Path = None
    respaldados: int = 0
    errores: list = field(default_factory=list)

    @property
    def accion(self) -> AccionFase3:
        if self.errores:
            return AccionFase3.ERROR
        if self.plan.accion == AccionFase3.LIMPIAR:
            return AccionFase3.LIMPIADA
        return self.plan.accion


@dataclass
class ResultadoFase3:
    carpeta_padre: Path
    carpeta_respaldo: Path
    items: list = field(default_factory=list)
    ruta_excel: Path = None
    cancelado: bool = False

    def contar(self, accion: AccionFase3) -> int:
        return sum(1 for i in self.items if i.accion == accion)

    def resumen(self) -> str:
        return (f"Limpiadas: {self.contar(AccionFase3.LIMPIADA)} | "
                f"Ya limpias: {self.contar(AccionFase3.YA_LIMPIA)} | "
                f"Omitidas: {self.contar(AccionFase3.OMITIR)} | "
                f"Con error: {self.contar(AccionFase3.ERROR)}")


def _enumerar(items: list) -> str:
    """['A'] -> 'A' | ['A','B'] -> 'A y B' | ['A','B','C'] -> 'A, B y C'"""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} y {items[-1]}"


def _sin_pdf(nombre: str) -> str:
    """'BIT.pdf' -> 'BIT'. Otros tipos de archivo conservan su extensión ('notas.txt')."""
    return nombre[:-4] if nombre.lower().endswith(".pdf") else nombre
