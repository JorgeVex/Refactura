"""Refactura - punto de entrada de la aplicación."""
import sys

from PyQt5.QtCore import QLibraryInfo, Qt, QTranslator
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

# Pantallas con escalado (125%, 150%) en Windows
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

from app import __version__                            # noqa: E402
from app.ui.estilos import QSS                         # noqa: E402
from app.ui.ventana_principal import VentanaPrincipal  # noqa: E402
from app.utils.recursos import ruta_recurso            # noqa: E402


def _icono_barra_tareas_windows():
    """Hace que Windows muestre el ícono de Refactura (y no el de Python) en la barra."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"ESE_LPG.Refactura.{__version__}")
        except Exception:
            pass


def main():
    _icono_barra_tareas_windows()
    app = QApplication(sys.argv)
    app.setApplicationName("Refactura")
    app.setOrganizationName("ESE_LPG")
    app.setWindowIcon(QIcon(str(ruta_recurso("icono.ico"))))
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)

    # Botones estándar de Qt en español ("Ver detalles...", "Sí", "No", "Cancelar")
    traductor = QTranslator(app)
    if traductor.load("qtbase_es", QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        app.installTranslator(traductor)

    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
