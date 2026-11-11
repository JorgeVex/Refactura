"""Utilidades para nombres de archivos y carpetas compatibles con Windows."""
import re

_INVALIDOS = r'[\\/:*?"<>|]'
_RESERVADOS = {"CON", "PRN", "AUX", "NUL",
               *(f"COM{i}" for i in range(1, 10)),
               *(f"LPT{i}" for i in range(1, 10))}


def nombre_carpeta_seguro(texto: str) -> str:
    """Quita caracteres no válidos en Windows, espacios dobles y puntos/espacios finales.
    Conserva tildes y Ñ (Windows las acepta)."""
    limpio = re.sub(_INVALIDOS, "", texto or "")
    limpio = re.sub(r"\s+", " ", limpio).strip().rstrip(". ")
    if limpio.upper() in _RESERVADOS:
        limpio = f"_{limpio}"
    return limpio or "SIN_NOMBRE"
