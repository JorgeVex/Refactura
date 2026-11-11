"""
Paneles de cada fase. No ejecutan tareas largas por sí mismos: piden a la
ventana principal que las corra en el worker (señal `pedir_tarea`).
"""
from collections import Counter
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt, QSettings, QTimer
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMessageBox,
                             QScrollArea, QVBoxLayout, QWidget)

from app.config.aseguradoras import PerfilAseguradora
from app.core.modelos import AccionFase3
from app.services.armador_paquetes import ArmadorPaquetes
from app.services.limpiador_carpetas import LimpiadorCarpetas
from app.services.organizador_fev import OrganizadorFEV
from app.ui.componentes import (CajaResumen, SelectorCarpeta, Tarjeta, abrir_ruta,
                                boton)


class PanelFase(QWidget):
    pedir_tarea = pyqtSignal(object, object, str)   # tarea, al_terminar, descripción
    carpeta_padre_lista = pyqtSignal(object)        # Path -> para las fases siguientes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.perfil: PerfilAseguradora = None
        self.ajustes = QSettings("ESE_LPG", "DevolucionFacturas")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(4, 8, 4, 4)
        self.lay.setSpacing(12)

    def set_perfil(self, perfil: PerfilAseguradora):
        self.perfil = perfil

    def set_carpeta_padre(self, ruta: Path):
        pass

    def _mostrar_resultado(self, tarjeta):
        """Muestra la tarjeta y desplaza el scroll hasta ella."""
        tarjeta.show()

        def desplazar():
            w = self.parentWidget()
            while w and not isinstance(w, QScrollArea):
                w = w.parentWidget()
            if w:
                w.ensureWidgetVisible(tarjeta, 0, 10)
        QTimer.singleShot(50, desplazar)

    @staticmethod
    def _fila(*widgets, estirar_al_final=True):
        f = QHBoxLayout()
        for w in widgets:
            f.addWidget(w)
        if estirar_al_final:
            f.addStretch()
        return f


