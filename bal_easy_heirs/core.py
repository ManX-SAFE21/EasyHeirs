# -*- coding: utf-8 -*-
"""
Easy Heirs - SAFE21
core.py : logica pura, nessuna dipendenza da Qt.

Modello dati (deciso al passo 1)
--------------------------------
La lista di BAL resta l'unica fonte di verita' per nome, indirizzo, quota e
data. Questo modulo aggiunge, in una chiave separata, solo cio' che BAL non
sa: seed generati, chiave pubblica estesa, numero di busta, data di stampa.

    BAL      wallet.db["heirs"]                 -> nome: (indirizzo, quota, locktime)
    nostro   wallet.db["safe21_beneficiaries"]  -> {version, entries: [...]}

Il collegamento fra i due e' l'INDIRIZZO, non il nome: rinominare un
beneficiario in BAL non spezza nulla.

Il tipo di beneficiario non e' un campo memorizzato: si deduce. Se un
indirizzo presente in BAL compare anche nel nostro registro, il seed lo
abbiamo generato noi; altrimenti l'indirizzo lo ha fornito lui.

Nota di compatibilita' (importante)
-----------------------------------
Non registriamo NULLA in json_db / stored_dict. Electrum 4.8.0 ha rimosso
``json_db.register_dict`` sostituendolo con ``stored_dict.register_name``,
con firma diversa: chi si era appoggiato a quella API ha dovuto scrivere un
adattatore. Usando solo strutture JSON semplici (dict, list, str, int) il
problema non si pone affatto, ne' oggi ne' al prossimo cambio.
"""

import hashlib
import json
import os
import time
import unicodedata

from electrum.logging import get_logger

_logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Formato della lista eredi di BAL (verificato su bal/core/heirs.py 0.5.36)
# --------------------------------------------------------------------------- #
HEIR_ADDRESS = 0
HEIR_AMOUNT = 1
HEIR_LOCKTIME = 2

BAL_HEIRS_KEY = "heirs"
BAL_WILL_KEY = "will"

# Chiave nostra. Nessun'altra parte del wallet viene scritta.
REGISTRY_KEY = "safe21_beneficiaries"
REGISTRY_VERSION = 1

# Derivazione dei seed generati.
DERIVATION_ACCOUNT = "m/84'/0'/0'"      # da stampare: e' quello che si digita
DERIVATION_FIRST = "m/84'/0'/0'/0/0"    # solo per ricavare il primo indirizzo
XTYPE = "p2wpkh"

SEED_WORDS = 12

# I due formati di frase che il plugin sa produrre.
#
#   BIP39     lo standard: funziona in quasi tutti i portafogli, ma per
#             ripristinarlo bisogna anche digitare il percorso di derivazione,
#             ed e' l'errore piu' facile da fare (percorso sbagliato ->
#             portafoglio diverso e vuoto, senza alcun messaggio d'errore).
#   ELECTRUM  il formato nativo di Electrum: niente percorso da digitare
#             (quindi quell'errore non esiste) e frase riconoscibile grazie a
#             un marcatore di versione, ma si ripristina praticamente solo in
#             Electrum.
#
# Gli EREDI usano sempre BIP39: quei fogli finiscono in mano ad altri, che
# useranno il portafoglio che vogliono loro. La scelta esiste solo per i paper
# wallet, che restano di chi li crea.
SEED_KIND_BIP39 = "bip39"
SEED_KIND_ELECTRUM = "electrum"
SEED_KINDS = (SEED_KIND_BIP39, SEED_KIND_ELECTRUM)

# Tipo di seed Electrum da generare: "segwit" da indirizzi bc1q e chiave
# zpub, gli stessi che gia' produciamo con BIP39.
ELECTRUM_SEED_TYPE = "segwit"
# Percorso usato internamente da Electrum per i seed segwit. Lo teniamo come
# informazione, NON come istruzione: non va digitato da nessuna parte.
ELECTRUM_DERIVATION = "m/0'"

# Importo segnaposto. Deve superare due filtri di BAL: validate_amount
# (float > 0.00000001) e la soglia dust in fase di costruzione transazione,
# sotto la quale l'erede verrebbe escluso senza alcun messaggio.
PLACEHOLDER_SATS = 10000

# Oltre questo valore un locktime Bitcoin e' un timestamp, sotto e' un numero
# di blocco. Serve a non trasformare l'altezza 800000 in una data del 1970.
LOCKTIME_IS_TIME = 500_000_000


# Versione del CODICE che sta girando adesso. Non viene letta da un file:
# deve valere esattamente quanto era scritto nei sorgenti al momento
# dell'import, perche' serve proprio a confrontarla con quella dichiarata dal
# file su disco. scripts/build_release.py verifica che coincida con il
# manifest a ogni build, cosi' non puo' restare indietro per distrazione.
RUNNING_VERSION = "1.0.12"


PLUGIN_NAME = "bal_easy_heirs"   # il campo "name" del manifest, come lo usa Electrum


def _package_path():
    """Il file .zip (o la cartella) da cui questo plugin e' stato caricato.

    Dentro uno ZIP ``__file__`` e' un percorso finto del tipo
    ``.../plugin.zip/bal_easy_heirs/core.py``: risalendo si trova il primo
    elemento che esiste davvero su disco. Puo' essere l'archivio, ma anche
    soltanto la cartella dei plugin, se quell'archivio nel frattempo e' stato
    rimosso -- ed e' proprio cio' che accade aggiornando.
    """
    p = os.path.abspath(__file__)
    while True:
        if os.path.exists(p):
            return p
        parent = os.path.dirname(p)
        if not parent or parent == p:
            return None
        p = parent


def plugin_dir():
    """La cartella in cui Electrum tiene i plugin esterni, o None."""
    path = _package_path()
    if not path:
        return None
    return path if os.path.isdir(path) else os.path.dirname(path)


def _manifest_version(path):
    """La versione dichiarata da uno ZIP, se contiene QUESTO plugin.

    Il confronto e' sul campo ``name`` del manifest, non sul nome del file:
    e' lo stesso criterio con cui Electrum riconosce i plugin esterni, e il
    nome del file e' invece libero (il nostro ci mette dentro la versione).
    """
    import zipfile
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith("manifest.json") and name.count("/") <= 1:
                d = json.loads(z.read(name).decode("utf-8"))
                if d.get("name") == PLUGIN_NAME:
                    return d.get("version")
                return None
    return None


