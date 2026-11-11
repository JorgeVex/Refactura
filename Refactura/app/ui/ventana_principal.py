"""Ventana principal: aseguradora, pestañas por fase y panel de progreso."""
from datetime import datetime

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow,
                             QMessageBox, QPlainTextEdit, QProgressBar, QRadioButton,
                             QScrollArea, QTabWidget, QVBoxLayout, QWidget)

from app import __version__
from app.config.aseguradoras import PERFILES
from app.ui.componentes import Tarjeta, boton
from app.ui.paneles import PanelFase1, PanelFase2, PanelFase3, PanelRIPS
from app.utils.recursos import ruta_recurso
from app.workers.worker_tarea import WorkerTarea


class VentanaPrincipal(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Refactura - Devolución de Facturas")
        self.setWindowIcon(QIcon(str(ruta_recurso("icono.ico"))))
        self.setMinimumSize(820, 600)
        # Ajustar al tamaño de la pantalla (portátiles de 1366x768)
        pantalla = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1000, pantalla.width() - 40), min(860, pantalla.height() - 40))
        self.worker = None
        self._al_terminar = None
        self.ajustes = QSettings("ESE_LPG", "DevolucionFacturas")

        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._crear_encabezado())

        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(18, 8, 18, 14)
        cuerpo.setSpacing(10)
        cuerpo.addWidget(self._crear_aseguradoras())
        cuerpo.addWidget(self._crear_pestanas(), 1)
        cuerpo.addWidget(self._crear_progreso())
        raiz.addLayout(cuerpo, 1)

        self.statusBar().showMessage("Listo")
        self._seleccionar_perfil_inicial()

    # ------------------------------------------------------------ construcción
    def _crear_encabezado(self):
        f = QFrame()
        f.setObjectName("Encabezado")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(22, 12, 22, 12)
        lay.setSpacing(14)

        logo = QLabel()
        logo.setObjectName("Logo")
        logo.setFixedSize(58, 58)
        logo.setAlignment(Qt.AlignCenter)
        pix = QPixmap(str(ruta_recurso("icono.png")))
        if not pix.isNull():
            logo.setPixmap(pix.scaled(46, 46, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        textos = QVBoxLayout()
        textos.setSpacing(2)
        titulo = QLabel("Refactura")
        titulo.setObjectName("Titulo")
        sub = QLabel("Devolución de facturas  ·  E.S.E. Hospital Laura Perdomo de García"
                     "  ·  Equipo de facturación")
        sub.setObjectName("Subtitulo")
        textos.addWidget(titulo)
        textos.addWidget(sub)
        insignia = QLabel(f"LPG  v{__version__}")
        insignia.setObjectName("Insignia")
        lay.addWidget(logo, 0, Qt.AlignVCenter)
        lay.addLayout(textos)
        lay.addStretch()
        lay.addWidget(insignia, 0, Qt.AlignVCenter)
        return f

    def _crear_aseguradoras(self):
        t = Tarjeta("Aseguradora")
        self.tarjeta_aseguradora = t
        fila = QHBoxLayout()
        self.grupo = QButtonGroup(self)
        self.radios = {}
        for perfil in PERFILES:
            rb = QRadioButton(perfil.nombre)
            rb.setEnabled(perfil.activo)
            rb.setCursor(Qt.PointingHandCursor)
            tip = perfil.notas if perfil.activo else f"Próximamente. {perfil.notas}".strip()
            if tip:
                rb.setToolTip(tip)
            self.grupo.addButton(rb)
            self.radios[rb] = perfil
            fila.addWidget(rb)
        fila.addStretch()
        t.cuerpo.addLayout(fila)

        # Segunda fila: variantes del perfil (ej. Nueva EPS: Subsidiado / Contributivo)
        self.caja_variantes = QWidget()
        self.lay_variantes = QHBoxLayout(self.caja_variantes)
        self.lay_variantes.setContentsMargins(0, 2, 0, 0)
        self.grupo_variantes = QButtonGroup(self)
        self.grupo_variantes.buttonToggled.connect(self._variante_cambiada)
        self.radios_variantes = {}
        self.caja_variantes.hide()
        t.cuerpo.addWidget(self.caja_variantes)

        self.grupo.buttonToggled.connect(self._perfil_cambiado)
        return t

    def _crear_pestanas(self):
        self.tabs = QTabWidget()
        barra = self.tabs.tabBar()
        fuente = QFont(barra.font())
        fuente.setWeight(QFont.DemiBold)
        barra.setFont(fuente)                  # El ancho se calcula ya en negrilla
        barra.setElideMode(Qt.ElideNone)       # Nunca recortar el texto
        barra.setExpanding(False)
        self.paneles = [PanelFase1(), PanelFase2(), PanelFase3(), PanelRIPS()]
        nombres = ["1. Organizar FEV", "2. Armar soportes", "3. Limpiar carpetas",
                   "4. Limpiador de RIPS"]
        for panel, nombre in zip(self.paneles, nombres):
            # Scroll para que el contenido nunca se aplaste en pantallas pequeñas
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidget(panel)
            self.tabs.addTab(scroll, nombre)
            panel.pedir_tarea.connect(self.ejecutar_tarea)

        f1, f2, f3 = self.paneles[:3]
        f1.carpeta_padre_lista.connect(f2.set_carpeta_padre)
        f1.carpeta_padre_lista.connect(f3.set_carpeta_padre)
        f2.carpeta_padre_lista.connect(f3.set_carpeta_padre)
        # El Limpiador de RIPS no depende de la aseguradora: se atenúa esa tarjeta
        self.tabs.currentChanged.connect(self._pestana_cambiada)
        return self.tabs

    def _pestana_cambiada(self, indice):
        usa_aseguradora = not isinstance(self.paneles[indice], PanelRIPS)
        self.tarjeta_aseguradora.setEnabled(usa_aseguradora)
        self.tarjeta_aseguradora.setToolTip(
            "" if usa_aseguradora else "El Limpiador de RIPS funciona igual para todas las aseguradoras")

    def _crear_progreso(self):
        t = Tarjeta("Progreso")
        fila = QHBoxLayout()
        self.barra = QProgressBar()
        self.barra.setValue(0)
        self.barra.setFormat("%v / %m  (%p%)")
        self.btn_cancelar = boton("Cancelar", "Cancelar", self._cancelar)
        self.btn_cancelar.setEnabled(False)
        fila.addWidget(self.barra, 1)
        fila.addWidget(self.btn_cancelar)
        self.lbl_estado = QLabel("Sin procesos en curso")
        self.lbl_estado.setObjectName("Estado")
        self.log = QPlainTextEdit()
        self.log.setObjectName("Log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setFixedHeight(92)
        t.cuerpo.addLayout(fila)
        t.cuerpo.addWidget(self.lbl_estado)
        t.cuerpo.addWidget(self.log)
        return t

    # ------------------------------------------------------------ aseguradora
    def _seleccionar_perfil_inicial(self):
        guardada = self.ajustes.value("aseguradora", "")
        activos = [rb for rb, p in self.radios.items() if p.activo]
        elegido = next((rb for rb in activos if self.radios[rb].clave == guardada), None)
        (elegido or activos[0]).setChecked(True)

    def _perfil_cambiado(self, rb, marcado):
        if not marcado:
            return
        perfil = self.radios[rb]
        self.ajustes.setValue("aseguradora", perfil.clave)
        self._perfil_base = perfil
        self._construir_variantes(perfil)
        if not perfil.variantes:
            self._aplicar_perfil(perfil)

    def _construir_variantes(self, perfil):
        """Muestra la segunda fila de RadioButtons si el perfil tiene variantes."""
        for rb in list(self.radios_variantes):
            self.grupo_variantes.removeButton(rb)
            rb.deleteLater()
        self.radios_variantes.clear()
        while self.lay_variantes.count():
            item = self.lay_variantes.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not perfil.variantes:
            self.caja_variantes.hide()
            return

        etiqueta = QLabel("Régimen:")
        etiqueta.setObjectName("Descripcion")
        self.lay_variantes.addWidget(etiqueta)
        for v in perfil.variantes:
            rb = QRadioButton(v.nombre)
            rb.setCursor(Qt.PointingHandCursor)
            rb.setToolTip(f"Se creará la carpeta {v.carpeta_padre}")
            self.grupo_variantes.addButton(rb)
            self.radios_variantes[rb] = v
            self.lay_variantes.addWidget(rb)
        self.lay_variantes.addStretch()
        self.caja_variantes.show()

        guardada = self.ajustes.value(f"variante/{perfil.clave}", "")
        elegido = next((rb for rb, v in self.radios_variantes.items() if v.clave == guardada),
                       next(iter(self.radios_variantes)))
        elegido.setChecked(True)

    def _variante_cambiada(self, rb, marcado):
        if not marcado or rb not in self.radios_variantes:
            return
        v = self.radios_variantes[rb]
        self.ajustes.setValue(f"variante/{self._perfil_base.clave}", v.clave)
        self._aplicar_perfil(self._perfil_base.con_variante(v))

    def _aplicar_perfil(self, perfil):
        """Perfil efectivo (con variante aplicada) para todos los paneles."""
        self.perfil_actual = perfil
        for panel in self.paneles:
            panel.set_perfil(perfil)
        self._escribir_log(f"Aseguradora seleccionada: {perfil.nombre} "
                           f"(carpeta padre: {perfil.descripcion_carpeta})")

    # ------------------------------------------------------------ tareas
    def ejecutar_tarea(self, tarea, al_terminar, descripcion):
        if self.worker and self.worker.isRunning():
            return
        self._al_terminar = al_terminar
        self._ocupado(True)
        self.barra.setRange(0, 0)       # Animación indeterminada hasta el primer avance
        self.lbl_estado.setText(descripcion + "...")
        self._escribir_log(f"▶ {descripcion}")
        self.statusBar().showMessage(descripcion)

        self.worker = WorkerTarea(tarea, self)
        self.worker.progreso.connect(self._progreso)
        self.worker.terminado.connect(self._terminado)
        self.worker.fallo.connect(self._fallo)
        self.worker.start()

    def _progreso(self, actual, total, mensaje):
        if self.barra.maximum() != total:
            self.barra.setRange(0, max(total, 1))
        self.barra.setValue(actual)
        self.lbl_estado.setText(mensaje)
        # En el log solo lo que importa revisar
        if any(p in mensaje for p in ("Excluida", "INCOMPLETO", "Omitida", "Error",
                                      "Ya existía", "Generando", "Sin CUV")):
            self._escribir_log(f"  {mensaje}")

    def _terminado(self, resultado):
        self._ocupado(False)
        self.barra.setRange(0, 1)
        self.barra.setValue(1)
        cancelado = getattr(resultado, "cancelado", False)
        resumen = resultado.resumen() if hasattr(resultado, "resumen") else "Terminado"
        self._escribir_log(("■ Cancelado. " if cancelado else "✔ ") + resumen)
        self.lbl_estado.setText("Cancelado" if cancelado else "Terminado")
        self.statusBar().showMessage(resumen)
        if self._al_terminar:
            self._al_terminar(resultado)

    def _fallo(self, mensaje):
        self._ocupado(False)
        self.barra.setRange(0, 1)
        self.barra.setValue(0)
        self.lbl_estado.setText("Ocurrió un error")
        self._escribir_log("✖ ERROR: " + mensaje.splitlines()[0])
        caja = QMessageBox(QMessageBox.Critical, "Error",
                           "Ocurrió un error durante el proceso.", parent=self)
        caja.setInformativeText(mensaje.splitlines()[0])
        caja.setDetailedText(mensaje)
        caja.exec_()

    def _cancelar(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancelar()
            self.btn_cancelar.setEnabled(False)
            self.lbl_estado.setText("Cancelando... (termina el archivo actual)")

    def _ocupado(self, ocupado: bool):
        for rb, perfil in self.radios.items():
            rb.setEnabled(perfil.activo and not ocupado)
        for rb in self.radios_variantes:
            rb.setEnabled(not ocupado)
        self.tabs.tabBar().setEnabled(not ocupado)
        for panel in self.paneles:
            panel.setEnabled(not ocupado)
        self.btn_cancelar.setEnabled(ocupado)

    def _escribir_log(self, texto):
        self.log.appendPlainText(f"[{datetime.now():%H:%M:%S}] {texto}")

    # ------------------------------------------------------------ cierre
    def closeEvent(self, evento):
        if self.worker and self.worker.isRunning():
            r = QMessageBox.question(self, "Proceso en curso",
                                     "Hay un proceso en curso. ¿Cancelarlo y salir?")
            if r != QMessageBox.Yes:
                evento.ignore()
                return
            self.worker.cancelar()
            self.worker.wait(15000)
        evento.accept()
