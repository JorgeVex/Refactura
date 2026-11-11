"""Exportación de resultados a Excel (openpyxl)."""
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.modelos import ResultadoFase1, EstadoLectura

_FILL_ENCABEZADO = PatternFill("solid", fgColor="1F4E78")
_FONT_ENCABEZADO = Font(bold=True, color="FFFFFF")
_FILL_ADVERTENCIA = PatternFill("solid", fgColor="FFF2CC")
_FILL_ERROR = PatternFill("solid", fgColor="F8CBAD")


class ExportadorExcel:

    # ------------------------------------------------------------ Fase 1
    def exportar_fase1(self, resultado: ResultadoFase1, ruta: Path) -> Path:
        wb = Workbook()

        # Hoja 1: pacientes (solo facturas incluidas) -> para descargar soportes
        ws = wb.active
        ws.title = "Pacientes"
        enc = ["N°", "Nombre", "Tipo documento", "N° documento",
               "Consecutivo", "Fecha factura", "Carpeta"]
        filas = []
        incluidas = sorted(resultado.incluidas,
                           key=lambda i: (i.factura.nombre, i.factura.numero))
        for n, item in enumerate(incluidas, 1):
            f = item.factura
            filas.append([n, f.nombre, f.tipo_doc, f.num_doc,
                          f.consecutivo, f.fecha_factura, f.nombre_carpeta])
        self._llenar_hoja(ws, enc, filas, columnas_texto={4})

        # Hoja 2: novedades (excluidas + advertencias) -> para revisar
        ws2 = wb.create_sheet("Novedades")
        enc2 = ["Archivo", "Consecutivo", "Nombre", "Administradora",
                "Estado", "Acción", "Observaciones"]
        filas2, estados = [], []
        for item in resultado.con_novedad:
            f = item.factura
            filas2.append([f.ruta.name, f.consecutivo, f.nombre, f.administradora,
                           f.estado.value, item.accion.value, "; ".join(f.observaciones)])
            estados.append(EstadoLectura.ERROR if not item.incluida else f.estado)
        self._llenar_hoja(ws2, enc2, filas2)
        for fila_excel, estado in enumerate(estados, 2):
            fill = _FILL_ERROR if estado == EstadoLectura.ERROR else _FILL_ADVERTENCIA
            for celda in ws2[fila_excel]:
                celda.fill = fill

        return self._guardar(wb, ruta)

    # ------------------------------------------------------------ Fase 2
    def exportar_fase2(self, resultado, ruta: Path) -> Path:
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte"
        enc = ["Carpeta", "Consecutivo", "Estado", "Qué hacer", "Faltantes",
               "PDE (unidos)", "HEV (unidos)", "No reconocidos", "Observaciones"]

        # Incompletas primero: es lo que el usuario debe revisar
        items = sorted(resultado.items, key=lambda i: (i.completo, i.carpeta.name))
        filas = []
        for it in items:
            obs = list(it.observaciones)
            for p in (it.pde, it.hev):
                if p:
                    obs += p.errores
                    if not p.armado:
                        obs.append(f"{p.prefijo} no se armó (sin soportes)")
            filas.append([
                it.carpeta.name, it.consecutivo,
                "Completo" if it.completo else "INCOMPLETO",
                it.que_hacer(),
                ", ".join(it.faltantes),
                ", ".join(it.pde.incluidos) if it.pde else "",
                ", ".join(it.hev.incluidos) if it.hev else "",
                ", ".join(it.no_reconocidos),
                "; ".join(obs),
            ])
        self._llenar_hoja(ws, enc, filas)
        for fila_excel, it in enumerate(items, 2):
            if not it.completo:
                for celda in ws[fila_excel]:
                    celda.fill = _FILL_ERROR if it.faltantes else _FILL_ADVERTENCIA

        # "Qué hacer": columna ancha, con ajuste de texto y en negrilla si hay acción
        ws.column_dimensions["D"].width = 60
        for fila_excel, it in enumerate(items, 2):
            celda = ws.cell(row=fila_excel, column=4)
            celda.alignment = Alignment(wrap_text=True, vertical="top")
            if not it.completo:
                celda.font = Font(bold=True)
        for fila in ws.iter_rows(min_row=2):
            for celda in fila:
                if celda.column != 4:
                    celda.alignment = Alignment(vertical="top")

        return self._guardar(wb, ruta)

    # ------------------------------------------------------------ Fase 3
    def exportar_fase3(self, resultado, ruta: Path) -> Path:
        wb = Workbook()
        ws = wb.active
        ws.title = "Limpieza"
        enc = ["Carpeta original", "Carpeta final", "Acción",
               "Archivos respaldados", "Detalle"]
        orden = {"Error": 0, "Omitida": 1}
        items = sorted(resultado.items,
                       key=lambda i: (orden.get(i.accion.value, 2), i.plan.carpeta.name))
        filas = []
        for it in items:
            detalle = "; ".join(it.errores) or it.plan.motivo
            filas.append([it.plan.carpeta.name,
                          it.carpeta_final.name if it.carpeta_final else "",
                          it.accion.value, it.respaldados, detalle])
        self._llenar_hoja(ws, enc, filas)
        for fila_excel, it in enumerate(items, 2):
            if it.accion.value in orden:
                fill = _FILL_ERROR if it.accion.value == "Error" else _FILL_ADVERTENCIA
                for celda in ws[fila_excel]:
                    celda.fill = fill
        return self._guardar(wb, ruta)

    # ------------------------------------------------------------ Limpiador RIPS
    def exportar_rips(self, resultado, ruta: Path) -> Path:
        from app.services.limpiador_rips import EstadoRIPS, TipoArchivo
        wb = Workbook()
        ws = wb.active
        ws.title = "Limpieza RIPS"
        enc = ["Carpeta", "Estado", "CUV", "JSON", "XML", "Eliminados",
               "Archivos eliminados", "Observaciones"]
        alerta = {EstadoRIPS.ERROR: 0, EstadoRIPS.SIN_CUV: 1, EstadoRIPS.VACIA: 2}

        def prioridad(i):
            """Lo que hay que revisar, arriba: errores, sin CUV, vacías, con observaciones."""
            if i.estado in alerta:
                return alerta[i.estado]
            return 3 if i.observaciones else 4

        items = sorted(resultado.items, key=lambda i: (prioridad(i), i.carpeta.name))
        filas = []
        for it in items:
            si_no = lambda t: "Sí" if it.contar(t) else "NO"
            eliminados = ", ".join(a.name for a in it.eliminar) if it.estado in (
                EstadoRIPS.LIMPIADA, EstadoRIPS.ERROR) else ""
            filas.append([it.carpeta.name, it.estado.value, si_no(TipoArchivo.CUV),
                          si_no(TipoArchivo.JSON), si_no(TipoArchivo.XML), it.eliminados,
                          eliminados, "; ".join(it.errores + it.observaciones)])
        self._llenar_hoja(ws, enc, filas, columnas_texto={1})
        for fila_excel, it in enumerate(items, 2):
            if it.estado == EstadoRIPS.ERROR:
                fill = _FILL_ERROR
            elif it.estado in alerta or it.observaciones:
                fill = _FILL_ADVERTENCIA
            else:
                continue
            for celda in ws[fila_excel]:
                celda.fill = fill
        return self._guardar(wb, ruta)

    # ------------------------------------------------------------ comunes
    @staticmethod
    def _llenar_hoja(ws, encabezados, filas, columnas_texto=()):
        ws.append(encabezados)
        for celda in ws[1]:
            celda.fill = _FILL_ENCABEZADO
            celda.font = _FONT_ENCABEZADO
            celda.alignment = Alignment(horizontal="center", vertical="center")
        for fila in filas:
            ws.append(fila)

        # Documento como texto para que Excel no lo vuelva notación científica
        for col in columnas_texto:
            for (celda,) in ws.iter_rows(min_row=2, min_col=col, max_col=col):
                celda.number_format = "@"

        for i, titulo in enumerate(encabezados, 1):
            largo = max([len(str(titulo))] +
                        [len(str(c.value or "")) for (c,) in
                         ws.iter_rows(min_row=2, min_col=i, max_col=i)])
            ws.column_dimensions[get_column_letter(i)].width = min(largo + 3, 70)

        ws.freeze_panes = "A2"
        if filas:
            ws.auto_filter.ref = ws.dimensions

    @staticmethod
    def _guardar(wb, ruta: Path) -> Path:
        ruta = Path(ruta)
        try:
            wb.save(ruta)
        except PermissionError:
            # El archivo está abierto en Excel: guardar con otro nombre
            sello = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta = ruta.with_name(f"{ruta.stem}_{sello}{ruta.suffix}")
            wb.save(ruta)
        return ruta
