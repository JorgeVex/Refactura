"""Constantes generales de la IPS y de nombres de archivo."""

NIT_IPS = "813003431"
PREFIJO_FACTURA = "LPG"

# Prefijos de los paquetes finales
PREFIJO_FEV = "FEV"
PREFIJO_HEV = "HEV"
PREFIJO_PDE = "PDE"

# FEV_813003431_LPG152133.pdf  -> grupo 1 = LPG152133, grupo 2 = 152133
PATRON_ARCHIVO_FEV = rf"^{PREFIJO_FEV}_{NIT_IPS}_({PREFIJO_FACTURA}(\d+))\.pdf$"

# Sufijo de la carpeta de respaldo (ej. "ASMET EVENTO_RESPALDO")
SUFIJO_RESPALDO = "_RESPALDO"


def nombre_paquete(prefijo: str, consecutivo: str) -> str:
    """Ej: nombre_paquete("PDE", "LPG152133") -> PDE_813003431_LPG152133.pdf"""
    return f"{prefijo}_{NIT_IPS}_{consecutivo}.pdf"
