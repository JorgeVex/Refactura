# -*- mode: python ; coding: utf-8 -*-
# Especificación de PyInstaller para Refactura.
# Compilar con:  pyinstaller --clean --noconfirm Refactura.spec   (o ejecutar build.bat)
# Resultado:     dist/Refactura.exe  (un solo archivo, sin consola)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("recursos/icono.ico", "recursos"),
           ("recursos/icono.png", "recursos")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    # Librerías que no usa la app: el .exe queda más liviano
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "scipy", "IPython",
              "jupyter", "pytest", "reportlab", "PyQt5.QtWebEngineWidgets",
              "PyQt5.QtWebEngineCore", "PyQt5.QtQml", "PyQt5.QtQuick",
              "PyQt5.QtMultimedia", "PyQt5.QtSql", "PyQt5.QtNetwork"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Refactura",
    icon="recursos/icono.ico",
    console=False,        # Sin ventana negra de consola
    upx=False,            # UPX a veces dispara falsos positivos del antivirus
    debug=False,
    strip=False,
    runtime_tmpdir=None,
)
