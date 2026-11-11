"""
Fase 3: deja en cada carpeta solo FEV, PDE y HEV, mueve el resto a la carpeta de
respaldo y renombra la carpeta al número del consecutivo.

    ASMET EVENTO/PEREZ PEPITO 152334/{FEV, PDE, HEV, ANE2, ENV, ...}
 -> ASMET EVENTO/152334/{FEV, PDE, HEV}
    ASMET EVENTO_RESPALDO/PEREZ PEPITO 152334/{FEV, PDE, HEV (copias), ANE2, ENV, ...}

Seguridad:
- Primero se PLANEA (no toca nada) para mostrarlo en la confirmación.
- Se omite la carpeta si le falta FEV, PDE o HEV (si no, se perderían los soportes
  del paquete sin armar). El usuario corrige, corre la Fase 2 y vuelve a limpiar.
- Nada se borra: todo va al respaldo. Si un nombre ya existe en el respaldo, se
  agrega un sufijo (_1, _2...).
"""
import re
import shutil
from pathlib import Path
from typing import Callable, Optional

from app.config.aseguradoras import PerfilAseguradora
from app.config.constantes import (PATRON_ARCHIVO_FEV, PREFIJO_FEV, PREFIJO_HEV,
                                   PREFIJO_PDE, SUFIJO_RESPALDO, nombre_paquete)
from app.core.modelos import (AccionFase3, PlanCarpeta, ResultadoFase3,
                              ResultadoLimpieza)
from app.services.exportador_excel import ExportadorExcel

Progreso = Callable[[int, int, str], None]
Cancelado = Callable[[], bool]

_RE_FEV = re.compile(PATRON_ARCHIVO_FEV, re.IGNORECASE)
_RE_NUM_FINAL = re.compile(r"(\d+)\s*$")


class LimpiadorCarpetas:

    def __init__(self, perfil: PerfilAseguradora, exportador: ExportadorExcel = None):
        self.perfil = perfil
        self.exportador = exportador or ExportadorExcel()

    # ------------------------------------------------------------------ API
    @staticmethod
    def carpeta_respaldo(carpeta_padre: Path) -> Path:
        carpeta_padre = Path(carpeta_padre)
        return carpeta_padre.parent / f"{carpeta_padre.name}{SUFIJO_RESPALDO}"

    def planear(self, carpeta_padre) -> list:
        """Calcula qué se hará con cada carpeta, sin modificar nada."""
        carpetas = sorted(p for p in Path(carpeta_padre).iterdir() if p.is_dir())
        return [self._planear_carpeta(c) for c in carpetas]

    def ejecutar(self, carpeta_padre, plan: list = None,
                 progreso: Optional[Progreso] = None,
                 cancelado: Optional[Cancelado] = None) -> ResultadoFase3:
        progreso = progreso or (lambda *a: None)
        cancelado = cancelado or (lambda: False)
        carpeta_padre = Path(carpeta_padre)
        plan = plan if plan is not None else self.planear(carpeta_padre)

        respaldo = self.carpeta_respaldo(carpeta_padre)
        resultado = ResultadoFase3(carpeta_padre=carpeta_padre, carpeta_respaldo=respaldo)

        total = len(plan)
        for n, p in enumerate(plan, 1):
            if cancelado():
                resultado.cancelado = True
                break
            r = self._ejecutar_carpeta(p, respaldo)
            resultado.items.append(r)
            progreso(n, total, f"{p.carpeta.name}: {r.accion.value}")

        progreso(total, total, "Generando registro de limpieza...")
        resultado.ruta_excel = self.exportador.exportar_fase3(
            resultado, carpeta_padre.parent / f"{carpeta_padre.name} - LIMPIEZA.xlsx")
        return resultado

    # ------------------------------------------------------------ planear
    def _planear_carpeta(self, carpeta: Path) -> PlanCarpeta:
        p = PlanCarpeta(carpeta=carpeta)
        contenido = list(carpeta.iterdir())
        fevs = [f for f in contenido if f.is_file() and _RE_FEV.match(f.name)]

        if len(fevs) != 1:
            p.accion = AccionFase3.OMITIR
            p.motivo = "No tiene FEV" if not fevs else f"Tiene {len(fevs)} FEV"
            return p

        consecutivo = _RE_FEV.match(fevs[0].name).group(1).upper()
        p.numero = consecutivo[3:]
        esperados = {nombre_paquete(pref, consecutivo).upper()
                     for pref in (PREFIJO_FEV, PREFIJO_PDE, PREFIJO_HEV)}

        for item in contenido:
            if item.is_file() and item.name.upper() in esperados:
                p.conservar.append(item)
            else:
                p.respaldar.append(item)

        presentes = {f.name.upper() for f in p.conservar}
        faltan = [pref for pref in (PREFIJO_PDE, PREFIJO_HEV)
                  if nombre_paquete(pref, consecutivo).upper() not in presentes]
        destino = carpeta.parent / p.numero

        if faltan:
            p.accion = AccionFase3.OMITIR
            p.motivo = f"Falta {' y '.join(faltan)} (corre la Fase 2 primero)"
        elif carpeta.name == p.numero and not p.respaldar:
            p.accion = AccionFase3.YA_LIMPIA
        elif carpeta.name != p.numero and destino.exists():
            p.accion = AccionFase3.OMITIR
            p.motivo = f"Ya existe otra carpeta llamada {p.numero}"
        return p

    # ------------------------------------------------------------ ejecutar
    def _ejecutar_carpeta(self, p: PlanCarpeta, respaldo: Path) -> ResultadoLimpieza:
        r = ResultadoLimpieza(plan=p, carpeta_final=p.carpeta)
        if p.accion != AccionFase3.LIMPIAR:
            return r

        destino_resp = respaldo / p.carpeta.name
        destino_resp.mkdir(parents=True, exist_ok=True)

        # 1) COPIAR FEV, PDE y HEV al respaldo (medida preventiva: el respaldo
        #    queda como copia completa de la carpeta antes de limpiar)
        for item in p.conservar:
            try:
                copia = destino_resp / item.name
                if not copia.exists():
                    shutil.copy2(str(item), str(copia))
            except Exception as e:
                r.errores.append(f"No se pudo copiar {item.name} al respaldo: {_motivo(e)}")
        if r.errores:
            return r                    # Sin copia de seguridad no se toca nada más

        # 2) MOVER los soportes al respaldo
        if p.respaldar:
            for item in p.respaldar:
                try:
                    shutil.move(str(item), str(_ruta_libre(destino_resp / item.name)))
                    r.respaldados += 1
                except Exception as e:
                    r.errores.append(f"No se pudo mover {item.name}: {_motivo(e)}")

        # 3) Renombrar solo si todo se movió bien
        if r.errores or p.carpeta.name == p.numero:
            return r
        try:
            nueva = p.carpeta.with_name(p.numero)
            p.carpeta.rename(nueva)
            r.carpeta_final = nueva
        except Exception as e:
            r.errores.append(f"No se pudo renombrar: {_motivo(e)}")
        return r


def _ruta_libre(ruta: Path) -> Path:
    """ANE2.pdf -> ANE2_1.pdf si ya existe."""
    if not ruta.exists():
        return ruta
    n = 1
    while True:
        candidata = ruta.with_name(f"{ruta.stem}_{n}{ruta.suffix}")
        if not candidata.exists():
            return candidata
        n += 1


def _motivo(e: Exception) -> str:
    if isinstance(e, PermissionError):
        return "archivo abierto o sin permisos (ciérralo e intenta de nuevo)"
    return f"{type(e).__name__}: {e}"
