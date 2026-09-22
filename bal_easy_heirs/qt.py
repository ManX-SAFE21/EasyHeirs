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
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from electrum.i18n import _
from electrum.logging import get_logger
from electrum.plugin import BasePlugin, hook

# Il pulsante ufficiale della barra di stato di Electrum (in basso a destra):
# lo usiamo cosi' l'icona ha la STESSA dimensione e resa degli altri loghi
# gia' presenti li'. Import difensivo: se un domani Electrum lo spostasse,
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
    full = f"{pkg}.{mod_name}" if pkg else f"bal_easy_heirs_{mod_name}"

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


core = _load_sibling("core")
sheets = _load_sibling("sheets")


# ===========================================================================
#  Icona del plugin (tessera SAFE21 con serratura)
# ===========================================================================
# PNG incorporato in base64: cosi' l'icona si carica sempre, senza dipendere
# dai percorsi interni dello ZIP con cui Electrum importa il plugin. La
# sorgente e' icons/safe21-keyhole.svg / .png, derivata dal logo ufficiale di
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
# Un'unica fonte di verita' per colori, font e forma dei pulsanti: cosi' TUTTE
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
DANGER_BG = "#fceeee"
DANGER_BD = "#e6c3c3"

# Stile dell'indicatore delle caselle di spunta. Va DEFINITO esplicitamente:
# con un foglio di stile attivo, Qt smette di disegnare il segno di spunta
# nativo e senza queste regole la casella resta vuota anche quando e' spuntata
# (era il bug segnalato). Qui: casella bianca col bordo, TEAL PIENO quando
# spuntata. Riusato anche dalle caselle che hanno un proprio stylesheet.
_CHECK_INDICATOR = f"""
QCheckBox {{ spacing:8px; }}
QCheckBox::indicator {{ width:16px; height:16px; border:1px solid #b0b8c0;
    border-radius:4px; background:{SURFACE}; }}
QCheckBox::indicator:hover {{ border:1px solid {TEAL}; }}
QCheckBox::indicator:checked {{ background:{TEAL}; border:1px solid {TEAL}; }}
QCheckBox::indicator:checked:hover {{ background:{TEAL_DARK};
    border:1px solid {TEAL_DARK}; }}
QCheckBox::indicator:disabled {{ background:#eef0f2; border:1px solid #dde2e6; }}
"""

_QSS = f"""
QDialog {{ background:#f6f7f9; }}
QLabel {{ color:{BODY}; font-size:13px; }}
QLineEdit, QSpinBox {{ padding:6px 8px; border:1px solid {BORDER};
    border-radius:6px; background:{SURFACE}; font-size:13px; color:{INK}; }}
QLineEdit:focus, QSpinBox:focus {{ border:1px solid {TEAL}; }}
QTableWidget {{ border:1px solid {BORDER}; border-radius:6px;
    background:{SURFACE}; gridline-color:#eef1f4; font-size:13px; }}
QHeaderView::section {{ background:#f0f3f5; color:{MUTED}; padding:7px 10px;
    border:none; border-bottom:1px solid #e1e6ea; font-weight:600; }}
QPushButton {{ background:{SURFACE}; border:1px solid #cdd4db; border-radius:7px;
    padding:8px 14px; font-size:13px; color:{BODY}; }}
QPushButton:hover {{ background:#eef2f4; }}
QPushButton[bal="primary"] {{ background:{TEAL}; border:none; color:white;
    font-weight:600; padding:10px 18px; }}
QPushButton[bal="primary"]:hover {{ background:{TEAL_DARK}; }}
QPushButton[bal="danger"] {{ background:{DANGER}; border:none; color:white;
    font-weight:600; }}
QPushButton[bal="danger"]:hover {{ background:#8f1c22; }}
QPushButton[bal="del"] {{ border:none; background:transparent; color:{MUTED};
    font-size:16px; font-weight:700; padding:2px 8px; }}
QPushButton[bal="del"]:hover {{ color:{DANGER}; }}
QPushButton[balMuted="true"] {{ background:#f0f2f4; border:1px solid #e2e6ea;
    color:#9aa5b0; }}
QPushButton[balMuted="true"]:hover {{ background:#f0f2f4; }}
""" + _CHECK_INDICATOR


def _apply_style(dialog):
    """Applica il foglio di stile condiviso a una finestra del plugin."""
    dialog.setStyleSheet(_QSS)


def _primary_button(text):
    """Pulsante dell'azione principale (teal pieno). Uno solo per finestra."""
    b = QPushButton(text)
    b.setProperty("bal", "primary")
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def _danger_button(text):
    """Pulsante di un'azione distruttiva (rosso pieno)."""
    b = QPushButton(text)
    b.setProperty("bal", "danger")
    return b


def _header_band(title, subtitle=""):
    """Fascia d'intestazione: icona SAFE21 + titolo (+ sottotitolo).

    Ritorna ``(band, right_layout, subtitle_label)``:
      * ``band`` = il widget da mettere in cima alla finestra;
      * ``right_layout`` = lo spazio a DESTRA dove agganciare l'azione
        principale (gia' spinto a destra da uno stretch);
      * ``subtitle_label`` = l'etichetta del sottotitolo (o None), per
        aggiornarla a runtime.
    """
    band = QWidget()
    # IMPORTANTE: lo stile va SCOPATO al solo widget (#objectName), altrimenti
    # in Qt lo sfondo della fascia si applica anche ai figli (il pulsante
    # "Aggiungi beneficiari" perdeva il suo teal e diventava quasi invisibile).
    band.setObjectName("balHeaderBand")
    band.setStyleSheet(
        f"#balHeaderBand {{ background:{TEAL_TINT}; "
        "border-bottom:1px solid #cfe6e1; }}")
    h = QHBoxLayout(band)
    h.setContentsMargins(18, 14, 18, 14)
    h.setSpacing(12)

    icon = QLabel()
    icon.setPixmap(_safe21_icon().pixmap(38, 38))
    h.addWidget(icon)

    col = QVBoxLayout()
    col.setSpacing(1)
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
    return band, h, sub


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