# =========================================================================== Fase 1
class PanelFase1(PanelFase):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resultado = None

        t = Tarjeta("1. Organizar facturas (FEV)",
                    "Selecciona la carpeta con todas las FEV devueltas. Se creará la carpeta "
                    "padre con una subcarpeta por paciente y factura, y un Excel con los "
                    "datos para descargar soportes e historias clínicas.")
        self.sel_origen = SelectorCarpeta("Carpeta con las FEV:", "Carpeta con las FEV")
        self.sel_destino = SelectorCarpeta("Guardar resultado en:", "Dónde crear la carpeta padre")
        self.lbl_destino = QLabel()
        self.lbl_destino.setObjectName("Descripcion")
        self.lbl_destino.setWordWrap(True)
        self.btn_ejecutar = boton("Organizar facturas", "Primario", self._ejecutar)
        t.cuerpo.addWidget(self.sel_origen)
        t.cuerpo.addWidget(self.sel_destino)
        t.cuerpo.addWidget(self.lbl_destino)
        t.cuerpo.addLayout(self._fila(self.btn_ejecutar))
        self.lay.addWidget(t)

        r = Tarjeta("Resultado")
        self.resumen = CajaResumen()
        self.btn_carpeta = boton("Abrir carpeta", "Enlace",
                                 lambda: abrir_ruta(self.resultado.carpeta_padre))
        self.btn_excel = boton("Abrir Excel de pacientes", "Enlace",
                               lambda: abrir_ruta(self.resultado.ruta_excel))
        r.cuerpo.addWidget(self.resumen)
        r.cuerpo.addLayout(self._fila(self.btn_carpeta, self.btn_excel))
        self.tarjeta_resultado = r
        r.hide()
        self.lay.addWidget(r)
        self.lay.addStretch()

        self.sel_origen.cambiada.connect(self._origen_cambiado)
        self.sel_destino.cambiada.connect(lambda _: self._actualizar())
        self.sel_origen.set_ruta(self.ajustes.value("fase1/origen", ""), emitir=False)
        self.sel_destino.set_ruta(self.ajustes.value("fase1/destino", ""), emitir=False)

    def set_perfil(self, perfil):
        super().set_perfil(perfil)
        self._actualizar()

    def _origen_cambiado(self, ruta):
        if ruta and not self.sel_destino.ruta:
            self.sel_destino.set_ruta(ruta.parent)
        self._actualizar()

    def _actualizar(self):
        listo = bool(self.perfil and self.sel_origen.ruta and self.sel_destino.ruta)
        self.btn_ejecutar.setEnabled(listo)
        if listo:
            if self.perfil.carpeta_dinamica:
                self.lbl_destino.setText(
                    f"Se creará la carpeta <b>{self.perfil.descripcion_carpeta}</b> y su Excel "
                    f"de pacientes dentro de la carpeta de resultado. El nombre se toma de las FEV.")
                self.lbl_destino.setToolTip("")
            else:
                padre, excel = OrganizadorFEV(self.perfil).rutas_destino(self.sel_destino.ruta)
                self.lbl_destino.setText(f"Se creará la carpeta <b>{padre.name}</b> y el Excel "
                                         f"<b>{excel.name}</b> dentro de la carpeta de resultado.")
                self.lbl_destino.setToolTip(f"{padre}\n{excel}")
        else:
            self.lbl_destino.setText("")

    def _ejecutar(self):
        origen, destino = self.sel_origen.ruta, self.sel_destino.ruta
        if not origen.exists():
            QMessageBox.warning(self, "Carpeta no encontrada", f"No existe:\n{origen}")
            return
        pdfs = [p for p in origen.iterdir() if p.suffix.lower() == ".pdf"]
        if not pdfs:
            QMessageBox.warning(self, "Sin facturas", "La carpeta no tiene archivos PDF.")
            return

        self.ajustes.setValue("fase1/origen", str(origen))
        self.ajustes.setValue("fase1/destino", str(destino))
        organizador = OrganizadorFEV(self.perfil)
        self.pedir_tarea.emit(
            lambda prog, canc: organizador.ejecutar(origen, destino, prog, canc),
            self._terminado, f"Organizando {len(pdfs)} facturas de {self.perfil.nombre}")

    def _terminado(self, res):
        self.resultado = res
        pacientes = len({(i.factura.tipo_doc, i.factura.num_doc) for i in res.incluidas})
        novedades = len(res.con_novedad)
        html = (f"<b>{len(res.incluidas)}</b> facturas organizadas de "
                f"<b>{pacientes}</b> pacientes.")
        if res.excluidas:
            html += f"<br>Excluidas: <b>{len(res.excluidas)}</b>."
        if novedades:
            html += (f"<br>Hay <b>{novedades}</b> novedades para revisar "
                     f"(hoja <i>Novedades</i> del Excel).")
        if res.cancelado:
            html += "<br><b>Proceso cancelado:</b> el resultado es parcial."
        self.resumen.mostrar(html, alerta=bool(novedades or res.cancelado))
        self._mostrar_resultado(self.tarjeta_resultado)
        self.carpeta_padre_lista.emit(res.carpeta_padre)


