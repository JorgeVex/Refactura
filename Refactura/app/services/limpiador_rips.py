"""
Limpiador de RIPS.

En la carpeta padre hay una subcarpeta por factura. En cada una se CONSERVAN:
  - el .json  (RIPS)
  - el .xml   (factura electrónica)
  - el plano .txt cuyo nombre termina en CUV (ej. ResultadosMSPS_LPG152460_ID329310568_A_CUV.txt)
y se ELIMINAN DEFINITIVAMENTE todos los demás archivos (ResultadosLocales_..., ..._R, etc.).

Seguridad:
- Primero se PLANEA (no toca nada) para mostrar la confirmación con los números exactos.
- Si una carpeta NO tiene CUV (RIPS rechazados o sin validar), no se le borra nada:
  el archivo de resultados es el que explica el rechazo.
- Se decide por la EXTENSIÓN real (Windows la oculta), no por el contenido: los
  ResultadosMSPS son .txt aunque por dentro tengan texto con formato JSON.
"""
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

Progreso = Callable[[int, int, str], None]
Cancelado = Callable[[], bool]

# Archivos de sistema de Windows: ni se cuentan ni se tocan
_IGNORAR = {"desktop.ini", "thumbs.db"}


class TipoArchivo(str, Enum):
    JSON = "JSON"
    XML = "XML"
    CUV = "CUV"
    OTRO = "Otro"


def tipo_archivo(ruta: Path) -> TipoArchivo:
    ext = ruta.suffix.lower()
    if ext == ".json":
        return TipoArchivo.JSON
    if ext == ".xml":
        return TipoArchivo.XML
    if ext == ".txt" and ruta.stem.upper().endswith("CUV"):
        return TipoArchivo.CUV
    # Por si el XML se guardó como .htm/.html (Windows lo muestra como "Edge HTML Document")
    if ext in (".htm", ".html") and _empieza_con(ruta, b"<?xml"):
        return TipoArchivo.XML
    return TipoArchivo.OTRO


def _empieza_con(ruta: Path, prefijo: bytes) -> bool:
    try:
        with open(ruta, "rb") as fh:
            return fh.read(64).lstrip(b"\xef\xbb\xbf \r\n\t").startswith(prefijo)
    except OSError:
        return False


class EstadoRIPS(str, Enum):
    LIMPIAR = "Se limpiará"
    YA_LIMPIA = "Ya estaba limpia"
    SIN_CUV = "Sin CUV (no se tocó)"
    VACIA = "Carpeta vacía"
    LIMPIADA = "Limpiada"
    ERROR = "Error"


@dataclass
class PlanRIPS:
    carpeta: Path
    conservar: list = field(default_factory=list)
    eliminar: list = field(default_factory=list)
    estado: EstadoRIPS = EstadoRIPS.LIMPIAR
    observaciones: list = field(default_factory=list)
    errores: list = field(default_factory=list)
    eliminados: int = 0

    def contar(self, tipo: TipoArchivo) -> int:
        return sum(1 for r in self.conservar if tipo_archivo(r) == tipo)


@dataclass
class ResultadoRIPS:
    carpeta_padre: Path
    items: list = field(default_factory=list)
    ruta_excel: Path = None
    cancelado: bool = False

    def contar(self, estado: EstadoRIPS) -> int:
        return sum(1 for i in self.items if i.estado == estado)

    @property
    def eliminados(self) -> int:
        return sum(i.eliminados for i in self.items)

    def resumen(self) -> str:
        return (f"Limpiadas: {self.contar(EstadoRIPS.LIMPIADA)} | "
                f"Ya limpias: {self.contar(EstadoRIPS.YA_LIMPIA)} | "
                f"Sin CUV: {self.contar(EstadoRIPS.SIN_CUV)} | "
                f"Con error: {self.contar(EstadoRIPS.ERROR)} | "
                f"Archivos eliminados: {self.eliminados}")


