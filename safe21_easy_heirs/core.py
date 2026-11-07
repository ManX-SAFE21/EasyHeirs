# -*- coding: utf-8 -*-
"""
Easy Heirs di SAFE21
core.py : logica pura, nessuna dipendenza da Qt.

Modello dati (2.0)
------------------
Easy Heirs prepara SOLO i fogli di carta: le guide per i beneficiari e i
paper wallet. Non ha più alcun legame con il plugin di eredità: non
legge e non scrive la sua lista eredi né il suo testamento.

    nostro   wallet.db["safe21_beneficiaries"]  -> {version, entries: [...]}

Ogni voce è un beneficiario: nome, indirizzo e, se il seed l'abbiamo
generato noi, seed, chiave pubblica estesa, numero di busta e data di
stampa. Chi ha fornito il proprio indirizzo ha solo nome e indirizzo.

L'erede si aggiunge poi nel plugin di eredità a mano, leggendo con la
fotocamera il QR dell'indirizzo stampato sul foglio: le quote e la data di
consegna stanno soltanto lì. Così nessuno dei due plugin può riscrivere
i dati dell'altro (con la lista condivisa, una finestra aperta riscriveva
la sua vecchia copia e cancellava l'erede appena aggiunto).

Nota di compatibilità
----------------------
Non registriamo NULLA in json_db / stored_dict: solo strutture JSON
semplici (dict, list, str, int), che non dipendono dall'API di Electrum.
"""

import hashlib
import json
import os
import time
import unicodedata

from electrum.logging import get_logger

_logger = get_logger(__name__)


# Chiave nostra. Nessun'altra parte del wallet viene letta o scritta.
REGISTRY_KEY = "safe21_beneficiaries"
REGISTRY_VERSION = 1

# Derivazione dei seed generati.
DERIVATION_ACCOUNT = "m/84'/0'/0'"      # da stampare: è quello che si digita
DERIVATION_FIRST = "m/84'/0'/0'/0/0"    # solo per ricavare il primo indirizzo
XTYPE = "p2wpkh"

SEED_WORDS = 12

# I due formati di frase che il plugin sa produrre.
#
#   BIP39     lo standard: funziona in quasi tutti i portafogli, ma per
#             ripristinarlo bisogna anche digitare il percorso di derivazione,
#             ed è l'errore più facile da fare (percorso sbagliato ->
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
# zpub, gli stessi che già produciamo con BIP39.
ELECTRUM_SEED_TYPE = "segwit"
# Percorso usato internamente da Electrum per i seed segwit. Lo teniamo come
# informazione, NON come istruzione: non va digitato da nessuna parte.
ELECTRUM_DERIVATION = "m/0'"


# Versione del CODICE che sta girando adesso. Non viene letta da un file:
# deve valere esattamente quanto era scritto nei sorgenti al momento
# dell'import, perché serve proprio a confrontarla con quella dichiarata dal
# file su disco. scripts/build_release.py verifica che coincida con il
# manifest a ogni build, così non può restare indietro per distrazione.
RUNNING_VERSION = "2.0.0"


PLUGIN_NAME = "safe21_easy_heirs"   # il campo "name" del manifest, come lo usa Electrum


def _package_path():
    """Il file .zip (o la cartella) da cui questo plugin è stato caricato.

    Dentro uno ZIP ``__file__`` è un percorso finto del tipo
    ``.../plugin.zip/safe21_easy_heirs/core.py``: risalendo si trova il primo
    elemento che esiste davvero su disco. Può essere l'archivio, ma anche
    soltanto la cartella dei plugin, se quell'archivio nel frattempo è stato
    rimosso -- ed è proprio ciò che accade aggiornando.
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

    Il confronto è sul campo ``name`` del manifest, non sul nome del file:
    è lo stesso criterio con cui Electrum riconosce i plugin esterni, e il
    nome del file è invece libero (il nostro ci mette dentro la versione).
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
    """La versione più recente di questo plugin presente su disco, o None.

    Guarda tutta la cartella perché un aggiornamento non sovrascrive niente:
    arriva come archivio con un altro nome. Fra più copie vince la più alta,
    così uno ZIP vecchio dimenticato accanto a quello nuovo non fa scattare
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
    ancora usando quello vecchio, perché Python tiene in memoria i moduli
    già importati e nemmeno riabilitare il plugin li ricarica.
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
    """True se la libreria BIP39 di riferimento è importabile.

    Electrum si porta dietro ``mnemonic`` (l'implementazione di riferimento
    dello standard). Non è garantita su ogni build, quindi la trattiamo come
    un di più: se c'è la usiamo per un controllo indipendente, se non c'è
    si prosegue con il nostro.
    """
    try:
        from mnemonic import Mnemonic
        Mnemonic("english")
        return True
    except Exception:
        return False


