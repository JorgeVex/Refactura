"""
Worker genérico en QThread para tareas largas (Fase 1, 2 y 3).

La tarea es cualquier función con la firma:
    tarea(progreso: Callable[[int, int, str], None], cancelado: Callable[[], bool]) -> resultado

Uso en la UI:
    self.worker = WorkerTarea(lambda prog, canc: organizador.ejecutar(origen, destino, prog, canc))
    self.worker.progreso.connect(self.actualizar_barra)
    self.worker.terminado.connect(self.mostrar_resultado)
    self.worker.fallo.connect(self.mostrar_error)
    self.worker.start()
"""
import traceback

from PyQt5.QtCore import QThread, pyqtSignal


class WorkerTarea(QThread):
    progreso = pyqtSignal(int, int, str)   # actual, total, mensaje
    terminado = pyqtSignal(object)         # resultado de la tarea
    fallo = pyqtSignal(str)                # mensaje de error con traceback

    def __init__(self, tarea, parent=None):
        super().__init__(parent)
        self._tarea = tarea
        self._cancelar = False

    def cancelar(self):
        self._cancelar = True

    def run(self):
        try:
            resultado = self._tarea(self._emitir_progreso, lambda: self._cancelar)
            self.terminado.emit(resultado)
        except Exception as e:
            self.fallo.emit(f"{e}\n\n{traceback.format_exc()}")

    def _emitir_progreso(self, actual, total, mensaje):
        self.progreso.emit(actual, total, mensaje)