# =========================================================================== Fase 2
class PanelFase2(PanelFase):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resultado = None

        t = Tarjeta("2. Armar soportes (PDE y HEV)",
                    "Cuando ya descargaste los soportes en cada carpeta, selecciona la carpeta "
                    "padre. Se armará el PDE y el HEV de cada factura y un reporte con lo que "
                    "falte.")
        self.sel_padre = SelectorCarpeta("Carpeta padre:", "Carpeta padre (ej. ASMET EVENTO)")
        self.lbl_reglas = QLabel()
        self.lbl_reglas.setObjectName("Descripcion")
        self.lbl_reglas.setWordWrap(True)
        self.lbl_reglas.setTextFormat(Qt.RichText)
        self.btn_ejecutar = boton("Armar paquetes", "Primario", self._ejecutar)
        t.cuerpo.addWidget(self.sel_padre)
        t.cuerpo.addWidget(self.lbl_reglas)
        t.cuerpo.addLayout(self._fila(self.btn_ejecutar))
        self.lay.addWidget(t)

        r = Tarjeta("Resultado")
        self.resumen = CajaResumen()
        self.btn_carpeta = boton("Abrir carpeta", "Enlace",
                                 lambda: abrir_ruta(self.resultado.carpeta_padre))
        self.btn_excel = boton("Abrir reporte de soportes", "Enlace",
                               lambda: abrir_ruta(self.resultado.ruta_excel))
        r.cuerpo.addWidget(self.resumen)
        r.cuerpo.addLayout(self._fila(self.btn_carpeta, self.btn_excel))
        self.tarjeta_resultado = r
        r.hide()
        self.lay.addWidget(r)
        self.lay.addStretch()

        self.sel_padre.cambiada.connect(lambda _: self._actualizar())
        self.sel_padre.set_ruta(self.ajustes.value("fase2/padre", ""), emitir=False)

    def set_perfil(self, perfil):
        super().set_perfil(perfil)
        self._actualizar()

    def set_carpeta_padre(self, ruta):
        self.sel_padre.set_ruta(ruta)

    def _actualizar(self):
        self.btn_ejecutar.setEnabled(bool(self.perfil and self.sel_padre.ruta))
        if not self.perfil or not self.perfil.regla_pde:
            self.lbl_reglas.setText("")
            return

        def fmt(regla):
            return " → ".join(f"<b>{s.codigo}</b>" if s.obligatorio else s.codigo
                              for s in regla.soportes)
        self.lbl_reglas.setText(
            f"PDE: {fmt(self.perfil.regla_pde)}<br>HEV: {fmt(self.perfil.regla_hev)}"
            f"<br><i>En negrilla los obligatorios. Ese es el orden de unión.</i>")

    def _ejecutar(self):
        padre = self.sel_padre.ruta
        if not padre.exists():
            QMessageBox.warning(self, "Carpeta no encontrada", f"No existe:\n{padre}")
            return
        if not self.perfil.carpeta_esperada(padre.name):
            r = QMessageBox.question(
                self, "Confirmar carpeta",
                f"La carpeta seleccionada se llama <b>{padre.name}</b> y para "
                f"<b>{self.perfil.nombre}</b> se esperaba <b>{self.perfil.descripcion_carpeta}</b>."
                f"<br><br>¿Continuar de todos modos?")
            if r != QMessageBox.Yes:
                return

        self.ajustes.setValue("fase2/padre", str(padre))
        armador = ArmadorPaquetes(self.perfil)
        self.pedir_tarea.emit(lambda prog, canc: armador.ejecutar(padre, prog, canc),
                              self._terminado, f"Armando paquetes de {self.perfil.nombre}")

    def _terminado(self, res):
        self.resultado = res
        inc = len(res.incompletos)
        html = (f"<b>{len(res.items)}</b> carpetas procesadas: "
                f"<b>{len(res.completos)}</b> completas, <b>{inc}</b> incompletas.")
        if inc:
            html += "<br>Las incompletas están arriba y en color en el reporte."
        if res.cancelado:
            html += "<br><b>Proceso cancelado:</b> el resultado es parcial."
        self.resumen.mostrar(html, alerta=bool(inc or res.cancelado))
        self._mostrar_resultado(self.tarjeta_resultado)
        self.carpeta_padre_lista.emit(res.carpeta_padre)

        # Alerta obligatoria antes de pasar a la limpieza
        caja = QMessageBox(self)
        caja.setWindowTitle("Verifica los soportes")
        caja.setIcon(QMessageBox.Warning if inc else QMessageBox.Information)
        caja.setText("<b>Verifica que los soportes tengan todos los documentos.</b>")
        caja.setInformativeText(
            f"Completas: {len(res.completos)}   |   Incompletas: {inc}\n\n"
            "Revisa el reporte y los paquetes. Cuando estés seguro, pasa a la pestaña "
            "\"3. Limpiar carpetas\" para dejar solo FEV, HEV y PDE.")
        if inc:
            caja.setDetailedText("\n\n".join(
                f"{i.carpeta.name}\n   → {i.que_hacer()}" for i in res.incompletos))
        abrir = caja.addButton("Abrir reporte", QMessageBox.ActionRole)
        caja.addButton("Entendido", QMessageBox.AcceptRole)
        caja.exec_()
        if caja.clickedButton() is abrir:
            abrir_ruta(res.ruta_excel)