def _jobs_for(row, seed=None):
    """Le pagine di un beneficiario. Sempre due, per tenere allineata la
    stampa fronte/retro: seed -> fronte + retro con le istruzioni; solo
    indirizzo -> scheda + retro vuoto."""
    data = {
        "name": row["name"], "address": row["address"],
        "xpub": row.get("xpub", ""), "seed": seed or "",
        "guardian": row.get("guardian", ""), "envelope": row.get("envelope", ""),
        "account_derivation": core.DERIVATION_ACCOUNT,
        "date": row["date"].strftime("%d %B %Y") if row.get("date") else "",
        "txid": row.get("txid", ""),
    }
    if seed:
        return [lambda s: sheets.render_seed_front(s, data),
                lambda s: sheets.render_seed_back(s, has_seed=True)]
    # Anche l'erede con solo indirizzo occupa DUE pagine (scheda + retro
    # vuoto): cosi' ogni documento ha un numero pari di pagine e la stampa
    # fronte/retro resta allineata, invece di sfasarsi dopo una pagina dispari.
    return [lambda s: sheets.render_given(s, data),
            lambda s: sheets.render_blank_back(s)]


# ===========================================================================
#  Creazione multipla
# ===========================================================================

class CreateDialog(QDialog):

    # Colonne della tabella di inserimento
    C_NAME, C_ADDR, C_SHARE, C_STATUS, C_DEL = range(5)

    def __init__(self, parent, wallet):
        QDialog.__init__(self, parent)
        self.wallet = wallet
        self.created = []
        self.setWindowTitle(_("Aggiungi beneficiari") + " \u2014 Easy Heirs")
        self.setMinimumSize(820, 560)

        self.existing = {r["name"].lower() for r in core.beneficiaries(wallet)}
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            _("Nome o denominazione"), _("Indirizzo bitcoin"),
            _("Quota"), _("Cosa succede"), ""])
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(self.C_NAME, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.C_ADDR, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.C_SHARE, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(self.C_STATUS, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(self.C_DEL, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(self.C_SHARE, 90)
        self.table.setColumnWidth(self.C_STATUS, 180)
        self.table.setColumnWidth(self.C_DEL, 40)
        vbox.addWidget(self.table, 1)

        # Aggiungi una riga (azione secondaria) + nota sulle quote
        addrow = QHBoxLayout()
        self.b_addrow = QPushButton("+  " + _("Aggiungi un'altra riga"))
        self.b_addrow.clicked.connect(lambda: (self._add_row(),
                                               self._recompute()))
        addrow.addWidget(self.b_addrow)
        addrow.addStretch(1)
        vbox.addLayout(addrow)

        share_note = QLabel(_(
            "Le quote si dividono in parti uguali; se ne scrivi una a mano, le "
            "altre si ribilanciano da sole. Togli una riga con la \u2715: le quote "
            "si ricalcolano."))
        share_note.setWordWrap(True)
        share_note.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        vbox.addWidget(share_note)

        self.err = QLabel("")
        self.err.setWordWrap(True)
        self.err.setStyleSheet(f"color:{DANGER}; font-size:12px;")
        vbox.addWidget(self.err)

        note = QLabel("\u24d8  " + _(
            "I seed generati restano dentro questo wallet, protetti dalla sua "
            "password, cosi' puoi ristampare un foglio smarrito. Ogni backup "
            "del file wallet li conterra'."))
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
        self._recompute()

    # ----------------------------------------------------------------- ui --

    def _add_row(self, name="", addr="", share="", edited=False):
        """Aggiunge una riga in fondo alla tabella. Ogni riga porta la sua \u2715
        per essere tolta con un solo click."""
        if self.table.rowCount() >= MAX_BATCH:
            return
        i = self.table.rowCount()
        self.table.insertRow(i)

        e_name = QLineEdit(name)
        e_addr = QLineEdit(addr)
        e_addr.setPlaceholderText(_("lascia vuoto per generarlo io"))
        e_share = QLineEdit()
        e_share.setPlaceholderText(_("es. 20%"))
        e_share._user_edited = edited
        if share:
            e_share.blockSignals(True)
            e_share.setText(share)
            e_share.blockSignals(False)

        e_name.textChanged.connect(self._refresh)
        e_addr.textChanged.connect(self._refresh)
        # Quando l'utente scrive una quota a mano, la segniamo come "sua" e
        # ricalcoliamo le altre; se la cancella, torna automatica.
        e_share.textEdited.connect(
            lambda _t, w=e_share: self._on_share_edited(w))

        self.table.setCellWidget(i, self.C_NAME, e_name)
        self.table.setCellWidget(i, self.C_ADDR, e_addr)
        self.table.setCellWidget(i, self.C_SHARE, e_share)
        self.table.setItem(i, self.C_STATUS, QTableWidgetItem(""))

        xb = QPushButton("\u2715")     # \u2715
        xb.setProperty("bal", "del")
        xb.setToolTip(_("Togli questo beneficiario"))
        xb.setCursor(Qt.CursorShape.PointingHandCursor)
        xb.clicked.connect(lambda _c=False, marker=e_name: self._del_row(marker))
        self.table.setCellWidget(i, self.C_DEL, xb)

    def _row_of(self, marker):
        """Indice ATTUALE della riga il cui campo Nome e' ``marker`` (le righe
        si spostano quando se ne cancella una, quindi va ricercata al click)."""
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, self.C_NAME) is marker:
                return r
        return -1

    def _del_row(self, marker):
        """Toglie la riga con un click e ricalcola le quote automatiche."""
        r = self._row_of(marker)
        if r < 0:
            return
        self.table.removeRow(r)
        self._recompute()

    def _on_share_edited(self, w):
        # Una quota scritta a mano e' "sua" finche' non la svuota; svuotandola
        # torna automatica e si ribilancia con le altre.
        w._user_edited = bool(w.text().strip())
        self._recompute()

    def _recompute(self):
        """Ridistribuisce le quote automatiche in parti uguali, rispettando
        quelle scritte a mano e quanto gia' assegnato in BAL."""
        n = self.table.rowCount()
        manual = []
        for i in range(n):
            w = self.table.cellWidget(i, self.C_SHARE)
            txt = w.text().strip() if w else ""
            manual.append(txt if (w and getattr(w, "_user_edited", False)
                                  and txt) else None)
        suggested = core.suggest_shares(self.wallet, manual)
        for i in range(n):
            w = self.table.cellWidget(i, self.C_SHARE)
            if w is not None and not getattr(w, "_user_edited", False):
                w.blockSignals(True)
                w.setText(suggested[i] if i < len(suggested) else "")
                w.blockSignals(False)
        self._refresh()

    def _name(self, i):
        w = self.table.cellWidget(i, self.C_NAME)
        return w.text().strip() if w else ""

    def _addr(self, i):
        w = self.table.cellWidget(i, self.C_ADDR)
        return w.text().strip() if w else ""

    def _share(self, i):
        w = self.table.cellWidget(i, self.C_SHARE)
        return w.text().strip() if w else ""

    def _refresh(self):
        problems = []
        seen_names, seen_addr = set(), set()
        n_rows = self.table.rowCount()
        for i in range(n_rows):
            name, addr, share = self._name(i), self._addr(i), self._share(i)
            label, bad = "", False
            if not name:
                label, bad = _("il nome e' obbligatorio"), True
            elif name.lower() in self.existing or name.lower() in seen_names:
                label, bad = _("nome gia' presente"), True
            elif share and not self._valid_share(share):
                label, bad = _("quota non valida"), True
            elif addr:
                if not self._valid(addr):
                    label, bad = _("indirizzo non valido"), True
                elif addr in seen_addr:
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

    @staticmethod
    def _valid_share(share):
        """Una quota vuota va bene (resta il segnaposto): qui si valida solo
        se l'utente ha scritto qualcosa."""
        s = share.strip()
        if s.endswith("%"):
            try:
                v = float(s[:-1])
                return v > 0
            except Exception:
                return False
        try:
            return float(s) > 0
        except Exception:
            return False

    # ------------------------------------------------------------- azione --

    def _create(self):
        rows = [(self._name(i), self._addr(i), self._share(i))
                for i in range(self.table.rowCount())]
        done, errors = [], []
        for name, addr, share in rows:
            try:
                if addr:
                    core.add_provided(self.wallet, name, addr, amount=share)
                    done.append((name, False, not bool(share)))
                else:
                    mnemonic, address, xpub = core.generate_beneficiary()
                    core.add_generated(self.wallet, name, address, xpub,
                                       mnemonic, amount=share)
                    del mnemonic
                    done.append((name, True, not bool(share)))
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
        band, _r, _s = _header_band(_("Stampa documenti"))
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
        # riceve ne' clic ne' passaggio del mouse, quindi non potrebbe mostrare
        # alcun tooltip). Quando non e' utilizzabile lo mostriamo "grigio" via
        # stile e spieghiamo il perche' nel tooltip (e al clic).
        has_something = bool(sel) or self.cb_report.isChecked()
        if with_seed:
            self._pdf_ok = False
            self._pdf_reason = _(
                "Non posso salvare in PDF i fogli con le parole di recupero: "
                "sul disco resterebbero in chiaro e potrebbero finire per "
                "sbaglio su un cloud. Questi fogli vanno solo stampati.\n\n"
                "Puoi pero' salvare in PDF il “Riepilogo per l'esecutore” "
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
        self.b_pdf.setProperty("balMuted", not self._pdf_ok)
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
        if with_seed and not ReminderDialog(self, len(with_seed)).exec():
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        _setup(printer)
        printer.setDocName("Easy Heirs")
        # Preimpostiamo la stampa fronte/retro con giro sul LATO LUNGO: e' il
        # modo in cui la banda nera del retro finisce dietro le parole del
        # fronte. Cosi' la finestra di stampa si apre gia' su questa scelta;
        # l'utente puo' comunque cambiarla, e il promemoria glielo ricorda.
        try:
            printer.setDuplex(QPrinter.DuplexMode.DuplexLongSide)
        except Exception as e:
            _logger.info(f"impossibile preimpostare il fronte/retro: {e}")
        if QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return

        jobs = []
        for r in sel:
            seed = core.seed_for(self.wallet, r["address"]) \
                if r["generated"] else None
            jobs += _jobs_for(r, seed)
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
        self.accept()

    def _save_pdf(self):
        # Il tasto e' sempre attivo: se in questo momento non e' utilizzabile,
        # spieghiamo il perche' invece di non fare nulla in silenzio.
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

    def __init__(self, parent, n):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Prima di stampare"))
        self.setMinimumWidth(560)
        vbox = QVBoxLayout(self)

        head = QLabel("⚠  " + _(
            "Stai per stampare {} fogli che contengono parole di recupero. "
            "Chi legge quelle parole puo' prendere i fondi.").format(n))
        head.setWordWrap(True)
        head.setStyleSheet(
            f"color:{DANGER}; background:{DANGER_BG}; border:1px solid "
            f"{DANGER_BD}; border-radius:6px; padding:9px; font-size:12px;")
        vbox.addWidget(head)

        steps = QLabel(_(
            "1.  Imposta la stampa fronte/retro con GIRO SUL LATO LUNGO: la "
            "banda nera deve finire dietro le parole.\n"
            "2.  Non allontanarti dalla stampante finche' i fogli non sono "
            "usciti.\n"
            "3.  Piega ogni foglio in tre lungo i crocini e imbustalo subito.\n"
            "4.  Numera le buste come indicato nel riepilogo."))
        steps.setWordWrap(True)
        vbox.addWidget(steps)

        check = QLabel(_(
            "Verifica consigliata su un foglio: guardalo piegato in "
            "controluce. Le parole non devono leggersi attraverso la carta. "
            "Se si leggono, la stampa ha girato sul lato corto e la banda "
            "nera e' finita dal lato sbagliato."))
        check.setWordWrap(True)
        check.setStyleSheet(
            f"color:{TEAL_DARK}; background:{TEAL_TINT}; border-radius:6px; "
            "padding:9px; font-size:12px;")
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
    """La data viene registrata solo se l'utente conferma che e' andata bene."""

    def __init__(self, parent, n):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_("Stampa completata"))
        self.setMinimumWidth(520)
        vbox = QVBoxLayout(self)
        lbl = QLabel(_(
            "Sono stati inviati alla stampante {} documenti.\n\n"
            "Se qualcosa e' andato storto (carta inceppata, stampa parziale, "
            "banda nera dal lato sbagliato) distruggi i fogli e ristampa: i "
            "dati restano nel wallet, non si perde nulla.").format(n))
        lbl.setWordWrap(True)
        vbox.addWidget(lbl)
        row = QHBoxLayout()
        b = QPushButton(_("No, ristampo"))
        b.clicked.connect(self.reject)
        row.addWidget(b)
        row.addStretch(1)
        ok = _primary_button(_("Si', tutto a posto"))
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
            "border-radius:8px; }}")
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
        vbox.addWidget(zone)

        keep = QLabel("\u24d8  " + _(
            "Non viene toccato in nessun caso: la lista beneficiari di BAL "
            "con nomi, indirizzi e quote; il will con le transazioni gia' "
            "firmate; le chiavi e i fondi del tuo wallet."))
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
                "Questi fogli non risultano mai stampati: {}. Se cancelli i "
                "loro seed adesso, quegli indirizzi restano senza chiavi e "
                "qualunque somma inviata sara' persa. Stampali prima di "
                "procedere.").format(
                    ", ".join(e.get("name", "?") for e in never)))
        else:
            self.never.hide()
        ok = (self.c_meta.isChecked() or seeds)
        if seeds:
            ok = ok and self.c_confirm.isChecked() and not never
        self.b_ok.setEnabled(ok)
        # Il pulsante diventa rosso solo quando si cancellano i seed (azione
        # distruttiva); altrimenti resta l'azione principale neutra.
        self.b_ok.setProperty("bal", "danger" if seeds else "primary")
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


