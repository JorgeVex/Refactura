"""
Fase 2: arma PDE y HEV por carpeta (paciente + factura) y genera el reporte.

Reglas:
- Se une en el orden definido en el perfil.
- Si faltan obligatorios, el paquete SE ARMA igual con lo que haya y queda INCOMPLETO.
- Si no hay ningún soporte para un paquete, no se crea (y no se toca uno existente).
- Los soportes originales no se modifican.
"""
import logging
import os
from pathlib import Path
from typing import Callable, Optional

from pypdf import PdfReader, PdfWriter

from app.config.aseguradoras import PerfilAseguradora, ReglaPaquete
from app.config.constantes import nombre_paquete
from app.core.modelos import ResultadoCarpeta, ResultadoFase2, ResultadoPaquete
from app.services.clasificador_soportes import Clasificacion, ClasificadorSoportes
from app.services.exportador_excel import ExportadorExcel

Progreso = Callable[[int, int, str], None]
Cancelado = Callable[[], bool]

# Los PDF dañados ya se reportan en el Excel; no ensuciar la consola
logging.getLogger("pypdf").setLevel(logging.ERROR)


class UnidorPDF:
    """Une varios PDF en uno. Un archivo dañado no detiene el resto."""

    @staticmethod
    def unir(entradas: list, salida: Path):
        """entradas: [(codigo, Path)]. Devuelve (rutas_unidas, errores)."""
        unidas, errores, escritor = [], [], PdfWriter()
        for codigo, ruta in entradas:
            try:
                lector = PdfReader(str(ruta))
                if lector.is_encrypted:
                    lector.decrypt("")
                paginas = list(lector.pages)          # Si falla, falla antes de agregar
                for pagina in paginas:
                    escritor.add_page(pagina)
                unidas.append(ruta)
            except Exception as e:
                errores.append(f"{ruta.name} dañado o ilegible ({type(e).__name__})")

        if not unidas:
            return unidas, errores + ["Ningún soporte se pudo leer"]

        # Escribir a temporal y reemplazar: nunca queda un PDF a medias
        temporal = salida.with_suffix(".tmp")
        with open(temporal, "wb") as fh:
            escritor.write(fh)
        os.replace(temporal, salida)
        return unidas, errores


class ArmadorPaquetes:

    def __init__(self, perfil: PerfilAseguradora, clasificador=None,
                 unidor=None, exportador=None):
        self.perfil = perfil
        self.clasificador = clasificador or ClasificadorSoportes(perfil)
        self.unidor = unidor or UnidorPDF()
        self.exportador = exportador or ExportadorExcel()

    # ------------------------------------------------------------------ API
    def ruta_reporte(self, carpeta_padre: Path) -> Path:
        carpeta_padre = Path(carpeta_padre)
        return carpeta_padre.parent / f"{carpeta_padre.name} - REPORTE SOPORTES.xlsx"

    def ejecutar(self, carpeta_padre, progreso: Optional[Progreso] = None,
                 cancelado: Optional[Cancelado] = None) -> ResultadoFase2:
        progreso = progreso or (lambda *a: None)
        cancelado = cancelado or (lambda: False)
        carpeta_padre = Path(carpeta_padre)
        resultado = ResultadoFase2(carpeta_padre=carpeta_padre)

        carpetas = sorted(p for p in carpeta_padre.iterdir() if p.is_dir())
        total = len(carpetas)
        for n, carpeta in enumerate(carpetas, 1):
            if cancelado():
                resultado.cancelado = True
                break
            item = self.procesar_carpeta(carpeta)
            resultado.items.append(item)
            estado = "Completo" if item.completo else "INCOMPLETO"
            progreso(n, total, f"{carpeta.name}: {estado}")

        progreso(total, total, "Generando reporte...")
        resultado.ruta_excel = self.exportador.exportar_fase2(
            resultado, self.ruta_reporte(carpeta_padre))
        return resultado

    def procesar_carpeta(self, carpeta: Path) -> ResultadoCarpeta:
        cl = self.clasificador.clasificar(carpeta)
        r = ResultadoCarpeta(carpeta=carpeta, consecutivo=cl.consecutivo,
                             no_reconocidos=cl.no_reconocidos)

        if len(cl.fevs) == 1:
            r.fev = cl.fevs[0]
        elif len(cl.fevs) > 1:
            r.fev = cl.fevs[0]
            r.observaciones.append(f"Hay {len(cl.fevs)} FEV en la carpeta")
        if not r.consecutivo:
            r.observaciones.append("No se pudo determinar el consecutivo")
            return r

        r.pde = self._armar(self.perfil.regla_pde, cl, carpeta, r.consecutivo)
        r.hev = self._armar(self.perfil.regla_hev, cl, carpeta, r.consecutivo)
        return r

    # ------------------------------------------------------------ internos
    def _armar(self, regla: ReglaPaquete, cl: Clasificacion,
               carpeta: Path, consecutivo: str) -> ResultadoPaquete:
        res = ResultadoPaquete(prefijo=regla.prefijo)
        entradas = []
        for d in regla.soportes:                       # El orden de la regla manda
            archivos = cl.soportes.get(d.codigo, [])
            if not archivos and d.obligatorio:
                res.faltantes.append(d.codigo)
            entradas += [(d.codigo, ruta) for ruta in archivos]

        if not entradas:
            return res                                  # Nada que unir

        salida = carpeta / nombre_paquete(regla.prefijo, consecutivo)
        unidas, res.errores = self.unidor.unir(entradas, salida)
        res.incluidos = [r.stem.upper() for r in unidas]
        if unidas:
            res.ruta = salida
        return res
