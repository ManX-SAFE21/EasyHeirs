"""Piccoli disegni per la fascia d'intestazione delle finestre.

Sono SVG scritti a mano e tenuti qui come stringhe, non come file: pesano
poche righe e cosi' restano accanto al codice che li usa, senza aggiungere
risorse da imballare nello ZIP.

Perche' SVG e non QSvgWidget: la build ufficiale di Electrum NON contiene
QtSvg (manca ``QtSvg.pyd``), quindi quella strada e' preclusa. Contiene pero'
il lettore d'immagini ``qsvg``, per cui Qt sa aprire un SVG come una
qualsiasi immagine: e' la via che usiamo. Per quel lettore restiamo su SVG
1.1 elementare -- tracciati, rettangoli, cerchi, attributi di presentazione --
senza fogli di stile o filtri, che non e' detto interpreti.

Se per qualunque motivo il disegno non si carica, ``band_pixmap`` restituisce
None e la fascia resta come prima: un'illustrazione decorativa non deve mai
impedire l'apertura di una finestra.
"""

from electrum.logging import get_logger

_logger = get_logger(__name__)

# Proporzioni del riquadro: largo poco piu' del triplo dell'altezza, per
# riempire lo spazio libero a destra del titolo senza toccare i bordi.
ART_W, ART_H = 124, 40

_TEAL = "#0f6e56"        # tratto principale (marchio SAFE21)
_TEAL_SOLID = "#0d9488"  # piccoli pieni
_ORANGE = "#d97e0d"      # solo il paper wallet: richiama il pulsante arancio

# Il corpo di ogni disegno. L'intestazione <svg> viene aggiunta da _document(),
# che ci scrive dentro la dimensione richiesta.
_BODIES = {

    # Il patrimonio di un portafoglio che si divide fra tre eredi.
    "heirs": f'''
  <g fill="none" stroke="{_TEAL}" stroke-width="1.6" stroke-linecap="round"
     stroke-linejoin="round">
    <rect x="3" y="10" width="33" height="21" rx="4" fill="#ffffff"
          fill-opacity=".65"/>
    <rect x="29" y="17.5" width="7" height="6" rx="3" fill="{_TEAL_SOLID}"
          stroke="none"/>
    <g stroke-width="1.3">
      <path d="M13 15.5v10M15.6 13.6v1.9M18.6 13.6v1.9M15.6 25.5v1.9
               M18.6 25.5v1.9"/>
      <path d="M13 15.5h5.4a2.4 2.4 0 0 1 0 4.8H13"/>
      <path d="M13 20.3h6a2.6 2.6 0 0 1 0 5.2h-6"/>
    </g>
    <g stroke-width="1.3" opacity=".75">
      <path d="M39 20.5h7c4 0 3-11 7-11h7"/>
      <path d="M39 20.5h15"/>
      <path d="M39 20.5h7c4 0 3 11 7 11h7"/>
    </g>
    <g>
      <circle cx="67" cy="9.5" r="2.9" fill="#ffffff" fill-opacity=".8"/>
      <path d="M62.8 15.6a4.4 4.4 0 0 1 8.4 0"/>
      <circle cx="67" cy="20.5" r="2.9" fill="#ffffff" fill-opacity=".8"/>
      <path d="M62.8 26.6a4.4 4.4 0 0 1 8.4 0"/>
      <circle cx="67" cy="31.5" r="2.9" fill="#ffffff" fill-opacity=".8"/>
      <path d="M62.8 37.6a4.4 4.4 0 0 1 8.4 0"/>
    </g>
  </g>''',

    # Una stampante e i fogli A4 in verticale, con le due pieghe orizzontali:
    # e' il formato che produciamo davvero (A4 ritratto piegato in tre).
    "print": f'''
  <g fill="none" stroke="{_TEAL}" stroke-width="1.6" stroke-linecap="round"
     stroke-linejoin="round">
    <rect x="3" y="14" width="44" height="17" rx="3" fill="#ffffff"
          fill-opacity=".65"/>
    <path d="M11 14V6h28v8"/>
    <circle cx="41" cy="19.5" r="1.4" fill="{_TEAL_SOLID}" stroke="none"/>
    <path d="M11 31v3h28v-3"/>
    <g>
      <rect x="60" y="3" width="26" height="34" rx="2" fill="#ffffff"
            fill-opacity=".9"/>
      <path d="M60 14.3h26M60 25.6h26" stroke-width="1.1"
            stroke-dasharray="2.4 2.6" opacity=".8"/>
      <g stroke-width="1.2" opacity=".55">
        <path d="M64 8h13M64 11h9"/>
        <path d="M64 19h13M64 22h10"/>
        <path d="M64 30h13M64 33h8"/>
      </g>
    </g>
    <g>
      <rect x="92" y="3" width="26" height="34" rx="2" fill="#ffffff"
            fill-opacity=".9"/>
      <path d="M92 14.3h26M92 25.6h26" stroke-width="1.1"
            stroke-dasharray="2.4 2.6" opacity=".8"/>
      <g stroke-width="1.2" opacity=".55">
        <path d="M96 8h13M96 11h9"/>
        <path d="M96 19h11M96 22h13"/>
        <path d="M96 30h13M96 33h7"/>
      </g>
    </g>
  </g>''',

    # Un foglio con QR e una moneta che ci entra: il portafoglio di carta va
    # alimentato dopo averlo stampato.
    "paper": f'''
  <g fill="none" stroke="{_TEAL}" stroke-width="1.6" stroke-linecap="round"
     stroke-linejoin="round">
    <rect x="4" y="5" width="58" height="30" rx="2" fill="#ffffff"
          fill-opacity=".9"/>
    <g stroke-width="1.3">
      <rect x="9" y="10" width="7" height="7" rx="1"/>
      <rect x="22" y="10" width="7" height="7" rx="1"/>
      <rect x="9" y="23" width="7" height="7" rx="1"/>
      <path d="M22 23h3M28 23v3M25 26v4M22 30h3" stroke-width="1.5"/>
    </g>
    <g stroke-width="1.2" opacity=".55">
      <path d="M36 12h20M36 17h20M36 22h14M36 27h17"/>
    </g>
    <path d="M100 12c-9-6-19-4-24 2" stroke="{_ORANGE}" stroke-width="1.4"
          stroke-dasharray="3 2.6"/>
    <path d="M76 10.5 75.2 16.5 81 15" fill="{_ORANGE}" stroke="none"/>
    <circle cx="105" cy="24" r="11" fill="#ffffff" fill-opacity=".9"
            stroke="{_ORANGE}"/>
    <g stroke="{_ORANGE}" stroke-width="1.3">
      <path d="M101 20v9M103.5 18.4v1.6M106.5 18.4v1.6M103.5 29v1.6
               M106.5 29v1.6"/>
      <path d="M101 20h5.4a2.2 2.2 0 0 1 0 4.4H101"/>
      <path d="M101 24.4h6a2.3 2.3 0 0 1 0 4.6h-6"/>
    </g>
  </g>''',
}