# ===========================================================================
#  Rimozione di un singolo beneficiario
# ===========================================================================

class ConfirmDeleteDialog(QDialog):
    """Conferma la rimozione di UN beneficiario dalla lista.

    Per chi ha 'indirizzo fornito' e' una semplice conferma. Per chi e' stato
    generato da Easy Heirs, il seed di default viene CONSERVATO; una zona
    pericolosa a parte permette, con doppia conferma, di cancellarlo del tutto.
    """

    def __init__(self, parent, wallet, row):
        QDialog.__init__(self, parent)
        self.wallet = wallet
        self.row = row
        self.delete_seed = False
        generated = bool(row.get("generated"))
        name = row.get("name", "?")

        self.setWindowTitle(_("Rimuovi beneficiario"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(10)

        lead = QLabel(
            _("Vuoi rimuovere <b>{}</b> dalla lista dell'eredità?").format(name))
        lead.setWordWrap(True)
        lead.setStyleSheet(f"color:{INK}; font-size:14px;")
        v.addWidget(lead)

        info = QLabel("ⓘ  " + _(
            "Viene tolto dalla lista di BAL. Le quote degli altri restano "
            "invariate: eventuali ritocchi si fanno in BAL. Se hai BAL aperto, "
            "chiudi e riapri il wallet perché veda la modifica."))
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        v.addWidget(info)

        self.c_seed = None
        if generated:
            keep = QLabel("ⓘ  " + _(
                "Il seed generato resta salvato nel wallet: potrai ristamparlo "
                "o riaggiungere il beneficiario. Nulla va perso."))
            keep.setWordWrap(True)
            keep.setStyleSheet(f"color:{MUTED}; font-size:12px;")
            v.addWidget(keep)

            zone = QFrame()
            zone.setStyleSheet(
                f"QFrame {{ background:{DANGER_BG}; border:1px solid "
                f"{DANGER_BD}; border-radius:8px; }}")
            zl = QVBoxLayout(zone)
            zl.setContentsMargins(14, 12, 14, 12)
            zl.setSpacing(8)
            zh = QLabel("⚠  " + _("Zona pericolosa — cancellazione del seed"))
            zh.setStyleSheet(
                f"color:{DANGER}; font-weight:600; background:transparent; "
                "border:none;")
            zl.addWidget(zh)
            self.c_seed = QCheckBox(_(
                "Cancella anche il seed generato — IRREVERSIBILE"))
            self.c_seed.setStyleSheet(
                f"QCheckBox {{ color:{DANGER}; font-weight:600; }}"
                + _CHECK_INDICATOR)
            self.c_seed.stateChanged.connect(self._refresh)
            zl.addWidget(self.c_seed)
            detail = QLabel(_(
                "Il seed non e' salvato da nessun'altra parte se non sul foglio "
                "che hai stampato. Cancellandolo, se il foglio va perso i "
                "bitcoin inviati a quell'indirizzo diventano irrecuperabili "
                "per sempre."))
            detail.setWordWrap(True)
            detail.setStyleSheet(
                "color:#7a2a2a; background:transparent; border:none; "
                "font-size:12px;")
            zl.addWidget(detail)
            self.c_confirm = QCheckBox(_(
                "Confermo che il foglio e' stato stampato, verificato e "
                "consegnato"))
            self.c_confirm.setStyleSheet(_CHECK_INDICATOR)
            self.c_confirm.stateChanged.connect(self._refresh)
            zl.addWidget(self.c_confirm)
            self.never = QLabel("")
            self.never.setWordWrap(True)
            self.never.setStyleSheet(
                f"color:white; background:{DANGER}; border-radius:6px; "
                "padding:9px; font-size:12px;")
            zl.addWidget(self.never)
            v.addWidget(zone)

        row_l = QHBoxLayout()
        b = QPushButton(_("Annulla"))
        b.clicked.connect(self.reject)
        row_l.addWidget(b)
        row_l.addStretch(1)
        self.b_ok = QPushButton(_("Rimuovi"))
        self.b_ok.clicked.connect(self._accept)
        row_l.addWidget(self.b_ok)
        v.addLayout(row_l)

        _apply_style(self)
        self._refresh()

    def _never_printed(self):
        return bool(self.row.get("generated") and not self.row.get("printed_at"))

    def _refresh(self):
        seed = bool(self.c_seed and self.c_seed.isChecked())
        if self.c_seed is not None:
            self.c_confirm.setEnabled(seed)
            never = self._never_printed()
            if seed and never:
                self.never.show()
                self.never.setText("⚠  " + _(
                    "Questo foglio non risulta mai stampato. Se cancelli il "
                    "seed adesso, l'indirizzo resta senza chiave e qualunque "
                    "somma inviata sara' persa. Stampalo prima di procedere."))
            else:
                self.never.hide()
            ok = (not seed) or (self.c_confirm.isChecked() and not never)
        else:
            ok = True
        self.b_ok.setEnabled(ok)
        self.b_ok.setProperty("bal", "danger" if seed else "primary")
        self.b_ok.style().unpolish(self.b_ok)
        self.b_ok.style().polish(self.b_ok)

    def _accept(self):
        self.delete_seed = bool(self.c_seed and self.c_seed.isChecked())
        self.accept()


# ===========================================================================
#  Finestra principale
# ===========================================================================

class MainDialog(QDialog):

    def __init__(self, plugin, window):
        QDialog.__init__(self, window)
        self.plugin = plugin
        self.window = window
        self.wallet = window.wallet
        self.setWindowTitle(_("Easy Heirs") + " \u2014 SAFE21")
        self.setWindowIcon(_safe21_icon())
        self.setMinimumSize(940, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Intestazione: icona + titolo + sottotitolo. L'azione principale
        # (Aggiungi beneficiari) sta in basso a sinistra, nel footer.
        band, _right, self.subtitle = _header_band(
            _("Beneficiari dell'eredita'"), " ")
        outer.addWidget(band)

        # Riga informativa leggera (al posto del banner colorato)
        outer.addWidget(_info_line(_(
            "L'elenco proviene dalla lista di BAL. Quote e date restano di "
            "competenza di BAL.")))

        # Avviso password: sobrio, mostrato solo quando serve
        self.pwd_warn = QLabel("\u26a0  " + _(
            "Questo wallet non ha una password: la generazione di nuovi seed "
            "e' disattivata (finirebbero in chiaro). Impostala da "
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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            _("Beneficiario"), _("Tipo"), _("Indirizzo"), _("Quota"),
            _("Busta"), _("Ultima stampa"), ""])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        # Ultima colonna fissa e stretta: ospita la ✕ per togliere la riga
        self.table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 40)
        # Doppio clic sulla colonna Quota = modifica rapida della quota
        self.table.cellDoubleClicked.connect(self._on_cell_double)
        v.addWidget(self.table, 1)

        # Stato vuoto: invita all'azione invece di lasciare una tabella vuota
        self.empty = self._build_empty_state()
        v.addWidget(self.empty, 1)

        # Footer: azione principale (verde) a sinistra, poi le secondarie,
        # e "Stampa documenti" spinta a destra.
        foot = QHBoxLayout()
        foot.setSpacing(8)
        self.b_add = _primary_button("+  " + _("Aggiungi beneficiari"))
        self.b_add.setToolTip(_(
            "Genera indirizzo e seed per chi non ha un portafoglio proprio, "
            "oppure inserisci un indirizzo gia' tuo."))
        self.b_add.clicked.connect(self.on_add)
        foot.addWidget(self.b_add)
        b_copy = QPushButton(_("Copia indirizzo"))
        b_copy.clicked.connect(self.on_copy)
        foot.addWidget(b_copy)
        b_env = QPushButton(_("Numero busta") + "\u2026")
        b_env.clicked.connect(self.on_envelope)
        foot.addWidget(b_env)
        b_quota = QPushButton(_("Modifica quota") + "\u2026")
        b_quota.setToolTip(_(
            "Cambia la percentuale o l'importo del beneficiario selezionato "
            "(puoi anche fare doppio clic sulla colonna Quota)."))
        b_quota.clicked.connect(lambda: self.on_edit_quota())
        foot.addWidget(b_quota)
        b_del = QPushButton(_("Rimuovi") + "\u2026")
        b_del.setToolTip(_(
            "Togli il beneficiario selezionato dalla lista (come la \u2715 "
            "sulla riga)."))
        b_del.clicked.connect(lambda: self.on_delete())
        foot.addWidget(b_del)
        b_export = QPushButton(_("Esporta lista (JSON)") + "\u2026")
        b_export.setToolTip(_(
            "Salva la lista eredi in un file .json da importare in BAL con "
            "Import. Contiene solo indirizzi, quote e date: mai i seed."))
        b_export.clicked.connect(self.on_export)
        foot.addWidget(b_export)
        foot.addStretch(1)
        b_print = QPushButton(_("Stampa documenti") + "\u2026")
        b_print.clicked.connect(self.on_print)
        foot.addWidget(b_print)
        v.addLayout(foot)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{MUTED}; font-size:11.5px;")
        v.addWidget(self.status)

        _apply_style(self)
        self.rows = []
        self.refresh()

    def _build_empty_state(self):
        """Pannello mostrato quando non c'e' ancora nessun beneficiario:
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
            "non ha un portafoglio, oppure inserire un indirizzo gia' tuo."))
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
        date = next((r["date"] for r in self.rows if r.get("date")), None)
        extra = (" \u00b7 " + _("consegna: {}").format(date.strftime("%d/%m/%Y"))
                 if date else "")
        n = len(self.rows)
        count = (_("nessun beneficiario") if n == 0
                 else _("{} beneficiari").format(n) if n != 1
                 else _("1 beneficiario"))
        self.subtitle.setText(
            _("Portafoglio {} \u00b7 {} \u00b7 {} con seed generato{}").format(
                self._wallet_name(), count, n_gen, extra))

        # Tabella oppure stato vuoto: mai una tabella vuota e muta
        empty = (n == 0)
        self.table.setVisible(not empty)
        self.empty.setVisible(empty)

        self.table.setRowCount(len(self.rows))
        pct, missing, never = 0.0, 0, 0
        for i, r in enumerate(self.rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(
                _("Generato") if r["generated"] else _("Indirizzo fornito")))
            it = QTableWidgetItem(r["address"] or "\u2014")
            it.setToolTip(r["address"] or "")
            self.table.setItem(i, 2, it)

            share = r.get("share", "")
            its = QTableWidgetItem(share)
            if r.get("placeholder_amount"):
                its.setForeground(QColor(DANGER))
                missing += 1
            elif share.endswith("%"):
                try:
                    pct += float(share[:-1])
                except Exception:
                    pass
            self.table.setItem(i, 3, its)
            self.table.setItem(i, 4, QTableWidgetItem(r.get("envelope") or "\u2014"))

            when = r.get("printed_at")
            itp = QTableWidgetItem(
                time.strftime("%d/%m/%Y", time.localtime(when)) if when
                else _("mai"))
            if not when:
                itp.setForeground(QColor(DANGER))
                never += 1
            self.table.setItem(i, 5, itp)

            # ✕ per togliere il beneficiario con un click (apre la conferma).
            # Catturiamo il dizionario della riga, non l'indice, cosi' resta
            # corretto anche dopo un refresh che riordina la lista.
            xb = QPushButton("✕")
            xb.setProperty("bal", "del")
            xb.setToolTip(_("Rimuovi questo beneficiario dalla lista"))
            xb.setCursor(Qt.CursorShape.PointingHandCursor)
            xb.clicked.connect(lambda _c=False, row=r: self.on_delete(row))
            self.table.setCellWidget(i, 6, xb)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(6, 40)   # la colonna ✕ resta stretta

        bits = []
        if pct:
            bits.append(_("somma delle quote in percentuale: {:.0f}%").format(pct))
        if missing:
            bits.append(_("{} senza quota definita").format(missing))
        if never:
            bits.append(_("{} fogli mai stampati").format(never))
        self.status.setText(" \u00b7 ".join(bits))

    def _wallet_name(self):
        try:
            return os.path.basename(self.wallet.storage.path)
        except Exception:
            return _("wallet")

    def _current(self):
        i = self.table.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    # -------------------------------------------------------------- azioni --

    def on_copy(self):
        r = self._current()
        if r and r["address"]:
            QApplication.clipboard().setText(r["address"])
            self.status.setText(_("Indirizzo copiato: {}").format(r["address"]))

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

    def _on_cell_double(self, row, col):
        # Doppio clic sulla colonna Quota (indice 3) -> modifica la quota.
        if col == 3 and 0 <= row < len(self.rows):
            self.on_edit_quota(self.rows[row])

    def on_edit_quota(self, row=None):
        """Modifica SOLO la quota (percentuale o importo) del beneficiario.

        ``row`` e' il dizionario della riga (dal doppio clic); se manca si usa
        la riga selezionata. Indirizzo e data non vengono toccati.
        """
        r = row if isinstance(row, dict) else self._current()
        if not r:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Seleziona prima un beneficiario, poi Modifica quota."))
            return

        raw = r.get("amount_raw")
        prefill = "" if str(raw) == str(core.PLACEHOLDER_SATS) else str(raw or "")

        dlg = QDialog(self)
        dlg.setWindowTitle(_("Modifica quota"))
        dlg.setWindowIcon(_safe21_icon())
        dlg.setMinimumWidth(420)
        vv = QVBoxLayout(dlg)
        vv.setContentsMargins(18, 16, 18, 14)
        vv.setSpacing(10)
        title = QLabel(_("Quota per <b>{}</b>").format(r.get("name", "?")))
        title.setStyleSheet(f"color:{INK}; font-size:14px;")
        vv.addWidget(title)
        e = QLineEdit(prefill)
        e.setPlaceholderText(_("es. 25%  oppure un importo in satoshi"))
        vv.addWidget(e)
        hint = QLabel("ⓘ  " + _(
            "Percentuale (es. 25%) o importo fisso in satoshi. Se hai BAL "
            "aperto, chiudi e riapri il wallet perché veda la modifica."))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        vv.addWidget(hint)
        hb = QHBoxLayout()
        bc = QPushButton(_("Annulla"))
        bc.clicked.connect(dlg.reject)
        hb.addWidget(bc)
        hb.addStretch(1)
        bo = _primary_button(_("Salva"))
        bo.setDefault(True)
        bo.clicked.connect(dlg.accept)
        hb.addWidget(bo)
        vv.addLayout(hb)
        _apply_style(dlg)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            core.set_heir_amount(self.wallet, r["name"], e.text().strip())
        except Exception as ex:
            QMessageBox.warning(self, _("Quota non valida"), str(ex))
            return
        self.refresh()
        self.status.setText(_("Quota di {} aggiornata.").format(r["name"]))

    def on_delete(self, row=None):
        """Rimuove un beneficiario dalla lista, con conferma.

        ``row`` e' il dizionario della riga (passato dalla ✕ di quella riga);
        se manca, si usa la riga selezionata. Per i generati la conferma
        include (in una zona pericolosa a parte) la possibilita' di cancellare
        anche il seed. Vedi ConfirmDeleteDialog.
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
            res = core.delete_beneficiary(
                self.wallet, r["name"], delete_seed=dlg.delete_seed)
        except Exception as e:
            _logger.error(f"rimozione beneficiario fallita: {e}")
            QMessageBox.critical(self, _("Errore"), str(e))
            return
        self.refresh()
        msg = _("{} rimosso dalla lista.").format(r["name"])
        if res.get("seed_deleted"):
            msg += "  " + _("Anche il suo seed e' stato cancellato.")
        self.status.setText(msg)

    def on_add(self):
        # La generazione e' libera e gratuita: il plugin non chiede alcun
        # pagamento e non contatta internet. E' voluto, perche' i seed vanno
        # generati su una macchina scollegata dalla rete.
        dlg = CreateDialog(self, self.wallet)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.created:
            return
        self.refresh()
        AfterCreateDialog(self, self.window, dlg.created).exec()



    def on_print(self):
        if not self.rows:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Non c'e' ancora nessun beneficiario."))
            return
        PrintDialog(self, self.wallet, self.rows).exec()
        self.refresh()

    def on_export(self):
        """Salva la lista eredi in un file .json importabile da BAL.

        Il file usa lo stesso formato che BAL produce ed importa, cosi' basta
        aprirlo in BAL con tasto destro sulla lista eredi > Import. Vengono
        esportati solo indirizzi, quote e date: i seed non fanno parte della
        lista di BAL e non entrano mai nel file.
        """
        if not self.rows:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Non c'e' ancora nessun erede da esportare."))
            return

        # Proponiamo il salvataggio sul Desktop (con ripiego sulla home se non
        # esiste), coerente con quanto chiesto: un file pronto sul desktop.
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.isdir(desktop):
            desktop = os.path.expanduser("~")
        suggested = os.path.join(
            desktop, "BAL_eredi_{}.json".format(self._wallet_name()))

        path, _sel = QFileDialog.getSaveFileName(
            self, _("Salva la lista eredi per BAL"), suggested,
            "JSON (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"

        try:
            n = core.export_heirs_to_bal_json(self.wallet, path)
        except Exception as e:
            _logger.error(f"export lista eredi fallito: {e}")
            QMessageBox.warning(self, _("Errore"), str(e))
            return

        self.status.setText(_("Lista eredi esportata: {}").format(path))
        QMessageBox.information(self, _("Easy Heirs"), _(
            "{} eredi salvati in:\n{}\n\nPer usarli in BAL: apri BAL, tasto "
            "destro sulla lista eredi, scegli Import e seleziona questo "
            "file.").format(n, path))


class AfterCreateDialog(QDialog):
    """I due promemoria che contano, subito dopo la creazione."""

    def __init__(self, parent, window, created):
        """``created`` e' una lista di triple (nome, generato, segnaposto).

        ``segnaposto`` e' True se per quel beneficiario non e' stata scritta
        nessuna quota nella finestra di creazione: in quel caso in BAL c'e'
        ancora l'importo fittizio usato solo per superare i controlli. Se
        invece l'utente ha accettato o modificato il suggerimento automatico,
        la quota scritta e' gia' un valore sensato e non va segnalata come
        "da correggere".
        """
        QDialog.__init__(self, parent)
        self.window = window
        self.wallet = window.wallet
        self.created = created
        self.setWindowTitle(_("Beneficiari creati"))
        self.setWindowIcon(_safe21_icon())
        self.setMinimumWidth(600)
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(18, 16, 18, 14)
        vbox.setSpacing(10)

        gen = [n for n, g, _p in created if g]
        pending = [n for n, _g, p in created if p]
        ok = QLabel(_("{} beneficiari creati: {}.").format(
            len(created), ", ".join(n for n, _g, _p in created)))
        ok.setWordWrap(True)
        ok.setStyleSheet(
            f"color:{TEAL_DARK}; background:{TEAL_TINT}; border-radius:6px; "
            "padding:9px; font-weight:600;")
        vbox.addWidget(ok)
        if gen:
            s = QLabel(_("Seed e indirizzi generati e salvati in questo "
                         "wallet per: {}.").format(", ".join(gen)))
            s.setWordWrap(True)
            vbox.addWidget(s)

        # Invito a stampare SUBITO, prima di chiudere il wallet: e' il momento
        # giusto, con i beneficiari appena creati gia' pronti.
        cta = QFrame()
        cta.setStyleSheet(
            f"QFrame {{ background:{TEAL_TINT}; border:1px solid #cfe6e1; "
            "border-radius:8px; }}")
        cl = QVBoxLayout(cta)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(8)
        ct = QLabel(_(
            "Stampa ora i fogli dei beneficiari appena creati, prima di "
            "chiudere il wallet: è il momento giusto per metterli al sicuro."))
        ct.setWordWrap(True)
        ct.setStyleSheet(
            f"color:{TEAL_DARK}; font-weight:600; background:transparent; "
            "border:none;")
        cl.addWidget(ct)
        bp = _primary_button(_("Stampa i fogli ora"))
        bp.setDefault(True)
        bp.clicked.connect(self._print_now)
        crow = QHBoxLayout()
        crow.addWidget(bp)
        crow.addStretch(1)
        cl.addLayout(crow)
        vbox.addWidget(cta)

        warn = QLabel(_(
            "Dopo aver stampato, chiudi e riapri questo wallet prima di "
            "tornare in BAL. BAL tiene la lista dei beneficiari in memoria: "
            "se lo apri adesso potrebbe non vedere quelli nuovi, o "
            "sovrascriverli al primo salvataggio."))
        warn.setWordWrap(True)
        warn.setStyleSheet(
            f"color:{DANGER}; background:{DANGER_BG}; border:1px solid "
            f"{DANGER_BD}; border-radius:6px; padding:9px; font-size:12px;")
        vbox.addWidget(warn)

        if pending:
            note = QLabel(_(
                "Per {} non era stata scritta una quota: hanno un importo "
                "segnaposto di {} sat, messo solo per non farli scartare dai "
                "controlli. Correggilo in BAL con la quota reale, altrimenti "
                "riceveranno quella cifra senza alcun messaggio di errore."
            ).format(", ".join(pending), core.PLACEHOLDER_SATS))
        else:
            note = QLabel(_(
                "A tutti e' stata assegnata una quota (suggerita o scritta a "
                "mano): verificala comunque in BAL prima di firmare, e "
                "controlla che il totale sia quello voluto."))
        note.setWordWrap(True)
        note.setStyleSheet(
            f"color:{MUTED}; background:#fbfcfd; border:1px solid #eef1f4; "
            "border-radius:6px; padding:9px; font-size:12px;")
        vbox.addWidget(note)

        row = QHBoxLayout()
        b = QPushButton(_("Resta qui"))
        b.clicked.connect(self.accept)
        row.addWidget(b)
        row.addStretch(1)
        c = QPushButton(_("Chiudi il wallet ora"))
        c.clicked.connect(self._close_wallet)
        row.addWidget(c)
        vbox.addLayout(row)
        _apply_style(self)

    def _print_now(self):
        """Apre la finestra di stampa gia' filtrata sui beneficiari appena
        creati, cosi' si possono mettere al sicuro i fogli prima di chiudere
        il wallet."""
        names = {n for n, _g, _p in self.created}
        try:
            rows = [r for r in core.beneficiaries(self.wallet)
                    if r["name"] in names]
        except Exception as e:
            _logger.error(f"lettura beneficiari per la stampa fallita: {e}")
            rows = []
        if not rows:
            QMessageBox.information(self, _("Easy Heirs"), _(
                "Non ci sono fogli da stampare per questi beneficiari."))
            return
        PrintDialog(self, self.wallet, rows).exec()

    def _close_wallet(self):
        self.accept()
        try:
            p = self.parent()
            if isinstance(p, QDialog):
                p.accept()
        except Exception:
            pass
        try:
            self.window.close()
        except Exception:
            pass


# ===========================================================================
#  Plugin
# ===========================================================================

class Plugin(BasePlugin):
    """Aggancio a Electrum.

    Perche' non basta creare un menu proprio
    ----------------------------------------
    Aggiungere un menu alla barra con ``menuBar().addMenu()`` non compare su
    Electrum 4.8.0. La strada che funziona, ed e' quella usata da BAL, e'
    l'oggetto ufficiale ``window.tools_menu``: la voce finisce dentro
    Strumenti. Da evitare invece la ricerca del menu per titolo, perche' con
    Electrum in italiano si chiama "Strumenti" e il confronto con "Tools"
    fallirebbe.

    Agganci usati, tutti idempotenti:

    * ``init_menubar``      avvio normale, con il plugin gia' abilitato
    * ``init_qt``           abilitazione a caldo, finestre gia' aperte
    * ``load_wallet``       ulteriore rete di sicurezza
    * ``create_status_bar`` pulsante in basso a destra, sempre visibile
    """

    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self._wired = set()
        self._wired_windows = []
        self._buttons = {}

    # ------------------------------------------------------------- hooks --

    @hook
    def init_qt(self, gui_object):
        _logger.info("hook init_qt")
        try:
            for window in list(getattr(gui_object, "windows", []) or []):
                self._wire(window)
        except Exception as e:
            _logger.error(f"init_qt fallito: {e}")

    @hook
    def init_menubar(self, window):
        _logger.info("hook init_menubar")
        self._wire(window)

    @hook
    def load_wallet(self, wallet, window):
        _logger.info("hook load_wallet")
        self._wire(window)

    @hook
    def create_status_bar(self, sb):
        """Pulsante in basso a destra: la via piu' visibile, e non dipende da
        come Electrum costruisce la barra dei menu. Chiamato da Electrum quando
        crea la barra (avvio normale o ricreazione della finestra)."""
        _logger.info("hook create_status_bar")
        try:
            self._add_status_button(sb)
        except Exception as e:
            _logger.error(f"icona barra di stato fallita: {e}")

    def _add_status_button(self, sb):
        """Aggiunge (o rimpiazza) l'icona SAFE21 nella barra di stato ``sb``.
        Idempotente: una sola icona per barra, tracciata per ``id(sb)``."""
        key = id(sb)
        old = self._buttons.pop(key, None)
        if old is not None:
            try:
                old.setParent(None)
                old.deleteLater()
            except Exception:
                pass
        tip = _("Easy Heirs: beneficiari e stampe")
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
        sb.addPermanentWidget(btn)
        self._buttons[key] = btn
        _logger.info("icona SAFE21 aggiunta alla barra di stato")

    def _ensure_status_button(self, window):
        """Aggancio a CALDO: su una finestra gia' aperta la barra di stato
        esiste gia', quindi aggiungiamo l'icona subito, senza aspettare che
        Electrum ricrei la finestra. Cosi', appena si abilita il plugin, e'
        gia' utilizzabile senza riavviare Electrum. Idempotente."""
        try:
            sb = window.statusBar() if hasattr(window, "statusBar") else None
            if sb is not None and id(sb) not in self._buttons:
                self._add_status_button(sb)
        except Exception as e:
            _logger.error(f"aggancio barra di stato a caldo fallito: {e}")

    @hook
    def close_wallet(self, wallet):
        pass

    # -------------------------------------------------------------- menu --

    def _wire(self, window):
        """Aggiunge le voci nel menu Strumenti. Ripetibile senza duplicare."""
        if window is None or id(window) in self._wired:
            return
        added = False

        # 1) la via che funziona: l'oggetto ufficiale di Electrum
        tools = getattr(window, "tools_menu", None)
        if tools is not None:
            try:
                tools.addSeparator()
                tools.addAction(_("Easy Heirs: beneficiari e stampe") + "\u2026",
                                lambda: self.open_main(window))
                tools.addAction(_("Easy Heirs: rimuovi i dati dal wallet") + "\u2026",
                                lambda: self.open_remove(window))
                added = True
                _logger.info("voci aggiunte al menu Strumenti")
            except Exception as e:
                _logger.error(f"tools_menu non utilizzabile: {e}")

        # 2) ripiego: un menu nostro nella barra
        if not added:
            try:
                menu = window.menuBar().addMenu(_("Easy Heirs"))
                menu.addAction(_("Beneficiari e stampe") + "\u2026",
                               lambda: self.open_main(window))
                menu.addAction(_("Rimuovi i dati dal wallet") + "\u2026",
                               lambda: self.open_remove(window))
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
        if getattr(window, "wallet", None) is None:
            QMessageBox.information(window, _("Easy Heirs"),
                                    _("Nessun wallet aperto."))
            return
        try:
            MainDialog(self, window).exec()
        except Exception as e:
            _logger.error(f"apertura finestra fallita: {e}")
            QMessageBox.critical(window, _("Easy Heirs"), str(e))

    def _resolve_window(self, widget):
        """Risale fino alla finestra di Electrum che possiede un wallet.

        Tentativi in ordine: la catena dei genitori del widget, la finestra
        di primo livello, quelle su cui abbiamo gia' agganciato il menu, e
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

    def open_remove(self, window):
        if getattr(window, "wallet", None) is None:
            return
        try:
            RemoveDialog(window, window.wallet).exec()
        except Exception as e:
            _logger.error(f"apertura rimozione fallita: {e}")
            QMessageBox.critical(window, _("Easy Heirs"), str(e))