# =========================================================================== Fase 3
class PanelFase3(PanelFase):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resultado = None

        t = Tarjeta("3. Limpiar y renombrar carpetas",
                    "Deja en cada carpeta solo FEV, PDE y HEV, y la renombra con el número del "
                    "consecutivo. Antes de limpiar, se guarda en la carpeta de respaldo una copia "
                    "completa de cada carpeta (paquetes y soportes).")
        self.sel_padre = SelectorCarpeta("Carpeta padre:", "Carpeta padre (ej. ASMET EVENTO)")
        self.lbl_respaldo = QLabel()
        self.lbl_respaldo.setObjectName("Descripcion")
        self.lbl_respaldo.setWordWrap(True)
        self.btn_ejecutar = boton("Limpiar y renombrar...", "Peligro", self._ejecutar)
        t.cuerpo.addWidget(self.sel_padre)
        t.cuerpo.addWidget(self.lbl_respaldo)
        t.cuerpo.addLayout(self._fila(self.btn_ejecutar))
        self.lay.addWidget(t)

        r = Tarjeta("Resultado")
        self.resumen = CajaResumen()
        self.btn_carpeta = boton("Abrir carpeta", "Enlace",
                                 lambda: abrir_ruta(self.resultado.carpeta_padre))
        self.btn_respaldo = boton("Abrir respaldo", "Enlace",
                                  lambda: abrir_ruta(self.resultado.carpeta_respaldo))
        self.btn_excel = boton("Abrir registro de limpieza", "Enlace",
                               lambda: abrir_ruta(self.resultado.ruta_excel))
        r.cuerpo.addWidget(self.resumen)
        r.cuerpo.addLayout(self._fila(self.btn_carpeta, self.btn_respaldo, self.btn_excel))
        self.tarjeta_resultado = r
        r.hide()
        self.lay.addWidget(r)
        self.lay.addStretch()

        self.sel_padre.cambiada.connect(lambda _: self._actualizar())
        self.sel_padre.set_ruta(self.ajustes.value("fase3/padre", ""), emitir=False)

    def set_perfil(self, perfil):
        super().set_perfil(perfil)
        self._actualizar()

    def set_carpeta_padre(self, ruta):
        self.sel_padre.set_ruta(ruta)

    def _actualizar(self):
        padre = self.sel_padre.ruta
        self.btn_ejecutar.setEnabled(bool(self.perfil and padre))
        if padre:
            resp = LimpiadorCarpetas.carpeta_respaldo(padre)
            self.lbl_respaldo.setText(f"El respaldo se guardará en <b>{resp.name}</b>, "
                                      f"al lado de la carpeta padre.")
            self.lbl_respaldo.setToolTip(str(resp))
        else:
            self.lbl_respaldo.setText("")

    def _ejecutar(self):
        padre = self.sel_padre.ruta
        if not padre.exists():
            QMessageBox.warning(self, "Carpeta no encontrada", f"No existe:\n{padre}")
            return
        if not self.perfil.carpeta_esperada(padre.name):
            r = QMessageBox.question(
                self, "Confirmar carpeta",
                f"La carpeta seleccionada se llama <b>{padre.name}</b> y para "
                f"<b>{self.perfil.nombre}</b> se esperaba <b>{self.perfil.descripcion_carpeta}</b>."
                f"<br><br>¿Continuar de todos modos?")
            if r != QMessageBox.Yes:
                return
        self.ajustes.setValue("fase3/padre", str(padre))
        limpiador = LimpiadorCarpetas(self.perfil)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            plan = limpiador.planear(padre)
        finally:
            QApplication.restoreOverrideCursor()

        conteo = Counter(p.accion for p in plan)
        a_limpiar = conteo[AccionFase3.LIMPIAR]
        if not a_limpiar:
            QMessageBox.information(
                self, "Nada que limpiar",
                f"No hay carpetas para limpiar.\n\nYa limpias: {conteo[AccionFase3.YA_LIMPIA]}"
                f"\nOmitidas: {conteo[AccionFase3.OMITIR]}")
            return

        archivos = sum(len(p.respaldar) for p in plan if p.accion == AccionFase3.LIMPIAR)
        caja = QMessageBox(self)
        caja.setWindowTitle("Confirmar limpieza")
        caja.setIcon(QMessageBox.Warning)
        caja.setText(f"<b>¿Seguro que deseas limpiar {a_limpiar} carpetas?</b>")
        texto = (f"• Se moverán {archivos} soportes al respaldo y las carpetas quedarán "
                 f"solo con el número del consecutivo.\n"
                 f"• Ya limpias: {conteo[AccionFase3.YA_LIMPIA]}\n"
                 f"• Se omitirán: {conteo[AccionFase3.OMITIR]}\n\n"
                 f"Respaldo: {limpiador.carpeta_respaldo(padre)}")
        caja.setInformativeText(texto)
        omitidas = [p for p in plan if p.accion == AccionFase3.OMITIR]
        if omitidas:
            caja.setDetailedText("\n".join(f"{p.carpeta.name}: {p.motivo}" for p in omitidas))
        si = caja.addButton("Sí, limpiar", QMessageBox.AcceptRole)
        no = caja.addButton("Cancelar", QMessageBox.RejectRole)
        caja.setDefaultButton(no)
        caja.exec_()
        if caja.clickedButton() is not si:
            return

        self.pedir_tarea.emit(lambda prog, canc: limpiador.ejecutar(padre, plan, prog, canc),
                              self._terminado, f"Limpiando {a_limpiar} carpetas")

    def _terminado(self, res):
        self.resultado = res
        errores = res.contar(AccionFase3.ERROR)
        omitidas = res.contar(AccionFase3.OMITIR)
        html = (f"<b>{res.contar(AccionFase3.LIMPIADA)}</b> carpetas limpiadas y renombradas."
                f"<br>Ya limpias: {res.contar(AccionFase3.YA_LIMPIA)} | Omitidas: {omitidas} | "
                f"Con error: {errores}")
        if errores or omitidas:
            html += "<br>Revisa el registro de limpieza para ver el detalle."
        if res.cancelado:
            html += "<br><b>Proceso cancelado:</b> el resultado es parcial."
        self.resumen.mostrar(html, alerta=bool(errores or omitidas or res.cancelado))
        self._mostrar_resultado(self.tarjeta_resultado)