def _version_key(v):
    """Ordina "0.10.0" dopo "0.9.4", cosa che l'ordine alfabetico non fa."""
    try:
        return tuple(int(part) for part in str(v).split("."))
    except (TypeError, ValueError):
        return ()


def installed_version(directory=None):
    """La versione piu' recente di questo plugin presente su disco, o None.

    Guarda tutta la cartella perche' un aggiornamento non sovrascrive niente:
    arriva come archivio con un altro nome. Fra piu' copie vince la piu' alta,
    cosi' uno ZIP vecchio dimenticato accanto a quello nuovo non fa scattare
    avvisi a sproposito.
    """
    here = os.path.abspath(__file__)
    try:
        # Installazione scompattata: il manifest sta accanto ai sorgenti.
        if os.path.isfile(here):
            fn = os.path.join(os.path.dirname(here), "manifest.json")
            if os.path.isfile(fn):
                with open(fn, "r", encoding="utf-8") as fh:
                    return json.load(fh).get("version")
            return None
    except Exception as e:
        _logger.info(f"manifest su disco non leggibile: {e}")
        return None

    folder = directory or plugin_dir()
    if not folder or not os.path.isdir(folder):
        return None
    found = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".zip"):
            continue
        try:
            v = _manifest_version(os.path.join(folder, name))
        except Exception as e:
            # Un archivio illeggibile o di un altro plugin non deve impedire
            # di esaminare gli altri.
            _logger.info(f"{name} non leggibile: {e}")
            continue
        if v:
            found.append(v)
    if not found:
        return None
    return max(found, key=_version_key)


def stale_version(directory=None):
    """La versione su disco se DIVERSA da quella in esecuzione, altrimenti None.

    Serve a un solo scopo: dire all'utente che ha aggiornato il plugin ma sta
    ancora usando quello vecchio, perche' Python tiene in memoria i moduli
    gia' importati e nemmeno riabilitare il plugin li ricarica.
    """
    disk = installed_version(directory)
    if disk and disk != RUNNING_VERSION:
        return disk
    return None


class EasyHeirsError(Exception):
    pass


class NoWalletPassword(EasyHeirsError):
    """Il wallet non ha password: i seed finirebbero in chiaro su disco."""


class DuplicateName(EasyHeirsError):
    pass


# ===========================================================================
#  BIP39
# ===========================================================================

def load_bip39_wordlist():
    words = None
    try:
        from electrum.mnemonic import load_wordlist
        words = list(load_wordlist("english.txt"))
    except Exception as e:
        _logger.info(f"load_wordlist non disponibile ({e}), leggo il file")
    if not words:
        try:
            import electrum
            path = os.path.join(os.path.dirname(electrum.__file__),
                                "wordlist", "english.txt")
            with open(path, "r", encoding="utf-8") as f:
                words = [w.strip() for w in f if w.strip()]
        except Exception as e:
            raise EasyHeirsError(f"wordlist BIP39 non trovata: {e}")
    if len(words) != 2048:
        raise EasyHeirsError(
            f"wordlist BIP39 non valida: {len(words)} parole invece di 2048")
    return words


def bip39_reference_available() -> bool:
    """True se la libreria BIP39 di riferimento e' importabile.

    Electrum si porta dietro ``mnemonic`` (l'implementazione di riferimento
    dello standard). Non e' garantita su ogni build, quindi la trattiamo come
    un di piu': se c'e' la usiamo per un controllo indipendente, se non c'e'
    si prosegue con il nostro.
    """
    try:
        from mnemonic import Mnemonic
        Mnemonic("english")
        return True
    except Exception:
        return False


def _reference_rejects(mnemonic: str) -> bool:
    """True SOLO se la libreria di riferimento dice che la frase non e' valida.

    Se la libreria manca o solleva un errore suo, ritorna False: un problema
    della libreria non deve impedire di generare un seed che il nostro
    controllo ha gia' dato per buono.
    """
    try:
        from mnemonic import Mnemonic
    except Exception:
        return False
    try:
        return not Mnemonic("english").check(mnemonic)
    except Exception as e:
        _logger.info(f"controllo BIP39 di riferimento non eseguito: {e}")
        return False


