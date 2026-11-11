"""
Clasifica los PDF de la carpeta de un paciente según las reglas del perfil.

ANE2.pdf, ane2.PDF -> "ANE2" | EKG1.pdf, EKG2.pdf -> "EKG" (varios) | FEV_... -> FEV
Los paquetes ya armados (PDE_..., HEV_...) se ignoran.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config.aseguradoras import PerfilAseguradora
from app.config.constantes import PATRON_ARCHIVO_FEV, NIT_IPS, PREFIJO_PDE, PREFIJO_HEV

_RE_FEV = re.compile(PATRON_ARCHIVO_FEV, re.IGNORECASE)
_RE_PAQUETE = re.compile(rf"^({PREFIJO_PDE}|{PREFIJO_HEV})_{NIT_IPS}_", re.IGNORECASE)
_RE_NUM_FINAL = re.compile(r"(\d+)\s*$")


@dataclass
class Clasificacion:
    carpeta: Path
    fevs: list = field(default_factory=list)          # Debería ser exactamente 1
    soportes: dict = field(default_factory=dict)      # código -> [Path] ordenados
    no_reconocidos: list = field(default_factory=list)

    @property
    def consecutivo(self) -> str:
        """Del nombre de la FEV; si no hay FEV, del número al final de la carpeta."""
        if self.fevs:
            return _RE_FEV.match(self.fevs[0].name).group(1).upper()
        m = _RE_NUM_FINAL.search(self.carpeta.name)
        return f"LPG{m.group(1)}" if m else ""


class ClasificadorSoportes:

    def __init__(self, perfil: PerfilAseguradora):
        self.perfil = perfil
        self._defs = [d for regla in (perfil.regla_pde, perfil.regla_hev) if regla
                      for d in regla.soportes]

    def clasificar(self, carpeta: Path) -> Clasificacion:
        c = Clasificacion(carpeta=Path(carpeta))
        for ruta in sorted(Path(carpeta).iterdir(), key=lambda p: _orden_natural(p.stem)):
            if not ruta.is_file() or ruta.suffix.lower() != ".pdf":
                if ruta.is_file():
                    c.no_reconocidos.append(ruta.name)
                continue
            if _RE_FEV.match(ruta.name):
                c.fevs.append(ruta)
            elif _RE_PAQUETE.match(ruta.name):
                continue                                   # PDE/HEV ya armados
            else:
                codigo = self._codigo_de(ruta.stem.strip())
                if codigo:
                    c.soportes.setdefault(codigo, []).append(ruta)
                else:
                    c.no_reconocidos.append(ruta.name)
        return c

    def _codigo_de(self, nombre_sin_ext: str):
        for d in self._defs:
            if d.coincide(nombre_sin_ext):
                return d.codigo
        return None


def _orden_natural(texto: str):
    """EKG, EKG1, EKG2, EKG10 (y no EKG1, EKG10, EKG2)."""
    return [int(t) if t.isdigit() else t.upper() for t in re.split(r"(\d+)", texto)]
