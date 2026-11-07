# -*- coding: utf-8 -*-
"""
Easy Heirs - SAFE21
qt.py : interfaccia grafica.

Caricamento dei moduli fratelli
-------------------------------
Electrum importa un plugin esterno sotto un nome sintetico
(``electrum_external_plugins.<nome>``) ed esegue solo il ``__init__`` del
pacchetto e questo modulo, senza registrare i pacchetti intermedi in
``sys.modules``. Un ``from . import core`` fallisce quindi con
``ModuleNotFoundError``. Risolviamo caricando i moduli per percorso, con
ripiego sulla lettura diretta dallo zip.
"""

import base64
import html
import importlib.util
import os
import threading
import sys
import time

from PyQt6.QtCore import QMarginsF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor, QIcon, QPageLayout, QPageSize, QPainter, QPdfWriter, QPixmap,
)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton,
    QComboBox, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from electrum.i18n import _
from electrum.logging import get_logger
from electrum.plugin import BasePlugin, hook

# Il pulsante ufficiale della barra di stato di Electrum (in basso a destra):
# lo usiamo così l'icona ha la STESSA dimensione e resa degli altri loghi
# già presenti lì. Import difensivo: se un domani Electrum lo spostasse,
# ripieghiamo su un QPushButton semplice invece di rompere il plugin.
try:
    from electrum.gui.qt.main_window import StatusBarButton
except Exception:
    StatusBarButton = None

_logger = get_logger(__name__)


def _load_sibling(mod_name):
    pkg = __name__.rsplit(".", 1)[0] if "." in __name__ else None
    if pkg:
        try:
            import importlib
            return importlib.import_module(f"{pkg}.{mod_name}")
        except Exception:
            pass
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, mod_name + ".py")
    full = f"{pkg}.{mod_name}" if pkg else f"safe21_easy_heirs_{mod_name}"

    if os.path.isfile(path):
        spec = importlib.util.spec_from_file_location(full, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[full] = mod
            spec.loader.exec_module(mod)
            return mod

    probe = here
    while probe and not probe.lower().endswith(".zip"):
        parent = os.path.dirname(probe)
        if parent == probe:
            probe = None
            break
        probe = parent
    if probe and os.path.isfile(probe):
        import zipfile
        inner = os.path.relpath(path, probe).replace(os.sep, "/")
        with zipfile.ZipFile(probe) as z:
            source = z.read(inner)
        mod = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(full, loader=None))
        mod.__file__ = path
        sys.modules[full] = mod
        exec(compile(source, path, "exec"), mod.__dict__)
        return mod

    raise ImportError(f"impossibile caricare {mod_name}")


art = _load_sibling("art")
core = _load_sibling("core")
sheets = _load_sibling("sheets")


# ===========================================================================
#  Icona del plugin (tessera SAFE21 con serratura)
# ===========================================================================
# PNG incorporato in base64: così l'icona si carica sempre, senza dipendere
# dai percorsi interni dello ZIP con cui Electrum importa il plugin. La
# sorgente è icons/safe21-keyhole.svg / .png, derivata dal logo ufficiale di
# safe21.io (Cyber Teal, serratura trasparente).
_ICON_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAFu0lEQVR4nO3cQU7cQBCG0SFiOzfl"
    "AByBA3BTH4CskGBECGhsd1X97+0iJZlua+pz2yi5XAAAAAAAAAAAAAAAAAAAAIBqHi6Brq8vb6vX"
    "QE3b03PUTIzfrGHnXtvgKIzcmKHnKNuwGIzZjKHnbNuAGLTegKGniq1pDFou2uBT1dYsBK0Wa/Dp"
    "YmsSgj+XJgw/nVyb/Ki5fKW6XEjoeBoofQIw/ExwLXwTK1mmyhcMJp0Gyp0ADD+TXYvd3EoFoNrF"
    "genf8zIBqHRRIOX7vvx5pMqFgMT3AktPAIYfLkvnYFkADD+sn4cy7wCAkAC4+0ONuTg9AIYf6szH"
    "qQEw/FBrTk4LgOGHevPiJSAEOyUA7v5Qc24OD4Dhh7rz4xEAgh0aAHd/qD1HhwXA8EP9efIIAMEO"
    "CYC7P/SYKycACLZ7ANz94Th7z5cTAAQTAAi2awAc/+F4e86ZEwAEEwAItlsAHP/hPHvNmxMABBMA"
    "CLZLABz/4Xx7zJ0TAAQTAAgmABBMACDY3QHwAhDWuXf+nAAgmABAMAGAYAIAwQQAggkABBMACCYA"
    "EEwAIJgAQDABgGACAMEEAIIJAAR7XL0AzrM9PT/89Pf6Z94ZBGCw3wz8//6sIMwkAMPcM/Q//XvF"
    "YA4BGOKowf/us4SgPwFo7szB/9dnC0FffgrQ2Mrhr7gOfs8JoKGKA+c00JMTQDMVh7/T+vhMABrp"
    "Mlxd1okAtNFtqLqtN5UTQANdh6nrupMIQHHdh6j7+qcTgMKmDM+UfUwkAEVNG5pp+5lCACCYABQ0"
    "9W45dV+dCUAx04dk+v66EQAIJgCFpNwdU/bZgQBAMAEoIu2umLbfqgQAggkABBOAAlKPw6n7rkQA"
    "IJgAQDABgGACsFj6c3D6/lcTAAgmABBMACCYAEAwAYBgAgDBBACCCQAEEwAIJgAQTAAWu76+vF2C"
    "pe9/NQGAYAIAwQQAgglAAanPwan7rkQAIJgAQDABKCLtOJy236oEAIIJQCEpd8WUfXYgABBMAIqZ"
    "fnecvr9uBKCgqUMydV+dCQAEE4Cipt0tp+1nCgEobMrQTNnHRAJQXPfh6b7+6QSgga5D1HXdSQSg"
    "iW7D1G29qQSgkS5D1WWdCEA71Yer+vr47PHm1zTwPmTb0/PDpQiD35NHgMaqDF2VdfB7AgDBBACC"
    "CUBjVd4BVFkHvycAEEwAIJgAQDABgGACAMEEoKlqb96rrYefEQAIJgAQTAAgmABAMAFoqOoLt6rr"
    "4t8EAIIJAAQTAAgmABBMACCYADRT/U179fXxmQBAMAGAYAIAwQQAgglAI11esHVZJwIA0ZwAIJgA"
    "QDABgGACAMEEoIlub9a7rTeVAEAwAYBgAgDBBACCCUADXV+odV13EgGAYAIAwQQAggkABBMACCYA"
    "xXV/k959/dMJAAQTAAj2uHoBfO/6+vLmGnEUJwAIJgAQTAAgmABAMAGAYAIAwQQAggkABBMACCYA"
    "EEwAIJgAQDABgGACAMHuDoD/8QXWuXf+nAAgmABAMAGAYAIAwXYJgBeBcL495s4JAIIJAATbLQAe"
    "A+A8e82bEwAEEwAItmsAPAbA8facMycACCYAEGz3AHgMgOPsPV9OABDskAA4BUCPuXICgGCHBcAp"
    "AOrP06EnABGA2nPkEQCCHR4ApwCoOz+nnABEAGrOjUcACHZaAJwCoN68nHoCEAGoNSenPwKIANSZ"
    "jyXvAEQAasyFl4AQbFkAnAJg/TwsPQGIAFyWzsGyD751fX15W70GSLsBlnkHUOFiQNr3vUwAKl0U"
    "SPmelwpAtYsD07/fpRZzy3sBptiKDX7ZE0CHiwZTvsdlF3bLaYButsKD3+IE0O1iQrfva4tF3nIa"
    "oKqtyeC/a7XYW0JAFVuzwX/XctFfEQPOtjUd+o/ab+ArYsBRtgFD/9GozXxFDLjXNmzoPxq7se+I"
    "AonDDgAAAAAAAAAAAAAAAAAAXDr5CyXMrNeksoVlAAAAAElFTkSuQmCC"
)


def _safe21_icon() -> QIcon:
    """Ritorna la QIcon SAFE21 costruita dai byte incorporati.

    Se per qualunque motivo la decodifica fallisse, ritorna una QIcon vuota
    invece di sollevare: un plugin senza icona resta preferibile a un plugin
    che non parte.
    """
    try:
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(_ICON_B64))
        return QIcon(pm)
    except Exception as e:
        _logger.error(f"icona SAFE21 non caricata: {e}")
        return QIcon()


RENDER_DPI = 600
MAX_BATCH = 20


# ===========================================================================
#  Stile condiviso (palette SAFE21 + helper per le finestre)
# ===========================================================================
# Un'unica fonte di verità per colori, font e forma dei pulsanti: così TUTTE
# le finestre del plugin hanno lo stesso aspetto e la stessa gerarchia visiva
# (una sola azione principale in teal, il resto in grigio quieto).

TEAL = "#0d9488"        # colore dell'azione principale (marchio SAFE21)
TEAL_DARK = "#0f6e56"
TEAL_TINT = "#e6f4f2"   # fascia d'intestazione / accenti leggeri
INK = "#16202a"         # titoli
BODY = "#39454f"        # testo corrente
MUTED = "#7c8892"       # testo secondario
BORDER = "#d9dee4"
SURFACE = "#ffffff"
DANGER = "#b4232a"
# Arancio Bitcoin: usato SOLO per i paper wallet, per distinguerli a colpo
# d'occhio dalle azioni sugli eredi (teal).
BTC_ORANGE = "#f7931a"
BTC_ORANGE_D = "#d97e0d"
DANGER_BG = "#fceeee"
DANGER_BD = "#e6c3c3"

# Stile dell'indicatore delle caselle di spunta. Va DEFINITO esplicitamente:
# con un foglio di stile attivo, Qt smette di disegnare il segno di spunta
# nativo e senza queste regole la casella resta vuota anche quando è spuntata
# (era il bug segnalato). Qui: casella bianca col bordo, TEAL PIENO quando
# spuntata. Riusato anche dalle caselle che hanno un proprio stylesheet.
def _make_check_png():
    """Il segno di spunta bianco delle caselle, come PNG in una cartella
    temporanea; ritorna il percorso con le barre "/" che il foglio di stile
    vuole, o "" se non si riesce.

    Il foglio di stile colorava il quadratino della casella spuntata ma senza
    segno dentro (prova del titolare, 2026-11-07: "ci dovrebbe essere anche
    una X interna"). Qt nel foglio di stile accetta solo un file: lo
    disegniamo noi, una volta, con QPainter su una QImage (nessun file nel
    plugin da leggere dallo ZIP, nessun SVG da far interpretare).
    """
    try:
        import tempfile
        from PyQt6.QtCore import QPointF
        from PyQt6.QtGui import QImage, QPainter, QPen
        path = os.path.join(tempfile.gettempdir(), "safe21_easy_heirs_check_v1.png")
        if not os.path.isfile(path):
            img = QImage(32, 32, QImage.Format.Format_ARGB32)
            img.fill(0)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("white"), 4.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPolyline([QPointF(7, 16.5), QPointF(13.5, 23), QPointF(25, 9.5)])
            p.end()
            if not img.save(path, "PNG"):
                return ""
        return path.replace("\\", "/")
    except Exception as e:
        _logger.info(f"segno di spunta non disponibile: {e}")
        return ""


_CHECK_PNG = _make_check_png()
_CHECK_IMAGE = f"image:url({_CHECK_PNG});" if _CHECK_PNG else ""

_CHECK_INDICATOR = f"""
QCheckBox {{ spacing:8px; }}
QCheckBox::indicator {{ width:16px; height:16px; border:1px solid #b0b8c0;
    border-radius:4px; background:{SURFACE}; }}
QCheckBox::indicator:hover {{ border:1px solid {TEAL}; }}
QCheckBox::indicator:checked {{ background:{TEAL}; border:1px solid {TEAL};
    {_CHECK_IMAGE} }}
QCheckBox::indicator:checked:hover {{ background:{TEAL_DARK};
    border:1px solid {TEAL_DARK}; {_CHECK_IMAGE} }}
QCheckBox::indicator:disabled {{ background:#eef0f2; border:1px solid #dde2e6; }}
QCheckBox::indicator:checked:disabled {{ background:#a9cfc9; border:1px solid #a9cfc9;
    {_CHECK_IMAGE} }}
QCheckBox:disabled {{ color:#9aa5b0; }}
"""

_QSS = f"""
QDialog {{ background:#f6f7f9; }}
QLabel {{ color:{BODY}; font-size:13px; }}
QLineEdit {{ padding:6px 8px; border:1px solid {BORDER};
    border-radius:6px; background:{SURFACE}; font-size:13px; color:{INK}; }}
QLineEdit:focus {{ border:1px solid {TEAL}; }}
QTableWidget {{ border:1px solid {BORDER}; border-radius:6px;
    background:{SURFACE}; gridline-color:#eef1f4; font-size:13px; }}
QHeaderView::section {{ background:#f0f3f5; color:{MUTED}; padding:7px 10px;
    border:none; border-bottom:1px solid #e1e6ea; font-weight:600; }}
QPushButton {{ background:{SURFACE}; border:1px solid #cdd4db; border-radius:7px;
    padding:8px 14px; font-size:13px; color:{BODY}; }}
QPushButton:hover {{ background:#eef2f4; }}
QPushButton[eh="primary"] {{ background:{TEAL}; border:none; color:white;
    font-weight:600; padding:10px 18px; }}
QPushButton[eh="primary"]:hover {{ background:{TEAL_DARK}; }}
QPushButton[eh="danger"] {{ background:{DANGER}; border:none; color:white;
    font-weight:600; }}
QPushButton[eh="danger"]:hover {{ background:#8f1c22; }}
QPushButton:disabled {{ background:#f0f2f4; border:1px solid #e2e6ea;
    color:#9aa5b0; }}
QPushButton[eh="primary"]:disabled, QPushButton[eh="danger"]:disabled,
QPushButton[eh="btc"]:disabled {{ background:#e3e7eb; border:none; color:#9aa5b0; }}
QPushButton[eh="btc"] {{ background:{BTC_ORANGE}; border:none; color:white;
    font-weight:600; padding:10px 18px; }}
QPushButton[eh="btc"]:hover {{ background:{BTC_ORANGE_D}; }}
QPushButton[eh="del"] {{ border:none; background:transparent; color:{MUTED};
    font-size:16px; font-weight:700; padding:2px 8px; }}
QPushButton[eh="del"]:hover {{ color:{DANGER}; }}
QPushButton[ehMuted="true"] {{ background:#f0f2f4; border:1px solid #e2e6ea;
    color:#9aa5b0; }}
QPushButton[ehMuted="true"]:hover {{ background:#f0f2f4; }}
""" + _CHECK_INDICATOR


def _apply_style(dialog):
    """Applica il foglio di stile condiviso a una finestra del plugin."""
    dialog.setStyleSheet(_QSS)


def _primary_button(text):
    """Pulsante dell'azione principale (teal pieno). Uno solo per finestra."""
    b = QPushButton(text)
    b.setProperty("eh", "primary")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _btc_button(text):
    """Pulsante dei paper wallet (arancio Bitcoin pieno).

    Colore diverso di proposito: i paper wallet non c'entrano con la
    lista eredi, e un teal in più li farebbe sembrare la stessa cosa.
    """
    b = QPushButton(text)
    b.setProperty("eh", "btc")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b



