"""
Fase 1: organiza las FEV en <CARPETA PADRE>/<NOMBRE CONSECUTIVO>/ y genera el Excel.

Trabaja en dos pasadas:
  1) Lee todas las FEV (y, si la carpeta es dinámica como en SOAT, decide su
     nombre con la aseguradora que más se repite).
  2) Copia cada FEV a su carpeta.

No depende de PyQt: recibe callbacks para progreso y cancelación, así se puede
usar desde el worker (interfaz) o desde consola.
"""
import shutil
from collections import Counter
from pathlib import Path
from typing import Callable, Optional

from app.config.aseguradoras import PerfilAseguradora, nombre_corto_aseguradora
from app.core.modelos import AccionFase1, ItemFase1, ResultadoFase1
from app.services.exportador_excel import ExportadorExcel
from app.services.lector_fev import LectorFEV
from app.utils.nombres import nombre_carpeta_seguro

Progreso = Callable[[int, int, str], None]    # (actual, total, mensaje)
Cancelado = Callable[[], bool]


class OrganizadorFEV:

    def __init__(self, perfil: PerfilAseguradora,
                 lector: LectorFEV = None, exportador: ExportadorExcel = None):
        self.perfil = perfil
        self.lector = lector or LectorFEV(perfil)
        self.exportador = exportador or ExportadorExcel()

    # ------------------------------------------------------------------ API
    def rutas_destino(self, carpeta_destino: Path, nombre_padre: str = None):
        """Dónde quedarán la carpeta padre y el Excel."""
        carpeta_destino = Path(carpeta_destino)
        nombre = nombre_padre or self.perfil.carpeta_padre
        return carpeta_destino / nombre, carpeta_destino / f"{nombre} - PACIENTES.xlsx"

    def ejecutar(self, carpeta_origen, carpeta_destino,
                 progreso: Optional[Progreso] = None,
                 cancelado: Optional[Cancelado] = None) -> ResultadoFase1:
        progreso = progreso or (lambda *a: None)
        cancelado = cancelado or (lambda: False)

        pdfs = sorted(p for p in Path(carpeta_origen).iterdir()
                      if p.is_file() and p.suffix.lower() == ".pdf")
        total = len(pdfs)
        fueron_cancelados = False

        # ---- 1) Leer todas
        facturas = []
        for n, ruta in enumerate(pdfs, 1):
            if cancelado():
                fueron_cancelados = True
                break
            f = self.lector.leer(ruta)
            facturas.append(f)
            progreso(n, total, f"Leyendo {f.consecutivo or ruta.name}")

        # ---- Nombre de la carpeta padre
        nombre_padre = self.perfil.carpeta_padre
        if self.perfil.carpeta_dinamica:
            nombre_padre = self._nombre_dinamico(facturas)
        carpeta_padre, ruta_excel = self.rutas_destino(carpeta_destino, nombre_padre)
        carpeta_padre.mkdir(parents=True, exist_ok=True)
        resultado = ResultadoFase1(carpeta_padre=carpeta_padre, cancelado=fueron_cancelados)

        # ---- 2) Copiar
        vistos = set()
        for n, factura in enumerate(facturas, 1):
            if cancelado():
                resultado.cancelado = True
                break
            item = self._organizar(factura, carpeta_padre, nombre_padre, vistos)
            resultado.items.append(item)
            progreso(n, len(facturas), f"{factura.consecutivo or factura.ruta.name}: {item.accion.value}")

        progreso(total, total, "Generando Excel...")
        resultado.ruta_excel = self.exportador.exportar_fase1(resultado, ruta_excel)
        return resultado

    # ------------------------------------------------------------ internos
    def _nombre_dinamico(self, facturas) -> str:
        """SOAT: 'SOAT ' + la aseguradora que más se repite entre las facturas válidas."""
        conteo = Counter(nombre_corto_aseguradora(f.administradora) for f in facturas
                         if f.es_valida and not f.otra_aseguradora and f.administradora)
        if not conteo:
            return self.perfil.carpeta_padre
        return nombre_carpeta_seguro(f"{self.perfil.carpeta_padre} {conteo.most_common(1)[0][0]}")

    def _organizar(self, factura, carpeta_padre: Path, nombre_padre: str, vistos: set) -> ItemFase1:
        if not factura.es_valida:
            return ItemFase1(factura, AccionFase1.EXCLUIDA_ERROR)
        if factura.otra_aseguradora:
            return ItemFase1(factura, AccionFase1.EXCLUIDA_OTRA_ASEGURADORA)
        if factura.otro_regimen:
            return ItemFase1(factura, AccionFase1.EXCLUIDA_OTRO_REGIMEN)
        if self.perfil.carpeta_dinamica and factura.administradora:
            propia = nombre_carpeta_seguro(
                f"{self.perfil.carpeta_padre} {nombre_corto_aseguradora(factura.administradora)}")
            if propia != nombre_padre:
                factura.otra_aseguradora = True
                factura.agregar_obs(f"Es de {factura.administradora}; la carpeta es {nombre_padre}. "
                                    f"Organízala en un lote aparte")
                return ItemFase1(factura, AccionFase1.EXCLUIDA_OTRA_ASEGURADORA)
        if factura.consecutivo in vistos:
            factura.agregar_obs("Consecutivo repetido en la carpeta de origen")
            return ItemFase1(factura, AccionFase1.EXCLUIDA_DUPLICADA)
        vistos.add(factura.consecutivo)

        carpeta = carpeta_padre / factura.nombre_carpeta
        carpeta.mkdir(exist_ok=True)
        destino = carpeta / factura.nombre_fev     # Siempre con el nombre correcto

        if destino.exists():
            return ItemFase1(factura, AccionFase1.YA_EXISTIA, destino)
        shutil.copy2(factura.ruta, destino)
        return ItemFase1(factura, AccionFase1.COPIADA, destino)
