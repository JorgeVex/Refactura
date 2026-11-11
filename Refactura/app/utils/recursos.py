"""Rutas a recursos (ícono, logo) que funcionan en desarrollo y dentro del .exe."""
import sys
from pathlib import Path


def ruta_recurso(nombre: str) -> Path:
    """
    En desarrollo: <proyecto>/recursos/<nombre>
    En el .exe (PyInstaller): <carpeta temporal _MEIPASS>/recursos/<nombre>
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "recursos" / nombre