def _danger_button(text):
    """Pulsante di un'azione distruttiva (rosso pieno)."""
    b = QPushButton(text)
    b.setProperty("eh", "danger")
    return b


def _band_art(name, height=40):
    """Il disegno decorativo della fascia, come QLabel, o None.

    ``height`` in pixel: 40 nella fascia, di più nelle schede della
    schermata iniziale.

    Sta a destra del titolo, dove altrimenti resterebbe solo sfondo: dice a
    colpo d'occhio che cosa si sta facendo in quella finestra. Se il disegno
    non si carica non succede nulla, la fascia resta come prima.
    """
    try:
        ratio = 1.0
        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        if screen is not None:
            ratio = screen.devicePixelRatio()
        pm = art.band_pixmap(name, height=height, ratio=ratio)
    except Exception as e:
        _logger.info(f"disegno della fascia non disponibile: {e}")
        return None
    if pm is None:
        return None
    label = QLabel()
    label.setPixmap(pm)
    # Puramente decorativo: non deve rubare spazio al titolo se la finestra
    # viene stretta.
    label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    return label


def _header_band(title, subtitle="", art_name=None, back=None):
    """Fascia d'intestazione: icona SAFE21 + titolo (+ sottotitolo).

    Ritorna ``(band, right_layout, subtitle_label)``:
      * ``band`` = il widget da mettere in cima alla finestra;
      * ``right_layout`` = lo spazio a DESTRA dove agganciare l'azione
        principale (già spinto a destra da uno stretch);
      * ``subtitle_label`` = l'etichetta del sottotitolo (o None), per
        aggiornarla a runtime.

    ``art_name`` sceglie il disegno da mettere in fondo a destra fra quelli
    di ``art.py``. Le finestre che in quello spazio hanno un pulsante non lo
    passano.
    """
    band = QWidget()
    # IMPORTANTE: lo stile va SCOPATO al solo widget (#objectName), altrimenti
    # in Qt lo sfondo della fascia si applica anche ai figli (il pulsante
    # "Aggiungi beneficiari" perdeva il suo teal e diventava quasi invisibile).
    band.setObjectName("ehHeaderBand")
    band.setStyleSheet(
        f"#ehHeaderBand {{ background:{TEAL_TINT}; "
        "border-bottom:1px solid #cfe6e1; }")
    h = QHBoxLayout(band)
    h.setContentsMargins(18, 14, 18, 14)
    h.setSpacing(12)

    if back is not None:
        # Indietro (scelta C del titolare): un pulsante quadrato con la
        # freccia al posto dell'icona, e sopra il titolo la "strada"
        # Easy Heirs di SAFE21 ›, cosi' si vede dove si torna.
        b = QPushButton("\u2190")
        b.setObjectName("ehBack")
        b.setFixedSize(36, 36)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(_("Torna alla schermata iniziale"))
        b.setStyleSheet(
            f"#ehBack {{ background:white; border:1px solid #9fe1cb; "
            f"border-radius:8px; color:{TEAL_DARK}; font-size:18px; "
            "font-weight:600; padding:0; }"
            f"#ehBack:hover {{ background:{TEAL_TINT}; border:1px solid {TEAL}; }}")
        b.clicked.connect(back.reject)
        h.addWidget(b)
    else:
        icon = QLabel()
        icon.setPixmap(_safe21_icon().pixmap(38, 38))
        h.addWidget(icon)

    col = QVBoxLayout()
    col.setSpacing(1)
    if back is not None:
        crumb = QLabel(_("Easy Heirs di SAFE21") + "  \u203a")
        crumb.setStyleSheet(f"color:{TEAL_DARK}; font-size:11.5px;")
        col.addWidget(crumb)
    t = QLabel(title)
    t.setStyleSheet(f"color:{INK}; font-size:17px; font-weight:600;")
    col.addWidget(t)
    sub = None
    if subtitle:
        sub = QLabel(subtitle)
        sub.setStyleSheet("color:#6a8480; font-size:12px;")
        col.addWidget(sub)
    h.addLayout(col)
    h.addStretch(1)
    if art_name:
        picture = _band_art(art_name)
        if picture is not None:
            h.addWidget(picture)
    return band, h, sub


def _ask(parent, title, text):
    """Domanda si'/no, con i pulsanti in italiano. True se l'utente conferma.

    QMessageBox.question userebbe i pulsanti standard di Qt, che senza le
    traduzioni di Qt caricate escono in inglese ("Yes"/"No") in mezzo a una
    finestra italiana. Li rinominiamo a mano. Il No resta quello preselezionato:
    queste domande arrivano tutte prima di buttare via qualcosa.
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    yes = box.addButton(_("Sì"), QMessageBox.ButtonRole.YesRole)
    no = box.addButton(_("No"), QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(no)
    box.setEscapeButton(no)
    box.exec()
    return box.clickedButton() is yes


def _info_line(text):
    """Riga informativa leggera (ⓘ grigia), al posto dei banner colorati."""
    w = QLabel("ⓘ  " + text)
    w.setWordWrap(True)
    w.setStyleSheet(
        f"color:{MUTED}; font-size:12px; background:#fbfcfd; padding:8px 18px; "
        "border-bottom:1px solid #eef1f4;")
    return w


# ===========================================================================
#  Stampa e PDF
# ===========================================================================

def _setup(device):
    try:
        device.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    except Exception:
        pass
    try:
        device.setResolution(RENDER_DPI)
    except Exception:
        pass
    try:
        device.setPageMargins(QMarginsF(0, 0, 0, 0),
                              QPageLayout.Unit.Millimeter)
    except Exception:
        pass


def _res(device):
    try:
        r = int(device.resolution())
        return r if r > 0 else RENDER_DPI
    except Exception:
        return RENDER_DPI


def _draw(device, jobs):
    """jobs: lista di funzioni (sheet) -> None, una per pagina."""
    painter = QPainter(device)
    try:
        s = sheets.Sheet(painter, _res(device))
        for i, job in enumerate(jobs):
            if i:
                device.newPage()
            job(s)
    finally:
        painter.end()


# ---------------------------------------------------------------------------
#  Fronte e retro, o solo fronte (titolare, 2026-11-07)
# ---------------------------------------------------------------------------
# Modi di stampa scelti in SidesDialog.
SIDES_DUPLEX = "duplex"        # fronte e retro sullo stesso foglio
SIDES_FRONT = "front"          # solo la facciata principale
SIDES_FRONT_INSTR = "front+instr"  # solo fronte + istruzioni su un foglio a parte


def _side_icon(two_sided):
    """Il disegno della scelta: due fogli sovrapposti (fronte e retro) o un
    foglio solo. Disegnato qui, cosi' segue i colori del plugin."""
    from PyQt6.QtGui import QPainter, QPen, QPixmap
    pm = QPixmap(96, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(TEAL), 2)
    p.setPen(pen)
    if two_sided:
        p.drawRoundedRect(22, 6, 34, 46, 3, 3)
        p.setBrush(QColor(TEAL_TINT))
        p.drawRoundedRect(40, 12, 34, 46, 3, 3)
        x = 46
        y0 = 26
    else:
        p.setBrush(QColor(TEAL_TINT))
        p.drawRoundedRect(31, 8, 34, 48, 3, 3)
        x = 37
        y0 = 22
    p.setPen(QPen(QColor(TEAL_DARK), 2))
    p.drawLine(x, y0, x + 22, y0)
    p.drawLine(x, y0 + 6, x + 22, y0 + 6)
    p.drawLine(x, y0 + 12, x + 14, y0 + 12)
    p.end()
    return pm