def _document(name, width, height):
    """L'SVG completo alla dimensione richiesta, in byte."""
    body = _BODIES[name]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" '
           f'viewBox="0 0 {ART_W} {ART_H}" width="{width}" '
           f'height="{height}">{body}</svg>')
    return svg.encode("utf-8")


def band_pixmap(name, height=ART_H, ratio=1.0):
    """Il disegno ``name`` pronto da mettere in una QLabel, o None.

    Il lettore SVG di Qt disegna alla misura scritta nell'attributo
    ``width``/``height``, non a quella della QLabel: per gli schermi ad alta
    densita' lo generiamo quindi gia' ingrandito di ``ratio`` e poi diciamo
    alla pixmap di che fattore si tratta, cosi' resta nitido senza occupare
    piu' spazio nel layout.
    """
    if name not in _BODIES:
        return None
    # Import locale: cosi' questo modulo resta importabile (e collaudabile)
    # anche dove non c'e' una GUI.
    from PyQt6.QtGui import QPixmap
    ratio = max(1.0, float(ratio or 1.0))
    h = int(round(height * ratio))
    w = int(round(height * ratio * ART_W / ART_H))
    pm = QPixmap()
    try:
        loaded = pm.loadFromData(_document(name, w, h), "svg")
    except Exception as e:
        _logger.info(f"disegno {name} non caricato: {e}")
        return None
    if not loaded or pm.isNull():
        # Succede se manca il lettore SVG: non e' un errore da mostrare.
        _logger.info(f"disegno {name} non disponibile (lettore SVG assente?)")
        return None
    pm.setDevicePixelRatio(ratio)
    return pm
