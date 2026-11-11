"""
Perfiles por aseguradora.

Cada perfil define, como DATOS, las reglas de armado. Para agregar una
aseguradora nueva basta con crear otro PerfilAseguradora y registrarlo
en PERFILES; la lógica no cambia.

Extras:
- variantes: sub-opciones con su propia carpeta padre (ej. Nueva EPS:
  Subsidiado / Contributivo). Se muestran como una segunda fila de RadioButtons.
- carpeta_dinamica: la carpeta padre se arma con el nombre de la aseguradora
  leído de las FEV (ej. SOAT -> "SOAT PREVISORA").
"""
from dataclasses import dataclass, replace
import re


@dataclass(frozen=True)
class DefSoporte:
    """Un soporte esperado dentro de la carpeta del paciente."""
    codigo: str                 # Ej: "ANE2", "EKG"
    obligatorio: bool = False
    patron: str = ""            # Regex del nombre (sin extensión). Por defecto, el código exacto.

    def coincide(self, nombre_sin_ext: str) -> bool:
        patron = self.patron or re.escape(self.codigo)
        return re.fullmatch(patron, nombre_sin_ext, flags=re.IGNORECASE) is not None


@dataclass(frozen=True)
class ReglaPaquete:
    """Regla para armar un paquete (PDE o HEV). El orden de la lista = orden de unión."""
    prefijo: str
    soportes: tuple

    @property
    def obligatorios(self):
        return [s.codigo for s in self.soportes if s.obligatorio]


@dataclass(frozen=True)
class Variante:
    """Sub-opción de un perfil (ej. régimen Subsidiado de Nueva EPS)."""
    clave: str              # "SUB"
    nombre: str             # Texto del RadioButton: "Subsidiado"
    carpeta_padre: str      # "SUBSIDIADO"
    regimen: str            # Palabra que debe aparecer en "Tipo Usuario" de la FEV


@dataclass(frozen=True)
class PerfilAseguradora:
    clave: str                       # Identificador interno: "ASMET"
    nombre: str                      # Texto del RadioButton
    carpeta_padre: str               # Ej: "ASMET EVENTO" (o prefijo si es dinámica)
    palabras_administradora: tuple = ()   # La administradora de la FEV debe contener alguna
    palabras_texto: tuple = ()       # Alternativa: buscar en todo el texto de la FEV
    regla_pde: ReglaPaquete = None
    regla_hev: ReglaPaquete = None
    activo: bool = True              # False = visible pero deshabilitado ("próximamente")
    notas: str = ""
    variantes: tuple = ()            # Tupla de Variante
    regimen: str = ""                # Lo fija la variante escogida
    carpeta_dinamica: bool = False   # carpeta_padre + nombre corto de la aseguradora

    # -- helpers ------------------------------------------------------------
    def con_variante(self, variante: Variante) -> "PerfilAseguradora":
        """Perfil efectivo para una variante: cambia la carpeta y el régimen exigido."""
        return replace(self, nombre=f"{self.nombre} - {variante.nombre}",
                       carpeta_padre=variante.carpeta_padre, regimen=variante.regimen)

    def carpeta_esperada(self, nombre_carpeta: str) -> bool:
        """¿El nombre de la carpeta padre que escogió el usuario parece de este perfil?"""
        nombre = nombre_carpeta.strip().upper()
        if self.carpeta_dinamica:
            return nombre.startswith(self.carpeta_padre.upper())
        return nombre == self.carpeta_padre.upper()

    @property
    def descripcion_carpeta(self) -> str:
        if self.carpeta_dinamica:
            return f"{self.carpeta_padre} + nombre de la aseguradora (ej. {self.carpeta_padre} PREVISORA)"
        return self.carpeta_padre


# Palabras que se quitan para el nombre corto de la aseguradora (carpeta dinámica)
_LEGALES = {"S.A", "S.A.", "SA", "S.A.S", "S.A.S.", "SAS", "CIA", "CIA.", "COMPAÑIA", "COMPANIA",
            "SOAT", "NIT"}
_ARTICULOS_INICIALES = {"LA", "EL", "LOS", "LAS"}
_COLA = {"DE", "SEGUROS", "GENERALES", "Y"}


def nombre_corto_aseguradora(administradora: str) -> str:
    """'LA PREVISORA S.A cia Seguros' -> 'PREVISORA'
       'COMPAÑIA MUNDIAL DE SEGUROS SOAT' -> 'MUNDIAL'
       'SEGUROS DEL ESTADO S.A.' -> 'SEGUROS DEL ESTADO'"""
    palabras = [p for p in re.split(r"\s+", administradora.upper().strip()) if p]
    palabras = [p for p in palabras if p not in _LEGALES]
    while palabras and palabras[0] in _ARTICULOS_INICIALES:
        palabras.pop(0)
    if palabras[:2] == ["SEGUROS", "GENERALES"] and len(palabras) > 2:
        palabras = palabras[2:]
    while len(palabras) > 1 and palabras[-1] in _COLA:
        palabras.pop()
    return " ".join(palabras) or "ASEGURADORA"


# ---------------------------------------------------------------------------
# HEV: estructura general (igual para todas las aseguradoras de evento)
# ---------------------------------------------------------------------------
REGLA_HEV_GENERAL = ReglaPaquete(
    prefijo="HEV",
    soportes=(
        DefSoporte("HC", obligatorio=True),
        DefSoporte("TRI", obligatorio=True),
        DefSoporte("APL"),
        DefSoporte("REM", patron=r"REM\d*"),     # REM, REM1, REM2... (remisiones)
    ),
)

