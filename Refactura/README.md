# Refactura

App de escritorio (PyQt5) para la **devolución masiva de facturas** del equipo de
facturación de la E.S.E. Hospital Laura Perdomo de García. Soporta **Asmet Salud**, **Nueva EPS** y **Sanitas**
(Subsidiado / Contributivo) y **SOAT**; está preparada para agregar otros eventos.

## Flujo

| Fase | Entrada | Resultado |
|---|---|---|
| **1. Organizar FEV** | Carpeta con todas las `FEV_813003431_LPG#####.pdf` | `ASMET EVENTO/<NOMBRE CONSECUTIVO>/FEV_...pdf` (copias) + `ASMET EVENTO - PACIENTES.xlsx` |
| *(manual)* | Descargar soportes con el Excel | `ANE2.pdf`, `ENV.pdf`, `TRI.pdf`... dentro de cada carpeta |
| **2. Armar soportes** | Carpeta `ASMET EVENTO` | `PDE_...pdf` y `HEV_...pdf` por carpeta + `ASMET EVENTO - REPORTE SOPORTES.xlsx` |
| **3. Limpiar carpetas** | Carpeta `ASMET EVENTO` | Cada carpeta queda solo con FEV, PDE y HEV y se renombra al número del consecutivo. Copia completa en `ASMET EVENTO_RESPALDO` + `ASMET EVENTO - LIMPIEZA.xlsx` |

### Reglas por aseguradora (orden de unión; **negrilla = obligatorio**)

| Aseguradora | Carpeta padre | PDE | HEV |
|---|---|---|---|
| **Asmet Salud** | `ASMET EVENTO` | **ANE2** → ANE3 → **ENV** → **EST** → BIT (BIT1) → RET → DIS → FIC → EKG (EKG1...) | **HC** → **TRI** → APL → REM (REM1...) |
| **Nueva EPS** | `SUBSIDIADO` o `CONTRIBUTIVO` (según el régimen escogido) | **ANE2** → ANE3 → **ENV** → **EST** → **COD** → **AUT** → BIT → Tras → RET → DIS → FIC → EKG | igual |
| **Sanitas** | `SANITAS SUBSIDIADO` o `SANITAS CONTRIBUTIVO` | igual que Asmet Salud | igual |
| **SOAT** | `SOAT <ASEGURADORA>` (ej. `SOAT PREVISORA`), tomado de las FEV | **SOAT** → **TP** → **CC** → CCPROP → **CM** → BIT → Tras → RET → DIS | igual |

- **Nueva EPS y Sanitas:** las FEV cuyo *Tipo Usuario* no coincide con el régimen escogido se excluyen (hoja Novedades).
- **SOAT:** se reconoce por "Cobertura Póliza SOAT". Si en el lote hay FEV de otra aseguradora SOAT, se excluyen: organizar un lote por aseguradora.

Si falta un obligatorio, el paquete se arma con lo que haya y queda marcado como
**INCOMPLETO** en el reporte.

## 4. Limpiador de RIPS

Pestaña independiente de la aseguradora. Se escoge la carpeta padre de los RIPS
(una subcarpeta por factura) y en cada subcarpeta:

- **Se conservan:** el `.json`, el `.xml` y el `.txt` cuyo nombre termina en `CUV`.
- **Se eliminan DEFINITIVAMENTE** (sin papelera) todos los demás archivos
  (`ResultadosLocales_...`, `..._R`, etc.).
- Las carpetas **sin CUV no se tocan** (RIPS rechazados o sin validar) y quedan marcadas.
- Se decide por la extensión real, no por el contenido.
- Reporte: `<CARPETA> - LIMPIEZA RIPS.xlsx`, al lado de la carpeta padre.

## Ejecutar en desarrollo

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py
```

## Generar el ejecutable

Doble clic en **`build.bat`**. Crea el entorno, instala dependencias y deja
**`dist\Refactura.exe`** (un solo archivo, no necesita Python instalado).

Manual: `pyinstaller --clean --noconfirm Refactura.spec`

## Datos de prueba

```bat
python herramientas\generar_fev_prueba.py                     :: 50 FEV en FEV_PRUEBA
python herramientas\generar_fev_prueba.py -n 1000 -o FEV_MIL  :: prueba de volumen
python herramientas\generar_fev_prueba.py --aseguradora soat -o FEV_SOAT
python herramientas\generar_fev_prueba.py --aseguradora nueva_eps -o FEV_NEPS
python herramientas\generar_soportes_prueba.py "SALIDA\ASMET EVENTO"
python herramientas\generar_rips_prueba.py -o "RIPS_PRUEBA\NUEVA. SUB"
```

Pruebas por consola (sin interfaz): `herramientas\probar_lector.py`,
`probar_fase1.py`, `probar_fase2.py`, `probar_fase3.py`, `probar_rips.py`.

## Estructura

```
Refactura/
├── main.py                  Punto de entrada
├── Refactura.spec           Configuración de PyInstaller
├── build.bat                Compilación en un clic
├── recursos/                Ícono y logo
├── herramientas/            Generadores de datos y pruebas por consola
└── app/
    ├── config/              Constantes y perfiles por aseguradora (reglas como datos)
    ├── core/                Modelos (Factura, resultados de cada fase)
    ├── services/            Lector FEV, organizador, clasificador, armador, limpiador, Excel
    ├── workers/             QThread genérico (progreso y cancelación)
    ├── utils/               Nombres de carpeta seguros, rutas de recursos
    └── ui/                  Ventana, paneles por fase, estilos
```

## Agregar una aseguradora

En `app/config/aseguradoras.py`: definir su `regla_pde` (y `regla_hev` si cambia),
poner `activo=True` y listo; aparece habilitada en los RadioButtons.