def generate_mnemonic(num_words: int = SEED_WORDS) -> str:
    """
    Genera una frase BIP39 con os.urandom, il generatore crittografico del
    sistema operativo. Mai il modulo random: sarebbe prevedibile.
    """
    if num_words not in (12, 24):
        raise EasyHeirsError("supportate solo frasi da 12 o 24 parole")
    entropy_bits = 128 if num_words == 12 else 256
    entropy = os.urandom(entropy_bits // 8)
    checksum_bits = entropy_bits // 32
    digest = hashlib.sha256(entropy).digest()

    bits = "".join(f"{b:08b}" for b in entropy)
    bits += "".join(f"{b:08b}" for b in digest)[:checksum_bits]

    wl = load_bip39_wordlist()
    mnemonic = " ".join(wl[int(bits[i:i + 11], 2)]
                        for i in range(0, len(bits), 11))

    # Doppia verifica prima di consegnare la frase. La prima e' nostra; la
    # seconda, quando disponibile, la fa la libreria BIP39 di riferimento, che
    # non condivide una riga di codice con la nostra. Un errore nostro
    # nell'impacchettare i bit verrebbe intercettato li'.
    if not checksum_is_valid(mnemonic):
        raise EasyHeirsError("checksum BIP39 non valido, generazione annullata")
    if _reference_rejects(mnemonic):
        raise EasyHeirsError(
            "la libreria BIP39 di riferimento rifiuta la frase generata: "
            "generazione annullata")
    return mnemonic


def checksum_is_valid(mnemonic: str) -> bool:
    try:
        wl = load_bip39_wordlist()
        idx = {w: i for i, w in enumerate(wl)}
        words = mnemonic.split()
        if len(words) not in (12, 15, 18, 21, 24):
            return False
        bits = ""
        for w in words:
            if w not in idx:
                return False
            bits += f"{idx[w]:011b}"
        cs = len(bits) // 33
        ent = len(bits) - cs
        entropy = int(bits[:ent], 2).to_bytes(ent // 8, "big")
        expected = "".join(f"{b:08b}" for b in hashlib.sha256(entropy).digest())[:cs]
        return bits[ent:] == expected
    except Exception as e:
        _logger.error(f"verifica checksum fallita: {e}")
        return False


def mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    try:
        from electrum.mnemonic import bip39_to_seed
        return bip39_to_seed(mnemonic, passphrase)
    except Exception:
        m = unicodedata.normalize("NFKD", mnemonic)
        p = unicodedata.normalize("NFKD", "mnemonic" + passphrase)
        return hashlib.pbkdf2_hmac("sha512", m.encode(), p.encode(), 2048)


def derive_account(mnemonic: str, passphrase: str = "") -> dict:
    """
    Ritorna {"address", "xpub"}.

    Due percorsi indipendenti: prima l'API di Electrum per i seed BIP39
    (la stessa della procedura guidata), poi la derivazione BIP32 esplicita
    se quella firma cambia fra versioni.
    """
    err = None
    try:
        from electrum import keystore
        from electrum.bitcoin import pubkey_to_address
        try:
            ks = keystore.from_bip39_seed(mnemonic, passphrase,
                                          DERIVATION_ACCOUNT, xtype=XTYPE)
        except TypeError:
            ks = keystore.from_bip39_seed(mnemonic, passphrase,
                                          DERIVATION_ACCOUNT)
        pub = ks.derive_pubkey(0, 0)
        if isinstance(pub, (bytes, bytearray)):
            pub = pub.hex()
        return {"address": pubkey_to_address(XTYPE, pub),
                "xpub": ks.get_master_public_key()}
    except Exception as e:
        err = e

    _logger.info(f"from_bip39_seed non utilizzabile ({err}), "
                 "uso la derivazione BIP32 esplicita")
    from electrum.bip32 import BIP32Node
    from electrum.bitcoin import pubkey_to_address
    seed = mnemonic_to_seed(mnemonic, passphrase)
    root = BIP32Node.from_rootseed(seed, xtype=XTYPE)
    account = root.subkey_at_private_derivation(DERIVATION_ACCOUNT)
    first = root.subkey_at_private_derivation(DERIVATION_FIRST)
    return {"address": pubkey_to_address(
                XTYPE, first.eckey.get_public_key_hex(compressed=True)),
            "xpub": account.to_xpub()}


def generate_electrum_seed() -> str:
    """Genera una frase nel formato nativo di Electrum (tipo segwit).

    Qui non scriviamo nulla di nostro: la frase la produce ``make_seed`` di
    Electrum, con la sua sorgente di casualita' (132 bit). Ci limitiamo a
    richiamarla in modo difensivo, perche' la firma e' cambiata fra versioni,
    e a farci confermare da Electrum stesso che la frase risultante e'
    davvero riconosciuta come seed segwit.
    """
    from electrum.mnemonic import Mnemonic
    m = Mnemonic("en")
    try:
        seed = m.make_seed(seed_type=ELECTRUM_SEED_TYPE)
    except TypeError:
        # Firme piu' vecchie accettavano il tipo come primo argomento.
        seed = m.make_seed(ELECTRUM_SEED_TYPE)

    kind = electrum_seed_type(seed)
    if kind != ELECTRUM_SEED_TYPE:
        raise EasyHeirsError(
            "Electrum non riconosce la frase appena generata come seed "
            f"{ELECTRUM_SEED_TYPE} (ha risposto {kind!r}): generazione "
            "annullata")
    return seed


def electrum_seed_type(seed: str):
    """Il tipo di seed secondo Electrum, o None se non si riesce a chiederlo.

    Il nome della funzione e' cambiato fra le versioni (prima ``seed_type``,
    poi ``calc_seed_type``), quindi le proviamo entrambe.
    """
    for mod, name in (("electrum.mnemonic", "calc_seed_type"),
                      ("electrum.mnemonic", "seed_type"),
                      ("electrum.keystore", "seed_type")):
        try:
            fn = getattr(__import__(mod, fromlist=[name]), name)
        except Exception:
            continue
        try:
            return fn(seed)
        except Exception as e:
            _logger.info(f"{mod}.{name} non utilizzabile: {e}")
    return None


def derive_electrum_account(seed: str, passphrase: str = "") -> dict:
    """Indirizzo e chiave pubblica di un seed nativo Electrum.

    Ritorna la stessa coppia {"address", "xpub"} di ``derive_account``, cosi'
    il resto del plugin non deve sapere quale formato sia stato usato.
    """
    from electrum import keystore
    from electrum.bitcoin import pubkey_to_address

    # La firma di from_seed e' cambiata fra le versioni di Electrum: oggi e'
    # from_seed(seed, *, passphrase, for_multisig=False), cioe' la passphrase
    # si passa SOLO per nome, mentre in passato era posizionale. Proviamo le
    # forme note in ordine, dalla piu' recente alla piu' vecchia, invece di
    # indovinarne una: una firma sbagliata qui bloccherebbe del tutto la
    # generazione del paper wallet.
    attempts = (
        lambda: keystore.from_seed(seed, passphrase=passphrase,
                                   for_multisig=False),
        lambda: keystore.from_seed(seed, passphrase=passphrase),
        lambda: keystore.from_seed(seed),
        lambda: keystore.from_seed(seed, passphrase, False),
        lambda: keystore.from_seed(seed, passphrase),
    )
    ks, last = None, None
    for attempt in attempts:
        try:
            ks = attempt()
            break
        except TypeError as e:
            last = e
    if ks is None:
        raise EasyHeirsError(
            f"impossibile ricavare le chiavi dal seed Electrum: {last}")

    pub = ks.derive_pubkey(0, 0)
    if isinstance(pub, (bytes, bytearray)):
        pub = pub.hex()
    return {"address": pubkey_to_address(XTYPE, pub),
            "xpub": ks.get_master_public_key()}


def generate_beneficiary(num_words: int = SEED_WORDS):
    """Ritorna (mnemonic, address, xpub). Il mnemonic non deve uscire dalla RAM
    se non per andare in stampa."""
    mnemonic = generate_mnemonic(num_words)
    info = derive_account(mnemonic)
    return mnemonic, info["address"], info["xpub"]


# ===========================================================================
#  Paper wallet
# ===========================================================================
#
# Un paper wallet e' un portafoglio nuovo, generato solo per essere stampato e
# poi alimentato versandoci dei fondi. A differenza dei beneficiari:
#
#   * NON entra nella lista eredi di BAL (non e' un erede: riceverebbe
#     un'eredita' che nessuno gli ha assegnato);
#   * NON viene salvato da nessuna parte. Niente registro, niente wallet,
#     niente file: il seed esiste solo nella RAM del programma e, dopo la
#     stampa, solo sulla carta.
#
# La conseguenza e' voluta ma va ricordata: se il foglio si perde o la stampa
# esce illeggibile, i fondi versati a quell'indirizzo sono irrecuperabili. Per
# questo l'interfaccia consente di ristampare finche' la finestra resta
# aperta, e chiede conferma esplicita prima di chiudere e perdere i seed.

MAX_PAPER_WALLETS = 20


def generate_paper_wallets(count: int, num_words: int = SEED_WORDS,
                           seed_kind: str = SEED_KIND_BIP39) -> list:
    """Genera ``count`` paper wallet nuovi, senza salvare nulla.

    Ritorna una lista di dizionari con ``name`` ("paperwallet 01", ...),
    ``address``, ``xpub``, ``seed`` e ``created`` (epoch della generazione).
    La numerazione riparte sempre da 01: non essendo memorizzato nulla, non
    c'e' un conteggio precedente a cui agganciarsi.

    ``seed_kind`` sceglie il formato della frase: BIP39 (predefinito, portabile
    ovunque) oppure il formato nativo di Electrum (piu' semplice da
    ripristinare ma legato a Electrum).

    Non riceve il wallet come parametro proprio per rendere evidente, anche
    dalla firma, che non lo tocca in alcun modo.
    """
    if seed_kind not in SEED_KINDS:
        raise EasyHeirsError(f"formato di seed sconosciuto: {seed_kind!r}")
    if not isinstance(count, int) or count < 1:
        raise EasyHeirsError("indicare quanti paper wallet creare (almeno 1)")
    if count > MAX_PAPER_WALLETS:
        raise EasyHeirsError(
            f"massimo {MAX_PAPER_WALLETS} paper wallet per volta")

    now = int(time.time())
    # Registrato una volta sola: finisce stampato sul foglio, quindi deve
    # dire il vero. Se la libreria non c'e', il foglio non dovra' vantare un
    # controllo che non e' avvenuto.
    is_bip39 = seed_kind == SEED_KIND_BIP39
    ref = bip39_reference_available() if is_bip39 else False
    out = []
    for i in range(1, count + 1):
        if is_bip39:
            mnemonic, address, xpub = generate_beneficiary(num_words)
            derivation = DERIVATION_ACCOUNT
            bits = 128 if num_words == 12 else 256
        else:
            mnemonic = generate_electrum_seed()
            info = derive_electrum_account(mnemonic)
            address, xpub = info["address"], info["xpub"]
            # Percorso informativo: con un seed Electrum non si digita.
            derivation = ELECTRUM_DERIVATION
            bits = 132
        out.append({
            "name": f"paperwallet {i:02d}",
            "address": address,
            "xpub": xpub,
            "seed": mnemonic,
            "created": now,
            "seed_kind": seed_kind,
            "account_derivation": derivation,
            "entropy_bits": bits,
            "ref_checked": ref,
        })
    return out


# ===========================================================================
#  Lettura della lista di BAL
# ===========================================================================

def read_bal_heirs(wallet) -> dict:
    """{nome: {address, amount, locktime}}. Non modifica nulla."""
    out = {}
    try:
        raw = read_heirs_raw(wallet)
    except Exception as e:
        _logger.error(f"lettura lista BAL fallita: {e}")
        return out
    for name, v in raw.items():
        try:
            out[name] = {"address": v[HEIR_ADDRESS],
                         "amount": v[HEIR_AMOUNT],
                         "locktime": v[HEIR_LOCKTIME]}
        except Exception:
            _logger.info(f"voce non interpretabile, saltata: {name!r}")
            out[name] = {"address": None, "amount": None, "locktime": None}
    return out


def _plain(value):
    """Copia "nuda" di un valore letto dal wallet: solo dict, list e scalari.

    Electrum non restituisce dizionari e liste normali: li avvolge in
    ``StoredDict`` / ``StoredList``, che tengono un riferimento al database --
    e quindi al suo lock. Ogni lista annidata viene convertita cosi', sempre,
    a prescindere dalle chiavi registrate.

    Il guaio salta fuori solo quando si RISCRIVE: ``db.put`` fa una copia
    profonda del valore, che su un lock non e' possibile, e fallisce con
    "cannot pickle '_thread.RLock' object". Per noi significava non riuscire
    piu' ad aggiungere un beneficiario appena nella lista ce n'era gia' uno.

    Le tuple diventano liste: e' quello che erano gia' una volta salvate in
    JSON, quindi sul file non cambia nulla.
    """
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def read_heirs_raw(wallet) -> dict:
    """La lista eredi di BAL, gia' ridotta a strutture riscrivibili.

    Unico punto da cui leggerla quando poi la si rimette nel wallet: cosi' la
    conversione non puo' essere dimenticata in uno dei rami.
    """
    return _plain(wallet.db.get(BAL_HEIRS_KEY, {}) or {})


def _as_percent(amount) -> float:
    """Se amount e' una percentuale valida ("30%", "12.5%") ritorna il numero,
    altrimenti None. Un importo fisso in sat/BTC non e' una percentuale."""
    if amount is None:
        return None
    s = str(amount).strip()
    if not s.endswith("%"):
        return None
    try:
        return float(s[:-1])
    except Exception:
        return None


def _existing_percent(wallet):
    """Somma delle quote percentuali degli eredi GIA' presenti in BAL.

    Ritorna la coppia ``(existing_pct, has_fixed)``:
      * ``existing_pct`` = somma delle percentuali gia' assegnate in BAL;
      * ``has_fixed`` = True se almeno un erede esistente usa un importo FISSO
        (sat/BTC) invece di una percentuale: in quel caso percentuali e importi
        fissi non si sommano in modo pulito e non proponiamo suggerimenti.
    """
    heirs = read_bal_heirs(wallet)
    existing_pct = 0.0
    has_fixed = False
    for h in heirs.values():
        pct = _as_percent(h.get("amount"))
        if pct is not None:
            existing_pct += pct
        elif h.get("amount") not in (None, ""):
            has_fixed = True
    return existing_pct, has_fixed


# Perche' non c'e' nulla da suggerire. La finestra di creazione li usa per
# spiegarlo: sono gli stessi casi in cui le caselle restano vuote, e senza
# spiegazione sembrano un guasto del programma.
NO_ROOM_FIXED = "fixed"   # un erede esistente ha un importo fisso
NO_ROOM_FULL = "full"     # il 100% risulta gia' tutto assegnato


def share_state(wallet, manual: list) -> dict:
    """La situazione delle quote: quanto e' gia' assegnato e quanto resta.

    Una sola fonte per due usi -- calcolare i suggerimenti e spiegarli --
    perche' la stessa formula scritta in due posti prima o poi diverge, e a
    divergere sarebbe proprio la frase che dice all'utente perche' le caselle
    sono vuote.

    Chiavi ritornate:
      ``existing_pct``  quote percentuali gia' assegnate in BAL;
      ``manual_pct``    quote percentuali scritte a mano nelle righe nuove;
      ``remaining``     il resto da distribuire (mai negativo);
      ``each``          quanto toccherebbe a ogni riga automatica, arrotondato;
      ``free``          indici delle righe da riempire in automatico;
      ``has_fixed``     un erede esistente usa un importo fisso;
      ``reason``        None, oppure NO_ROOM_FIXED / NO_ROOM_FULL.
    """
    existing_pct, has_fixed = _existing_percent(wallet)

    # Le quote manuali che NON sono percentuali (es. un importo fisso digitato
    # a mano) non entrano nel conteggio del resto: non si sommano al 100%.
    manual_pct = 0.0
    for m in manual:
        p = _as_percent(m)
        if p is not None:
            manual_pct += p

    free = [i for i, m in enumerate(manual) if m is None]
    remaining = max(0.0, 100.0 - existing_pct - manual_pct)
    each = round(remaining / len(free), 2) if free else 0.0

    reason = None
    if has_fixed:
        reason = NO_ROOM_FIXED
    elif free and each <= 0:
        # Il confronto e' sul valore ARROTONDATO, lo stesso che finirebbe
        # nella casella: se scriveremmo "0%", non c'e' quota da proporre.
        reason = NO_ROOM_FULL

    return {"existing_pct": existing_pct, "manual_pct": manual_pct,
            "remaining": remaining, "each": each, "free": free,
            "has_fixed": has_fixed, "reason": reason}


def suggest_shares(wallet, manual: list) -> list:
    """Quote suggerite per una lista di nuovi beneficiari, RISPETTANDO quelle
    gia' scritte a mano.

    ``manual`` ha una voce per riga: la stringa che l'utente ha digitato
    (es. ``"30%"``) per le righe modificate a mano, oppure ``None`` per le
    righe da riempire automaticamente.

    Ritorna una lista della stessa lunghezza in cui:
      * le righe manuali restano invariate (viene riproposto cio' che c'era);
      * le righe automatiche si spartiscono IN PARTI UGUALI il 100% che resta
        dopo aver tolto sia le quote gia' assegnate in BAL, sia le quote
        percentuali digitate a mano nelle altre righe.

    Cosi', togliendo o aggiungendo un erede, le righe non toccate si
    ribilanciano da sole (5 eredi -> 20% a testa; ne togli uno -> 25% a testa),
    mentre una quota scritta a mano non viene mai sovrascritta.

    Quando non c'e' un resto da distribuire le righe automatiche restano
    VUOTE (``""``) invece di ricevere ``"0%"``. Due casi:

      * un erede gia' presente in BAL usa un importo FISSO, e allora un
        "resto in percentuale" pulito non esiste;
      * il 100% risulta gia' assegnato fra eredi esistenti e quote scritte
        a mano.

    Una casella vuota ha un seguito sensato (l'erede si crea con l'importo
    segnaposto, da correggere poi in BAL), mentre ``"0%"`` verrebbe respinto
    dalla validazione come quota non valida: il plugin rifiuterebbe un valore
    scritto da lui stesso. Il motivo viene mostrato dalla finestra di
    creazione, che lo chiede a ``share_state``.
    """
    n = len(manual)
    if n <= 0:
        return []

    st = share_state(wallet, manual)
    free_idx = st["free"]
    out = [m if m is not None else "" for m in manual]
    if st["reason"] or not free_idx:
        return out

    remaining, each = st["remaining"], st["each"]
    for i in free_idx:
        out[i] = f"{each:g}%"
    # l'ultima riga automatica assorbe lo scarto di arrotondamento, cosi' la
    # somma torna esatta invece di fermarsi a 99.98%
    assigned = each * (len(free_idx) - 1)
    last = round(remaining - assigned, 2)
    out[free_idx[-1]] = f"{last:g}%"
    return out


def suggest_equal_shares(wallet, n_new: int) -> list:
    """Quote suggerite per ``n_new`` nuovi beneficiari, dividendo cio' che
    resta del 100% dopo gli eredi gia' presenti in BAL.

    Replica lo stesso principio del vecchio dialogo di creazione multipla di
    BAL (100/n a testa), ma con una differenza voluta: quel dialogo divideva
    sempre 100% fra i SOLI nuovi, ignorando chi era gia' nella lista. Se la
    lista non era vuota il totale finiva sopra il 100% senza che nessuno se
    ne accorgesse. Qui invece:

      1. sommiamo le quote GIA' espresse in percentuale dagli eredi esistenti;
      2. se qualche esistente ha un importo FISSO (sat o BTC) invece che una
         percentuale, il "resto in percentuale" non e' calcolabile in modo
         pulito: percentuali e importi fissi non si sommano. In quel caso
         ripieghiamo su quote vuote (nessun suggerimento), lasciando che sia
         l'utente a decidere in BAL con cognizione del quadro completo;
      3. altrimenti dividiamo in parti uguali cio' che resta del 100% fra i
         nuovi, arrotondato a due decimali. L'eventuale resto dell'arrotonda-
         mento va tutto sull'ultima riga, cosi' la somma torna esatta.

    Ritorna una lista di ``n_new`` stringhe (es. "30%") oppure di stringhe
    vuote se non e' stato possibile suggerire nulla.

    Oggi nessuno la chiama: la finestra di creazione usa ``suggest_shares``,
    che rispetta anche le quote gia' scritte a mano. Resta qui come caso
    particolare di quella (nessuna riga manuale) e le delega il calcolo,
    invece di tenerne una seconda copia: due formule uguali scritte in due
    punti prima o poi smettono di esserlo.
    """
    if n_new <= 0:
        return []
    return suggest_shares(wallet, [None] * n_new)


def format_share(amount) -> str:
    """Quota leggibile: percentuale o importo. '' se non interpretabile."""
    if amount is None:
        return ""
    s = str(amount).strip()
    if not s:
        return ""
    if s.endswith("%"):
        return s
    try:
        sats = int(float(s))
    except Exception:
        return s
    if sats == PLACEHOLDER_SATS:
        return "da definire"
    if sats >= 1_000_000:
        return f"{sats / 1e8:.8f}".rstrip("0").rstrip(".") + " BTC"
    return f"{sats:,} sat".replace(",", ".")


# ===========================================================================
#  Lettura difensiva del will (data di consegna e hash)
# ===========================================================================

def _will_tx(item):
    """Estrae la transazione da una voce del will di BAL.

    Serve tolleranza su due fronti, verificati sul codice di BAL 0.6.1:

    * la voce viene usata sia come dizionario (``will[w]["tx"]``) sia come
      oggetto (``will[wid].tx``), a seconda del punto del codice;
    * il valore ``tx`` puo' essere gia' una transazione oppure una stringa
      serializzata, che BAL converte in modo pigro con ``tx_from_any``.

    Ritorna la transazione o None, senza mai sollevare.
    """
    tx = None
    try:
        if hasattr(item, "get"):
            tx = item.get("tx")
        if tx is None:
            tx = getattr(item, "tx", None)
    except Exception:
        return None
    if tx is None:
        return None
    if isinstance(tx, str):
        try:
            from electrum.transaction import tx_from_any
            tx = tx_from_any(tx)
        except Exception as e:
            _logger.info(f"transazione del will non interpretabile: {e}")
            return None
    return tx


def read_will_info(wallet) -> dict:
    """
    {indirizzo: {"date": datetime|None, "txid": str}} ricavato dal will di BAL.

    Struttura di BAL: will = {txid: voce}, dove la voce porta la transazione
    con il proprio locktime e i propri output.

    Difensiva per scelta: qualunque cosa non torni, la voce viene saltata e
    al limite il dizionario resta vuoto, cosi' i fogli escono senza data ne'
    hash invece di fallire. E' la struttura interna di un altro plugin e puo'
    cambiare senza preavviso.
    """
    out = {}
    try:
        will = _plain(wallet.db.get(BAL_WILL_KEY, {}) or {})
        items = will.items() if hasattr(will, "items") else []
    except Exception as e:
        _logger.info(f"will non leggibile: {e}")
        return out

    for wid, item in items:
        try:
            tx = _will_tx(item)
            if tx is None:
                continue

            locktime = getattr(tx, "locktime", None)
            date = None
            if isinstance(locktime, int) and locktime >= LOCKTIME_IS_TIME:
                from datetime import datetime
                date = datetime.fromtimestamp(locktime)

            try:
                txid = tx.txid() or str(wid)
            except Exception:
                txid = str(wid)

            for o in tx.outputs():
                addr = getattr(o, "address", None)
                if not addr:
                    continue
                prev = out.get(addr)
                # se un indirizzo compare in piu' transazioni teniamo quella
                # con la data piu' vicina: e' la prima che l'erede vedra'
                if prev is None:
                    out[addr] = {"date": date, "txid": txid}
                elif date and prev.get("date") and date < prev["date"]:
                    out[addr] = {"date": date, "txid": txid}
        except Exception as e:
            _logger.info(f"voce del will ignorata ({wid}): {e}")
            continue
    return out


# ===========================================================================
#  Registro nostro
# ===========================================================================

def _registry(wallet) -> dict:
    try:
        d = wallet.db.get(REGISTRY_KEY, None)
    except Exception:
        d = None
    if not isinstance(d, dict):
        return {"version": REGISTRY_VERSION, "entries": []}
    # _plain e non dict(): una copia superficiale lascerebbe dentro gli
    # oggetti di Electrum, che poi non si riescono a riscrivere.
    d = _plain(d)
    entries = d.get("entries")
    return {"version": d.get("version", REGISTRY_VERSION),
            "entries": entries if isinstance(entries, list) else []}


def _persist(wallet) -> bool:
    """Forza la scrittura su disco. db.put marca soltanto come modificato: qui
    dentro ci sono seed, non preferenze."""
    fn = getattr(wallet, "save_db", None)
    if callable(fn):
        try:
            fn()
            return True
        except Exception as e:
            _logger.error(f"save_db fallito: {e}")
    try:
        wallet.db.write(wallet.storage)
        return True
    except Exception as e:
        _logger.error(f"scrittura wallet fallita: {e}")
    return False


def _save_registry(wallet, reg) -> None:
    wallet.db.put(REGISTRY_KEY, {"version": REGISTRY_VERSION,
                                 "entries": [dict(e) for e in reg["entries"]]})
    _persist(wallet)


def registry_entries(wallet) -> list:
    return _registry(wallet)["entries"]


def entry_by_address(wallet, address: str):
    for e in _registry(wallet)["entries"]:
        if e.get("address") == address:
            return dict(e)
    return None


def wallet_has_password(wallet) -> bool:
    try:
        return bool(wallet.has_password())
    except Exception:
        # nel dubbio diciamo di no: meglio bloccare che scrivere seed in chiaro
        return False


def next_envelope(wallet) -> str:
    used = []
    for e in _registry(wallet)["entries"]:
        try:
            used.append(int(str(e.get("envelope") or "0")))
        except Exception:
            continue
    return f"{(max(used) + 1) if used else 1:02d}"


def _amount_field(amount) -> str:
    """Normalizza l'importo per la lista di BAL: percentuale ("30%") o
    satoshi. None o vuoto -> il segnaposto, con la stessa funzione di sempre:
    superare i controlli di BAL finche' l'utente non mette la quota vera."""
    if amount is None or str(amount).strip() == "":
        return str(int(PLACEHOLDER_SATS))
    s = str(amount).strip()
    if s.endswith("%"):
        try:
            float(s[:-1])
        except Exception:
            raise EasyHeirsError(f"quota non valida: {s!r}")
        return s
    try:
        return str(int(float(s)))
    except Exception:
        raise EasyHeirsError(f"importo non valido: {amount!r}")


def add_generated(wallet, name: str, address: str, xpub: str, mnemonic: str,
                  envelope: str = "", amount=None, locktime=None) -> None:
    """
    Scrive un beneficiario generato: voce in BAL + voce nel nostro registro.

    Entrambi i dizionari vengono riletti dal wallet subito prima di scrivere
    e aggiornati in merge, cosi' non si perde nulla di quanto inserito da BAL
    o dall'utente nel frattempo.
    """
    if not wallet_has_password(wallet):
        raise NoWalletPassword(
            "il wallet non ha password: i seed verrebbero salvati in chiaro")

    name = (name or "").strip()
    if not name:
        raise EasyHeirsError("il nome non puo' essere vuoto")

    from electrum import bitcoin, constants
    if not bitcoin.is_address(address, net=constants.net):
        raise EasyHeirsError(f"indirizzo non valido su questa rete: {address}")

    heirs = read_heirs_raw(wallet)
    if name in heirs:
        raise DuplicateName(f"esiste gia' un beneficiario di nome {name!r}")

    if locktime is None:
        locktime = int(time.time()) + 365 * 24 * 3600

    # tupla: e' il formato che BAL si aspetta per le voci di "heirs"
    heirs[name] = (str(address), _amount_field(amount), str(int(locktime)))
    wallet.db.put(BAL_HEIRS_KEY, heirs)

    reg = _registry(wallet)
    reg["entries"].append({
        "name": name,
        "address": address,
        "xpub": xpub,
        "seed": mnemonic,
        "envelope": envelope or next_envelope(wallet),
        "created": int(time.time()),
        "printed_at": None,
    })
    _save_registry(wallet, reg)


def add_provided(wallet, name: str, address: str,
                 amount=None, locktime=None) -> None:
    """Beneficiario che ha fornito il proprio indirizzo: nessun seed, quindi
    nessuna voce nel registro e nessun vincolo sulla password."""
    name = (name or "").strip()
    if not name:
        raise EasyHeirsError("il nome non puo' essere vuoto")
    from electrum import bitcoin, constants
    if not bitcoin.is_address(address, net=constants.net):
        raise EasyHeirsError(f"indirizzo non valido su questa rete: {address}")

    heirs = read_heirs_raw(wallet)
    if name in heirs:
        raise DuplicateName(f"esiste gia' un beneficiario di nome {name!r}")
    if locktime is None:
        locktime = int(time.time()) + 365 * 24 * 3600
    heirs[name] = (str(address), _amount_field(amount), str(int(locktime)))
    wallet.db.put(BAL_HEIRS_KEY, heirs)
    _persist(wallet)


def delete_beneficiary(wallet, name: str, delete_seed: bool = False) -> dict:
    """Toglie un beneficiario dalla lista eredi di BAL.

    Comportamento (deciso con l'utente):
      * di default toglie SOLO la voce dalla lista di BAL (``heirs``); se il
        beneficiario era stato generato da Easy Heirs, il suo seed resta nel
        nostro registro, cosi' nulla va perso e lo si puo' ristampare o
        riaggiungere;
      * con ``delete_seed=True`` rimuove ANCHE il seed dal registro. Operazione
        irreversibile: se a quell'indirizzo sono gia' stati inviati bitcoin,
        diventano irrecuperabili. La conferma spetta all'interfaccia.

    Il collegamento fra lista di BAL e registro e' l'INDIRIZZO, non il nome
    (come per il resto del plugin). Ritorna un piccolo riepilogo di cosa e'
    stato fatto.
    """
    result = {"removed_from_list": False, "seed_deleted": False,
              "address": None}

    heirs = read_heirs_raw(wallet)
    addr = None
    if name in heirs:
        try:
            addr = heirs[name][HEIR_ADDRESS]
        except Exception:
            addr = None
        del heirs[name]
        wallet.db.put(BAL_HEIRS_KEY, heirs)
        result["removed_from_list"] = True
        result["address"] = addr

    if delete_seed and addr:
        reg = _registry(wallet)
        before = len(reg["entries"])
        reg["entries"] = [e for e in reg["entries"]
                          if e.get("address") != addr]
        if len(reg["entries"]) != before:
            _save_registry(wallet, reg)   # scrive su disco
            result["seed_deleted"] = True
        else:
            _persist(wallet)
    else:
        _persist(wallet)

    _logger.info(f"beneficiario {name!r} rimosso dalla lista "
                 f"(seed cancellato: {result['seed_deleted']})")
    return result


def set_heir_amount(wallet, name: str, amount) -> None:
    """Aggiorna SOLO la quota (percentuale o importo) di un erede nella lista
    di BAL. Indirizzo e data restano intatti.

    L'importo passa da ``_amount_field``, che accetta una percentuale
    ("25%") o un importo in satoshi e rifiuta valori non validi. Vuoto ->
    torna al segnaposto (come alla creazione). Non tocca il seed ne' il
    registro: cambia solo il campo quota della voce ``heirs`` di BAL.
    """
    heirs = read_heirs_raw(wallet)
    if name not in heirs:
        raise EasyHeirsError(f"beneficiario non trovato: {name!r}")
    v = heirs[name]
    try:
        addr = v[HEIR_ADDRESS]
        locktime = v[HEIR_LOCKTIME]
    except Exception:
        raise EasyHeirsError(f"voce non valida per {name!r}")
    heirs[name] = (str(addr), _amount_field(amount), str(locktime))
    wallet.db.put(BAL_HEIRS_KEY, heirs)
    _persist(wallet)
    _logger.info(f"quota di {name!r} aggiornata")


def set_envelope(wallet, address: str, envelope: str) -> None:
    reg = _registry(wallet)
    for e in reg["entries"]:
        if e.get("address") == address:
            e["envelope"] = envelope
            _save_registry(wallet, reg)
            return


def mark_printed(wallet, addresses, when=None) -> None:
    """Annota la data di stampa, ma solo su conferma dell'utente."""
    when = int(when or time.time())
    reg = _registry(wallet)
    touched = False
    for e in reg["entries"]:
        if e.get("address") in set(addresses):
            e["printed_at"] = when
            touched = True
    if touched:
        _save_registry(wallet, reg)


# ===========================================================================
#  Vista unificata per l'interfaccia
# ===========================================================================

def beneficiaries(wallet) -> list:
    """
    Elenco completo, di entrambi i tipi, ordinato per nome.

    Il tipo si deduce dalla presenza dell'indirizzo nel nostro registro:
    non e' un campo da tenere aggiornato, quindi non puo' desincronizzarsi.
    """
    heirs = read_bal_heirs(wallet)
    reg = {e.get("address"): e for e in _registry(wallet)["entries"]}
    will = read_will_info(wallet)

    rows = []
    for name in sorted(heirs, key=lambda s: s.lower()):
        h = heirs[name]
        addr = h.get("address")
        mine = reg.get(addr)
        w = will.get(addr, {})
        rows.append({
            "name": name,
            "address": addr,
            "generated": mine is not None,
            "xpub": (mine or {}).get("xpub", ""),
            "envelope": (mine or {}).get("envelope", ""),
            "printed_at": (mine or {}).get("printed_at"),
            "share": format_share(h.get("amount")),
            "amount_raw": h.get("amount"),
            "placeholder_amount": format_share(h.get("amount")) == "da definire",
            "date": w.get("date"),
            "txid": w.get("txid", ""),
        })
    return rows


def seed_for(wallet, address: str):
    """Il seed di un beneficiario generato, per la stampa. None se non nostro."""
    e = entry_by_address(wallet, address)
    return e.get("seed") if e else None


# ===========================================================================
#  Esportazione della lista eredi nel formato di BAL
# ===========================================================================

def export_heirs_to_bal_json(wallet, path: str) -> int:
    """Scrive su ``path`` la lista eredi nel formato che il plugin BAL importa.

    BAL memorizza ogni erede come una lista di tre stringhe
    ``[indirizzo, quota, locktime]`` sotto la chiave ``heirs`` del wallet, e la
    sua funzione Import legge esattamente un dizionario
    ``{nome: [indirizzo, quota, locktime]}``. Easy Heirs scrive gia' gli eredi
    in quella stessa chiave, quindi qui basta rileggerla e riversarla su file,
    normalizzando ogni voce a tre stringhe cosi' il file risulta importabile in
    BAL senza alcun ritocco.

    Vengono inclusi TUTTI gli eredi presenti nella lista di BAL: sia quelli con
    seed generato da Easy Heirs sia quelli che hanno fornito il proprio
    indirizzo. E' la lista completa, pronta per l'Import di BAL.

    IMPORTANTE: il file contiene solo indirizzi, quote e date, MAI i seed. I
    seed non entrano nella lista di BAL e non devono uscire da questo computer
    se non sui fogli da stampare.

    Ritorna il numero di eredi scritti. Non modifica nulla nel wallet.
    """
    try:
        raw = read_heirs_raw(wallet)
    except Exception as e:
        raise EasyHeirsError(f"lettura lista eredi fallita: {e}")

    out = {}
    for name, v in raw.items():
        # Ogni voce di BAL e' una sequenza [indirizzo, quota, locktime]. La
        # normalizziamo a tre stringhe: se una voce e' malformata la saltiamo
        # invece di far fallire l'intero export.
        try:
            out[str(name)] = [str(v[HEIR_ADDRESS]),
                              str(v[HEIR_AMOUNT]),
                              str(v[HEIR_LOCKTIME])]
        except Exception:
            _logger.info(f"voce non esportabile, saltata: {name!r}")
            continue

    if not out:
        raise EasyHeirsError(
            "la lista eredi e' vuota: non c'e' niente da esportare")

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise EasyHeirsError(f"scrittura del file fallita: {e}")

    _logger.info(f"esportati {len(out)} eredi in {path}")
    return len(out)


# ===========================================================================
#  Rimozione dei nostri dati
# ===========================================================================

def removal_summary(wallet) -> dict:
    entries = _registry(wallet)["entries"]
    return {
        "seeds": [e for e in entries if e.get("seed")],
        "never_printed": [e for e in entries
                          if e.get("seed") and not e.get("printed_at")],
        "envelopes": sum(1 for e in entries if e.get("envelope")),
        "print_dates": sum(1 for e in entries if e.get("printed_at")),
    }


def remove_data(wallet, remove_metadata: bool = True,
                remove_seeds: bool = False) -> None:
    """
    Rimuove i dati di questo plugin. Non tocca mai heirs, will, chiavi o fondi.

    Rimuovere i seed e' irreversibile: dopo, l'unica copia sono i fogli
    stampati. L'interfaccia deve chiedere conferma esplicita e avvisare se
    qualche foglio non risulta ancora stampato.
    """
    reg = _registry(wallet)
    if remove_seeds:
        wallet.db.put(REGISTRY_KEY, None)
        _persist(wallet)
        _logger.info("registro beneficiari rimosso, seed compresi")
        return
    if remove_metadata:
        for e in reg["entries"]:
            e["envelope"] = ""
            e["printed_at"] = None
        _save_registry(wallet, reg)
        _logger.info("metadati rimossi, seed conservati")


def slugify(text: str) -> str:
    keep = []
    for ch in unicodedata.normalize("NFKD", text or ""):
        if ch.isalnum():
            keep.append(ch.lower())
        elif ch in (" ", "-", "_"):
            keep.append("_")
    slug = "".join(keep).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "beneficiario"
