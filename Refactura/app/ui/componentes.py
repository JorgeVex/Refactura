"""Componentes reutilizables de la interfaz."""
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, QUrl, Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QWidget, QGroupBox, QVBoxLayout)


def abrir_ruta(ruta):
    """Abre una carpeta o archivo con la aplicación predeterminada de Windows."""
    if ruta and Path(ruta).exists():
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta)))


class SelectorCarpeta(QWidget):
    """Etiqueta + campo de solo lectura + botón 'Examinar...'."""
    cambiada = pyqtSignal(object)   # Path

    def __init__(self, etiqueta: str, titulo_dialogo: str, parent=None):
        super().__init__(parent)
        self._titulo = titulo_dialogo
        self._ruta = None

        self.lbl = QLabel(etiqueta)
        self.lbl.setMinimumWidth(150)
        self.campo = QLineEdit()
        self.campo.setReadOnly(True)
        self.campo.setPlaceholderText("Selecciona una carpeta...")
        self.campo.setMinimumWidth(120)   # Rutas largas no deben ensanchar la ventana
        self.btn = QPushButton("Examinar...")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self._elegir)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.lbl)
        lay.addWidget(self.campo, 1)
        lay.addWidget(self.btn)

    @property
    def ruta(self):
        return self._ruta

    def set_ruta(self, ruta, emitir=True):
        self._ruta = Path(ruta) if ruta else None
        self.campo.setText(str(self._ruta) if self._ruta else "")
        self.campo.setToolTip(self.campo.text())
        if emitir:
            self.cambiada.emit(self._ruta)

    def _elegir(self):
        inicio = str(self._ruta) if self._ruta else ""
        ruta = QFileDialog.getExistingDirectory(self, self._titulo, inicio)
        if ruta:
            self.set_ruta(ruta)


class Tarjeta(QGroupBox):
    """Contenedor blanco con título y descripción opcional."""

    def __init__(self, titulo: str, descripcion: str = "", parent=None):
        super().__init__(titulo, parent)
        self.cuerpo = QVBoxLayout(self)
        self.cuerpo.setSpacing(10)
        if descripcion:
            lbl = QLabel(descripcion)
            lbl.setObjectName("Descripcion")
            lbl.setWordWrap(True)
            self.cuerpo.addWidget(lbl)


class CajaResumen(QLabel):
    """Resumen del último resultado (verde = bien, ámbar = revisar)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Resumen")
        self.setWordWrap(True)
        self.setTextFormat(Qt.RichText)
        self.hide()

    def mostrar(self, html: str, alerta: bool = False):
        self.setProperty("tipo", "alerta" if alerta else "")
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText(html)
        self.show()


def boton(texto: str, nombre_objeto: str = "", al_click=None) -> QPushButton:
    b = QPushButton(texto)
    if nombre_objeto:
        b.setObjectName(nombre_objeto)
    b.setCursor(Qt.PointingHandCursor)
    if al_click:
        b.clicked.connect(al_click)
    return b
