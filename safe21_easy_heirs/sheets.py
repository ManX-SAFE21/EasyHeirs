# -*- coding: utf-8 -*-
"""
Easy Heirs - SAFE21
sheets.py : disegno dei fogli, coordinate in millimetri.

Correzione rispetto alla versione precedente
--------------------------------------------
Le metriche del font venivano prese con QFontMetricsF(font), cioè SENZA
dispositivo: restituivano misure in pixel-schermo (~96 dpi) che venivano poi
confrontate con larghezze calcolate a 600 dpi. Conseguenze: le righe non
andavano a capo (la zpub finiva sopra i QR) e l'interlinea era sbagliata (i
titoli si sovrapponevano ai testi).

Qui le metriche si prendono sempre con QFontMetricsF(font, device), dove
device è il dispositivo su cui il painter sta dipingendo. Tutte le misure
restano quindi nella stessa unità.
"""

import os
import pkgutil
import random

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QImage, QPen

# --------------------------------------------------------------------------- #
PAGE_W, PAGE_H = 210.0, 297.0
MARGIN = 15.0
FOLD1, FOLD2 = 99.0, 198.0

C_INK = QColor("#16202A")
C_BODY = QColor("#39454F")
C_MUTED = QColor("#7C8892")
C_RULE = QColor("#C9D0D6")
C_HAIR = QColor("#E4E9ED")
# Accento: Cyber Teal di SAFE21, lo stesso dell'interfaccia del plugin, così
# i fogli stampati sono in sintonia con le finestre (fascia superiore, titoli,
# etichette di sezione). C_ACC = tinta piena, C_ACC_D = versione scura per il
# testo su fondo chiaro.
C_ACC = QColor("#0D9488")
C_ACC_D = QColor("#0F6E56")
# Rosso d'allerta allineato a quello del plugin.
C_ALERT = QColor("#B4232A")
C_BLACK = QColor("#000000")
C_WHITE = QColor("#FFFFFF")


class Sheet:
    """Contesto di disegno. Un'istanza per pagina/documento."""

    def __init__(self, painter, dpi):
        self.p = painter
        self.dpi = float(dpi)

    # ------------------------------------------------------------ unità --
    def mm(self, v):
        return v / 25.4 * self.dpi

    def to_mm(self, dots):
        return dots / self.dpi * 25.4

    def font(self, size=9.0, bold=False, mono=False):
        f = QFont("Courier New" if mono else "Helvetica")
        f.setStyleHint(QFont.StyleHint.Monospace if mono
                       else QFont.StyleHint.SansSerif)
        f.setPointSizeF(size)
        f.setBold(bold)
        return f

    def metrics(self, font):
        """Metriche NEL dispositivo corrente: è il punto che prima era rotto."""
        return QFontMetricsF(font, self.p.device())

    def line_h(self, font, leading=1.18):
        return self.to_mm(self.metrics(font).height()) * leading

    # ------------------------------------------------------------- testo --
    def text(self, x, y, s, color=C_BODY, font=None, **kw):
        """Disegna una riga. y = bordo superiore della riga, in mm."""
        f = font or self.font(**kw)
        fm = self.metrics(f)
        self.p.setFont(f)
        self.p.setPen(QPen(color))
        self.p.drawText(QPointF(self.mm(x), self.mm(y) + fm.ascent()), s)
        return y + self.to_mm(fm.height())

    def centred(self, cx, y, s, color=C_BODY, font=None, **kw):
        f = font or self.font(**kw)
        fm = self.metrics(f)
        self.p.setFont(f)
        self.p.setPen(QPen(color))
        w = fm.horizontalAdvance(s)
        self.p.drawText(QPointF(self.mm(cx) - w / 2,
                                self.mm(y) + fm.ascent()), s)
        return y + self.to_mm(fm.height())

    def wrapped(self, x, y, w, s, color=C_BODY, font=None,
                leading=1.18, anywhere=False, **kw):
        """Testo a capo dentro w mm. Ritorna la y sotto l'ultima riga."""
        f = font or self.font(**kw)
        fm = self.metrics(f)
        self.p.setFont(f)
        self.p.setPen(QPen(color))
        maxw = self.mm(w)
        lh = self.to_mm(fm.height()) * leading

        units = list(s) if anywhere else s.split(" ")
        join = "" if anywhere else " "
        line, yy = "", y
        for u in units:
            trial = (line + join + u) if line else u
            if line and fm.horizontalAdvance(trial) > maxw:
                self.p.drawText(QPointF(self.mm(x), self.mm(yy) + fm.ascent()),
                                line)
                yy += lh
                line = u
            else:
                line = trial
        if line:
            self.p.drawText(QPointF(self.mm(x), self.mm(yy) + fm.ascent()),
                            line)
            yy += lh
        return yy

    def measure(self, w, s, font=None, leading=1.18, anywhere=False, **kw):
        """Altezza in mm che occuperebbe wrapped(), senza disegnare."""
        f = font or self.font(**kw)
        fm = self.metrics(f)
        maxw = self.mm(w)
        lh = self.to_mm(fm.height()) * leading
        units = list(s) if anywhere else s.split(" ")
        join = "" if anywhere else " "
        line, n = "", 0
        for u in units:
            trial = (line + join + u) if line else u
            if line and fm.horizontalAdvance(trial) > maxw:
                n += 1
                line = u
            else:
                line = trial
        if line:
            n += 1
        return n * lh

    # ----------------------------------------------------------- grafica --
    def fill(self, x, y, w, h, color):
        self.p.setPen(Qt.PenStyle.NoPen)
        self.p.setBrush(QBrush(color))
        self.p.drawRect(QRectF(self.mm(x), self.mm(y), self.mm(w), self.mm(h)))

    def box(self, x, y, w, h, color=C_RULE, width=0.35):
        pen = QPen(color)
        pen.setWidthF(self.mm(width))
        self.p.setPen(pen)
        self.p.setBrush(Qt.BrushStyle.NoBrush)
        self.p.drawRect(QRectF(self.mm(x), self.mm(y), self.mm(w), self.mm(h)))

    def rule(self, x1, y, x2, color=C_RULE, width=0.3):
        pen = QPen(color)
        pen.setWidthF(self.mm(width))
        self.p.setPen(pen)
        self.p.drawLine(QPointF(self.mm(x1), self.mm(y)),
                        QPointF(self.mm(x2), self.mm(y)))

    def qr(self, data, x, y, size):
        img = qr_image(data)
        if img is None:
            self.box(x, y, size, size, C_RULE)
            self.centred(x + size / 2, y + size / 2 - 2, "QR n/d",
                         C_MUTED, size=6)
            return
        self.p.drawImage(QRectF(self.mm(x), self.mm(y),
                                self.mm(size), self.mm(size)), img)

    def fold_marks(self):
        # Le tacche laterali stanno a 3 mm dai bordi: se arrivassero fino al
        # bordo del foglio finirebbero nel margine morto che quasi tutte le
        # stampanti non stampano, ed è il motivo per cui prima si vedevano
        # solo a sinistra. Tenendole simmetriche e dentro l'area stampabile
        # compaiono su entrambi i lati.
        edge = 3.0
        tick = 8.0
        for y in (FOLD1, FOLD2):
            self.rule(edge, y, edge + tick, C_MUTED, 0.4)
            self.rule(PAGE_W - edge - tick, y, PAGE_W - edge, C_MUTED, 0.4)
            x = 15.0
            while x <= PAGE_W - 15:
                self.rule(x, y, x + 2.5, C_HAIR, 0.3)
                x += 6.0