# =========================================================================== Limpiador RIPS
class PanelRIPS(PanelFase):
    """Pestaña independiente de la aseguradora: deja en cada carpeta solo CUV, JSON y XML."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resultado = None

        t = Tarjeta("4. Limpiador de RIPS",
                    "Selecciona la carpeta padre de los RIPS (la que tiene una carpeta por factura). "
                    "En cada carpeta se conservan solo el <b>JSON</b>, el <b>XML</b> y el plano que "
                    "termina en <b>CUV</b>; los demás archivos se <b>eliminan definitivamente</b>. "
                    "Las carpetas sin CUV no se tocan. No depende de la aseguradora seleccionada.")
        t.findChild(QLabel, "Descripcion").setTextFormat(Qt.RichText)
        self.sel_padre = SelectorCarpeta("Carpeta de RIPS:", "Carpeta padre de los RIPS")
        self.btn_ejecutar = boton("Limpiar RIPS...", "Peligro", self._ejecutar)
        t.cuerpo.addWidget(self.sel_padre)
        t.cuerpo.addLayout(self._fila(self.btn_ejecutar))
        self.lay.addWidget(t)

        r = Tarjeta("Resultado")
        self.resumen = CajaResumen()
        self.btn_carpeta = boton("Abrir carpeta", "Enlace",
                                 lambda: abrir_ruta(self.resultado.carpeta_padre))
        self.btn_excel = boton("Abrir reporte", "Enlace",
                               lambda: abrir_ruta(self.resultado.ruta_excel))
        r.cuerpo.addWidget(self.resumen)
        r.cuerpo.addLayout(self._fila(self.btn_carpeta, self.btn_excel))
        self.tarjeta_resultado = r
        r.hide()
        self.lay.addWidget(r)
        self.lay.addStretch()

        self.sel_padre.cambiada.connect(lambda _: self._actualizar())
        self.sel_padre.set_ruta(self.ajustes.value("rips/padre", ""), emitir=False)
        self._actualizar()

    def set_perfil(self, perfil):
        super().set_perfil(perfil)          # No se usa: este módulo es igual para todas

    def _actualizar(self):
        self.btn_ejecutar.setEnabled(bool(self.sel_padre.ruta))

    def _ejecutar(self):
        from app.services.limpiador_rips import EstadoRIPS, LimpiadorRIPS
        padre = self.sel_padre.ruta
        if not padre.exists():
            QMessageBox.warning(self, "Carpeta no encontrada", f"No existe:\n{padre}")
            return
        self.ajustes.setValue("rips/padre", str(padre))
        limpiador = LimpiadorRIPS()

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            plan = limpiador.planear(padre)
        finally:
            QApplication.restoreOverrideCursor()

        if not plan:
            QMessageBox.information(self, "Sin carpetas",
                                    "La carpeta seleccionada no tiene subcarpetas de RIPS.")
            return
        conteo = Counter(p.estado for p in plan)
        a_limpiar = [p for p in plan if p.estado == EstadoRIPS.LIMPIAR]
        archivos = sum(len(p.eliminar) for p in a_limpiar)
        if not a_limpiar:
            QMessageBox.information(
                self, "Nada que limpiar",
                f"No hay archivos para eliminar.\n\nYa limpias: {conteo[EstadoRIPS.YA_LIMPIA]}\n"
                f"Sin CUV (no se tocan): {conteo[EstadoRIPS.SIN_CUV]}")
            return

        caja = QMessageBox(self)
        caja.setWindowTitle("Confirmar limpieza de RIPS")
        caja.setIcon(QMessageBox.Warning)
        caja.setText(f"<b>Se eliminarán DEFINITIVAMENTE {archivos} archivos de "
                     f"{len(a_limpiar)} carpetas.</b>")
        caja.setInformativeText(
            "Esta acción no se puede deshacer (no pasa por la papelera).\n\n"
            f"• Se conservan en cada carpeta: CUV, JSON y XML\n"
            f"• Ya limpias: {conteo[EstadoRIPS.YA_LIMPIA]}\n"
            f"• Sin CUV, no se tocan: {conteo[EstadoRIPS.SIN_CUV]}\n"
            f"• Vacías: {conteo[EstadoRIPS.VACIA]}")
        detalle = [f"{p.carpeta.name}: {p.estado.value}" for p in plan if p.estado == EstadoRIPS.SIN_CUV]
        detalle += [f"{p.carpeta.name}: {'; '.join(p.observaciones)}"
                    for p in a_limpiar if p.observaciones]
        if detalle:
            caja.setDetailedText("\n".join(detalle))
        si = caja.addButton("Sí, eliminar", QMessageBox.AcceptRole)
        no = caja.addButton("Cancelar", QMessageBox.RejectRole)
        caja.setDefaultButton(no)
        caja.exec_()
        if caja.clickedButton() is not si:
            return

        self.pedir_tarea.emit(lambda prog, canc: limpiador.ejecutar(padre, plan, prog, canc),
                              self._terminado, f"Limpiando RIPS de {len(a_limpiar)} carpetas")

    def _terminado(self, res):
        from app.services.limpiador_rips import EstadoRIPS
        self.resultado = res
        sin_cuv, errores = res.contar(EstadoRIPS.SIN_CUV), res.contar(EstadoRIPS.ERROR)
        html = (f"<b>{res.eliminados}</b> archivos eliminados en "
                f"<b>{res.contar(EstadoRIPS.LIMPIADA)}</b> carpetas.<br>"
                f"Ya limpias: {res.contar(EstadoRIPS.YA_LIMPIA)} | Sin CUV: {sin_cuv} | "
                f"Con error: {errores}")
        if sin_cuv or errores:
            html += "<br>Revisa el reporte: las carpetas sin CUV y con error están arriba y en color."
        if res.cancelado:
            html += "<br><b>Proceso cancelado:</b> el resultado es parcial."
        self.resumen.mostrar(html, alerta=bool(sin_cuv or errores or res.cancelado))
        self._mostrar_resultado(self.tarjeta_resultado)