# ---------------------------------------------------------------------------
# ASMET SALUD
# ---------------------------------------------------------------------------
ASMET = PerfilAseguradora(
    clave="ASMET",
    nombre="Asmet Salud",
    carpeta_padre="ASMET EVENTO",
    palabras_administradora=("ASMET",),
    regla_pde=ReglaPaquete(
        prefijo="PDE",
        soportes=(
            DefSoporte("ANE2", obligatorio=True),
            DefSoporte("ANE3"),
            DefSoporte("ENV", obligatorio=True),
            DefSoporte("EST", obligatorio=True),
            DefSoporte("BIT", patron=r"BIT\d*"),     # BIT (bitácora), BIT1 (traslado)
            DefSoporte("RET"),
            DefSoporte("DIS"),
            DefSoporte("FIC"),
            DefSoporte("EKG", patron=r"EKG\d*"),   # EKG, EKG1, EKG2...
        ),
    ),
    regla_hev=REGLA_HEV_GENERAL,
)

# ---------------------------------------------------------------------------
# NUEVA EPS (con régimen: Subsidiado / Contributivo)
# ---------------------------------------------------------------------------
NUEVA_EPS = PerfilAseguradora(
    clave="NUEVA_EPS",
    nombre="Nueva EPS",
    carpeta_padre="SUBSIDIADO",
    palabras_administradora=("NUEVA EPS",),
    regla_pde=ReglaPaquete(
        prefijo="PDE",
        soportes=(
            DefSoporte("ANE2", obligatorio=True),
            DefSoporte("ANE3"),
            DefSoporte("ENV", obligatorio=True),
            DefSoporte("EST", obligatorio=True),
            DefSoporte("COD", obligatorio=True),
            DefSoporte("AUT", obligatorio=True),
            DefSoporte("BIT", patron=r"BIT\d*"),
            DefSoporte("TRAS", patron=r"TRAS\d*"),   # Traslado (Tras, Tras1...)
            DefSoporte("RET"),
            DefSoporte("DIS"),
            DefSoporte("FIC"),
            DefSoporte("EKG", patron=r"EKG\d*"),
        ),
    ),
    regla_hev=REGLA_HEV_GENERAL,
    variantes=(
        Variante("SUB", "Subsidiado", "SUBSIDIADO", "SUBSIDIADO"),
        Variante("CON", "Contributivo", "CONTRIBUTIVO", "CONTRIBUTIVO"),
    ),
)

# ---------------------------------------------------------------------------
# SOAT (cualquier aseguradora; la carpeta lleva su nombre)
# ---------------------------------------------------------------------------
SOAT = PerfilAseguradora(
    clave="SOAT",
    nombre="SOAT",
    carpeta_padre="SOAT",
    # La administradora es la aseguradora (Previsora, Mundial...): se reconoce
    # el SOAT por el plan de beneficio "Cobertura Póliza SOAT" del texto.
    palabras_texto=("SOAT",),
    regla_pde=ReglaPaquete(
        prefijo="PDE",
        soportes=(
            DefSoporte("SOAT", obligatorio=True),      # Póliza SOAT
            DefSoporte("TP", obligatorio=True),        # Tarjeta de propiedad
            DefSoporte("CC", obligatorio=True),        # Cédula del paciente
            DefSoporte("CCPROP"),                      # Cédula del propietario
            DefSoporte("CM", obligatorio=True),        # Certificado médico
            DefSoporte("BIT", patron=r"BIT\d*"),       # Bitácora
            DefSoporte("TRAS", patron=r"TRAS\d*"),     # Traslado
            DefSoporte("RET"),                         # Retiro voluntario
            DefSoporte("DIS"),                         # Desistimiento de remisión
        ),
    ),
    regla_hev=REGLA_HEV_GENERAL,
    carpeta_dinamica=True,
)

# ---------------------------------------------------------------------------
# Perfiles preparados para el futuro (deshabilitados por ahora)
# ---------------------------------------------------------------------------
SANITAS = PerfilAseguradora(
    clave="SANITAS",
    nombre="Sanitas",
    carpeta_padre="SANITAS SUBSIDIADO",
    palabras_administradora=("SANITAS",),
    regla_pde=ASMET.regla_pde,            # Mismos soportes y orden que Asmet Salud
    regla_hev=REGLA_HEV_GENERAL,
    # Prefijo "SANITAS" para no chocar con las carpetas de Nueva EPS
    variantes=(
        Variante("SUB", "Subsidiado", "SANITAS SUBSIDIADO", "SUBSIDIADO"),
        Variante("CON", "Contributivo", "SANITAS CONTRIBUTIVO", "CONTRIBUTIVO"),
    ),
)

OTRO_EVENTO = PerfilAseguradora(
    clave="OTRO", nombre="Otro tipo de evento", carpeta_padre="OTRO EVENTO",
    activo=False,
)

# Orden = orden de los RadioButton en la interfaz
PERFILES = (ASMET, NUEVA_EPS, SANITAS, SOAT, OTRO_EVENTO)


def obtener_perfil(clave: str) -> PerfilAseguradora:
    for p in PERFILES:
        if p.clave == clave:
            return p
    raise KeyError(f"Aseguradora no registrada: {clave}")
