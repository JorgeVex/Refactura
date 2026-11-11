"""Paleta y hoja de estilos (QSS) con los colores de la E.S.E. Laura Perdomo de García."""

AZUL = "#1F6FD1"          # Azul del logo LPG
AZUL_OSCURO = "#0F3D7A"   # Encabezado
AZUL_HOVER = "#1A5DB0"
VERDE = "#8CC63F"         # Verde lima "E.S.E. HOSPITAL"
VERDE_OSCURO = "#6FA22C"
FONDO = "#F3F6FA"
TARJETA = "#FFFFFF"
BORDE = "#DCE3EC"
TEXTO = "#1E2A38"
TEXTO_SUAVE = "#5B6B7F"
ROJO = "#D64545"
ROJO_HOVER = "#B83636"
AMBAR = "#E9A400"

QSS = f"""
* {{
    font-family: "Segoe UI", "Arial";
    font-size: 10pt;
    color: {TEXTO};
}}
QMainWindow, QWidget#Central {{ background: {FONDO}; }}

/* ---------- Encabezado ---------- */
QFrame#Encabezado {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {AZUL_OSCURO}, stop:1 {AZUL});
    border-bottom: 4px solid {VERDE};
}}
QLabel#Logo {{ background: white; border-radius: 12px; }}
QLabel#Titulo {{ color: white; font-size: 18pt; font-weight: 700; }}
QLabel#Subtitulo {{ color: #CFE0F5; font-size: 9.5pt; }}
QLabel#Insignia {{
    color: {AZUL_OSCURO}; background: {VERDE}; border-radius: 10px;
    padding: 4px 12px; font-weight: 700; font-size: 9pt;
}}

/* ---------- Tarjetas ---------- */
QGroupBox {{
    background: {TARJETA}; border: 1px solid {BORDE}; border-radius: 10px;
    margin-top: 14px; padding: 14px 12px 10px 12px; font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 14px; padding: 0 6px;
    color: {AZUL_OSCURO};
}}
QLabel#Descripcion {{ color: {TEXTO_SUAVE}; }}
QLabel#Resumen {{
    background: #EEF7E3; border: 1px solid #CFE7B0; border-left: 4px solid {VERDE};
    border-radius: 6px; padding: 8px 10px;
}}
QLabel#Resumen[tipo="alerta"] {{
    background: #FFF6DD; border: 1px solid #F3DC9C; border-left: 4px solid {AMBAR};
}}

/* ---------- RadioButtons ---------- */
QRadioButton {{ spacing: 8px; padding: 4px 10px 4px 2px; }}
QRadioButton:disabled {{ color: #A3AEBB; }}
QRadioButton::indicator {{
    width: 14px; height: 14px; border-radius: 9px;
    border: 2px solid #9AA9BC; background: white;
}}
QRadioButton::indicator:hover {{ border-color: {AZUL}; }}
QRadioButton::indicator:checked {{
    border: 2px solid {AZUL};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {AZUL}, stop:0.5 {AZUL}, stop:0.6 white, stop:1 white);
}}
QRadioButton::indicator:disabled {{ border-color: #D3DAE3; background: #F1F4F8; }}

/* ---------- Pestañas ---------- */
QTabWidget::pane {{ border: none; background: transparent; }}
/* La negrilla de las pestañas se asigna con setFont() en la ventana (no aquí),
   para que Qt calcule el ancho con la misma fuente con la que dibuja. */
QTabBar::tab {{
    background: transparent; color: {TEXTO_SUAVE};
    padding: 9px 22px; margin-right: 4px; min-width: 150px;
    border-bottom: 3px solid transparent;
}}
QTabBar::tab:hover {{ color: {AZUL}; }}
QTabBar::tab:selected {{ color: {AZUL_OSCURO}; border-bottom: 3px solid {VERDE}; }}
QTabBar::tab:disabled {{ color: #B5BFCB; }}

/* ---------- Campos ---------- */
QLineEdit {{
    background: white; border: 1px solid {BORDE}; border-radius: 6px; padding: 6px 8px;
}}
QLineEdit:focus {{ border: 1px solid {AZUL}; }}
QLineEdit[readOnly="true"] {{ background: #F8FAFC; }}

/* ---------- Botones ---------- */
QPushButton {{
    background: white; color: {AZUL}; border: 1px solid {AZUL};
    border-radius: 6px; padding: 6px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: #EAF2FC; }}
QPushButton:disabled {{ color: #A3AEBB; border-color: #D3DAE3; background: #F6F8FA; }}

QPushButton#Primario {{ background: {AZUL}; color: white; border: none; padding: 9px 22px; }}
QPushButton#Primario:hover {{ background: {AZUL_HOVER}; }}
QPushButton#Primario:disabled {{ background: #B9C9DE; color: white; }}

QPushButton#Peligro {{ background: {ROJO}; color: white; border: none; padding: 9px 22px; }}
QPushButton#Peligro:hover {{ background: {ROJO_HOVER}; }}
QPushButton#Peligro:disabled {{ background: #E8B7B7; color: white; }}

QPushButton#Enlace {{ border: none; background: transparent; color: {AZUL}; padding: 4px 6px; }}
QPushButton#Enlace:hover {{ text-decoration: underline; }}
QPushButton#Enlace:disabled {{ color: #B5BFCB; }}

QPushButton#Cancelar {{ color: {ROJO}; border-color: {ROJO}; }}
QPushButton#Cancelar:hover {{ background: #FBECEC; }}
QPushButton#Cancelar:disabled {{ color: #C9CFD8; border-color: #E1E6ED; background: #F8FAFC; }}

/* ---------- Progreso y log ---------- */
QProgressBar {{
    background: #E4EAF1; border: none; border-radius: 7px; height: 14px;
    text-align: center; color: {AZUL_OSCURO}; font-size: 8.5pt; font-weight: 600;
}}
QProgressBar::chunk {{
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {VERDE_OSCURO}, stop:1 {VERDE});
}}
QLabel#Estado {{ color: {TEXTO_SUAVE}; font-size: 9pt; }}
QPlainTextEdit#Log {{
    background: #12233D; color: #D6E4F5; border-radius: 8px; padding: 6px;
    font-family: "Consolas", "Courier New", monospace; font-size: 9pt;
    selection-background-color: {AZUL};
}}

QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C5D0DD; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QMessageBox QLabel#qt_msgbox_label, QMessageBox QLabel#qt_msgbox_informativelabel {{
    min-width: 380px;
}}
QStatusBar {{ background: white; border-top: 1px solid {BORDE}; color: {TEXTO_SUAVE}; }}
"""