def qr_image(data, scale=6):
    try:
        import qrcode
    except Exception:
        return None
    try:
        qr = qrcode.QRCode(border=1,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(data)
        qr.make(fit=True)
        m = qr.get_matrix()
        n = len(m)
        img = QImage(n * scale, n * scale, QImage.Format.Format_RGB32)
        img.fill(C_WHITE)
        black = C_BLACK.rgb()
        for yy in range(n):
            row = m[yy]
            for xx in range(n):
                if row[xx]:
                    for dy in range(scale):
                        for dx in range(scale):
                            img.setPixel(xx * scale + dx, yy * scale + dy,
                                         black)
        return img
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  Blocchi comuni
# --------------------------------------------------------------------------- #

EXPLORER = "mempool.space"


# Icona di SAFE21, in alto a sinistra sui fogli dei beneficiari: sono
# documenti che qualcuno ritroverà fra anni, e il marchio dice a colpo
# d'occhio chi li ha preparati. Sta nello spazio bianco a sinistra del
# titolo, che è centrato: non si tocca nulla d'altro. (Fino alla 1.x qui
# c'era il logo del plugin di eredità; dalla 2.0 Easy Heirs non ha più
# legami con quel plugin.)
HEAD_LOGO_FILE = "safe21.png"
HEAD_LOGO_W = 20.0       # mm; l'icona è quadrata
HEAD_LOGO_Y = 1.5
HEAD_BAR_GAP = 4.0       # stacco fra il logo e l'inizio della banda verde


def _header(s, title, name, subtitle=""):
    """Testata: icona SAFE21 a sinistra, titolo e nome centrati.

    La banda verde non parte dal bordo del foglio ma DOPO il logo: così il
    marchio sta nel suo spazio bianco invece di sembrare appiccicato alla
    banda. Se il logo non si carica la banda riprende l'intera larghezza,
    perché un rientro senza nulla dentro sembrerebbe un errore di stampa.
    """
    logo_bottom = _draw_image(s, HEAD_LOGO_FILE, MARGIN, HEAD_LOGO_Y, HEAD_LOGO_W)
    bar_x = 0.0 if logo_bottom == HEAD_LOGO_Y else MARGIN + HEAD_LOGO_W + HEAD_BAR_GAP
    # A destra la banda finisce dove finiscono le righe del foglio, non al
    # bordo della carta: allineata alle linee sotto sembra parte della stessa
    # griglia, mentre arrivando al taglio sembrava un fondino a sé.
    s.fill(bar_x, 0, PAGE_W - MARGIN - bar_x, 3.5, C_ACC)
    s.centred(PAGE_W / 2, 9.5, title, C_ACC_D, size=7.5, bold=True)
    y = s.centred(PAGE_W / 2, 15, name, C_INK, size=19, bold=True)
    if subtitle:
        y = s.centred(PAGE_W / 2, y + 1.5, subtitle, C_MUTED, size=8)
    # Il logo è più alto del blocco di testo: chi viene dopo deve saperlo,
    # altrimenti la prima riga di contenuto gli finisce sopra.
    return max(y + 3, logo_bottom + 2.5)


def _address_block(s, y, address, xpub=""):
    """Due blocchi impilati, separati da una linea.

    Indirizzo di ricezione: QR a SINISTRA, etichetta e valore a destra.

    Chiave pubblica (zpub): QR a DESTRA e più grande (25% in più), con
    etichetta e valore a SINISTRA. È il QR che il beneficiario inquadra per
    ricreare il portafoglio di sola lettura, quindi lo rendiamo il più
    comodo da leggere della pagina.

    Tenere l'etichetta dentro la colonna di testo invece che a tutta pagina
    fa guadagnare spazio verticale e permette al valore un corpo più grande.
    """
    qs = 24.0            # lato del QR dell'indirizzo
    qs_big = qs * 1.25   # QR della chiave pubblica: 25% più grande (30 mm)
    gap = 5.0

    def block_qr_left(y, label, value, max_lines, size_max, size_min, bold):
        """QR a sinistra, testo a destra."""
        tx = MARGIN + qs + gap
        tw = PAGE_W - MARGIN - tx
        s.qr(value, MARGIN, y, qs)
        s.text(tx, y + 1.5, label, C_ACC_D, size=7.5, bold=True)
        f = _fit_lines(s, value, tw, max_lines, size_max, size_min, bold)
        s.wrapped(tx, y + 7.5, tw, value,
                  C_INK if bold else C_BODY, font=f, anywhere=True)
        return y + qs + 3

    def block_qr_right(y, label, value, max_lines, size_max, size_min, bold):
        """Testo a sinistra, QR (più grande) a destra."""
        qx = PAGE_W - MARGIN - qs_big
        tw = qx - gap - MARGIN
        s.qr(value, qx, y, qs_big)
        s.text(MARGIN, y + 1.5, label, C_ACC_D, size=7.5, bold=True)
        f = _fit_lines(s, value, tw, max_lines, size_max, size_min, bold)
        s.wrapped(MARGIN, y + 7.5, tw, value,
                  C_INK if bold else C_BODY, font=f, anywhere=True)
        return y + qs_big + 3

    y = block_qr_left(y, "INDIRIZZO DI RICEZIONE", address, 1, 13.0, 7.5, True)
    if not xpub:
        return y

    s.rule(MARGIN, y, PAGE_W - MARGIN, C_HAIR, 0.4)
    y += 3.5
    y = block_qr_right(y, "CHIAVE PUBBLICA \u2014 PORTAFOGLIO DI SOLA LETTURA",
                       xpub, 2, 13.0, 6.5, False)
    return y


def _fit_lines(s, text, w_mm, max_lines, size_max, size_min, bold=False):
    """Il corpo più grande che fa stare il testo in max_lines righe.

    Serve a non dover indovinare una dimensione fissa: indirizzi e chiavi
    hanno lunghezze diverse (bc1q, bc1p, xpub, zpub) e una misura scelta a
    mano andrebbe bene solo per un caso.
    """
    size = size_max
    while size > size_min:
        f = s.font(size, bold=bold, mono=True)
        fm = s.metrics(f)
        maxw = s.mm(w_mm)
        line, n = "", 1
        for ch in text:
            if fm.horizontalAdvance(line + ch) > maxw:
                n += 1
                line = ch
            else:
                line += ch
        if n <= max_lines:
            return f
        size -= 0.25
    return s.font(size_min, bold=bold, mono=True)


# --------------------------------------------------------------------------- #
#  Foglio A: beneficiario con seed generato da noi (fronte/retro, piega in 3)
# --------------------------------------------------------------------------- #

STEPS_SEED = [
    ("1.  Controlla se i fondi sono arrivati",
     f"Digita a mano l'indirizzo qui sopra su un esploratore pubblico come "
     f"{EXPLORER}. Non serve alcuna password e non espone nulla: gli "
     f"indirizzi sono pubblici per definizione."),
    ("2.  Segui l'eredità dal telefono, senza rischi",
     "Installa un portafoglio che accetti una chiave pubblica (BlueWallet, "
     "Sparrow e altri) e crea un portafoglio di SOLA LETTURA incollando la "
     "chiave qui sopra, o inquadrando il secondo QR. Vedrai arrivare i fondi "
     "senza che quel telefono possa spenderli."),
    ("3.  Quando sarai pronto, prendi possesso dei fondi",
     "Apri l'ultimo terzo di questo foglio: contiene le dodici parole di "
     "recupero. Servono solo in quel momento, non prima."),
]


def _protection_band(s):
    """Banda scura sull'ultimo terzo del RETRO, cioè esattamente dietro
    le parole stampate sul fronte.

    Serve a impedire che le parole si leggano in controluce a foglio
    piegato. Non è nero pieno: sopra il fondo scuro spargiamo migliaia di
    puntini di grigi diversi, perché una tinta uniforme lascerebbe comunque
    intravedere la sagoma del testo, mentre un fondo irregolare la confonde.

    Condivisa fra il retro dell'erede e quello del paper wallet.
    """
    # banda di protezione sull'ultimo terzo, dietro le parole del fronte
    s.fill(0, FOLD2, PAGE_W, PAGE_H - FOLD2, C_BLACK)
    rnd = random.Random()
    s.p.setPen(Qt.PenStyle.NoPen)
    top, h, wd = s.mm(FOLD2), s.mm(PAGE_H - FOLD2), s.mm(PAGE_W)
    dot = s.mm(0.45)
    for _ in range(3200):
        g = rnd.randint(12, 92)
        s.p.setBrush(QBrush(QColor(g, g, g)))
        s.p.drawRect(QRectF(rnd.uniform(0, wd), top + rnd.uniform(0, h),
                            dot, dot))
    s.centred(PAGE_W / 2, (FOLD2 + PAGE_H) / 2 - 2,
              "AREA DI PROTEZIONE  \u2014  copre le parole in controluce",
              QColor("#3C3C3C"), size=8, bold=True)


# Corpo delle parole di recupero: 15.75 = 10.5 + 50%, come chiesto dal
# titolare. Sono il dato più importante del foglio e vanno lette senza
# sforzo, magari da una persona anziana e in un momento difficile.
WORDS_SIZE = 15.75

# Numero progressivo accanto a ogni parola: 13 = 6.5 x 2, come chiesto dal
# titolare. Serve a ricopiare la frase nell'ordine giusto.
NUM_SIZE = 13.0

# Sotto questa quota molte stampanti non stampano affatto: è il margine di
# sicurezza in fondo al foglio, non un margine estetico.
BOTTOM_SAFE = 6.0


def _num_gutter(s, n_words):
    """Larghezza della colonnina dei numeri, a sinistra di ogni casella.

    I numeri stanno FUORI dal riquadro: dentro rubavano spazio alla parola e,
    con il corpo raddoppiato, le finivano quasi addosso. La colonnina si
    dimensiona sul numero più largo che dovrà contenere (24 con una frase
    lunga, 12 con quella corta), misurato e non indovinato.
    """
    widest = str(max(n_words, 1))
    w = s.to_mm(s.metrics(s.font(NUM_SIZE, bold=False)).horizontalAdvance(widest))
    return w + 2.6          # il numero, più l'aria fra numero e riquadro


def _words_grid(s, words, top, bottom_limit=None, size=WORDS_SIZE):
    """Griglia delle parole di recupero. Ritorna la y sotto l'ultima riga.

    Condivisa fra il foglio dell'erede e il paper wallet: è la parte più
    delicata della stampa, quindi ha senso che esista in un solo posto.

    Ogni parola sta in un riquadro, con il suo numero d'ordine fuori a
    sinistra, allineato a destra contro il riquadro: così le cifre formano
    una colonna leggibile e il riquadro resta tutto per la parola.

    12 parole -> 3 colonne, caselle larghe e molto leggibili. 24 parole -> 4
    colonne: con 3 servirebbero 8 righe e si finirebbe sotto il bordo
    stampabile.

    L'altezza delle caselle NON è un numero fisso: si ricava dalle metriche
    del font, così cambiando il corpo le caselle crescono con le parole
    invece di tagliarle. Se ``bottom_limit`` è indicato e la griglia lo
    supererebbe, il corpo viene ridotto quel tanto che basta per rientrare:
    meglio parole un filo più piccole che parole stampate fuori dal foglio.
    """
    cols = 4 if len(words) > 12 else 3
    rows = (len(words) + cols - 1) // cols
    bw = (PAGE_W - 2 * MARGIN) / cols

    gutter = _num_gutter(s, len(words))
    box_w = bw - gutter - 2          # il riquadro, stretto per fare posto
    pad_x = 3.0                      # respiro fra bordo del riquadro e parola

    def box_height(sz):
        """Riga di testo più il respiro sopra e sotto."""
        return s.to_mm(s.metrics(s.font(sz, bold=True, mono=True)).height()) + 4.8

    bh = box_height(size)
    while bottom_limit is not None and size > 8.0 and top + rows * bh > bottom_limit:
        size -= 0.25
        bh = box_height(size)

    # Non deve sforare nemmeno in LARGHEZZA: le parole BIP39 arrivano a otto
    # lettere e il riquadro ora è più stretto. Il controllo è sulla parola
    # più lunga che stiamo davvero stampando, non su un caso ipotetico.
    longest = max(words, key=len) if words else ""
    while size > 8.0 and longest:
        room = box_w - 2 * pad_x
        if s.to_mm(s.metrics(s.font(size, bold=True,
                                    mono=True)).horizontalAdvance(longest)) <= room:
            break
        size -= 0.25
        bh = box_height(size)

    f = s.font(size, bold=True, mono=True)
    lh = s.to_mm(s.metrics(f).height())
    pad = max(1.6, (bh - 2 - lh) / 2)      # centra la parola nella casella

    fnum = s.font(NUM_SIZE, bold=False)
    lnum = s.to_mm(s.metrics(fnum).height())
    # Numero e parola sulla stessa linea ottica, pur avendo corpi diversi.
    num_dy = pad + (lh - lnum) / 2

    for i, word in enumerate(words):
        r, c = divmod(i, cols)
        bx = MARGIN + c * bw
        byy = top + r * bh
        s.box(bx + gutter, byy, box_w, bh - 2, C_RULE, 0.35)
        # Numero allineato a DESTRA contro il riquadro: unità e decine
        # restano incolonnate invece di ballare a seconda delle cifre.
        label = str(i + 1)
        nw = s.to_mm(s.metrics(fnum).horizontalAdvance(label))
        s.text(bx + gutter - 2.0 - nw, byy + num_dy, label, C_MUTED, font=fnum)
        # Parole in verde scuro invece che in nero: restano ben leggibili ma
        # trasparono molto meno se qualcuno illumina il foglio piegato da
        # dietro con una luce forte (il verde è meno denso del nero).
        s.text(bx + gutter + pad_x, byy + pad, word, C_ACC_D, font=f)
    return top + rows * bh


def _words_tail_limit(s, texts):
    """Fin dove può arrivare la griglia, dati i testi che la seguono.

    Li misuriamo PRIMA di disegnare: così la griglia sa quanto spazio deve
    lasciare e si adatta da sola, invece di scoprire troppo tardi che il testo
    finale non ci sta più.

    ``texts`` è una lista di ``(testo, corpo)``.
    """
    w = PAGE_W - 2 * MARGIN
    need = 3.0
    for txt, sz in texts:
        need += s.measure(w, txt, size=sz, bold=True) + 1
    return PAGE_H - BOTTOM_SAFE - need


def render_seed_front(s, d):
    y = _header(s, "EREDITÀ IN BITCOIN  \u00b7  DOCUMENTO PER IL BENEFICIARIO",
                d["name"],
                f"custodito da: {d['guardian']}" if d.get("guardian") else "")
    s.rule(MARGIN, y, PAGE_W - MARGIN, C_RULE, 0.4)
    y += 4

    y = _address_block(s, y, d["address"], d.get("xpub", ""))

    # ---- secondo terzo: istruzioni ----
    y = max(y, FOLD1 + 7)
    y = s.text(MARGIN, y, "COME CONTROLLARE E COME RICEVERE",
               C_ACC_D, size=10.5, bold=True) + 3
    w = PAGE_W - 2 * MARGIN
    for head, body in STEPS_SEED:
        y = s.text(MARGIN, y, head, C_INK, size=8.2, bold=True) + 0.8
        y = s.wrapped(MARGIN + 4, y, w - 4, body, C_BODY, size=7.8) + 2.2

    # Il riquadro anti-truffa è ancorato sopra la piega: calcoliamo prima
    # dove inizia, così il blocco data/hash sa quanto spazio ha davvero.
    warn = ("Notai, banche, avvocati, assistenza tecnica o presunti servizi di "
            "recupero non hanno mai bisogno delle parole di recupero. Chiunque "
            "te le chieda sta tentando una truffa. Si digitano solo dentro un "
            "portafoglio installato da te.")
    hw = s.measure(w - 6, warn, size=7.4) + 9
    by = FOLD2 - hw - 4


    s.box(MARGIN, by, w, hw, C_ALERT, 0.5)
    s.text(MARGIN + 3, by + 2, "NESSUNO DEVE MAI CHIEDERTI LE PAROLE",
           C_ALERT, size=7.8, bold=True)
    s.wrapped(MARGIN + 3, by + 6.5, w - 6, warn, C_BODY, size=7.4)

    # ---- terzo terzo: le parole ----
    s.text(MARGIN, FOLD2 + 4, "PAROLE DI RECUPERO  \u2014  DA TENERE SEGRETE",
           C_ALERT, size=10.5, bold=True)
    # Dicitura del formato accanto alle parole: chi ritrova il foglio fra anni
    # deve capire in tre secondi quali istruzioni valgono, senza dedurlo.
    kind_tag = ("SEED ELECTRUM" if d.get("seed_kind") == "electrum"
                else "SEED BIP39")
    fk = s.font(8, bold=True)
    kw_ = s.to_mm(s.metrics(fk).horizontalAdvance(kind_tag))
    s.text(PAGE_W - MARGIN - kw_, FOLD2 + 5, kind_tag, C_ACC_D, font=fk)
    words = d["seed"].split()
    # Va stampato il percorso dell'ACCOUNT (m/84'/0'/0'), non quello del
    # primo indirizzo (m/84'/0'/0'/0/0): è il primo che i wallet chiedono
    # nel campo "derivazione". Scrivere il secondo porterebbe a un wallet
    # diverso e vuoto.
    acct = d.get("account_derivation") or "m/84'/0'/0'"
    t_warn = ("Chiunque legga queste parole può prendere i fondi. "
              "Piega il foglio in tre lungo i segni e tienilo chiuso.")
    t_note = ("Seed in formato BIP39 standard: funziona in qualunque wallet "
              "compatibile, non solo in Electrum. Percorso di derivazione da "
              f"inserire: {acct}. " + _instructions_where(d))
    limit = _words_tail_limit(s, [(t_warn, 7.4), (t_note, 10.2)])

    yy = _words_grid(s, words, FOLD2 + 12, bottom_limit=limit) + 3
    yy = s.wrapped(MARGIN, yy, PAGE_W - 2 * MARGIN, t_warn,
                   C_ALERT, size=7.4, bold=True) + 1
    s.wrapped(MARGIN, yy, PAGE_W - 2 * MARGIN, t_note,
              C_INK, size=10.2, bold=True)

    s.fold_marks()


SEC_A = [
    ("Va bene qualunque wallet Bitcoin affidabile",
     "Queste dodici parole seguono lo standard BIP39, non sono legate a un "
     "singolo programma. Funzionano in Electrum, Sparrow, BlueWallet e nei "
     "dispositivi come Ledger, Trezor, Coldcard, oltre che in quasi ogni "
     "altro wallet Bitcoin. Nella maggior parte di questi la procedura è "
     "brevissima: scegli \"ripristina da seed\", digiti le parole, hai "
     "finito."),
    ("Come capire se un programma è affidabile",
     "Quei nomi sono quelli noti oggi e potrebbero cambiare: conta il "
     "criterio più del nome. Dev'essere open source, con anni di storia e "
     "molti utenti, scaricato SEMPRE dal sito ufficiale digitando "
     "l'indirizzo a mano. Mai da link ricevuti per messaggio o e-mail, e "
     "mai dai primi risultati di un motore di ricerca: le copie fatte per "
     "rubare i fondi si presentano bene e sono la truffa più comune."),
    ("Fatti aiutare, ma non consegnare le parole",
     "Puoi farti assistere da una persona di fiducia competente: può "
     "installare il programma e spiegarti. Quello che non deve mai "
     "succedere è che le parole finiscano in mano sua, in una foto o su "
     "un sito."),
]

SEC_B = [
    ("Attiva l'opzione BIP39",
     "Crea un nuovo wallet, scegli \"Standard wallet\" e poi \"I already "
     "have a seed\". Nella schermata dove si scrivono le parole clicca "
     "\"Options\" e spunta \"BIP39 seed\". Senza quella spunta Electrum "
     "rifiuterà le parole dicendo che il seed non è valido: non è vero, "
     "manca solo l'opzione."),
    ("L'avviso che compare è normale",
     "Spuntando quella casella Electrum mostra un messaggio: dice che i seed "
     "BIP39 si possono importare ma che Electrum non li genera, che non "
     "contengono un numero di versione e che il supporto futuro non è "
     "garantito. Non riguarda il tuo seed e non significa che ci sia un "
     "problema. Prosegui."),
    ("Percorso di derivazione",
     "Digita le parole nell'ordine esatto, in minuscolo, separate da uno "
     "spazio. Quando Electrum chiede il percorso di derivazione inserisci "
     "quello corto stampato sul fronte, del tipo m/84'/0'/0'. Non aggiungere "
     "altri numeri in fondo."),
]


# Aria sotto la piega prima di ricominciare a scrivere: la riga di piega è
# anche il punto in cui la carta si incurva, e un testo che le sta appiccicato
# si legge male.
FOLD_GAP = 5.0


def _start_below_fold(y, fold=FOLD1):
    """L'inizio del prossimo blocco, mai a cavallo della piega.

    A foglio piegato ogni terzo è una facciata a sé: un paragrafo tagliato
    in due dalla piega risulta illeggibile proprio nel mezzo. Meglio un po'
    di bianco sopra la piega e il blocco che riparte intero sotto.
    """
    return max(y, fold + FOLD_GAP)


def _section(s, y, w, letter, title, items, color):
    y = s.text(MARGIN, y, f"{letter}.   {title}", color, size=9.5,
               bold=True) + 2
    for head, body in items:
        y = s.text(MARGIN + 4, y, head, C_INK, size=8.0, bold=True) + 0.6
        y = s.wrapped(MARGIN + 8, y, w - 8, body, C_BODY, size=7.5) + 1.8
    return y + 1.2


SEPARATE_HEAD = ("FOGLIO DELLE ISTRUZIONI  \u2014  DA TENERE INSIEME AL "
                 "FOGLIO CON LE PAROLE DI RECUPERO")


def _instructions_where(d):
    """La frase del fronte su dove sono le istruzioni complete.

    ``d["instructions"]`` arriva dalla scelta di stampa (qt.SidesDialog):
    "back" (fronte e retro, predefinito), "separate" (foglio a parte) o
    "none" (solo fronte, istruzioni non stampate).
    """
    where = (d or {}).get("instructions", "back")
    if where == "separate":
        return "Istruzioni complete sul foglio delle istruzioni a parte."
    if where == "none":
        return ("Le istruzioni complete non sono state stampate: ristampa con "
                "fronte e retro, o con il foglio delle istruzioni a parte.")
    return "Istruzioni complete sul RETRO di questo foglio."


def render_seed_back(s, has_seed=True, separate=False):
    """Retro: istruzioni complete di recupero, più la banda di protezione.

    Ordine voluto: prima la libertà di scelta del programma (con il
    criterio per non cadere in una copia truffaldina), poi il caso
    particolare di Electrum, infine la verifica dell'indirizzo, che vale con
    qualunque wallet e non deve sembrare un dettaglio della procedura
    Electrum.

    ``separate=True``: lo stesso testo su un foglio a parte (stampa "solo
    fronte", titolare 2026-11-07): niente banda di protezione, che serve solo
    dietro alle parole, niente segni di piega, e in alto la scritta che dice
    di tenerlo insieme al foglio con le parole.
    """
    head = (SEPARATE_HEAD if separate else
            "STAMPA FRONTE/RETRO  \u2014  GIRO SUL LATO LUNGO   "
            "\u00b7   PIEGA IN TRE LUNGO I SEGNI")
    y = s.centred(PAGE_W / 2, 11, head, C_MUTED, size=8, bold=True) + 3.5

    w = PAGE_W - 2 * MARGIN
    y = s.text(MARGIN, y, "COME RECUPERARE I FONDI, QUANDO SARÀ IL MOMENTO",
               C_ACC_D, size=12, bold=True) + 1.5
    y = s.wrapped(MARGIN, y, w,
                  ("Da seguire solo quando avrai davanti il foglio con le "
                   "parole di recupero. Fino ad allora non serve fare nulla."
                   if separate else
                   "Da seguire solo quando avrai aperto l'ultimo terzo del "
                   "foglio e avrai davanti le parole di recupero. Fino ad "
                   "allora non serve fare nulla."), C_MUTED, size=7.6) + 3

    y = _section(s, y, w, "A", "CON QUALE PROGRAMMA", SEC_A, C_ACC_D)
    y = _section(s, _start_below_fold(y), w, "B", "SE SCEGLI ELECTRUM",
                 SEC_B, C_ACC_D)

    # --- C: vale per qualunque wallet, quindi sta fuori dalla sezione B ---
    y = s.text(MARGIN, y, "C.   VERIFICA FINALE  -  CON QUALUNQUE PROGRAMMA",
               C_ALERT, size=9.5, bold=True) + 2
    y = s.text(MARGIN + 4, y, "Confronta il primo indirizzo", C_INK,
               size=8.0, bold=True) + 0.6
    y = s.wrapped(MARGIN + 8, y, w - 8,
                  "A wallet creato, apri la sezione \"Ricevi\" o "
                  "\"Indirizzi\" e confronta il primo indirizzo con quello "
                  + ("stampato sul foglio con le parole di recupero. "
                     if separate else "stampato sul fronte di questo foglio. ")
                  + "Devono essere identici, carattere per carattere.",
                  C_BODY, size=7.6) + 2.2
    y = s.text(MARGIN + 4, y, "Se NON coincidono", C_ALERT,
                   size=8.0, bold=True) + 0.6
    y = s.wrapped(MARGIN + 8, y, w - 8,
                  "Hai sbagliato una parola o il percorso di derivazione. "
                  "Attenzione: il controllo automatico delle parole non "
                  "intercetta tutti gli errori, quindi il programma potrebbe "
                  "accettarle e crearti comunque un portafoglio: sarebbe "
                  "però un portafoglio diverso e vuoto, e potresti credere "
                  "di aver perso l'eredità. Non è così: è proprio per "
                  "questo che devi confrontare l'indirizzo. Ricontrolla "
                  "parola per parola e ripeti.",
                  C_BODY, size=7.5)

    # Guardia: sotto FOLD2 arriva la banda nera, che coprirebbe il testo
    # rendendolo invisibile in stampa. Meglio accorgersene qui che su carta.
    if has_seed and y > FOLD2:
        import logging
        logging.getLogger(__name__).error(
            "istruzioni del retro oltre la piega (%.1f mm > %.1f): "
            "verrebbero coperte dalla banda di protezione", y, FOLD2)

    if separate:
        return
    if not has_seed:
        s.fold_marks()
        return

    _protection_band(s)
    s.fold_marks()


# --------------------------------------------------------------------------- #
#  Foglio B: beneficiario che ha fornito il proprio indirizzo (una pagina)
# --------------------------------------------------------------------------- #

STEPS_GIVEN = [
    ("1.  Controlla quando vuoi se i fondi sono arrivati",
     f"Digita a mano l'indirizzo qui sopra su un esploratore pubblico come "
     f"{EXPLORER}. Non serve alcuna password: gli indirizzi sono pubblici e "
     f"la consultazione non comporta rischi."),
    ("2.  Verifica che l'indirizzo sia davvero tuo",
     "Controlla che compaia tra quelli del tuo portafoglio. Se non lo "
     "riconosci, non ignorare la cosa: contatta subito chi ti ha consegnato "
     "questo documento."),
    ("3.  Non devi fare nulla per ricevere",
     "I fondi arriveranno da soli all'indirizzo, in un momento futuro. Un "
     "indirizzo Bitcoin non scade e resta valido per sempre."),
    ("4.  Le tue chiavi restano tue",
     "Chi ha predisposto questa eredità non conosce le tue parole di "
     "recupero e non può toccare i tuoi fondi. Custodiscile come sempre: "
     "sono l'unica cosa che serve per spendere."),
]


def render_given(s, d):
    y = _header(s, "EREDITÀ IN BITCOIN  \u00b7  DOCUMENTO PER IL BENEFICIARIO",
                d["name"], "Indirizzo fornito dal beneficiario")
    s.rule(MARGIN, y, PAGE_W - MARGIN, C_RULE, 0.4)
    y += 5

    y = _address_block(s, y, d["address"], "")
    y += 3
    w = PAGE_W - 2 * MARGIN

    y = s.text(MARGIN, y, "COSA SAPERE", C_ACC_D, size=10.5, bold=True) + 3
    for head, body in STEPS_GIVEN:
        y = s.text(MARGIN, y, head, C_INK, size=8.2, bold=True) + 0.8
        y = s.wrapped(MARGIN + 4, y, w - 4, body, C_BODY, size=7.8) + 2.4

    warn = ("Nessuno, con nessuna qualifica, ha motivo di chiederti le tue "
            "parole di recupero in relazione a questa eredità. Chiunque lo "
            "faccia sta tentando una truffa. Diffida anche dei link ricevuti "
            "via e-mail o messaggio: digita sempre gli indirizzi a mano.")
    hw = s.measure(w - 6, warn, size=7.4) + 9
    y += 2
    s.box(MARGIN, y, w, hw, C_ALERT, 0.5)
    s.text(MARGIN + 3, y + 2, "ATTENZIONE ALLE TRUFFE", C_ALERT,
           size=7.8, bold=True)
    s.wrapped(MARGIN + 3, y + 6.5, w - 6, warn, C_BODY, size=7.4)

    s.text(MARGIN, PAGE_H - 14,
           "Nessuna parola di recupero è contenuta in questo foglio.",
           C_MUTED, size=7)
    s.text(MARGIN, PAGE_H - 10.5, "Easy Heirs \u00b7 SAFE21",
           C_MUTED, size=7)


def render_blank_back(s):
    """Retro deliberatamente vuoto per i documenti di UNA sola pagina
    (gli eredi che hanno fornito solo l'indirizzo, senza seed).

    Serve a dare a OGNI documento un numero PARI di pagine. In stampa
    fronte/retro il driver accoppia le pagine a due a due sullo stesso foglio
    fisico: un documento di una sola pagina sfaserebbe l'accoppiamento di
    tutti i documenti successivi (il fronte di uno finirebbe sul retro di un
    altro). Con questo retro ogni scheda occupa un foglio intero e
    l'allineamento resta corretto, anche stampando prima su PDF e poi in
    fronte/retro.
    """
    s.centred(PAGE_W / 2, PAGE_H / 2 - 2,
              "Pagina lasciata intenzionalmente vuota \u2014 serve a mantenere "
              "allineata la stampa fronte/retro",
              C_MUTED, size=9, bold=True)
    s.text(MARGIN, PAGE_H - 10.5, "Easy Heirs \u00b7 SAFE21",
           C_MUTED, size=7)


# --------------------------------------------------------------------------- #
#  Riepilogo: TUTTI i beneficiari, di entrambi i tipi
# --------------------------------------------------------------------------- #

def render_report(s, wallet_name, rows, page=1, per_page=9):
    _header(s, "RIEPILOGO  \u00b7  COPIA RISERVATA ALL'ESECUTORE",
            "Elenco dei beneficiari",
            f"{wallet_name}  \u00b7  {len(rows)} beneficiari")
    y = 32
    s.rule(MARGIN, y, PAGE_W - MARGIN, C_RULE, 0.4)
    y += 4

    w = PAGE_W - 2 * MARGIN
    note = ("Solo nomi e indirizzi pubblici: nessuna parola di recupero, "
            "nessuna chiave privata, nessun importo. Chi lo legge non può "
            "accedere ai fondi.")
    hn = s.measure(w - 6, note, size=7.4) + 9
    s.box(MARGIN, y, w, hn, C_RULE, 0.4)
    s.text(MARGIN + 3, y + 2, "QUESTO FOGLIO NON CONTIENE SEGRETI",
           C_INK, size=7.8, bold=True)
    s.wrapped(MARGIN + 3, y + 6.5, w - 6, note, C_BODY, size=7.4)
    y += hn + 5

    # Geometria delle colonne (in mm). Le teniamo come costanti così che le
    # intestazioni e i valori di ogni riga cadano sempre sotto/sopra la stessa
    # posizione. La colonna "Tipo" è allineata a destra rispetto a un bordo
    # fisso; il QR occupa l'ultima colonna, a fine riga. Le quote non ci
    # sono: stanno solo nel plugin di eredità (2.0).
    BEN_X = MARGIN + 13       # nome + indirizzo
    TIPO_R = 178.0            # bordo destro della colonna "Tipo"
    QS = 14.3                 # lato del QR (quadrato), in mm: +30% rispetto
                              # agli 11 mm precedenti, come richiesto
    # Centro della colonna "QR": lo teniamo allineato a destra in modo che il
    # QR più grande resti dentro il margine (bordo destro ~194 mm < 195).
    QR_C = PAGE_W - MARGIN - QS / 2

    # ---- intestazioni di colonna -----------------------------------------
    hy = y
    fh = s.font(7, bold=True)
    s.text(MARGIN, hy, "BUSTA", C_MUTED, font=fh)
    s.text(BEN_X, hy, "BENEFICIARIO  \u00b7  INDIRIZZO", C_MUTED, font=fh)
    lw = s.to_mm(s.metrics(fh).horizontalAdvance("TIPO"))
    s.text(TIPO_R - lw, hy, "TIPO", C_MUTED, font=fh)
    s.centred(QR_C, hy, "QR", C_MUTED, font=fh)
    y = hy + 5
    s.rule(MARGIN, y, PAGE_W - MARGIN, C_RULE, 0.4)
    y += 4

    start = (page - 1) * per_page
    chunk = rows[start:start + per_page]

    for r in chunk:
        y_top = y

        # Colonna "Busta": il numero della busta fisica che contiene il foglio
        # di questo beneficiario (non più la posizione nell'elenco). Se manca
        # lo segnaliamo con un trattino.
        env = r.get("envelope")
        busta = str(env) if env not in (None, "", 0) else "\u2014"
        s.text(MARGIN, y_top, busta, C_INK, size=11, bold=True)

        # Nome del beneficiario.
        s.text(BEN_X, y_top, r["name"], C_INK, size=10.5, bold=True)

        # Colonna "Tipo": generato dal titolare o indirizzo fornito.
        tag = "GENERATO DA ME" if r.get("generated") else "INDIRIZZO FORNITO"
        ftag = s.font(6.8, bold=True)
        tw = s.to_mm(s.metrics(ftag).horizontalAdvance(tag))
        s.text(TIPO_R - tw, y_top + 1, tag, C_ACC_D, font=ftag)

        y += 5.4

        # Indirizzo pubblico (monospazio). Corpo 10.5: +25% rispetto agli 8.4
        # precedenti. Anche un indirizzo taproot (62 caratteri) resta entro
        # ~166 mm, quindi non tocca né la colonna QR né il margine.
        s.text(BEN_X, y, r.get("address") or "\u2014", C_INK,
               size=10.5, bold=True, mono=True)
        y += 6.0

        # Colonna "QR": QR dell'indirizzo pubblico, a fine riga. Garantiamo
        # che il blocco sia alto almeno quanto il QR, poi lo centriamo
        # verticalmente nello spazio della riga (resta dentro la riga).
        if y < y_top + QS + 0.5:
            y = y_top + QS + 0.5
        addr = r.get("address")
        if addr:
            qy = y_top + ((y - y_top) - QS) / 2
            s.qr(addr, QR_C - QS / 2, qy, QS)

        s.rule(MARGIN, y, PAGE_W - MARGIN, C_HAIR, 0.25)
        y += 3.4


    total_pages = max(1, (len(rows) + per_page - 1) // per_page)
    s.text(MARGIN, PAGE_H - 14,
           "Le parole di recupero non sono mai state salvate in un file: "
           "esistono solo sui fogli stampati e dentro questo wallet.",
           C_MUTED, size=6.8)
    s.text(MARGIN, PAGE_H - 10.5,
           f"Easy Heirs \u00b7 SAFE21   \u2014   pagina {page} di "
           f"{total_pages}", C_MUTED, size=6.8)
    return total_pages


# --------------------------------------------------------------------------- #
#  Foglio C: paper wallet (intestazione col logo SAFE21, due pagine)
# --------------------------------------------------------------------------- #

LOGO_FILE = "safe21-logo-light.png"
SITE_URL = "safe21.io"

# Immagini già caricate, per nome di file (il valore è None se il file non
# c'è o non si legge: così non si riprova a ogni pagina).
_IMAGE_CACHE = {}


def _image(filename):
    """Un'immagine del pacchetto come QImage, oppure None.

    Letta con pkgutil.get_data e non con open(): il plugin gira dentro uno ZIP
    (zipimport) e un percorso su disco semplicemente non esiste. Il ripiego su
    open() serve solo quando si lavora sui sorgenti scompattati.
    """
    if filename in _IMAGE_CACHE:
        return _IMAGE_CACHE[filename]
    data = None
    pkg = __name__.rsplit(".", 1)[0] if "." in __name__ else None
    if pkg:
        try:
            data = pkgutil.get_data(pkg, filename)
        except Exception:
            data = None
    if data is None:
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(here, filename), "rb") as fh:
                data = fh.read()
        except Exception:
            data = None
    img = None
    if data:
        candidate = QImage()
        if candidate.loadFromData(data):
            img = candidate
    _IMAGE_CACHE[filename] = img
    return img


def _logo_image():
    """Il logo SAFE21 (usato sui paper wallet)."""
    return _image(LOGO_FILE)


def _draw_image(s, filename, x, y, w_mm):
    """Disegna un'immagine larga ``w_mm`` mantenendone le proporzioni.

    Ritorna la y sotto l'immagine, oppure ``y`` se non c'era nulla da
    disegnare: chi chiama decide se quello spazio serviva ad altro.
    """
    img = _image(filename)
    if img is None or img.isNull() or not img.width():
        return y
    h_mm = w_mm * img.height() / float(img.width())
    s.p.drawImage(QRectF(s.mm(x), s.mm(y), s.mm(w_mm), s.mm(h_mm)), img)
    return y + h_mm


def _draw_logo(s, x, y, w_mm):
    """Il logo SAFE21. Ritorna la y sotto il logo.

    Se il file mancasse non lasciamo un buco: scriviamo il nome. Un foglio
    senza logo resta valido, un foglio a metà no.
    """
    below = _draw_image(s, LOGO_FILE, x, y, w_mm)
    if below == y:
        s.text(x, y, "SAFE21", C_ACC_D, size=15, bold=True)
        return y + 7.5
    return below


STEPS_PAPER = [
    ("1.  Versa i fondi quando vuoi",
     "Inquadra il QR dell'indirizzo qui sopra con il tuo portafoglio e invia "
     "l'importo che vuoi mettere da parte. Puoi farlo subito o fra anni, e "
     "puoi versare più volte sullo stesso indirizzo."),
    ("2.  Controlla il saldo senza rischi",
     "Digita l'indirizzo su un esploratore pubblico come " + EXPLORER + ", "
     "oppure importa la chiave pubblica qui sopra in un portafoglio di sola "
     "lettura. In entrambi i casi non serve alcuna parola: si guarda soltanto."),
    ("3.  Per spendere servono le parole",
     "Apri l'ultimo terzo del foglio, digita le dodici parole in un "
     "portafoglio BIP39 (Electrum, Sparrow, BlueWallet, Ledger, Trezor...) e "
     "avrai di nuovo il controllo dei fondi."),
    ("4.  Custodia",
     "Piega il foglio in tre lungo i segni e mettilo in un posto asciutto e al "
     "riparo dalla luce. La carta teme acqua, sole e fuoco: se la somma è "
     "importante, valuta una seconda copia in un altro luogo sicuro."),
]


# Sezioni del retro per un seed NATIVO ELECTRUM. Non sono una variante
# cosmetica di quelle BIP39: dicono cose opposte (lì si spunta "BIP39 seed" e
# si digita un percorso, qui non si fa né l'uno né l'altro). Stampare le
# istruzioni sbagliate manderebbe la persona su un portafoglio vuoto, quindi i
# due testi restano separati e non si mescolano mai.

SEC_A_ELECTRUM = [
    ("Per queste parole serve Electrum",
     "Sono nel formato nativo di Electrum e contengono un marcatore che "
     "Electrum riconosce. La maggior parte degli altri portafogli non le "
     "accetta: per riprendere i fondi usa Electrum. (Se un domani volessi "
     "spostarli altrove, si fa comunque: apri il portafoglio in Electrum e "
     "invii i fondi dove vuoi.)"),
    ("Scaricalo solo dal sito ufficiale",
     "Digita electrum.org a mano nella barra dell'indirizzo. Mai da link "
     "ricevuti per messaggio o e-mail, e mai dai primi risultati di un motore "
     "di ricerca: le copie fatte per rubare i fondi si presentano bene e sono "
     "la truffa più comune."),
    ("Fatti aiutare, ma non consegnare le parole",
     "Puoi farti assistere da una persona di fiducia competente: può "
     "installare il programma e spiegarti. Quello che non deve mai succedere "
     "è che le parole finiscano in mano sua, in una foto o su un sito."),
]

SEC_B_ELECTRUM = [
    ("Il ripristino è breve",
     "Apri Electrum e scegli di creare un nuovo portafoglio, poi \"Standard "
     "wallet\" e \"I already have a seed\". Digita le dodici parole "
     "nell'ordine esatto, in minuscolo, separate da uno spazio."),
    ("Non serve nessuna opzione e nessun percorso",
     "A differenza dei seed BIP39 non devi spuntare nulla in \"Options\" e "
     "non devi indicare alcun percorso di derivazione: Electrum riconosce il "
     "formato da solo e ricostruisce il portafoglio giusto. E\' il motivo per "
     "cui questo foglio e\' più difficile da sbagliare."),
    ("Se Electrum dice che il seed non è valido",
     "Non prosegui: rileggi le parole. Con questo formato Electrum sa "
     "riconoscere una frase autentica, quindi quell'avviso significa quasi "
     "sempre che una parola è stata letta o digitata male."),
]


def render_paper_front(s, d):
    """Fronte del paper wallet: intestazione con logo, indirizzo da alimentare
    e, nell'ultimo terzo, le parole di recupero."""
    s.fill(0, 0, PAGE_W, 3.5, C_ACC)

    # --- intestazione: logo a sinistra, identificativo a destra ---
    ly = _draw_logo(s, MARGIN, 7.5, 38.0)
    s.text(MARGIN, ly + 1.2, SITE_URL, C_ACC_D, size=8, bold=True)

    right = PAGE_W - MARGIN
    ftag = s.font(7.5, bold=True)
    tag = "PAPER WALLET"
    tw = s.to_mm(s.metrics(ftag).horizontalAdvance(tag))
    s.text(right - tw, 8, tag, C_ACC_D, font=ftag)

    fname = s.font(17, bold=True)
    nm = d["name"]
    nw = s.to_mm(s.metrics(fname).horizontalAdvance(nm))
    s.text(right - nw, 12, nm, C_INK, font=fname)

    # Data di creazione al centro della fascia: è l'unico dato che dice
    # QUANDO questo foglio è stato generato, e su un documento che può
    # restare in un cassetto per anni non è un dettaglio.
    created = d.get("created_str") or ""
    if created:
        s.centred(PAGE_W / 2, 13, "creato il " + created, C_MUTED,
                  size=9.5, bold=True)

    y = 26
    s.rule(MARGIN, y, PAGE_W - MARGIN, C_RULE, 0.4)
    y += 4

    y = _address_block(s, y, d["address"], d.get("xpub", ""))

    # --- secondo terzo: istruzioni ---
    y = max(y, FOLD1 + 7)
    y = s.text(MARGIN, y, "COME SI USA", C_ACC_D, size=10.5, bold=True) + 3
    w = PAGE_W - 2 * MARGIN
    for head, body in STEPS_PAPER:
        y = s.text(MARGIN, y, head, C_INK, size=8.2, bold=True) + 0.8
        y = s.wrapped(MARGIN + 4, y, w - 4, body, C_BODY, size=7.8) + 2.2

    # --- avviso, ancorato sopra la piega ---
    warn = ("Questo foglio è l'unica copia: le parole non sono salvate da "
            "nessuna parte, nemmeno nel computer che le ha generate. Prima di "
            "versare qualsiasi importo, controlla che tutte le dodici parole "
            "siano stampate e leggibili. Se il foglio si perde o si rovina, i "
            "fondi non sono più recuperabili da nessuno.")
    hw = s.measure(w - 6, warn, size=7.4) + 9
    by = FOLD2 - hw - 4
    s.box(MARGIN, by, w, hw, C_ALERT, 0.5)
    s.text(MARGIN + 3, by + 2, "NON ESISTE UNA SECONDA COPIA",
           C_ALERT, size=7.8, bold=True)
    s.wrapped(MARGIN + 3, by + 6.5, w - 6, warn, C_BODY, size=7.4)

    # --- terzo terzo: le parole ---
    s.text(MARGIN, FOLD2 + 4, "PAROLE DI RECUPERO  —  DA TENERE SEGRETE",
           C_ALERT, size=10.5, bold=True)
    # Dicitura del formato accanto alle parole: chi ritrova il foglio fra
    # anni deve capire in tre secondi quali istruzioni valgono.
    kind_tag = ("SEED ELECTRUM" if d.get("seed_kind") == "electrum"
                else "SEED BIP39")
    fk = s.font(8, bold=True)
    kw_ = s.to_mm(s.metrics(fk).horizontalAdvance(kind_tag))
    s.text(PAGE_W - MARGIN - kw_, FOLD2 + 5, kind_tag, C_ACC_D, font=fk)
    acct = d.get("account_derivation") or "m/84'/0'/0'"
    t_warn = ("Chiunque legga queste parole può prendere i fondi. "
              "Piega il foglio in tre lungo i segni e tienilo chiuso.")
    if d.get("seed_kind") == "electrum":
        t_note = ("Seed in formato nativo Electrum: si ripristina digitando le "
                  "parole in Electrum, SENZA spuntare opzioni e SENZA indicare "
                  "alcun percorso di derivazione. Altri portafogli in genere "
                  "non lo accettano. " + _instructions_where(d))
    else:
        t_note = ("Seed in formato BIP39 standard: funziona in qualunque wallet "
                  "compatibile, non solo in Electrum. Percorso di derivazione da "
                  "inserire: " + acct + ". " + _instructions_where(d))
    limit = _words_tail_limit(s, [(t_warn, 7.4), (t_note, 10.2)])

    yy = _words_grid(s, d["seed"].split(), FOLD2 + 12, bottom_limit=limit) + 3
    yy = s.wrapped(MARGIN, yy, PAGE_W - 2 * MARGIN, t_warn,
                   C_ALERT, size=7.4, bold=True) + 1
    s.wrapped(MARGIN, yy, PAGE_W - 2 * MARGIN, t_note,
              C_INK, size=10.2, bold=True)

    s.fold_marks()


def render_paper_back(s, d=None, separate=False):
    """Retro del paper wallet: istruzioni di recupero, nota sulla generazione
    e banda di protezione.

    ``d`` serve solo alla nota finale, che deve dire il vero su COME e\' stata
    prodotta questa chiave: quanti bit di entropia e se il secondo controllo
    (libreria BIP39 di riferimento) e\' stato eseguito davvero. Se manca, la
    nota viene scritta nella versione prudente.

    ``separate=True``: foglio delle istruzioni a parte, come per
    :func:`render_seed_back` (niente banda e niente segni di piega).
    """
    s.centred(PAGE_W / 2, 11,
              SEPARATE_HEAD if separate else
              "STAMPA FRONTE/RETRO  —  GIRO SUL LATO LUNGO   "
              "·   PIEGA IN TRE LUNGO I SEGNI",
              C_MUTED, size=8, bold=True)

    # Niente logo e niente indirizzo del sito qui: stanno sul FRONTE, che è
    # la faccia che identifica il documento. Ripeterli sul retro rubava
    # quattordici millimetri alle istruzioni, che sono l'unica cosa per cui
    # questa facciata esiste -- ed erano proprio i millimetri che a volte
    # facevano saltare la nota sulla generazione della chiave.
    d = d or {}
    is_electrum = d.get("seed_kind") == "electrum"

    w = PAGE_W - 2 * MARGIN
    y = 20.0
    y = s.text(MARGIN, y, "COME RIPRENDERE I FONDI", C_ACC_D,
               size=12, bold=True) + 1.5
    y = s.wrapped(MARGIN, y, w,
                  "Da fare solo quando vuoi spendere: fino ad allora il foglio "
                  "resta chiuso e i fondi restano dove sono.",
                  C_MUTED, size=7.6) + 3

    if is_electrum:
        y = _section(s, y, w, "A", "CON QUALE PROGRAMMA", SEC_A_ELECTRUM,
                     C_ACC_D)
        y = _section(s, _start_below_fold(y), w, "B", "COME SI RIPRISTINA",
                     SEC_B_ELECTRUM, C_ACC_D)
    else:
        y = _section(s, y, w, "A", "CON QUALE PROGRAMMA", SEC_A, C_ACC_D)
        y = _section(s, _start_below_fold(y), w, "B", "SE SCEGLI ELECTRUM",
                     SEC_B, C_ACC_D)

    y = s.text(MARGIN, y, "C.   VERIFICA FINALE  -  CON QUALUNQUE PROGRAMMA",
               C_ALERT, size=9.5, bold=True) + 2
    y = s.text(MARGIN + 4, y, "Confronta il primo indirizzo", C_INK,
               size=8.0, bold=True) + 0.6
    y = s.wrapped(MARGIN + 8, y, w - 8,
                  "A portafoglio creato, apri la sezione Ricevi (o Indirizzi) "
                  "e confronta il primo indirizzo con quello stampato sul "
                  + ("foglio con le parole di recupero" if separate
                     else "fronte di questo foglio")
                  + ". Devono essere identici, carattere "
                  "per carattere. Se non coincidono hai sbagliato una parola o "
                  "il percorso di derivazione: ricontrolla e ripeti.",
                  C_BODY, size=7.6)

    # --- come è stata generata la chiave -------------------------------
    # Va stampato sulla carta, non solo scritto nel codice: chi riceve un
    # paper wallet deve poter sapere da dove viene la casualità senza dover
    # credere sulla parola a chi gliel'ha dato.
    bits = d.get("entropy_bits") or (132 if is_electrum else 128)
    if is_electrum:
        gen = ("Le parole non le ha scelte una persona e non le ha prodotte un "
               "generatore scritto per l'occasione: le ha generate Electrum "
               f"stesso, con la propria sorgente di casualità crittografica, "
               f"a partire da {bits} bit di entropia. Il plugin non si collega "
               "a internet per generarle: tutto avviene sul computer che ha "
               "stampato questo foglio. Prima della stampa Electrum ha "
               "confermato che la frase è un seed valido di tipo segwit; in "
               "caso contrario il foglio non sarebbe stato stampato. Formato "
               "nativo Electrum (segwit).")
    else:
        checks = ("Prima della stampa la frase è stata verificata due volte: "
                  "dal plugin e, in modo indipendente, dalla libreria BIP39 di "
                  "riferimento, che non condivide codice con la prima. "
                  if d.get("ref_checked") else
                  "Prima della stampa la frase è stata verificata dal "
                  "controllo di validità BIP39 del plugin. ")
        gen = ("Le parole non le ha scelte una persona e non le ha prodotte un "
               f"generatore inventato per l'occasione: derivano da {bits} bit "
               "di casualità forniti dal sistema operativo (os.urandom), lo "
               "stesso generatore crittografico su cui si appoggiano i "
               "programmi di cifratura. Il plugin non si collega a internet "
               "per generarle: tutto avviene sul computer che ha stampato "
               "questo foglio. " + checks +
               "Se un controllo fosse fallito, il foglio non sarebbe stato "
               "stampato. Standard BIP39, derivazione "
               + (d.get("account_derivation") or "m/84'/0'/0'") + ".")

    # Il riquadro si appoggia sopra la banda, ma senza mai salire sopra il
    # testo che lo precede: se le istruzioni fossero più lunghe del previsto
    # (traduzioni, font diversi) scenderebbe, e allora il corpo si riduce
    # quel tanto che basta per stare nello spazio rimasto.
    top_min = y + 4
    size = 7.4
    while True:
        hg = s.measure(w - 6, gen, size=size) + 9
        gy = max(top_min, FOLD2 - hg - 5)
        if gy + hg <= FOLD2 - 2 or size <= 5.8:
            break
        size -= 0.3

    if gy + hg <= FOLD2 - 2:
        s.box(MARGIN, gy, w, hg, C_RULE, 0.4)
        s.text(MARGIN + 3, gy + 2, "COME È STATA GENERATA QUESTA CHIAVE",
               C_ACC_D, size=7.8, bold=True)
        s.wrapped(MARGIN + 3, gy + 6.5, w - 6, gen, C_BODY, size=size)
    else:
        # Non ci sta nemmeno al minimo: meglio nessuna nota che una nota
        # stampata sopra la banda nera, dove sarebbe illeggibile.
        import logging
        logging.getLogger(__name__).error(
            "nota sulla generazione non stampata: spazio insufficiente "
            "(testo fino a %.1f mm, banda a %.1f)", y, FOLD2)

    if separate:
        return
    _protection_band(s)
    s.fold_marks()