def _reference_rejects(mnemonic: str) -> bool:
    """True SOLO se la libreria di riferimento dice che la frase non è valida.

    Se la libreria manca o solleva un errore suo, ritorna False: un problema
    della libreria non deve impedire di generare un seed che il nostro
    controllo ha già dato per buono.
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

    # Doppia verifica prima di consegnare la frase. La prima è nostra; la
    # seconda, quando disponibile, la fa la libreria BIP39 di riferimento, che
    # non condivide una riga di codice con la nostra. Un errore nostro
    # nell'impacchettare i bit verrebbe intercettato lì.
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
    Electrum, con la sua sorgente di casualità (132 bit). Ci limitiamo a
    richiamarla in modo difensivo, perché la firma è cambiata fra versioni,
    e a farci confermare da Electrum stesso che la frase risultante è
    davvero riconosciuta come seed segwit.
    """
    from electrum.mnemonic import Mnemonic
    m = Mnemonic("en")
    try:
        seed = m.make_seed(seed_type=ELECTRUM_SEED_TYPE)
    except TypeError:
        # Firme più vecchie accettavano il tipo come primo argomento.
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

    Il nome della funzione è cambiato fra le versioni (prima ``seed_type``,
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

    Ritorna la stessa coppia {"address", "xpub"} di ``derive_account``, così
    il resto del plugin non deve sapere quale formato sia stato usato.
    """
    from electrum import keystore
    from electrum.bitcoin import pubkey_to_address

    # La firma di from_seed è cambiata fra le versioni di Electrum: oggi è
    # from_seed(seed, *, passphrase, for_multisig=False), cioè la passphrase
    # si passa SOLO per nome, mentre in passato era posizionale. Proviamo le
    # forme note in ordine, dalla più recente alla più vecchia, invece di
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
# Un paper wallet è un portafoglio nuovo, generato solo per essere stampato e
# poi alimentato versandoci dei fondi. A differenza dei beneficiari:
#
#   * NON entra nella lista dei beneficiari (non è un erede);
#   * NON viene salvato da nessuna parte. Niente registro, niente wallet,
#     niente file: il seed esiste solo nella RAM del programma e, dopo la
#     stampa, solo sulla carta.
#
# La conseguenza è voluta ma va ricordata: se il foglio si perde o la stampa
# esce illeggibile, i fondi versati a quell'indirizzo sono irrecuperabili. Per
# questo l'interfaccia consente di ristampare finché la finestra resta
# aperta, e chiede conferma esplicita prima di chiudere e perdere i seed.

MAX_PAPER_WALLETS = 20


def generate_paper_wallets(count: int, num_words: int = SEED_WORDS,
                           seed_kind: str = SEED_KIND_BIP39) -> list:
    """Genera ``count`` paper wallet nuovi, senza salvare nulla.

    Ritorna una lista di dizionari con ``name`` ("paperwallet 01", ...),
    ``address``, ``xpub``, ``seed`` e ``created`` (epoch della generazione).
    La numerazione riparte sempre da 01: non essendo memorizzato nulla, non
    c'è un conteggio precedente a cui agganciarsi.

    ``seed_kind`` sceglie il formato della frase: BIP39 (predefinito, portabile
    ovunque) oppure il formato nativo di Electrum (più semplice da
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
    # dire il vero. Se la libreria non c'è, il foglio non dovrà vantare un
    # controllo che non è avvenuto.
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


def _plain(value):
    """Copia "nuda" di un valore letto dal wallet: solo dict, list e scalari.

    Electrum non restituisce dizionari e liste normali: li avvolge in
    ``StoredDict`` / ``StoredList``, che tengono un riferimento al database --
    e quindi al suo lock. Ogni lista annidata viene convertita così, sempre,
    a prescindere dalle chiavi registrate.

    Il guaio salta fuori solo quando si RISCRIVE: ``db.put`` fa una copia
    profonda del valore, che su un lock non è possibile, e fallisce con
    "cannot pickle '_thread.RLock' object". Per noi significava non riuscire
    più ad aggiungere un beneficiario appena nella lista ce n'era già uno.

    Le tuple diventano liste: è quello che erano già una volta salvate in
    JSON, quindi sul file non cambia nulla.
    """
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


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


def _name_taken(reg, name: str) -> bool:
    """True se nel registro c'è già un beneficiario con questo nome
    (senza distinguere maiuscole e minuscole)."""
    low = name.lower()
    return any((e.get("name") or "").lower() == low for e in reg["entries"])


def _check_new(reg, name: str, address: str) -> str:
    """Controlli comuni prima di aggiungere: nome non vuoto e non ripetuto,
    indirizzo valido su questa rete e non già presente. Ritorna il nome
    ripulito dagli spazi."""
    name = (name or "").strip()
    if not name:
        raise EasyHeirsError("il nome non può essere vuoto")
    if _name_taken(reg, name):
        raise DuplicateName(f"esiste già un beneficiario di nome {name!r}")
    from electrum import bitcoin, constants
    if not bitcoin.is_address(address, net=constants.net):
        raise EasyHeirsError(f"indirizzo non valido su questa rete: {address}")
    if any(e.get("address") == address for e in reg["entries"]):
        raise EasyHeirsError(f"indirizzo già presente: {address}")
    return name


def add_generated(wallet, name: str, address: str, xpub: str, mnemonic: str,
                  envelope: str = "") -> None:
    """Aggiunge un beneficiario con seed generato da noi.

    Il seed resta nel wallet, protetto dalla sua password, per poter
    ristampare un foglio smarrito: senza password non si scrive niente.
    """
    if not wallet_has_password(wallet):
        raise NoWalletPassword(
            "il wallet non ha password: i seed verrebbero salvati in chiaro")
    reg = _registry(wallet)
    name = _check_new(reg, name, address)
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


def add_provided(wallet, name: str, address: str) -> None:
    """Aggiunge un beneficiario che ha fornito il proprio indirizzo: nessun
    seed, quindi nessun vincolo sulla password del wallet."""
    reg = _registry(wallet)
    name = _check_new(reg, name, address)
    reg["entries"].append({
        "name": name,
        "address": address,
        "created": int(time.time()),
        "printed_at": None,
    })
    _save_registry(wallet, reg)


def delete_beneficiary(wallet, name: str) -> dict:
    """Toglie un beneficiario dalla lista di Easy Heirs, seed compreso.

    Operazione irreversibile per chi ha un seed generato: se a
    quell'indirizzo sono già stati inviati bitcoin e il foglio stampato
    va perso, diventano irrecuperabili. La conferma spetta all'interfaccia.
    Non tocca mai il plugin di eredità: se l'erede è anche lì, va tolto
    anche lì, a mano. Ritorna ``{"removed", "address", "had_seed"}``.
    """
    reg = _registry(wallet)
    keep, gone = [], None
    for e in reg["entries"]:
        if gone is None and e.get("name") == name:
            gone = e
        else:
            keep.append(e)
    if gone is None:
        return {"removed": False, "address": None, "had_seed": False}
    reg["entries"] = keep
    _save_registry(wallet, reg)
    _logger.info(f"beneficiario {name!r} rimosso (aveva un seed: {bool(gone.get('seed'))})")
    return {"removed": True, "address": gone.get("address"),
            "had_seed": bool(gone.get("seed"))}


def update_beneficiary(wallet, name: str, new_name: str,
                       new_address=None) -> dict:
    """Cambia nome e, solo per chi ha fornito il proprio indirizzo,
    l'indirizzo di un beneficiario.

    L'indirizzo di un beneficiario con seed generato non si cambia: nasce da
    quelle parole, e un altro indirizzo non sarebbe più spendibile con il
    seed stampato. Se qualcosa cambia e il foglio era già stampato, la data
    di stampa si azzera: il foglio di carta ha i dati vecchi e va ristampato.
    Non tocca il plugin di eredità. Ritorna ``{"changed", "reprint"}``.
    """
    reg = _registry(wallet)
    entry = next((e for e in reg["entries"] if e.get("name") == name), None)
    if entry is None:
        raise EasyHeirsError(f"beneficiario non trovato: {name!r}")
    new_name = (new_name or "").strip()
    if not new_name:
        raise EasyHeirsError("il nome non può essere vuoto")
    low = new_name.lower()
    if any(e is not entry and (e.get("name") or "").lower() == low
           for e in reg["entries"]):
        raise DuplicateName(f"esiste già un beneficiario di nome {new_name!r}")
    address = entry.get("address")
    if new_address is not None and new_address.strip() != address:
        new_address = new_address.strip()
        if entry.get("seed"):
            raise EasyHeirsError(
                "l'indirizzo di un beneficiario con seed generato non si cambia")
        from electrum import bitcoin, constants
        if not bitcoin.is_address(new_address, net=constants.net):
            raise EasyHeirsError(
                f"indirizzo non valido su questa rete: {new_address}")
        if any(e is not entry and e.get("address") == new_address
               for e in reg["entries"]):
            raise EasyHeirsError(f"indirizzo già presente: {new_address}")
        address = new_address
    changed = new_name != entry.get("name") or address != entry.get("address")
    reprint = bool(changed and entry.get("printed_at"))
    if changed:
        entry["name"] = new_name
        entry["address"] = address
        if reprint:
            entry["printed_at"] = None
        _save_registry(wallet, reg)
        _logger.info(f"beneficiario {name!r} modificato")
    return {"changed": changed, "reprint": reprint}


def beneficiaries(wallet) -> list:
    """Elenco completo, di entrambi i tipi, ordinato per nome.

    ``generated`` vale True se il seed l'abbiamo generato noi: è la
    presenza del seed a dirlo, non un campo da tenere allineato.
    """
    rows = []
    for e in _registry(wallet)["entries"]:
        rows.append({
            "name": e.get("name") or "",
            "address": e.get("address"),
            "generated": bool(e.get("seed")),
            "xpub": e.get("xpub", ""),
            "envelope": e.get("envelope", ""),
            "printed_at": e.get("printed_at"),
        })
    rows.sort(key=lambda r: r["name"].lower())
    return rows


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
#  Seed per la stampa
# ===========================================================================

def seed_for(wallet, address: str):
    """Il seed di un beneficiario generato, per la stampa. None se non nostro."""
    e = entry_by_address(wallet, address)
    return e.get("seed") if e else None


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
    Rimuove i dati di questo plugin. Non tocca mai chiavi o fondi del wallet.

    Rimuovere i seed è irreversibile: dopo, l'unica copia sono i fogli
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