class SidesDialog(QDialog):
    """Prima di stampare: "Fronte e retro" (gia' scelto) o "Solo fronte".

    Chi ha una stampante su un solo lato, con il fronte/retro, si ritrovava
    i retri sui fogli sbagliati o non stampati. Con "Solo fronte" si avvisa
    che cosa si perde (le istruzioni e la banda di protezione) e si puo'
    stampare il retro su un foglio a parte, senza parole di recupero.

    ``n_docs`` documenti selezionati, ``n_words`` quelli con parole di
    recupero (l'avviso compare solo se ce n'e' almeno uno). Dopo
    ``exec()``, ``self.mode`` e' uno dei valori SIDES_*.
    """

    def __init__(self, parent, n_docs, n_words):
        QDialog.__init__(self, parent)
        self.n_docs, self.n_words = n_docs, n_words
        self.mode = SIDES_DUPLEX
        self.setWindowTitle(_("Come stampa la tua stampante?"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumWidth(680)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sub = (_("1 documento selezionato") if n_docs == 1
               else _("{} documenti selezionati").format(n_docs))
        if n_words:
            sub += " \u00b7 " + (_("1 con parole di recupero") if n_words == 1
                                  else _("{} con parole di recupero").format(n_words))
        band, _r, _s = _header_band(_("Come stampa la tua stampante?"), sub)
        outer.addWidget(band)

        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(18, 16, 18, 12)
        v.setSpacing(12)
        outer.addWidget(body, 1)

        row = QHBoxLayout()
        row.setSpacing(14)
        self.c_duplex = self._choice(
            True, _("Fronte e retro"),
            _("La stampante stampa sui due lati. Un foglio per ogni documento, "
              "con la banda di protezione sul retro."))
        self.c_front = self._choice(
            False, _("Solo fronte"),
            _("Per le stampanti che stampano su un lato solo. Si stampa la "
              "facciata principale di ogni foglio."))
        row.addWidget(self.c_duplex, 1)
        row.addWidget(self.c_front, 1)
        v.addLayout(row)

        self.warn = QFrame()
        self.warn.setObjectName("ehWarn")
        self.warn.setStyleSheet(
            "#ehWarn { background:#faeeda; border:1px solid #ef9f27; "
            "border-radius:8px; }")
        wl = QVBoxLayout(self.warn)
        wl.setContentsMargins(14, 12, 14, 12)
        wl.setSpacing(6)
        wt = QLabel("\u26a0  " + _("Con la stampa solo fronte il retro non viene stampato"))
        wt.setStyleSheet("color:#633806; font-weight:600; background:transparent;")
        wl.addWidget(wt)
        wd = QLabel(_(
            "Sul retro dei fogli con le parole di recupero ci sono le "
            "istruzioni complete per recuperare i fondi e la banda che "
            "impedisce di leggere le parole in controluce. Senza retro queste "
            "parti vanno perse."))
        wd.setWordWrap(True)
        wd.setStyleSheet("color:#854f0b; font-size:12.5px; background:transparent;")
        wl.addWidget(wd)
        self.c_instr = QCheckBox(_(
            "Stampa le istruzioni del retro su un foglio a parte, da tenere "
            "insieme al foglio con le parole (consigliato)"))
        self.c_instr.setChecked(True)
        self.c_instr.setStyleSheet("QCheckBox { color:#633806; }" + _CHECK_INDICATOR)
        self.c_instr.stateChanged.connect(self._refresh)
        wl.addWidget(self.c_instr)
        wn = QLabel(_(
            "Il foglio a parte non contiene le parole di recupero. Tieni il "
            "foglio con le parole piegato e in una busta non trasparente."))
        wn.setWordWrap(True)
        wn.setStyleSheet("color:#854f0b; font-size:12px; background:transparent;")
        wl.addWidget(wn)
        v.addWidget(self.warn)

        foot = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(self.reject)
        foot.addWidget(b)
        foot.addStretch(1)
        self.pages = QLabel("")
        self.pages.setStyleSheet(f"color:{MUTED}; font-size:12.5px;")
        foot.addWidget(self.pages)
        foot.addStretch(1)
        ok = _primary_button(_("Continua alla stampa"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        foot.addWidget(ok)
        v.addLayout(foot)

        _apply_style(self)
        self._pick(SIDES_DUPLEX)

    def _choice(self, two_sided, title, text):
        """Una delle due schede, cliccabile in tutta la sua superficie."""
        box = QPushButton()
        box.setCheckable(True)
        box.setCursor(Qt.CursorShape.PointingHandCursor)
        box.setObjectName("ehSide")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        pic = QLabel()
        pic.setPixmap(_side_icon(two_sided))
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(pic)
        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"color:{INK}; font-size:14px; font-weight:600; background:transparent;")
        lay.addWidget(t)
        d = QLabel(text)
        d.setWordWrap(True)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setStyleSheet(f"color:{MUTED}; font-size:12.5px; background:transparent;")
        lay.addWidget(d)
        for w in (pic, t, d):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        box.setMinimumHeight(190)
        box.clicked.connect(lambda _c=False, two=two_sided:
                            self._pick(SIDES_DUPLEX if two else SIDES_FRONT))
        return box

    def _pick(self, mode):
        """Seleziona una scheda (bordo verde spesso) e aggiorna l'avviso."""
        duplex = mode == SIDES_DUPLEX
        for box, on in ((self.c_duplex, duplex), (self.c_front, not duplex)):
            box.setChecked(on)
            box.setStyleSheet(
                "#ehSide { background:white; border-radius:12px; text-align:center; "
                + (f"border:2px solid {TEAL}; }}" if on else "border:1px solid #d3d9df; }"))
        self._duplex = duplex
        self._refresh()

    def _refresh(self):
        """Avviso e numero di pagine secondo la scelta."""
        single = not self._duplex
        self.warn.setVisible(single and self.n_words > 0)
        if self._duplex:
            self.mode = SIDES_DUPLEX
            text = _("Fogli: {}").format(self.n_docs)
        elif self.n_words and self.c_instr.isChecked():
            self.mode = SIDES_FRONT_INSTR
            text = _("Pagine: {} fronti + {} fogli di istruzioni").format(
                self.n_docs, self.n_words)
        else:
            self.mode = SIDES_FRONT
            text = _("Pagine: {}").format(self.n_docs)
        self.pages.setText(text)
        self.adjustSize()


def _set_duplex(printer, mode):
    """Fronte/retro sul lato lungo solo se scelto; altrimenti su un lato."""
    try:
        printer.setDuplex(QPrinter.DuplexMode.DuplexLongSide if mode == SIDES_DUPLEX
                          else QPrinter.DuplexMode.DuplexNone)
    except Exception as e:
        _logger.info(f"impossibile impostare il fronte/retro: {e}")


# Stampanti "finte" che invece di stampare scrivono un file.
_FILE_PRINTERS = ("pdf", "xps", "onenote")


def _is_file_printer(printer):
    """True se la stampante scelta scrive un file (es. Microsoft Print to PDF)."""
    try:
        name = (printer.printerName() or "").lower()
    except Exception:
        return False
    return any(k in name for k in _FILE_PRINTERS)


def _suggest_pdf_name(parent, printer, label):
    """Con una stampante che scrive un file, propone un nome gia' compilato
    (titolare, 2026-11-07: la finestra di Windows lo lascia vuoto). Solo per
    documenti SENZA parole di recupero: per quelli il plugin non aiuta a
    salvarli su disco e resta la finestra di Windows di sempre. Ritorna False
    se l'utente annulla."""
    name = "Easy Heirs - {} - {}.pdf".format(label, time.strftime("%d-%m-%Y"))
    name = "".join(c for c in name if c not in '\\/:*?"<>|')
    folder = os.path.join(os.path.expanduser("~"), "Documents")
    if not os.path.isdir(folder):
        folder = os.path.expanduser("~")
    path, _sel = QFileDialog.getSaveFileName(
        parent, _("Salva il PDF"), os.path.join(folder, name), "PDF (*.pdf)")
    if not path:
        return False
    if not path.lower().endswith(".pdf"):
        path += ".pdf"
    # Con un nome .pdf Qt scrive il PDF da se': la finestra di Windows non
    # compare piu'.
    printer.setOutputFileName(path)
    return True


def _jobs_for(row, seed=None, mode=SIDES_DUPLEX):
    """Le pagine di un beneficiario. Sempre due, per tenere allineata la
    stampa fronte/retro: seed -> fronte + retro con le istruzioni; solo
    indirizzo -> scheda + retro vuoto."""
    data = {
        "name": row["name"], "address": row["address"],
        "xpub": row.get("xpub", ""), "seed": seed or "",
        "guardian": row.get("guardian", ""), "envelope": row.get("envelope", ""),
        "account_derivation": core.DERIVATION_ACCOUNT,
    }
    data["instructions"] = {SIDES_FRONT: "none",
                            SIDES_FRONT_INSTR: "separate"}.get(mode, "back")
    if seed:
        front = lambda s: sheets.render_seed_front(s, data)  # noqa: E731
        if mode == SIDES_FRONT:
            return [front]
        if mode == SIDES_FRONT_INSTR:
            return [front, lambda s: sheets.render_seed_back(s, has_seed=True,
                                                             separate=True)]
        return [front, lambda s: sheets.render_seed_back(s, has_seed=True)]
    if mode != SIDES_DUPLEX:
        # Su un lato solo la scheda non ha retro: niente pagina vuota.
        return [lambda s: sheets.render_given(s, data)]
    # Anche l'erede con solo indirizzo occupa DUE pagine (scheda + retro
    # vuoto): così ogni documento ha un numero pari di pagine e la stampa
    # fronte/retro resta allineata, invece di sfasarsi dopo una pagina dispari.
    return [lambda s: sheets.render_given(s, data),
            lambda s: sheets.render_blank_back(s)]


# ===========================================================================
#  Creazione multipla
# ===========================================================================

class CreateDialog(QDialog):
    """Aggiunge uno o più beneficiari alla lista di Easy Heirs.

    Una riga per beneficiario: con un indirizzo incollato si usa quello,
    con il campo vuoto si generano indirizzo, seed e chiave pubblica. Le
    quote non ci sono (2.0): si decidono nel plugin di eredità, dove
    l'erede si aggiunge leggendo il QR del foglio stampato.
    """

    # Colonne della tabella di inserimento
    C_NAME, C_ADDR, C_STATUS, C_DEL = range(4)

    def __init__(self, parent, wallet):
        QDialog.__init__(self, parent)
        self.wallet = wallet
        self.created = []
        self.setWindowTitle(_("Aggiungi beneficiari") + " \u2014 Easy Heirs")
        self.setMinimumSize(780, 520)

        rows = core.beneficiaries(wallet)
        self.existing = {r["name"].lower() for r in rows}
        self.existing_addr = {r["address"] for r in rows if r.get("address")}
        self.has_pwd = core.wallet_has_password(wallet)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        band, _right, _sub = _header_band(_("Aggiungi beneficiari"))
        outer.addWidget(band)
        outer.addWidget(_info_line(_(
            "Una riga per beneficiario. Incolla un indirizzo per usarlo; "
            "lascia vuoto il campo e genero io indirizzo, seed e chiave "
            "pubblica.")))

        if not self.has_pwd:
            warn = QLabel("\u26a0  " + _(
                "Questo wallet non ha una password: i seed verrebbero salvati "
                "in chiaro. Imposta una password da Wallet > Password. Puoi "
                "comunque aggiungere chi ti ha fornito il proprio indirizzo."))
            warn.setWordWrap(True)
            warn.setStyleSheet(
                f"color:{DANGER}; background:{DANGER_BG}; padding:8px 18px; "
                f"border-bottom:1px solid {DANGER_BD}; font-size:12px;")
            outer.addWidget(warn)

        body = QWidget()
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(18, 14, 18, 12)
        vbox.setSpacing(10)
        outer.addWidget(body, 1)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            _("Nome o denominazione"), _("Indirizzo bitcoin"),
            _("Cosa succede"), ""])
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(self.C_NAME, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.C_ADDR, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.C_STATUS, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(self.C_DEL, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(self.C_STATUS, 180)
        self.table.setColumnWidth(self.C_DEL, 40)
        vbox.addWidget(self.table, 1)

        addrow = QHBoxLayout()
        self.b_addrow = QPushButton("+  " + _("Aggiungi un'altra riga"))
        self.b_addrow.clicked.connect(lambda: (self._add_row(), self._refresh()))
        addrow.addWidget(self.b_addrow)
        addrow.addStretch(1)
        vbox.addLayout(addrow)

        self.err = QLabel("")
        self.err.setWordWrap(True)
        self.err.setStyleSheet(f"color:{DANGER}; font-size:12px;")
        vbox.addWidget(self.err)

        note = QLabel("\u24d8  " + _(
            "I seed generati restano dentro questo wallet, protetti dalla sua "
            "password, così puoi ristampare un foglio smarrito. Ogni backup "
            "del file wallet li conterrà. Le quote non si mettono qui: le "
            "decidi nel plugin di eredità, quando aggiungi l'erede."))
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        vbox.addWidget(note)

        row = QHBoxLayout()
        b_cancel = QPushButton(_("Annulla"))
        b_cancel.clicked.connect(self.reject)
        row.addWidget(b_cancel)
        row.addStretch(1)
        self.b_ok = _primary_button(_("Crea beneficiari"))
        self.b_ok.setDefault(True)
        self.b_ok.clicked.connect(self._create)
        row.addWidget(self.b_ok)
        vbox.addLayout(row)

        _apply_style(self)
        self._add_row()          # si parte con una riga
        self._refresh()
        # Dopo lo stile: è il foglio di stile a dare ai campi il padding che
        # decide quanto devono essere alte le righe.
        self._fit_rows()

    # ----------------------------------------------------------------- ui --

    def _add_row(self, name="", addr=""):
        """Aggiunge una riga in fondo alla tabella. Ogni riga porta la sua \u2715
        per essere tolta con un solo click."""
        if self.table.rowCount() >= MAX_BATCH:
            return
        i = self.table.rowCount()
        self.table.insertRow(i)

        e_name = QLineEdit(name)
        e_addr = QLineEdit(addr)
        e_addr.setPlaceholderText(_("lascia vuoto per generarlo io"))
        e_name.textChanged.connect(self._refresh)
        e_addr.textChanged.connect(self._refresh)

        self.table.setCellWidget(i, self.C_NAME, e_name)
        self.table.setCellWidget(i, self.C_ADDR, e_addr)
        self.table.setItem(i, self.C_STATUS, QTableWidgetItem(""))

        xb = QPushButton("\u2715")
        xb.setProperty("eh", "del")
        xb.setToolTip(_("Togli questo beneficiario"))
        xb.setCursor(Qt.CursorShape.PointingHandCursor)
        xb.clicked.connect(lambda _c=False, marker=e_name: self._del_row(marker))
        self.table.setCellWidget(i, self.C_DEL, xb)
        self._fit_rows()

    def _fit_rows(self):
        """Alza le righe quanto serve ai campi di testo che contengono.

        L'altezza predefinita di riga di Qt non tiene conto del padding che il
        foglio di stile dà ai QLineEdit: il campo veniva ritagliato in basso e
        le lettere con la coda (p, g, q, y) sparivano a metà. La misura la
        chiediamo al campo stesso invece di fissarla a mano, così regge anche
        con un altro font o un'altra densità di schermo.
        """
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, self.C_NAME)
            if w is None:
                continue
            need = max(w.sizeHint().height(), w.minimumSizeHint().height())
            self.table.setRowHeight(r, need + 6)

    def _row_of(self, marker):
        """Indice ATTUALE della riga il cui campo Nome è ``marker`` (le righe
        si spostano quando se ne cancella una, quindi va ricercata al click)."""
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, self.C_NAME) is marker:
                return r
        return -1

    def _del_row(self, marker):
        """Toglie la riga con un click."""
        r = self._row_of(marker)
        if r < 0:
            return
        self.table.removeRow(r)
        self._refresh()

    def _name(self, i):
        w = self.table.cellWidget(i, self.C_NAME)
        return w.text().strip() if w else ""

    def _addr(self, i):
        w = self.table.cellWidget(i, self.C_ADDR)
        return w.text().strip() if w else ""

    def _refresh(self):
        """Controlla ogni riga e dice, nella colonna "Cosa succede", che cosa
        verrà fatto o che cosa va corretto."""
        problems = []
        seen_names, seen_addr = set(), set()
        n_rows = self.table.rowCount()
        for i in range(n_rows):
            name, addr = self._name(i), self._addr(i)
            label, bad = "", False
            if not name:
                label, bad = _("il nome è obbligatorio"), True
            elif name.lower() in self.existing or name.lower() in seen_names:
                label, bad = _("nome già presente"), True
            elif addr:
                if not self._valid(addr):
                    label, bad = _("indirizzo non valido"), True
                elif addr in seen_addr or addr in self.existing_addr:
                    label, bad = _("indirizzo ripetuto"), True
                else:
                    label = _("indirizzo fornito")
            else:
                if not self.has_pwd:
                    label, bad = _("serve la password del wallet"), True
                else:
                    label = _("genero io indirizzo e seed")
            if name:
                seen_names.add(name.lower())
            if addr:
                seen_addr.add(addr)
            if bad:
                problems.append(f"{i + 1}: {label}")
            it = QTableWidgetItem(label)
            it.setForeground(QColor(DANGER if bad else "#5a6672"))
            self.table.setItem(i, self.C_STATUS, it)

        self.b_addrow.setEnabled(n_rows < MAX_BATCH)
        if n_rows == 0:
            self.err.setText(_("Aggiungi almeno un beneficiario."))
            self.b_ok.setEnabled(False)
            self.b_ok.setText(_("Crea beneficiari"))
            return
        self.err.setText("" if not problems
                         else _("Da correggere \u2014 ") + " \u00b7 ".join(problems))
        self.b_ok.setEnabled(not problems)
        self.b_ok.setText(_("Crea {} beneficiari").format(n_rows))

    @staticmethod
    def _valid(addr):
        try:
            from electrum import bitcoin, constants
            return bool(bitcoin.is_address(addr, net=constants.net))
        except Exception:
            return False

    # ------------------------------------------------------------- azione --

    def _create(self):
        """Crea i beneficiari delle righe; ``self.created`` = [(nome, generato)]."""
        rows = [(self._name(i), self._addr(i))
                for i in range(self.table.rowCount())]
        done, errors = [], []
        for name, addr in rows:
            try:
                if addr:
                    core.add_provided(self.wallet, name, addr)
                    done.append((name, False))
                else:
                    mnemonic, address, xpub = core.generate_beneficiary()
                    core.add_generated(self.wallet, name, address, xpub, mnemonic)
                    del mnemonic
                    done.append((name, True))
            except Exception as e:
                _logger.error(f"creazione di {name!r} fallita: {e}")
                errors.append(f"{name}: {e}")
        self.created = done
        if errors:
            QMessageBox.warning(self, _("Alcuni non sono stati creati"),
                                "\n".join(errors))
        self.accept()


# ===========================================================================
#  Stampa
# ===========================================================================

class PrintDialog(QDialog):

    def __init__(self, parent, wallet, rows):
        QDialog.__init__(self, parent)
        self.wallet = wallet
        self.rows = rows
        self.setWindowTitle(_("Stampa documenti") + " \u2014 Easy Heirs")
        self.setMinimumSize(820, 500)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        band, _r, _s = _header_band(_("Stampa documenti"),
                                    art_name="print")
        outer.addWidget(band)
        outer.addWidget(_info_line(_(
            "Scegli cosa stampare. Puoi ristampare in qualsiasi momento: i "
            "dati restano nel wallet.")))
        body = QWidget()
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(18, 14, 18, 12)
        vbox.setSpacing(10)
        outer.addWidget(body, 1)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "", _("Beneficiario"), _("Tipo"), _("Fogli"),
            _("Ultima stampa"), _("Destinazione")])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setRowCount(len(rows) + 1)
        self.boxes = []

        for i, r in enumerate(rows):
            cb = QCheckBox()
            cb.setChecked(not r.get("printed_at"))
            cb.stateChanged.connect(self._refresh)
            self.boxes.append(cb)
            holder = QWidget()
            lay = QHBoxLayout(holder)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(cb, alignment=Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 0, holder)

            self.table.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.table.setItem(i, 2, QTableWidgetItem(
                _("Generato") if r["generated"] else _("Indirizzo fornito")))
            self.table.setItem(i, 3, QTableWidgetItem(
                _("1 A4 fronte/retro") if r["generated"] else _("1 pagina")))
            when = r.get("printed_at")
            it = QTableWidgetItem(
                time.strftime("%d/%m/%Y", time.localtime(when)) if when
                else _("mai"))
            if not when:
                it.setForeground(QColor(DANGER))
            self.table.setItem(i, 4, it)
            self.table.setItem(i, 5, QTableWidgetItem(
                _("solo stampante \u2014 contiene le parole") if r["generated"]
                else _("stampante o PDF")))

        # riga del riepilogo
        i = len(rows)
        self.cb_report = QCheckBox()
        self.cb_report.setChecked(True)
        self.cb_report.stateChanged.connect(self._refresh)
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.cb_report, alignment=Qt.AlignmentFlag.AlignCenter)
        self.table.setCellWidget(i, 0, holder)
        self.table.setItem(i, 1, QTableWidgetItem(
            _("Riepilogo per l'esecutore")))
        self.table.setItem(i, 2, QTableWidgetItem(_("Riepilogo")))
        self.table.setItem(i, 3, QTableWidgetItem(_("1 pagina")))
        self.table.setItem(i, 4, QTableWidgetItem(""))
        self.table.setItem(i, 5, QTableWidgetItem(_("stampante o PDF")))

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 34)
        vbox.addWidget(self.table)

        quick = QHBoxLayout()
        for label, fn in ((_("Tutti"), lambda: self._set(lambda r: True)),
                          (_("Nessuno"), lambda: self._set(lambda r: False)),
                          (_("Solo mai stampati"),
                           lambda: self._set(lambda r: not r.get("printed_at"))),
                          (_("Solo i generati da me"),
                           lambda: self._set(lambda r: r["generated"]))):
            b = QPushButton(label)
            b.setFlat(True)
            b.clicked.connect(fn)
            quick.addWidget(b)
        quick.addStretch(1)
        vbox.addLayout(quick)

        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        self.warn.setStyleSheet(
            f"color:{DANGER}; background:{DANGER_BG}; "
            f"border:1px solid {DANGER_BD}; border-radius:6px; padding:9px; "
            "font-size:12px;")
        vbox.addWidget(self.warn)

        row = QHBoxLayout()
        b_cancel = QPushButton(_("Annulla"))
        b_cancel.clicked.connect(self.reject)
        row.addWidget(b_cancel)
        row.addStretch(1)
        self.b_pdf = QPushButton(_("Salva PDF dei selezionati") + "\u2026")
        self.b_pdf.clicked.connect(self._save_pdf)
        row.addWidget(self.b_pdf)
        self.b_print = _primary_button(_("Stampa selezionati"))
        self.b_print.setDefault(True)
        self.b_print.clicked.connect(self._print)
        row.addWidget(self.b_print)
        vbox.addLayout(row)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED}; font-size:11.5px;")
        vbox.addWidget(self.status)

        _apply_style(self)
        self._refresh()

    # ----------------------------------------------------------------- ui --

    def _set(self, pred):
        for cb, r in zip(self.boxes, self.rows):
            cb.setChecked(bool(pred(r)))

    def _selected(self):
        return [r for cb, r in zip(self.boxes, self.rows) if cb.isChecked()]

    def _refresh(self):
        sel = self._selected()
        with_seed = [r for r in sel if r["generated"]]
        pages = sum(2 if r["generated"] else 1 for r in sel)
        pages += 1 if self.cb_report.isChecked() else 0

        # Il tasto PDF resta sempre ATTIVO (in Qt un pulsante disabilitato non
        # riceve né clic né passaggio del mouse, quindi non potrebbe mostrare
        # alcun tooltip). Quando non è utilizzabile lo mostriamo "grigio" via
        # stile e spieghiamo il perché nel tooltip (e al clic).
        has_something = bool(sel) or self.cb_report.isChecked()
        if with_seed:
            self._pdf_ok = False
            self._pdf_reason = _(
                "Non posso salvare in PDF i fogli con le parole di recupero: "
                "sul disco resterebbero in chiaro e potrebbero finire per "
                "sbaglio su un cloud. Questi fogli vanno solo stampati.\n\n"
                "Puoi però salvare in PDF il “Riepilogo per l'esecutore” "
                "(non contiene parole): deseleziona i beneficiari generati da te "
                "e lascia spuntato il riepilogo.")
        elif not has_something:
            self._pdf_ok = False
            self._pdf_reason = _(
                "Seleziona almeno un documento senza parole di recupero "
                "(o il “Riepilogo per l'esecutore”) per salvarlo in PDF.")
        else:
            self._pdf_ok = True
            self._pdf_reason = _(
                "Salva sul disco i PDF dei documenti selezionati.")
        self.b_pdf.setProperty("ehMuted", not self._pdf_ok)
        self.b_pdf.setToolTip(self._pdf_reason)
        self.b_pdf.style().unpolish(self.b_pdf)
        self.b_pdf.style().polish(self.b_pdf)

        self.b_print.setEnabled(bool(sel) or self.cb_report.isChecked())

        if with_seed:
            self.warn.show()
            self.warn.setText(_(
                "I fogli con le parole di recupero vanno solo in stampa: un "
                "PDF su disco sarebbe in chiaro, copiabile e sincronizzabile "
                "per errore su un cloud. Usa una stampante collegata "
                "direttamente, mai di rete o cloud."))
        else:
            self.warn.hide()

        self.status.setText(_(
            "{} documenti selezionati \u00b7 {} pagine \u00b7 {} contengono "
            "parole di recupero").format(
                len(sel) + (1 if self.cb_report.isChecked() else 0),
                pages, len(with_seed)))

    # ------------------------------------------------------------ stampa --

    def _print(self):
        sel = self._selected()
        with_seed = [r for r in sel if r["generated"]]
        n_docs = len(sel) + (1 if self.cb_report.isChecked() else 0)
        sides = SidesDialog(self, n_docs, len(with_seed))
        if sides.exec() != QDialog.DialogCode.Accepted:
            return
        mode = sides.mode
        if with_seed and not ReminderDialog(self, len(with_seed),
                                            duplex=mode == SIDES_DUPLEX).exec():
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        _setup(printer)
        printer.setDocName("Easy Heirs")
        # Fronte/retro con giro sul LATO LUNGO solo se scelto: e' il modo in
        # cui la banda nera del retro finisce dietro le parole del fronte.
        _set_duplex(printer, mode)
        if QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return
        if _is_file_printer(printer) and not with_seed:
            label = (sel[0]["name"] if len(sel) == 1 else
                     _("{} beneficiari").format(len(sel)) if sel else _("riepilogo"))
            if not _suggest_pdf_name(self, printer, label):
                return

        jobs = []
        for r in sel:
            seed = core.seed_for(self.wallet, r["address"]) \
                if r["generated"] else None
            jobs += _jobs_for(r, seed, mode)
        if self.cb_report.isChecked():
            jobs.append(lambda s: sheets.render_report(
                s, self._wallet_name(), self.rows))

        try:
            _draw(printer, jobs)
        except Exception as e:
            _logger.error(f"stampa fallita: {e}")
            QMessageBox.critical(self, _("Errore di stampa"), str(e))
            return

        if ConfirmPrintDialog(self, len(sel)).exec():
            core.mark_printed(self.wallet, [r["address"] for r in sel])
            self._offer_removal()
        self.accept()

    def _offer_removal(self):
        """Dopo una stampa riuscita: se tutti i fogli con seed risultano
        stampati, propone di togliere i dati dal portafoglio (owner, 2026-11-06:
        il pulsante deve esserci anche qui, non solo nelle impostazioni)."""
        s = core.removal_summary(self.wallet)
        if not s["seeds"] or s["never_printed"]:
            return
        box = QMessageBox(self)
        box.setWindowTitle(_("Fogli stampati"))
        box.setText(_(
            "Tutti i fogli con le parole di recupero risultano stampati. "
            "Quando li hai verificati e consegnati, puoi togliere i dati di "
            "Easy Heirs da questo portafoglio: i seed resteranno solo sulla "
            "carta."))
        b_rm = box.addButton(_("Rimuovi i dati dal portafoglio") + "…",
                             QMessageBox.ButtonRole.ActionRole)
        box.addButton(_("Non ora"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is b_rm:
            RemoveDialog(self, self.wallet).exec()

    def _save_pdf(self):
        # Il tasto è sempre attivo: se in questo momento non è utilizzabile,
        # spieghiamo il perché invece di non fare nulla in silenzio.
        if not getattr(self, "_pdf_ok", False):
            QMessageBox.information(
                self, _("Salvataggio PDF non disponibile"), self._pdf_reason)
            return
        sel = self._selected()
        if any(r["generated"] for r in sel):
            return
        folder = QFileDialog.getExistingDirectory(
            self, _("Cartella in cui salvare i PDF"))
        if not folder:
            return
        out = os.path.join(folder, time.strftime("beneficiari_%Y%m%d_%H%M"))
        os.makedirs(out, exist_ok=True)
        written, errors = [], []
        for r in sel:
            try:
                path = os.path.join(
                    out, f"scheda_{core.slugify(r['name'])}.pdf")
                w = QPdfWriter(path)
                _setup(w)
                _draw(w, _jobs_for(r, None))
                written.append(path)
            except Exception as e:
                errors.append(f"{r['name']}: {e}")
        if self.cb_report.isChecked():
            try:
                path = os.path.join(out, "riepilogo.pdf")
                w = QPdfWriter(path)
                _setup(w)
                _draw(w, [lambda s: sheets.render_report(
                    s, self._wallet_name(), self.rows)])
                written.append(path)
            except Exception as e:
                errors.append(f"riepilogo: {e}")
        msg = _("{} file salvati in:\n{}").format(len(written), out)
        if errors:
            msg += "\n\n" + _("Problemi:") + "\n" + "\n".join(errors)
        QMessageBox.information(self, _("PDF salvati"), msg)

    def _wallet_name(self):
        try:
            return os.path.basename(self.wallet.storage.path)
        except Exception:
            return "wallet"


class ReminderDialog(QDialog):
    """Promemoria prima di mandare in stampa fogli con le parole."""

    def __init__(self, parent, n, duplex=True):
        """``duplex`` False: stampa solo fronte, niente istruzioni sul giro
        del foglio e sulla banda (che non c'e')."""
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Prima di stampare"))
        self.setMinimumWidth(560)
        vbox = QVBoxLayout(self)

        head = QLabel("⚠  " + _(
            "Stai per stampare {} fogli che contengono parole di recupero. "
            "Chi legge quelle parole può prendere i fondi.").format(n))
        head.setWordWrap(True)
        head.setStyleSheet(
            f"color:{DANGER}; background:{DANGER_BG}; border:1px solid "
            f"{DANGER_BD}; border-radius:6px; padding:9px; font-size:12px;")
        vbox.addWidget(head)

        first = (_("1.  Imposta la stampa fronte/retro con GIRO SUL LATO LUNGO: "
                   "la banda nera deve finire dietro le parole.\n") if duplex else
                 _("1.  Stampa solo fronte: la banda di protezione non c'è. "
                   "Tieni il foglio piegato e in una busta non trasparente.\n"))
        steps = QLabel(first + _(
            "2.  Non allontanarti dalla stampante finché i fogli non sono "
            "usciti.\n"
            "3.  Piega ogni foglio in tre lungo i crocini e imbustalo subito.\n"
            "4.  Numera le buste come indicato nel riepilogo."))
        steps.setWordWrap(True)
        vbox.addWidget(steps)

        check = QLabel(_(
            "Verifica consigliata su un foglio: guardalo piegato in "
            "controluce. Le parole non devono leggersi attraverso la carta. "
            "Se si leggono, la stampa ha girato sul lato corto e la banda "
            "nera è finita dal lato sbagliato."))
        check.setWordWrap(True)
        check.setStyleSheet(
            f"color:{TEAL_DARK}; background:{TEAL_TINT}; border-radius:6px; "
            "padding:9px; font-size:12px;")
        check.setVisible(duplex)
        vbox.addWidget(check)

        row = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(self.reject)
        row.addWidget(b)
        row.addStretch(1)
        ok = _primary_button(_("Ho capito, apri la stampa"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        vbox.addLayout(row)
        _apply_style(self)


class ConfirmPrintDialog(QDialog):
    """La data viene registrata solo se l'utente conferma che è andata bene."""

    def __init__(self, parent, n):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Stampa completata"))
        self.setMinimumWidth(520)
        vbox = QVBoxLayout(self)
        lbl = QLabel(_(
            "Sono stati inviati alla stampante {} documenti.\n\n"
            "Se qualcosa è andato storto (carta inceppata, stampa parziale, "
            "banda nera dal lato sbagliato) distruggi i fogli e ristampa: i "
            "dati restano nel wallet, non si perde nulla.").format(n))
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)
        row = QHBoxLayout()
        b = QPushButton(_("No, ristampo"))
        b.clicked.connect(self.reject)
        row.addWidget(b)
        row.addStretch(1)
        ok = _primary_button(_("Sì, tutto a posto"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        vbox.addLayout(row)
        _apply_style(self)


# ===========================================================================
#  Rimozione dati
# ===========================================================================

class RemoveDialog(QDialog):

    def __init__(self, parent, wallet):
        QDialog.__init__(self, parent)
        self.wallet = wallet
        self.setWindowTitle(_("Rimuovi i dati di Easy Heirs"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumWidth(660)
        s = core.removal_summary(wallet)
        self.summary = s

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        band, _r, _sub = _header_band(_("Rimuovi i dati del plugin"))
        outer.addWidget(band)
        outer.addWidget(_info_line(_(
            "Nel wallet, messi da questo plugin: {} seed generati, {} numeri "
            "di busta, {} date di stampa.").format(
                len(s["seeds"]), s["envelopes"], s["print_dates"])))

        body = QWidget()
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(18, 14, 18, 14)
        vbox.setSpacing(10)
        outer.addWidget(body, 1)

        # Opzione sicura (senza conseguenze)
        self.c_meta = QCheckBox(_(
            "Numeri busta e date di stampa \u2014 informazioni di servizio, "
            "rimuoverle non ha conseguenze"))
        self.c_meta.setChecked(True)
        self.c_meta.stateChanged.connect(self._refresh)
        vbox.addWidget(self.c_meta)

        # Zona pericolosa: recintata in un riquadro rosso a parte
        zone = QFrame()
        zone.setStyleSheet(
            f"QFrame {{ background:{DANGER_BG}; border:1px solid {DANGER_BD}; "
            "border-radius:8px; }")
        zl = QVBoxLayout(zone)
        zl.setContentsMargins(14, 12, 14, 12)
        zl.setSpacing(8)
        zhead = QLabel("\u26a0  " + _("Zona pericolosa \u2014 cancellazione dei seed"))
        zhead.setStyleSheet(
            f"color:{DANGER}; font-weight:600; font-size:13px; "
            "background:transparent; border:none;")
        zl.addWidget(zhead)

        self.c_seeds = QCheckBox(_(
            "Cancella anche i seed generati ({}) \u2014 OPERAZIONE IRREVERSIBILE"
        ).format(len(s["seeds"])))
        self.c_seeds.setStyleSheet(
            f"QCheckBox {{ color:{DANGER}; font-weight:600; }}"
            + _CHECK_INDICATOR)
        self.c_seeds.stateChanged.connect(self._refresh)
        zl.addWidget(self.c_seeds)

        detail = QLabel(_(
            "I seed non sono salvati da nessun'altra parte se non sui fogli "
            "che hai stampato. Cancellandoli, se un foglio va perso o si "
            "rovina, i bitcoin inviati a quegli indirizzi diventano "
            "irrecuperabili per chiunque e per sempre."))
        detail.setWordWrap(True)
        detail.setStyleSheet(
            "color:#7a2a2a; background:transparent; border:none; "
            "font-size:12px;")
        zl.addWidget(detail)

        self.c_confirm = QCheckBox(_(
            "Confermo che i fogli sono stati stampati, verificati e "
            "consegnati"))
        self.c_confirm.setStyleSheet(_CHECK_INDICATOR)
        self.c_confirm.stateChanged.connect(self._refresh)
        zl.addWidget(self.c_confirm)

        self.never = QLabel("")
        self.never.setWordWrap(True)
        self.never.setStyleSheet(
            f"color:white; background:{DANGER}; border-radius:6px; "
            "padding:9px; font-size:12px;")
        zl.addWidget(self.never)
        # Fogli mai stampati: non più un blocco senza uscita (titolare,
        # 2026-11-07), ma una conferma in più che dice il rischio.
        self.c_never = QCheckBox(_(
            "Ho capito: questi fogli non sono mai stati stampati e a quegli "
            "indirizzi non ho mandato bitcoin. Cancellali comunque."))
        self.c_never.setStyleSheet(_CHECK_INDICATOR)
        self.c_never.stateChanged.connect(self._refresh)
        zl.addWidget(self.c_never)
        vbox.addWidget(zone)

        keep = QLabel("\u24d8  " + _(
            "Non vengono toccati in nessun caso le chiavi e i fondi del tuo "
            "wallet, né i dati del plugin di eredità."))
        keep.setWordWrap(True)
        keep.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        vbox.addWidget(keep)

        row = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(self.reject)
        row.addWidget(b)
        row.addStretch(1)
        self.b_ok = QPushButton(_("Rimuovi i dati selezionati"))
        self.b_ok.clicked.connect(self._remove)
        row.addWidget(self.b_ok)
        vbox.addLayout(row)

        _apply_style(self)
        self._refresh()

    def _refresh(self):
        seeds = self.c_seeds.isChecked()
        self.c_confirm.setEnabled(seeds)
        never = self.summary["never_printed"]
        if seeds and never:
            self.never.show()
            self.never.setText("\u26a0  " + _(
                "Questi fogli non risultano mai stampati: {}. Se a quegli "
                "indirizzi sono già stati mandati bitcoin, cancellando i seed "
                "adesso diventano irrecuperabili: in quel caso stampali prima."
            ).format(", ".join(e.get("name", "?") for e in never)))
        else:
            self.never.hide()
        self.c_never.setVisible(bool(seeds and never))
        ok = (self.c_meta.isChecked() or seeds)
        if seeds:
            ok = ok and self.c_confirm.isChecked()
            if never:
                ok = ok and self.c_never.isChecked()
        self.b_ok.setEnabled(ok)
        # Il pulsante diventa rosso solo quando si cancellano i seed (azione
        # distruttiva); altrimenti resta l'azione principale neutra.
        self.b_ok.setProperty("eh", "danger" if seeds else "primary")
        self.b_ok.style().unpolish(self.b_ok)
        self.b_ok.style().polish(self.b_ok)

    def _remove(self):
        try:
            core.remove_data(self.wallet,
                             remove_metadata=self.c_meta.isChecked(),
                             remove_seeds=self.c_seeds.isChecked())
        except Exception as e:
            QMessageBox.critical(self, _("Errore"), str(e))
            return
        QMessageBox.information(self, _("Fatto"), _(
            "I dati selezionati sono stati rimossi da questo wallet."))
        self.accept()


class EditDialog(QDialog):
    """Modifica un beneficiario: il nome sempre, l'indirizzo solo per chi ha
    fornito il proprio (titolare, 2026-11-07)."""

    def __init__(self, parent, wallet, row):
        QDialog.__init__(self, parent)
        self.wallet = wallet
        self.row = row
        self.generated = bool(row.get("generated"))
        self.result = None
        self.setWindowTitle(_("Modifica beneficiario"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumWidth(600)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(8)

        v.addWidget(QLabel(_("Nome o denominazione")))
        self.e_name = QLineEdit(row.get("name") or "")
        v.addWidget(self.e_name)

        v.addWidget(QLabel(_("Indirizzo bitcoin")))
        self.e_addr = QLineEdit(row.get("address") or "")
        if self.generated:
            # Nasce dalle 12 parole: un altro indirizzo non c'entrerebbe più
            # con il seed stampato.
            self.e_addr.setReadOnly(True)
            self.e_addr.setStyleSheet("background:#f0f2f4; color:#5a6672;")
        v.addWidget(self.e_addr)
        if self.generated:
            lock = QLabel("\U0001F512  " + _(
                "Questo indirizzo è generato con le parole di recupero: non "
                "si può cambiare. Se serve un indirizzo diverso, aggiungi un "
                "nuovo beneficiario."))
            lock.setWordWrap(True)
            lock.setStyleSheet(f"color:{MUTED}; font-size:12px;")
            v.addWidget(lock)

        notes = []
        if row.get("printed_at"):
            notes.append(_("Il foglio è già stampato: dopo la modifica risulterà "
                           "da ristampare, perché la carta ha i dati vecchi."))
        notes.append(_("Se l'hai già aggiunto come erede in Àncòra, cambialo "
                       "anche lì, a mano: Easy Heirs non lo tocca."))
        info = QLabel("\u24d8  " + " ".join(notes))
        info.setWordWrap(True)
        info.setStyleSheet(
            f"color:{MUTED}; background:#fbfcfd; border:1px solid #eef1f4; "
            "border-radius:6px; padding:9px; font-size:12px;")
        v.addSpacing(6)
        v.addWidget(info)

        self.err = QLabel("")
        self.err.setWordWrap(True)
        self.err.setStyleSheet(f"color:{DANGER}; font-size:12px;")
        v.addWidget(self.err)

        row_l = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(self.reject)
        row_l.addWidget(b)
        row_l.addStretch(1)
        ok = _primary_button(_("Salva"))
        ok.setDefault(True)
        ok.clicked.connect(self._save)
        row_l.addWidget(ok)
        v.addLayout(row_l)
        _apply_style(self)

    def _save(self):
        """Salva con i controlli del nucleo; un errore resta nella finestra."""
        try:
            self.result = core.update_beneficiary(
                self.wallet, self.row["name"], self.e_name.text(),
                None if self.generated else self.e_addr.text())
        except Exception as e:
            self.err.setText(str(e))
            return
        self.accept()


class ConfirmDeleteDialog(QDialog):
    """Conferma la rimozione di UN beneficiario dalla lista di Easy Heirs.

    Per chi ha 'indirizzo fornito' è una semplice conferma. Per chi è stato
    generato da Easy Heirs la rimozione cancella anche il seed (dalla 2.0 la
    lista di Easy Heirs è l'unico posto dove il seed è salvato, fuori dal
    foglio): serve la conferma esplicita che il foglio è stato stampato, e
    un foglio mai stampato non si può rimuovere.
    """

    def __init__(self, parent, wallet, row):
        QDialog.__init__(self, parent)
        self.wallet = wallet
        self.row = row
        self.generated = bool(row.get("generated"))
        name = row.get("name", "?")

        self.setWindowTitle(_("Rimuovi beneficiario"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(10)

        # RichText esplicito: da solo QLabel non sempre riconosce il <b> e lo
        # mostrava come testo (prova del titolare). Il nome va protetto: un
        # "<" nel nome romperebbe la frase.
        lead = QLabel(_("Vuoi rimuovere <b>{}</b> dalla lista di Easy Heirs?"
                        ).format(html.escape(name)))
        lead.setTextFormat(Qt.TextFormat.RichText)
        lead.setWordWrap(True)
        lead.setStyleSheet(f"color:{INK}; font-size:14px;")
        v.addWidget(lead)

        info = QLabel("\u24d8  " + _(
            "Viene tolto solo da qui. Se l'hai già aggiunto come erede nel "
            "plugin di eredità, toglilo anche lì, a mano: Easy Heirs non lo "
            "tocca."))
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        v.addWidget(info)

        self.c_confirm = None
        if self.generated:
            zone = QFrame()
            zone.setStyleSheet(
                f"QFrame {{ background:{DANGER_BG}; border:1px solid "
                f"{DANGER_BD}; border-radius:8px; }}")
            zl = QVBoxLayout(zone)
            zl.setContentsMargins(14, 12, 14, 12)
            zl.setSpacing(8)
            zh = QLabel("\u26a0  " + _("Viene cancellato anche il seed \u2014 IRREVERSIBILE"))
            zh.setStyleSheet(
                f"color:{DANGER}; font-weight:600; background:transparent; "
                "border:none;")
            zl.addWidget(zh)
            # Mai stampato: il seed esiste solo qui, e la frase sul "foglio
            # che hai stampato" sarebbe falsa.
            detail = QLabel(_(
                "Il seed esiste solo in questo portafoglio: il foglio non è "
                "mai stato stampato. Cancellandolo, l'indirizzo resta senza "
                "chiave per sempre.") if self._never_printed() else _(
                "Il seed non è salvato da nessun'altra parte se non sul foglio "
                "che hai stampato. Se il foglio va perso, i bitcoin inviati a "
                "quell'indirizzo diventano irrecuperabili per sempre."))
            detail.setWordWrap(True)
            detail.setStyleSheet(
                "color:#7a2a2a; background:transparent; border:none; "
                "font-size:12px;")
            zl.addWidget(detail)
            # Un foglio mai stampato: prima la rimozione era bloccata e basta,
            # quindi un beneficiario creato per sbaglio non si toglieva più
            # (titolare, 2026-11-07). Ora si può, con una conferma diversa
            # che dice proprio il rischio.
            self.c_confirm = QCheckBox(
                _("Ho capito: questo foglio non è mai stato stampato e a "
                  "questo indirizzo non ho mandato bitcoin. Cancellalo "
                  "comunque.") if self._never_printed() else
                _("Confermo che il foglio è stato stampato, verificato e "
                  "consegnato"))
            self.c_confirm.setStyleSheet(_CHECK_INDICATOR)
            self.c_confirm.stateChanged.connect(self._refresh)
            zl.addWidget(self.c_confirm)
            self.never = QLabel("\u26a0  " + _(
                "Questo foglio non risulta mai stampato. Se a questo "
                "indirizzo sono già stati mandati bitcoin, cancellando il "
                "seed adesso diventano irrecuperabili: in quel caso stampalo "
                "prima."))
            self.never.setWordWrap(True)
            self.never.setStyleSheet(
                f"color:white; background:{DANGER}; border-radius:6px; "
                "padding:9px; font-size:12px;")
            self.never.setVisible(self._never_printed())
            zl.addWidget(self.never)
            v.addWidget(zone)

        row_l = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(self.reject)
        row_l.addWidget(b)
        row_l.addStretch(1)
        self.b_ok = QPushButton(_("Rimuovi"))
        self.b_ok.clicked.connect(self.accept)
        row_l.addWidget(self.b_ok)
        v.addLayout(row_l)

        _apply_style(self)
        self._refresh()

    def _never_printed(self):
        return bool(self.generated and not self.row.get("printed_at"))

    def _refresh(self):
        """Il pulsante Rimuovi si attiva solo con la conferma spuntata, per un
        seed generato (quella "foglio stampato" o quella "mai stampato")."""
        if self.c_confirm is not None:
            ok = self.c_confirm.isChecked()
            danger = True
        else:
            ok, danger = True, False
        self.b_ok.setEnabled(ok)
        self.b_ok.setProperty("eh", "danger" if danger else "primary")
        self.b_ok.style().unpolish(self.b_ok)
        self.b_ok.style().polish(self.b_ok)


# ===========================================================================
#  Finestra principale
# ===========================================================================

class MainDialog(QDialog):

    def __init__(self, plugin, window, parent=None):
        QDialog.__init__(self, parent or window)
        self.plugin = plugin
        self.window = window
        self.wallet = window.wallet
        self.setWindowTitle(_("Beneficiari") + " \u2014 " + _("Easy Heirs di SAFE21"))
        self.setWindowIcon(_safe21_icon())
        # Con i pulsanti su due righe la larghezza non è più dettata dal
        # footer; l'altezza cresce di una riga.
        self.setMinimumSize(660, 560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Intestazione: icona + titolo + sottotitolo. L'azione principale
        # (Aggiungi beneficiari) sta in basso a sinistra, nel footer.
        band, _right, self.subtitle = _header_band(
            _("Beneficiari dell'eredità"), " ", art_name="heirs", back=self)
        outer.addWidget(band)

        # Riga informativa leggera (al posto del banner colorato)
        outer.addWidget(_info_line(_(
            "La lista serve solo a stampare i fogli. Gli eredi li aggiungi poi "
            "nel plugin di eredità, leggendo con la fotocamera il QR "
            "dell'indirizzo stampato: quote e date si decidono lì.")))

        # Avviso password: sobrio, mostrato solo quando serve
        self.pwd_warn = QLabel("\u26a0  " + _(
            "Questo wallet non ha una password: la generazione di nuovi seed "
            "è disattivata (finirebbero in chiaro). Impostala da "
            "Wallet > Password."))
        self.pwd_warn.setWordWrap(True)
        self.pwd_warn.setStyleSheet(
            f"color:{DANGER}; background:{DANGER_BG}; padding:8px 18px; "
            f"border-bottom:1px solid {DANGER_BD}; font-size:12px;")
        outer.addWidget(self.pwd_warn)

        # Corpo con margini
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(18, 14, 18, 12)
        v.setSpacing(10)
        outer.addWidget(body, 1)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            _("Beneficiario"), _("Tipo"), _("Indirizzo"),
            _("Busta"), _("Ultima stampa"), ""])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        # Ultima colonna fissa e stretta: ospita la ✕ per togliere la riga
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 40)
        # Tasto destro su una riga: copia indirizzo e le altre azioni su
        # quel beneficiario. Doppio clic sull'indirizzo: lo copia.
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._row_menu)
        self.table.cellDoubleClicked.connect(self._on_double)
        self.table.itemSelectionChanged.connect(self._update_row_buttons)
        v.addWidget(self.table, 1)

        # Stato vuoto: invita all'azione invece di lasciare una tabella vuota
        self.empty = self._build_empty_state()
        v.addWidget(self.empty, 1)

        # Footer: sei pulsanti in una griglia 3x2 a colonne uguali.
        #
        # In fila unica la finestra nasceva larga oltre 1100 px. Su due righe
        # con uno spazio elastico in mezzo, però, allargando la finestra una
        # riga si apriva e l'altra restava ammucchiata a sinistra: il vuoto
        # cresceva sempre nello stesso punto. Con la griglia ogni pulsante
        # occupa una colonna della stessa larghezza, quindi restano
        # incolonnati e crescono tutti insieme, a qualunque dimensione.
        #
        # Le due righe restano divise per significato:
        #   riga 1 -> si crea qualcosa, o lo si porta fuori;
        #   riga 2 -> azioni sul beneficiario selezionato.
        grid = QGridLayout()
        grid.setSpacing(8)
        for c in range(3):
            grid.setColumnStretch(c, 1)

        def cell(button, row, col, tip=""):
            """Mette il pulsante nella cella, lasciandogli riempire la colonna."""
            if tip:
                button.setToolTip(tip)
            button.setSizePolicy(QSizePolicy.Policy.Expanding,
                                 QSizePolicy.Policy.Fixed)
            grid.addWidget(button, row, col)

        self.b_add = _primary_button("+  " + _("Aggiungi beneficiari"))
        self.b_add.clicked.connect(self.on_add)
        cell(self.b_add, 0, 0, _(
            "Genera indirizzo e seed per chi non ha un portafoglio proprio, "
            "oppure inserisci un indirizzo già tuo."))

        # I paper wallet hanno la loro finestra, dalla schermata iniziale.
        b_print = QPushButton(_("Stampa documenti") + "\u2026")
        b_print.clicked.connect(self.on_print)
        cell(b_print, 0, 1, _("Stampa i fogli dei beneficiari selezionati."))

        # I tre pulsanti che agiscono sulla riga selezionata dicono su CHI
        # agiscono (titolare, 2026-11-07: "non si capisce quale copia"); senza
        # una riga selezionata sono grigi. Vedi _update_row_buttons.
        self.b_copy = QPushButton(_("Copia indirizzo"))
        self.b_copy.clicked.connect(self.on_copy)
        cell(self.b_copy, 0, 2, _(
            "Copia negli appunti l'indirizzo del beneficiario selezionato."))

        self.b_edit = QPushButton(_("Modifica") + "\u2026")
        self.b_edit.clicked.connect(lambda: self.on_edit())
        cell(self.b_edit, 1, 0, _(
            "Cambia il nome (e, se l'ha fornito lui, l'indirizzo) del "
            "beneficiario selezionato."))

        self.b_env = QPushButton(_("Numero busta") + "\u2026")
        self.b_env.clicked.connect(self.on_envelope)
        cell(self.b_env, 1, 1, _(
            "Assegna un numero di busta al beneficiario selezionato."))

        self.b_del = QPushButton(_("Rimuovi") + "\u2026")
        self.b_del.clicked.connect(lambda: self.on_delete())
        cell(self.b_del, 1, 2, _(
            "Togli il beneficiario selezionato dalla lista (come la \u2715 "
            "sulla riga)."))

        v.addLayout(grid)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED}; font-size:11.5px;")
        v.addWidget(self.status)

        _apply_style(self)
        self.rows = []
        self.refresh()

    def _build_empty_state(self):
        """Pannello mostrato quando non c'è ancora nessun beneficiario:
        icona, un titolo, una riga di spiegazione e l'azione principale."""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(_safe21_icon().pixmap(52, 52))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(icon)
        t = QLabel(_("Non hai ancora aggiunto beneficiari"))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"color:{INK}; font-size:15px; font-weight:600;")
        v.addWidget(t)
        p = QLabel(_(
            "Aggiungi chi erediter\u00e0: puoi generare indirizzo e seed per chi "
            "non ha un portafoglio, oppure inserire un indirizzo già tuo."))
        p.setWordWrap(True)
        p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p.setMaximumWidth(440)
        p.setStyleSheet(f"color:{MUTED}; font-size:12.5px;")
        v.addWidget(p, 0, Qt.AlignmentFlag.AlignHCenter)
        b = _primary_button("+  " + _("Aggiungi il primo beneficiario"))
        b.clicked.connect(self.on_add)
        v.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        return w

    # ---------------------------------------------------------------- dati --

    def refresh(self):
        try:
            self.rows = core.beneficiaries(self.wallet)
        except Exception as e:
            _logger.error(f"lettura beneficiari fallita: {e}")
            QMessageBox.warning(self, _("Errore"), str(e))
            self.rows = []

        has_pwd = core.wallet_has_password(self.wallet)
        self.pwd_warn.setVisible(not has_pwd)
        self.b_add.setEnabled(True)

        n_gen = sum(1 for r in self.rows if r["generated"])
        n = len(self.rows)
        count = (_("nessun beneficiario") if n == 0
                 else _("{} beneficiari").format(n) if n != 1
                 else _("1 beneficiario"))
        self.subtitle.setText(
            _("Portafoglio {} \u00b7 {} \u00b7 {} con seed generato").format(
                self._wallet_name(), count, n_gen))

        # Tabella oppure stato vuoto: mai una tabella vuota e muta
        empty = (n == 0)
        self.table.setVisible(not empty)
        self.empty.setVisible(empty)

        self.table.setRowCount(len(self.rows))
        never = 0
        for i, r in enumerate(self.rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(
                _("Generato") if r["generated"] else _("Indirizzo fornito")))
            it = QTableWidgetItem(r["address"] or "\u2014")
            it.setToolTip(r["address"] or "")
            self.table.setItem(i, 2, it)

            self.table.setItem(i, 3, QTableWidgetItem(r.get("envelope") or "\u2014"))

            when = r.get("printed_at")
            itp = QTableWidgetItem(
                time.strftime("%d/%m/%Y", time.localtime(when)) if when
                else _("mai"))
            if not when:
                itp.setForeground(QColor(DANGER))
                never += 1
            self.table.setItem(i, 4, itp)

            # ✕ per togliere il beneficiario con un click (apre la conferma).
            # Catturiamo il dizionario della riga, non l'indice, così resta
            # corretto anche dopo un refresh che riordina la lista.
            xb = QPushButton("✕")
            xb.setProperty("eh", "del")
            xb.setToolTip(_("Rimuovi questo beneficiario dalla lista"))
            xb.setCursor(Qt.CursorShape.PointingHandCursor)
            xb.clicked.connect(lambda _c=False, row=r: self.on_delete(row))
            self.table.setCellWidget(i, 5, xb)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(5, 40)   # la colonna ✕ resta stretta

        bits = []
        if never:
            bits.append(_("{} fogli mai stampati").format(never))
        self._set_status(" \u00b7 ".join(bits))
        self._update_row_buttons()

    def _wallet_name(self):
        try:
            return os.path.basename(self.wallet.storage.path)
        except Exception:
            return _("wallet")

    def _current(self):
        i = self.table.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    # -------------------------------------------------------------- azioni --

    @staticmethod
    def _short(name, n=18):
        """Il nome nei pulsanti, accorciato se lungo."""
        name = name or "?"
        return name if len(name) <= n else name[:n - 1] + "\u2026"

    def _set_status(self, text, ok=False):
        """Riga di stato in basso: verde con la spunta per una conferma."""
        self.status.setText(("\u2714  " + text) if ok else text)
        self.status.setStyleSheet(
            f"color:{TEAL_DARK}; font-size:12px; font-weight:600;" if ok
            else f"color:{MUTED}; font-size:11.5px;")

    def _update_row_buttons(self):
        """I pulsanti della riga dicono il nome selezionato, o sono grigi."""
        r = self._current() if self.table.selectedItems() else None
        if r:
            nm = self._short(r["name"])
            self.b_copy.setText(_("Copia indirizzo di {}").format(nm))
            self.b_edit.setText(_("Modifica {}").format(nm) + "\u2026")
            self.b_env.setText(_("Numero busta di {}").format(nm) + "\u2026")
            self.b_del.setText(_("Rimuovi {}").format(nm) + "\u2026")
        else:
            self.b_copy.setText(_("Copia indirizzo"))
            self.b_edit.setText(_("Modifica") + "\u2026")
            self.b_env.setText(_("Numero busta") + "\u2026")
            self.b_del.setText(_("Rimuovi") + "\u2026")
        tip = "" if r else _("Seleziona prima un beneficiario nella lista.")
        for b in (self.b_copy, self.b_edit, self.b_env, self.b_del):
            b.setEnabled(r is not None)
            if tip:
                b.setToolTip(tip)
        # Il numero di busta esiste solo per i fogli con seed generato.
        self.b_env.setEnabled(bool(r and r.get("generated")))

    def _copy_address(self, r):
        """Copia l'indirizzo di ``r`` e lo dice chiaramente."""
        if r and r.get("address"):
            QApplication.clipboard().setText(r["address"])
            self._set_status(_("Indirizzo di {} copiato: {}").format(
                r["name"], r["address"]), ok=True)

    def on_copy(self):
        self._copy_address(self._current())

    def _on_double(self, row, col):
        """Doppio clic sulla colonna Indirizzo: copia l'indirizzo."""
        if col == 2 and 0 <= row < len(self.rows):
            self._copy_address(self.rows[row])

    def _row_menu(self, pos):
        """Menu del tasto destro sulla riga sotto il mouse."""
        row = self.table.rowAt(pos.y())
        if not 0 <= row < len(self.rows):
            return
        self.table.selectRow(row)
        r = self.rows[row]
        nm = self._short(r["name"], 24)
        m = QMenu(self)
        m.addAction(_("Copia indirizzo"), lambda: self._copy_address(r))
        m.addAction(_("Copia nome"), lambda: (
            QApplication.clipboard().setText(r["name"]),
            self._set_status(_("Nome copiato: {}").format(r["name"]), ok=True)))
        m.addAction(_("Modifica") + "\u2026", lambda: self.on_edit(r))
        m.addSeparator()
        m.addAction(_("Stampa il foglio di {}").format(nm) + "\u2026",
                    lambda: self._print_rows([r]))
        env = m.addAction(_("Numero busta") + "\u2026", self.on_envelope)
        env.setEnabled(bool(r.get("generated")))
        m.addSeparator()
        m.addAction(_("Rimuovi {}").format(nm) + "\u2026", lambda: self.on_delete(r))
        m.exec(self.table.viewport().mapToGlobal(pos))

    def on_edit(self, row=None):
        """Modifica il beneficiario della riga (o quello selezionato)."""
        r = row if isinstance(row, dict) else self._current()
        if not r:
            return
        dlg = EditDialog(self, self.wallet, r)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.result:
            return
        self.refresh()
        if dlg.result.get("changed"):
            msg = _("{} aggiornato.").format(dlg.e_name.text().strip())
            if dlg.result.get("reprint"):
                msg += " " + _("Il foglio va ristampato.")
            self._set_status(msg, ok=True)

    def _print_rows(self, rows):
        """La finestra di stampa con soli questi beneficiari."""
        PrintDialog(self, self.wallet, rows).exec()
        self.refresh()

    def on_envelope(self):
        r = self._current()
        if not r or not r["generated"]:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Il numero di busta esiste solo per i beneficiari con seed "
                "generato."))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Numero busta"))
        v = QVBoxLayout(dlg)
        v.addWidget(QLabel(_("Numero busta per {}").format(r["name"])))
        e = QLineEdit(r.get("envelope") or "")
        v.addWidget(e)
        h = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(dlg.reject)
        h.addWidget(b)
        h.addStretch(1)
        ok = _primary_button(_("Salva"))
        ok.setDefault(True)
        ok.clicked.connect(dlg.accept)
        h.addWidget(ok)
        v.addLayout(h)
        _apply_style(dlg)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            core.set_envelope(self.wallet, r["address"], e.text().strip())
            self.refresh()

    def on_delete(self, row=None):
        """Rimuove un beneficiario dalla lista, con conferma.

        ``row`` è il dizionario della riga (passato dalla ✕ di quella riga);
        se manca, si usa la riga selezionata. Per i generati la rimozione
        cancella anche il seed: vedi ConfirmDeleteDialog.
        """
        r = row if isinstance(row, dict) else self._current()
        if not r:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Seleziona prima un beneficiario nella lista, poi premi "
                "Rimuovi."))
            return
        dlg = ConfirmDeleteDialog(self, self.wallet, r)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            res = core.delete_beneficiary(self.wallet, r["name"])
        except Exception as e:
            _logger.error(f"rimozione beneficiario fallita: {e}")
            QMessageBox.critical(self, _("Errore"), str(e))
            return
        self.refresh()
        msg = _("{} rimosso dalla lista.").format(r["name"])
        if res.get("had_seed"):
            msg += "  " + _("Anche il suo seed è stato cancellato.")
        self.status.setText(msg)

    def on_add(self):
        # La generazione è libera e gratuita: il plugin non chiede alcun
        # pagamento e non contatta internet. È voluto, perché i seed vanno
        # generati su una macchina scollegata dalla rete.
        # "Aggiungi altri beneficiari" (finestra di conferma) riapre la
        # creazione; "Torna alla lista" esce dal giro.
        while True:
            dlg = CreateDialog(self, self.wallet)
            if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.created:
                break
            self.refresh()
            after = AfterCreateDialog(self, self.window, dlg.created)
            after.exec()
            self.refresh()
            if not after.add_more:
                break



    def on_print(self):
        if not self.rows:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Non c'è ancora nessun beneficiario."))
            return
        PrintDialog(self, self.wallet, self.rows).exec()
        self.refresh()


class AfterCreateDialog(QDialog):
    """Subito dopo la creazione: stampa ora, poi aggiungi altri o torna alla
    lista (anteprima approvata dal titolare, 2026-11-07).

    Dopo ``exec()``, ``self.add_more`` e' True se l'utente vuole aggiungere
    altri beneficiari: la finestra principale riapre la creazione.
    """

    def __init__(self, parent, window, created):
        """``created`` e' una lista di coppie (nome, generato)."""
        QDialog.__init__(self, parent)
        self.window = window
        self.wallet = window.wallet
        self.created = created
        self.add_more = False
        n = len(created)
        gen = [nm for nm, g in created if g]
        self.setWindowTitle(_("Beneficiario creato") if n == 1
                            else _("Beneficiari creati"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumWidth(620)
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(18, 16, 18, 14)
        vbox.setSpacing(12)

        names = ", ".join(nm for nm, _g in created)
        if n == 1:
            title = _("1 beneficiario creato: {}").format(names)
        else:
            title = _("{} beneficiari creati: {}").format(n, names)
        if gen:
            detail = _("Indirizzo, chiave pubblica e parole di recupero generati e "
                       "salvati in questo portafoglio, protetti dalla sua password.")
        else:
            detail = _("Indirizzo salvato nella lista di Easy Heirs.")
        ok = QFrame()
        ok.setObjectName("ehOk")
        ok.setStyleSheet(f"#ehOk {{ background:{TEAL_TINT}; border-radius:8px; }}")
        ol = QVBoxLayout(ok)
        ol.setContentsMargins(14, 12, 14, 12)
        ol.setSpacing(3)
        t = QLabel("\u2714  " + title)
        t.setWordWrap(True)
        t.setStyleSheet(f"color:{TEAL_DARK}; font-weight:600; font-size:14px; background:transparent;")
        ol.addWidget(t)
        d = QLabel(detail)
        d.setWordWrap(True)
        d.setStyleSheet(f"color:{TEAL_DARK}; font-size:12.5px; background:transparent;")
        ol.addWidget(d)
        vbox.addWidget(ok)

        # L'azione che conta: stampare subito.
        cta = QFrame()
        cta.setObjectName("ehCta")
        cta.setStyleSheet(f"#ehCta {{ border:2px solid {TEAL}; border-radius:12px; }}")
        cl = QHBoxLayout(cta)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(14)
        col = QVBoxLayout()
        if n > 1:
            ct = QLabel(_("Adesso stampa i fogli"))
        elif gen:
            ct = QLabel(_("Adesso stampa il foglio"))
        else:
            ct = QLabel(_("Adesso stampa la scheda"))
        ct.setStyleSheet(f"color:{INK}; font-weight:600; font-size:14px;")
        col.addWidget(ct)
        cs = QLabel(_("È il momento giusto: il beneficiario è appena stato creato "
                      "e il foglio è pronto.") if n == 1 else
                    _("È il momento giusto: i beneficiari sono appena stati creati "
                      "e i fogli sono pronti."))
        cs.setWordWrap(True)
        cs.setStyleSheet(f"color:{MUTED}; font-size:12.5px;")
        col.addWidget(cs)
        cl.addLayout(col, 1)
        bp = _primary_button(_("Stampa i fogli ora"))
        bp.setDefault(True)
        bp.clicked.connect(self._print_now)
        cl.addWidget(bp)
        vbox.addWidget(cta)

        # Il passo successivo, che Easy Heirs non fa da solo (2.0).
        note = QLabel("\u24d8  " + _(
            "Dopo la stampa aggiungi l'erede in Àncòra: nella finestra del nuovo "
            "erede inquadra con la fotocamera il QR dell'indirizzo stampato. "
            "Quote e data di consegna si decidono lì."))
        note.setWordWrap(True)
        note.setStyleSheet(
            f"color:{MUTED}; background:#fbfcfd; border:1px solid #eef1f4; "
            "border-radius:6px; padding:9px; font-size:12px;")
        vbox.addWidget(note)

        row = QHBoxLayout()
        more = QPushButton("+  " + _("Aggiungi altri beneficiari"))
        more.clicked.connect(self._more)
        row.addWidget(more)
        row.addStretch(1)
        back = QPushButton(_("Torna alla lista") + "  \u2192")
        back.clicked.connect(self.accept)
        row.addWidget(back)
        vbox.addLayout(row)
        _apply_style(self)

    def _more(self):
        self.add_more = True
        self.accept()

    def _print_now(self):
        """Apre la stampa gia' filtrata sui beneficiari appena creati."""
        names = {nm for nm, _g in self.created}
        try:
            rows = [r for r in core.beneficiaries(self.wallet) if r["name"] in names]
        except Exception as e:
            _logger.error(f"lettura beneficiari per la stampa fallita: {e}")
            rows = []
        if not rows:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Non ci sono fogli da stampare per questi beneficiari."))
            return
        PrintDialog(self, self.wallet, rows).exec()


# ===========================================================================
#  Plugin
# ===========================================================================

# ===========================================================================
#  Paper wallet
# ===========================================================================

def _paper_jobs_for(pw, mode=SIDES_DUPLEX):
    """Le due pagine di un paper wallet: fronte + retro.

    Sempre due, come per i beneficiari, così la stampa fronte/retro resta
    allineata anche mescolando più paper wallet in un solo lavoro di stampa.

    La data di creazione arriva da core come numero (epoch): qui diventa la
    stringa che finisce sul foglio. La formattazione sta da questa parte, come
    per i fogli dei beneficiari, così sheets.py resta solo disegno.
    """
    data = dict(pw)
    created = pw.get("created")
    if created:
        data["created_str"] = time.strftime("%d/%m/%Y", time.localtime(created))
    data["instructions"] = {SIDES_FRONT: "none",
                            SIDES_FRONT_INSTR: "separate"}.get(mode, "back")
    front = lambda s: sheets.render_paper_front(s, data)  # noqa: E731
    if mode == SIDES_FRONT:
        return [front]
    if mode == SIDES_FRONT_INSTR:
        return [front, lambda s: sheets.render_paper_back(s, data, separate=True)]
    return [front, lambda s: sheets.render_paper_back(s, data)]


class PaperWalletDialog(QDialog):
    """Crea N paper wallet, li stampa e poi li dimentica.

    I seed NON vengono salvati da nessuna parte: vivono in ``self.wallets``
    finché questa finestra resta aperta, e spariscono alla chiusura. Per
    questo la finestra non si chiude finché l'utente non conferma di aver
    controllato i fogli, e fino a quel momento può ristampare quante volte
    vuole: è l'unica rete di sicurezza possibile quando non si salva nulla.
    """

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.wallets = []       # i paper wallet generati (solo in RAM)
        self.printed = False    # almeno una stampa è partita
        self.setWindowTitle(_("Paper wallet") + " \u2014 " + _("Easy Heirs di SAFE21"))
        self.setMinimumWidth(780)   # la riga del tipo di seed è larga

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        band, _r, _s = _header_band(_("Crea paper wallet"),
                                    art_name="paper", back=self)
        outer.addWidget(band)
        outer.addWidget(_info_line(PAPER_TEXT))

        body = QWidget()
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(18, 16, 18, 14)
        vbox.setSpacing(12)
        outer.addWidget(body, 1)

        # --- quantità ---
        row = QHBoxLayout()
        row.addWidget(QLabel(_("Quanti paper wallet vuoi creare?")))
        # Menu a tendina invece di uno spinbox: Qt lo disegna in modo
        # nativo, mentre i tastini su/giù di uno QSpinBox spariscono non
        # appena il foglio di stile tocca il widget (per le frecce Qt vuole
        # un'immagine, e il triangolo fatto coi bordi qui non funziona).
        self.spin = QComboBox()
        self.spin.addItems([str(i) for i in range(1, core.MAX_PAPER_WALLETS + 1)])
        self.spin.setFixedWidth(90)
        row.addWidget(self.spin)

        # Formato della frase. Solo qui: i fogli degli EREDI restano sempre
        # BIP39, perché finiscono in mano ad altri che useranno il
        # portafoglio che preferiscono loro, e lì la portabilità non si
        # negozia. Il paper wallet invece resta di chi lo crea, quindi la
        # scelta ha senso.
        row.addSpacing(24)
        row.addWidget(QLabel(_("Tipo di seed:")))
        self.kind = QComboBox()
        self.kind.addItem(_("BIP39 (standard, va in ogni wallet)"),
                          core.SEED_KIND_BIP39)
        self.kind.addItem(_("Electrum (più sicuro , solo x Electrum wallet)"),
                          core.SEED_KIND_ELECTRUM)
        self.kind.setMinimumWidth(330)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        row.addWidget(self.kind)
        row.addStretch(1)
        vbox.addLayout(row)

        self.kind_note = QLabel("")
        self.kind_note.setWordWrap(True)
        self.kind_note.setStyleSheet(
            f"color:{TEAL_DARK}; background:{TEAL_TINT}; border-radius:6px; "
            "padding:9px; font-size:12px;")
        vbox.addWidget(self.kind_note)
        self._kind_changed()

        # --- l'avvertenza che conta ---
        warn = QLabel(_(
            "I seed di questi paper wallet NON vengono salvati: non finiscono "
            "nel wallet, non finiscono in un file. Esisteranno solo sui fogli "
            "che stai per stampare.\n\n"
            "Finché questa finestra resta aperta puoi ristampare. Quando la "
            "chiudi le parole spariscono per sempre: se un foglio è venuto "
            "male o lo perdi, i fondi versati a quell'indirizzo non sono più "
            "recuperabili da nessuno.\n\n"
            "Non versare fondi prima di aver verificato che il foglio sia "
            "stampato bene e leggibile."))
        warn.setWordWrap(True)
        warn.setStyleSheet(
            f"color:{DANGER}; background:{DANGER_BG}; border:1px solid "
            f"{DANGER_BD}; border-radius:6px; padding:10px; font-size:12px;")
        vbox.addWidget(warn)

        note = QLabel(_(
            "Come per i fogli dei beneficiari: usa una stampante collegata "
            "direttamente via cavo, mai di rete o condivisa, e stampa "
            "fronte/retro con giro sul lato lungo."))
        note.setWordWrap(True)
        note.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        vbox.addWidget(note)

        # --- pulsanti ---
        br = QHBoxLayout()
        self.b_close = QPushButton(_("Annulla"))
        self.b_close.clicked.connect(self.reject)
        br.addWidget(self.b_close)
        br.addStretch(1)
        self.b_reprint = QPushButton(_("Ristampa"))
        self.b_reprint.clicked.connect(self._print)
        self.b_reprint.setVisible(False)
        br.addWidget(self.b_reprint)
        self.b_go = _btc_button(_("Genera e stampa"))
        self.b_go.setDefault(True)
        self.b_go.clicked.connect(self._generate_and_print)
        br.addWidget(self.b_go)
        vbox.addLayout(br)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED}; font-size:11.5px;")
        self.status.setWordWrap(True)
        vbox.addWidget(self.status)

        _apply_style(self)

    # ------------------------------------------------------------ azioni --

    def _kind_changed(self):
        """Spiega la scelta mentre la si fa, non dopo.

        Le due opzioni non differiscono per gusto: cambiano cosa dovrà fare
        chi un giorno riprenderà i fondi, ed è giusto saperlo prima.
        """
        if self.kind.currentData() == core.SEED_KIND_ELECTRUM:
            self.kind_note.setText(_(
                "Si ripristina praticamente solo in Electrum, ma senza "
                "spuntare opzioni e senza digitare alcun percorso di "
                "derivazione: ci sono meno cose da sbagliare."))
        else:
            self.kind_note.setText(_(
                "Formato standard: si ripristina in quasi tutti i portafogli "
                "(Electrum, Sparrow, BlueWallet, Ledger, Trezor...). In "
                "Electrum va spuntata l'opzione BIP39 e va digitato anche il "
                "percorso di derivazione, che è stampato sul foglio."))

    def _generate_and_print(self):
        """Genera i paper wallet (una volta sola) e apre la stampa."""
        if not self.wallets:
            n = int(self.spin.currentText())
            kind = self.kind.currentData()
            try:
                self.wallets = core.generate_paper_wallets(n, seed_kind=kind)
            except Exception as e:
                _logger.error(f"generazione paper wallet fallita: {e}")
                QMessageBox.critical(self, _("Easy Heirs"), str(e))
                return
            # Generati: la quantità non si tocca più, altrimenti i fogli
            # già stampati non corrisponderebbero a quelli in memoria.
            self.spin.setEnabled(False)
            self.kind.setEnabled(False)
            self.b_go.setText(_("Stampa"))
            self.status.setText(_(
                "{} paper wallet generati. Sono in memoria: stampali ora."
            ).format(len(self.wallets)))
        self._print()

    def _print(self):
        if not self.wallets:
            return
        if not PaperReminderDialog(self, len(self.wallets)).exec():
            return

        sides = SidesDialog(self, len(self.wallets), len(self.wallets))
        if sides.exec() != QDialog.DialogCode.Accepted:
            return
        mode = sides.mode

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        _setup(printer)
        printer.setDocName("Easy Heirs — paper wallet")
        _set_duplex(printer, mode)
        if QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return

        jobs = []
        for pw in self.wallets:
            jobs += _paper_jobs_for(pw, mode)
        try:
            _draw(printer, jobs)
        except Exception as e:
            _logger.error(f"stampa paper wallet fallita: {e}")
            QMessageBox.critical(self, _("Errore di stampa"), str(e))
            return

        self.printed = True
        self.b_reprint.setVisible(True)
        self.b_go.setVisible(False)
        self.b_close.setText(_("Ho verificato: chiudi"))
        self.status.setText(_(
            "Controlla i fogli: tutte le parole devono essere stampate e "
            "leggibili. Se qualcosa non va, premi Ristampa. Chiudendo, le "
            "parole spariscono."))

    # ----------------------------------------------------------- chiusura --

    def reject(self):
        """Chiudere significa perdere i seed: chiediamo conferma.

        Solo se non è stato stampato nulla la chiusura è innocua (i wallet
        generati non sono mai finiti su carta, quindi non c'è nulla da
        proteggere: si buttano e basta).
        """
        if self.wallets and self.printed:
            if not _ask(self, _("Chiudere?"),
                        _("Hai controllato che tutti i fogli siano stampati e "
                          "leggibili?\n\nChiudendo, le parole di recupero "
                          "vengono dimenticate: non sarà più possibile "
                          "ristamparle.")):
                return
        elif self.wallets and not self.printed:
            if not _ask(self, _("Chiudere senza stampare?"),
                        _("Hai generato {} paper wallet ma non li hai ancora "
                          "stampati. Chiudendo vengono buttati via."
                          ).format(len(self.wallets))):
                return
        # Non basta perdere il riferimento: azzeriamo esplicitamente, così
        # l'intenzione è leggibile nel codice.
        self.wallets = []
        QDialog.reject(self)


class PaperReminderDialog(QDialog):
    """Promemoria prima di mandare in stampa dei paper wallet."""

    def __init__(self, parent, n):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Prima di stampare"))
        self.setMinimumWidth(560)
        vbox = QVBoxLayout(self)

        head = QLabel("⚠  " + _(
            "Stai per stampare {} paper wallet. Ogni foglio contiene parole "
            "di recupero e non esiste una seconda copia.").format(n))
        head.setWordWrap(True)
        head.setStyleSheet(
            f"color:{DANGER}; background:{DANGER_BG}; border:1px solid "
            f"{DANGER_BD}; border-radius:6px; padding:9px; font-size:12px;")
        vbox.addWidget(head)

        steps = QLabel(_(
            "1.  Stampante collegata via cavo: mai di rete, mai condivisa, "
            "mai in copisteria.\n"
            "2.  Fronte/retro con GIRO SUL LATO LUNGO: la banda scura deve "
            "finire dietro le parole.\n"
            "3.  Non allontanarti dalla stampante finché i fogli non sono "
            "usciti.\n"
            "4.  Controlla ogni foglio prima di chiudere questa finestra: "
            "dopo non si può più ristampare."))
        steps.setWordWrap(True)
        vbox.addWidget(steps)

        row = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(self.reject)
        row.addWidget(b)
        row.addStretch(1)
        ok = _primary_button(_("Ho capito, apri la stampa"))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        vbox.addLayout(row)
        _apply_style(self)


# Versione minima di Electrum (titolare, 2026-11-07): provato solo su 4.8.3.
MIN_ELECTRUM = (4, 8, 3)


def _electrum_version():
    """La versione di Electrum in uso come tupla di interi, o None."""
    try:
        from electrum.version import ELECTRUM_VERSION
    except Exception:
        return None
    nums = []
    for part in str(ELECTRUM_VERSION).split(".")[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    return tuple(nums + [0] * (3 - len(nums)))


# Nome che portano le nostre voci di menu e la nostra icona: serve a
# ritrovarle (e toglierle) anche se le ha messe un'istanza precedente.
TAG = "safe21_easy_heirs"


def _drop_tagged(window, button=True):
    """Toglie da ``window`` le voci di menu marcate con TAG e, se
    ``button``, anche l'icona nella barra di stato.

    _wire passa ``button=False``: Electrum crea la barra di stato (e la
    nostra icona, hook create_status_bar) PRIMA del menu, quindi togliendo
    anche l'icona al momento del menu questa spariva subito (prova del
    titolare, 2026-11-07). L'icona si toglie solo spegnendo il plugin.
    """
    tools = getattr(window, "tools_menu", None)
    menus = [tools] if tools is not None else []
    try:
        menus.append(window.menuBar())
    except Exception:
        pass
    for menu in menus:
        for act in list(menu.actions()):
            if act.objectName().startswith(TAG):
                menu.removeAction(act)
                act.deleteLater()
    if not button:
        return
    try:
        sb = window.statusBar()
        for old in sb.findChildren(QWidget, TAG + ":button"):
            sb.removeWidget(old)
            old.setParent(None)
            old.deleteLater()
    except Exception:
        pass


# ===========================================================================
#  Schermata iniziale
# ===========================================================================

# Testi delle due scelte (approvati dal titolare, 2026-11-07). Il testo dei
# paper wallet torna anche in cima alla loro finestra.
HEIRS_TEXT = _(
    "Un foglio per ogni persona che riceverà l'eredità. La lista resta "
    "salvata, così puoi ristampare quando vuoi. Poi aggiungi ogni erede in "
    "Àncòra leggendo il QR stampato.")
PAPER_TEXT = _(
    "Un portafoglio nuovo su carta, da regalare o da tenere da parte: lo "
    "stampi e poi ci mandi i bitcoin. Le parole di recupero non vengono "
    "salvate da nessuna parte, quindi il foglio va custodito bene.")


class HomeDialog(QDialog):
    """La prima finestra di Easy Heirs: due strade diverse, due colori.

    Beneficiari (verde) e paper wallet (arancio) sono cose diverse: i primi
    restano in una lista salvata, i secondi non vengono salvati affatto.
    Nella stessa finestra sembravano la stessa cosa (titolare, 2026-11-07),
    quindi qui si sceglie, e ogni finestra ha il suo "Indietro".
    """

    def __init__(self, plugin, window):
        QDialog.__init__(self, window)
        self.plugin = plugin
        self.window = window
        self.wallet = window.wallet
        self.setWindowTitle(_("Easy Heirs di SAFE21"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumSize(700, 420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        band, _right, _sub = _header_band(
            _("Easy Heirs di SAFE21"),
            _("Portafoglio {} \u00b7 cosa vuoi preparare?").format(self._wallet_name()))
        outer.addWidget(band)

        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(18, 18, 18, 12)
        v.setSpacing(14)
        outer.addWidget(body, 1)

        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.heirs_status = QLabel("")
        cards.addWidget(self._card(
            _("Fogli per i beneficiari"), HEIRS_TEXT, self.heirs_status,
            _primary_button(_("Apri")), self.open_heirs, TEAL, TEAL_DARK,
            "heirs"), 1)
        paper_status = QLabel(_("Fino a {} per volta").format(core.MAX_PAPER_WALLETS))
        cards.addWidget(self._card(
            _("Paper wallet"), PAPER_TEXT, paper_status,
            _btc_button(_("Apri")), self.open_paper, BTC_ORANGE, "#854f0b",
            "paper"), 1)
        v.addLayout(cards, 1)

        foot = QHBoxLayout()
        note = QLabel(_("Nessuna connessione a internet: tutto avviene su "
                        "questo computer."))
        note.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        foot.addWidget(note)
        foot.addStretch(1)
        rm = QPushButton(_("Rimuovi i dati dal portafoglio") + "\u2026")
        rm.setFlat(True)
        rm.setCursor(Qt.CursorShape.PointingHandCursor)
        rm.setStyleSheet(f"color:{DANGER}; font-size:12px;")
        rm.setToolTip(_(
            "Toglie da questo portafoglio i dati di Easy Heirs: numeri di "
            "busta e date di stampa, oppure anche la lista e i seed."))
        rm.clicked.connect(self.open_remove)
        foot.addWidget(rm)
        v.addLayout(foot)

        _apply_style(self)
        self.refresh()

    def _card(self, title, text, status, button, action, border, ink, art_name):
        """Una delle due scelte: disegno, titolo, spiegazione, stato e
        pulsante. Il disegno (lo stesso della fascia di quella finestra) dice
        a colpo d'occhio che cosa si sta scegliendo."""
        box = QFrame()
        box.setObjectName("ehCard")
        box.setStyleSheet(
            f"#ehCard {{ border:2px solid {border}; border-radius:12px; "
            "background:white; }")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        picture = _band_art(art_name, height=72)
        if picture is not None:
            lay.addWidget(picture, 0, Qt.AlignmentFlag.AlignHCenter)
        t = QLabel(title)
        t.setStyleSheet(f"color:{INK}; font-size:15px; font-weight:600;")
        lay.addWidget(t)
        d = QLabel(text)
        d.setWordWrap(True)
        d.setStyleSheet(f"color:{MUTED}; font-size:12.5px;")
        lay.addWidget(d)
        lay.addStretch(1)
        status.setWordWrap(True)
        status.setStyleSheet(f"color:{ink}; font-size:12.5px;")
        lay.addWidget(status)
        button.clicked.connect(action)
        lay.addWidget(button)
        return box

    def refresh(self):
        """Il riassunto della scheda beneficiari: quanti e quanti mai stampati."""
        try:
            rows = core.beneficiaries(self.wallet)
        except Exception as e:
            _logger.error(f"lettura beneficiari fallita: {e}")
            rows = []
        n = len(rows)
        never = sum(1 for r in rows if not r.get("printed_at"))
        if n == 0:
            text = _("Nessun beneficiario ancora")
        else:
            text = (_("1 beneficiario") if n == 1
                    else _("{} beneficiari").format(n))
            if never:
                text += " \u00b7 " + (_("1 foglio mai stampato") if never == 1
                                       else _("{} fogli mai stampati").format(never))
        self.heirs_status.setText(text)

    def _wallet_name(self):
        try:
            return os.path.basename(self.wallet.storage.path)
        except Exception:
            return _("wallet")

    def open_heirs(self):
        """La finestra dei beneficiari; chiudendola si torna qui."""
        MainDialog(self.plugin, self.window, parent=self).exec()
        self.refresh()

    def open_paper(self):
        """La finestra dei paper wallet; chiudendola si torna qui."""
        PaperWalletDialog(self).exec()

    def open_remove(self):
        """Rimuovi i dati di Easy Heirs da questo portafoglio."""
        RemoveDialog(self, self.wallet).exec()
        self.refresh()


class Plugin(BasePlugin):
    """Aggancio a Electrum.

    Perché non basta creare un menu proprio
    ----------------------------------------
    Aggiungere un menu alla barra con ``menuBar().addMenu()`` non compare su
    Electrum 4.8.0. La strada che funziona, ed è quella usata dagli altri
    plugin, è
    l'oggetto ufficiale ``window.tools_menu``: la voce finisce dentro
    Strumenti. Da evitare invece la ricerca del menu per titolo, perché con
    Electrum in italiano si chiama "Strumenti" e il confronto con "Tools"
    fallirebbe.

    Agganci usati, tutti idempotenti:

    * ``init_menubar``      avvio normale, con il plugin già abilitato
    * ``init_qt``           abilitazione a caldo, finestre già aperte
    * ``load_wallet``       ulteriore rete di sicurezza
    * ``create_status_bar`` pulsante in basso a destra, sempre visibile
    """

    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self._wired = set()
        self._wired_windows = []
        self._stale_warned = False
        self._stale_scheduled = False
        self._buttons = {}
        ver = _electrum_version()
        # Su un Electrum piu' vecchio il plugin resta fermo: nessun menu,
        # nessuna icona, solo un messaggio (una volta).
        self._too_old = ver is not None and ver < MIN_ELECTRUM
        self._version_text = ".".join(str(x) for x in ver) if ver else "?"
        self._too_old_said = False

    # ------------------------------------------------------------- hooks --

    def _external_plugin_dir(self):
        """La cartella dei plugin esterni secondo Electrum stesso, o None.

        È la fonte più attendibile; core sa comunque ricavarla da solo dal
        percorso di caricamento, ma solo se l'archivio di partenza è ancora
        al suo posto.
        """
        try:
            return self.parent.get_external_plugin_dir()
        except Exception as e:
            _logger.info(f"cartella dei plugin non ottenibile da Electrum: {e}")
            return None

    def _schedule_stale_check(self, window):
        """Programma il controllo della versione subito dopo gli hook.

        Electrum riesegue gli hook appena si installa un aggiornamento
        (chiama ``reload_windows()``): è quello il momento in cui ha senso
        dire di riavviare, perché è quando l'utente sta aggiornando.
        Aspettare l'apertura della nostra finestra non basta -- chi installa e
        chiude Electrum non vedrebbe mai l'avviso, ed è esattamente ciò che
        succedeva.

        Il piccolo ritardo evita di aprire una finestra modale mentre Electrum
        sta ancora costruendo la propria.
        """
        if self._stale_warned or self._stale_scheduled:
            return
        self._stale_scheduled = True
        try:
            QTimer.singleShot(1500, lambda: self._warn_if_stale(window))
        except Exception as e:
            _logger.info(f"controllo della versione non programmato: {e}")

    def _warn_if_stale(self, window):
        """Avvisa una volta sola se su disco c'è una versione più nuova.

        Sostituire lo ZIP mentre Electrum è aperto non basta: Python
        continua a usare i moduli già importati. Senza questo avviso si
        starebbe usando il plugin vecchio credendo di usare quello nuovo, ed
        è il tipo di equivoco che fa perdere tempo (o peggio, fa pensare che
        una correzione non funzioni).
        """
        # Il controllo è finito: un'altra tornata di hook (per esempio dopo
        # l'installazione di un aggiornamento, più tardi nella stessa
        # sessione) potrà programmarne un altro.
        self._stale_scheduled = False
        if self._stale_warned:
            return
        try:
            # Fra la programmazione e lo scatto la finestra può essere stata
            # chiusa: usarla allora farebbe cadere il plugin. Senza padre il
            # messaggio si mostra lo stesso.
            window.isVisible()
        except Exception:
            window = None
        try:
            disk = core.stale_version(self._external_plugin_dir())
        except Exception as e:
            _logger.info(f"controllo della versione non riuscito: {e}")
            return
        # Tracciato sempre, anche quando va tutto bene: quando questo avviso
        # non compare, il log è l'unico modo per sapere se il controllo ha
        # girato e che cosa ha visto.
        _logger.info(f"versione in esecuzione {core.RUNNING_VERSION}, "
                     f"su disco {disk or 'nessuna diversa'}")
        if not disk:
            return
        self._stale_warned = True
        # Finestra standard di Electrum, col suo triangolo di avvertimento:
        # qui conta il richiamo d'attenzione, non il marchio.
        QMessageBox.warning(
            window, _("Easy Heirs") + " \u2014 " + _("riavvia Electrum"),
            _("Hai installato la versione {new} del plugin, ma Electrum sta "
              "ancora usando la {old}: i moduli già caricati restano in "
              "memoria finché il programma non viene chiuso.\n\n"
              "Chiudi e riapri Electrum prima di usare il plugin, altrimenti "
              "stai lavorando con la versione precedente."
              ).format(new=disk, old=core.RUNNING_VERSION))

    @hook
    def init_qt(self, gui_object):
        _logger.info("hook init_qt")
        try:
            for window in list(getattr(gui_object, "windows", []) or []):
                self._wire(window)
                self._ensure_status_button(window)
                self._schedule_stale_check(window)
        except Exception as e:
            _logger.error(f"init_qt fallito: {e}")

    @hook
    def init_menubar(self, window):
        _logger.info("hook init_menubar")
        self._wire(window)
        self._schedule_stale_check(window)

    @hook
    def load_wallet(self, wallet, window):
        _logger.info("hook load_wallet")
        self._wire(window)
        self._schedule_stale_check(window)

    @hook
    def create_status_bar(self, sb):
        """Pulsante in basso a destra: la via più visibile, e non dipende da
        come Electrum costruisce la barra dei menu. Chiamato da Electrum quando
        crea la barra (avvio normale o ricreazione della finestra)."""
        _logger.info("hook create_status_bar")
        if self._too_old:
            return
        try:
            self._add_status_button(sb)
        except Exception as e:
            _logger.error(f"icona barra di stato fallita: {e}")

    def _add_status_button(self, sb):
        """Aggiunge (o rimpiazza) l'icona SAFE21 nella barra di stato ``sb``.
        Idempotente: una sola icona per barra, tracciata per ``id(sb)``."""
        key = id(sb)
        self._buttons.pop(key, None)
        # Anche quello lasciato da un'istanza precedente del plugin.
        for old in sb.findChildren(QWidget, TAG + ":button"):
            try:
                sb.removeWidget(old)
                old.setParent(None)
                old.deleteLater()
            except Exception:
                pass
        tip = _("Easy Heirs di SAFE21")
        # La finestra va cercata al momento del CLIC (vedi _resolve_window):
        # all'aggancio la barra potrebbe non essere ancora legata alla finestra.
        cb = lambda: self.open_main(self._resolve_window(sb))  # noqa: E731
        if StatusBarButton is not None:
            # Solo icona, della STESSA dimensione degli altri loghi di Electrum:
            # StatusBarButton ridimensiona l'icona a sb.height().
            btn = StatusBarButton(_safe21_icon(), tip, cb, sb.height())
        else:
            # Ripiego: un pulsante piatto con la sola icona.
            btn = QPushButton()
            btn.setIcon(_safe21_icon())
            btn.setToolTip(tip)
            btn.setFlat(True)
            btn.clicked.connect(cb)
        btn.setObjectName(TAG + ":button")
        sb.addPermanentWidget(btn)
        self._buttons[key] = btn
        _logger.info("icona SAFE21 aggiunta alla barra di stato")

    def _ensure_status_button(self, window):
        """Aggancio a CALDO: su una finestra già aperta la barra di stato
        esiste già, quindi aggiungiamo l'icona subito, senza aspettare che
        Electrum ricrei la finestra. Così, appena si abilita il plugin, è
        già utilizzabile senza riavviare Electrum. Idempotente."""
        try:
            sb = window.statusBar() if hasattr(window, "statusBar") else None
            if sb is not None and not sb.findChildren(QWidget, TAG + ":button"):
                self._add_status_button(sb)
        except Exception as e:
            _logger.error(f"aggancio barra di stato a caldo fallito: {e}")

    @hook
    def close_wallet(self, wallet):
        pass

    def requires_settings(self):
        """Il pulsante Impostazioni nella finestra Plugins di Electrum."""
        return not self._too_old

    def settings_dialog(self, window):
        """Plugins > Easy Heirs di SAFE21 > Impostazioni: rimuovi i dati dal
        portafoglio aperto (titolare, 2026-11-06). Electrum passa la finestra
        dei Plugins, non quella del portafoglio: lo si ritrova risalendo, o
        fra le finestre a cui il plugin e' agganciato."""
        target = self._resolve_window(window)
        if target is None or getattr(target, "wallet", None) is None:
            alive = [w for w in self._wired_windows
                     if getattr(w, "wallet", None) is not None]
            target = alive[-1] if alive else None
        if target is None:
            QMessageBox.information(window, _("Easy Heirs di SAFE21"),
                                    _("Apri prima un portafoglio."))
            return
        RemoveDialog(window, target.wallet).exec()

    def on_close(self):
        """Plugin disattivato: toglie le sue voci di menu e la sua icona da
        ogni finestra, così riattivandolo non compaiono doppie."""
        for ref in list(self._wired_windows):
            try:
                _drop_tagged(ref)
            except Exception as e:
                _logger.info(f"pulizia finestra saltata: {e}")
        self._wired.clear()
        self._wired_windows.clear()
        self._buttons.clear()
        try:
            BasePlugin.on_close(self)
        except Exception:
            pass

    # -------------------------------------------------------------- menu --

    def _say_too_old(self, window):
        """Una volta sola: serve Electrum 4.8.3 o successivo."""
        if self._too_old_said:
            return
        self._too_old_said = True
        try:
            QMessageBox.warning(window, _("Easy Heirs di SAFE21"), _(
                "Easy Heirs di SAFE21 richiede Electrum 4.8.3 o successivo. "
                "Questo Electrum è la versione {}: il plugin resta spento. "
                "Aggiorna Electrum per usarlo.").format(self._version_text))
        except Exception as e:
            _logger.error(f"avviso versione non mostrato: {e}")

    def _wire(self, window):
        """Aggiunge le voci nel menu Strumenti. Ripetibile senza duplicare."""
        if self._too_old:
            self._say_too_old(window)
            return
        if window is None or id(window) in self._wired:
            return
        added = False

        # Prima si tolgono le voci che una copia precedente del plugin ha
        # lasciato (disattivato e riattivato: Electrum crea un'istanza nuova,
        # con un _wired vuoto, e le vecchie voci restavano: menu doppio).
        _drop_tagged(window, button=False)

        # 1) la via che funziona: l'oggetto ufficiale di Electrum
        tools = getattr(window, "tools_menu", None)
        if tools is not None:
            try:
                tools.addSeparator().setObjectName(TAG + ":sep")
                act = tools.addAction(
                    _("Easy Heirs di SAFE21") + "\u2026",
                    lambda: self.open_main(window))
                act.setObjectName(TAG + ":main")
                added = True
                _logger.info("voce aggiunta al menu Strumenti")
            except Exception as e:
                _logger.error(f"tools_menu non utilizzabile: {e}")

        # 2) ripiego: un menu nostro nella barra
        if not added:
            try:
                menu = window.menuBar().addMenu(_("Easy Heirs"))
                menu.menuAction().setObjectName(TAG + ":menu")
                menu.addAction(_("Beneficiari e stampe") + "\u2026",
                               lambda: self.open_main(window))
                added = True
                _logger.info("menu proprio aggiunto alla barra")
            except Exception as e:
                _logger.error(f"creazione menu fallita: {e}")

        if added:
            self._wired.add(id(window))
            if window not in self._wired_windows:
                self._wired_windows.append(window)
        else:
            _logger.error("nessun aggancio riuscito: resta il pulsante "
                          "nella barra di stato")

    # ---------------------------------------------------------- apertura --

    def open_main(self, window):
        self._warn_if_stale(window)
        if getattr(window, "wallet", None) is None:
            QMessageBox.information(window, _("Easy Heirs"),
                                    _("Nessun wallet aperto."))
            return
        try:
            HomeDialog(self, window).exec()
        except Exception as e:
            _logger.error(f"apertura finestra fallita: {e}")
            QMessageBox.critical(window, _("Easy Heirs"), str(e))

    def _resolve_window(self, widget):
        """Risale fino alla finestra di Electrum che possiede un wallet.

        Tentativi in ordine: la catena dei genitori del widget, la finestra
        di primo livello, quelle su cui abbiamo già agganciato il menu, e
        infine la finestra attiva.
        """
        node = widget
        for _i in range(12):
            if node is None:
                break
            if getattr(node, "wallet", None) is not None:
                return node
            node = node.parent() if hasattr(node, "parent") else None
        try:
            top = widget.window()
            if getattr(top, "wallet", None) is not None:
                return top
        except Exception:
            pass
        for ref in list(self._wired_windows):
            if getattr(ref, "wallet", None) is not None:
                return ref
        try:
            active = QApplication.activeWindow()
            if getattr(active, "wallet", None) is not None:
                return active
        except Exception:
            pass
        return widget.window() if hasattr(widget, "window") else widget