class LimpiadorRIPS:

    def __init__(self, exportador=None):
        from app.services.exportador_excel import ExportadorExcel
        self.exportador = exportador or ExportadorExcel()

    # ------------------------------------------------------------------ API
    @staticmethod
    def ruta_reporte(carpeta_padre: Path) -> Path:
        carpeta_padre = Path(carpeta_padre)
        return carpeta_padre.parent / f"{carpeta_padre.name} - LIMPIEZA RIPS.xlsx"

    def planear(self, carpeta_padre) -> list:
        carpetas = sorted(p for p in Path(carpeta_padre).iterdir() if p.is_dir())
        return [self._planear_carpeta(c) for c in carpetas]

    def ejecutar(self, carpeta_padre, plan: list = None,
                 progreso: Optional[Progreso] = None,
                 cancelado: Optional[Cancelado] = None) -> ResultadoRIPS:
        progreso = progreso or (lambda *a: None)
        cancelado = cancelado or (lambda: False)
        carpeta_padre = Path(carpeta_padre)
        plan = plan if plan is not None else self.planear(carpeta_padre)
        resultado = ResultadoRIPS(carpeta_padre=carpeta_padre)

        total = len(plan)
        for n, p in enumerate(plan, 1):
            if cancelado():
                resultado.cancelado = True
                break
            if p.estado == EstadoRIPS.LIMPIAR:
                self._eliminar(p)
            resultado.items.append(p)
            progreso(n, total, f"{p.carpeta.name}: {p.estado.value}")

        progreso(total, total, "Generando reporte...")
        resultado.ruta_excel = self.exportador.exportar_rips(resultado, self.ruta_reporte(carpeta_padre))
        return resultado

    # ------------------------------------------------------------ internos
    def _planear_carpeta(self, carpeta: Path) -> PlanRIPS:
        p = PlanRIPS(carpeta=carpeta)
        archivos = [a for a in sorted(carpeta.iterdir())
                    if a.is_file() and a.name.lower() not in _IGNORAR]
        subcarpetas = [a.name for a in carpeta.iterdir() if a.is_dir()]
        if subcarpetas:
            p.observaciones.append(f"Tiene subcarpetas (no se revisan): {', '.join(subcarpetas)}")

        for a in archivos:
            (p.conservar if tipo_archivo(a) != TipoArchivo.OTRO else p.eliminar).append(a)

        n_cuv, n_json, n_xml = (p.contar(t) for t in (TipoArchivo.CUV, TipoArchivo.JSON, TipoArchivo.XML))
        if not archivos:
            p.estado = EstadoRIPS.VACIA
            return p
        if n_cuv == 0:
            p.estado = EstadoRIPS.SIN_CUV
            p.observaciones.insert(0, "No tiene el plano CUV: no se borró nada (revisa si los RIPS fueron rechazados)")
            return p

        if n_json == 0:
            p.observaciones.append("Falta el JSON")
        if n_xml == 0:
            p.observaciones.append("Falta el XML")
        for tipo, n in ((TipoArchivo.CUV, n_cuv), (TipoArchivo.JSON, n_json), (TipoArchivo.XML, n_xml)):
            if n > 1:
                p.observaciones.append(f"Hay {n} archivos {tipo.value}")
        if not p.eliminar:
            p.estado = EstadoRIPS.YA_LIMPIA
        return p

    @staticmethod
    def _eliminar(p: PlanRIPS):
        for a in p.eliminar:
            try:
                os.remove(a)
                p.eliminados += 1
            except PermissionError:
                p.errores.append(f"{a.name}: abierto en otro programa o sin permisos")
            except FileNotFoundError:
                pass                                  # Ya no estaba: nada que hacer
            except OSError as e:
                p.errores.append(f"{a.name}: {e}")
        p.estado = EstadoRIPS.ERROR if p.errores else EstadoRIPS.LIMPIADA
