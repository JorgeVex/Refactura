# Refactura

Aplicación de escritorio en Python (PyQt5) que automatiza la devolución masiva de facturas de una IPS: organiza las facturas electrónicas (FEV), arma los paquetes de soportes por aseguradora, valida los documentos faltantes y limpia las carpetas de RIPS. Se distribuye como un ejecutable de Windows que no requiere Python instalado.

Desarrollada para el equipo de facturación de la E.S.E. Hospital Laura Perdomo de García (Yaguará, Huila).

## Problema

Cuando una aseguradora devuelve facturas, cada una debe radicarse de nuevo con sus soportes organizados en un orden y una nomenclatura específicos. Con lotes de cientos o miles de facturas, el proceso manual implicaba crear una carpeta por paciente, unir PDF uno por uno, revisar qué documento faltaba en cada caso y dejar todo con el nombre exigido. Era lento y propenso a errores que generaban nuevas devoluciones.

## Qué hace

El proceso se divide en fases, cada una en su propia pestaña:

| Fase | Entrada | Resultado |
| --- | --- | --- |
| 1. Organizar FEV | Carpeta con todas las facturas en PDF | Una carpeta por paciente y factura, más un Excel con nombre, documento, aseguradora y fecha leídos de cada FEV |
| 2. Armar soportes | Carpeta con los soportes descargados | Paquetes PDE y HEV por factura, unidos en el orden que exige cada aseguradora, más un reporte en Excel de completos e incompletos |
| 3. Limpiar carpetas | Carpeta de la fase 2 | Cada carpeta queda solo con FEV, PDE y HEV, renombrada al consecutivo; copia de respaldo de todo lo demás |
| Limpiador de RIPS | Carpeta de RIPS por factura | Conserva el JSON, el XML y el TXT con CUV; elimina el resto y marca las carpetas sin validar |

Aseguradoras soportadas: Asmet Salud, Nueva EPS y Sanitas (régimen subsidiado y contributivo) y SOAT.

Detalles relevantes:

- Lee las facturas directamente del PDF y soporta los dos formatos que genera el sistema de facturación de la institución.
- Si falta un soporte obligatorio, el paquete se arma con lo disponible y queda marcado como incompleto en el reporte, en lugar de detener el proceso.
- Excluye y reporta las facturas cuyo régimen no coincide con el escogido.
- Las reglas de cada aseguradora (soportes, orden de unión, obligatorios, carpeta destino) están definidas como datos. Agregar una aseguradora nueva no requiere cambiar la lógica.
- Las tareas largas corren en un hilo aparte (QThread), con barra de progreso y opción de cancelar, para que la interfaz no se congele con lotes grandes.

## Tecnologías

| Área | Herramientas |
| --- | --- |
| Interfaz | PyQt5, QSS con los colores institucionales |
| Lectura y unión de PDF | pdfplumber, pypdf |
| Reportes | openpyxl |
| Distribución | PyInstaller (un solo archivo .exe) |

## Arquitectura

```
Refactura/
├── main.py                 Punto de entrada
├── app/
│   ├── config/             Perfiles por aseguradora y constantes
│   ├── core/               Modelos de dominio
│   ├── services/           Lógica de cada fase: lector de FEV, organizador,
│   │                       clasificador de soportes, armador de paquetes,
│   │                       limpiadores y exportación a Excel
│   ├── workers/            Ejecución de tareas largas en segundo plano
│   ├── ui/                 Ventana principal, paneles y estilos
│   └── utils/              Nombres de archivo y rutas de recursos
├── herramientas/           Generadores de datos de prueba y pruebas por consola
├── docs/                   Manual de usuario y documento del proceso
└── build.bat               Compilación del ejecutable en un clic
```

La interfaz no contiene lógica de negocio: los paneles solo piden tareas a la ventana principal, que las ejecuta en el worker usando los servicios. Esto permite probar cada fase por consola sin abrir la aplicación.

## Instalación y uso

Requiere Python 3.10 o superior en Windows.

```bat
git clone https://github.com/JorgeVex/refactura.git
cd refactura\Refactura
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py
```

Para generar el ejecutable, doble clic en `build.bat`. El resultado queda en `dist\Refactura.exe`.

## Pruebas

El repositorio no incluye datos reales de pacientes. La carpeta `herramientas/` genera facturas, soportes y RIPS sintéticos, incluida una prueba de volumen con 1.000 facturas:

```bat
python herramientas\generar_fev_prueba.py -n 1000 -o FEV_MIL
python herramientas\generar_soportes_prueba.py "SALIDA\ASMET EVENTO"
python herramientas\probar_fase2.py
```

## Documentación

- [Manual de usuario](Refactura/docs/Manual%20de%20usuario%20-%20Refactura.pdf)
- [Proceso de refacturación Asmet Salud](Refactura/docs/Proceso%20de%20refacturacion%20Asmet%20Salud.pdf)
- [Documentación técnica detallada](Refactura/README.md): reglas por aseguradora, nomenclatura de soportes y comandos de prueba

## Autor

Jorge Hernán Velasco Gómez · [GitHub](https://github.com/JorgeVex) · [LinkedIn](https://linkedin.com/in/jorge-hernán-velasco-gomez-776b39266)
