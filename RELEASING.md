# Come si pubblica una release di Easy Heirs

Procedura fissa per produrre una release firmata e verificabile. Va seguita
ogni volta: genera sempre lo stesso insieme di file.

La chiave di firma del progetto e' **SAFE21dev `<info@safe21.io>`**, impronta
`33E3393DFB10F4C45AE6F1E8206C20114CA96172` (identificativo breve
`206C20114CA96172`). La chiave pubblica sta nel repository come
[`SAFE21dev.asc`](SAFE21dev.asc) e viene allegata a ogni release.

## Cosa contiene ogni release

Per la versione `X.Y.Z` la pagina della release porta questi allegati:

| File | Cos'e' |
|------|--------|
| `bal_easy_heirs_vX.Y.Z.zip` | il plugin, da caricare in Electrum |
| `bal_easy_heirs_vX.Y.Z.zip.sha256` | impronta SHA-256 dello ZIP |
| `bal_easy_heirs_vX.Y.Z.zip.asc` | firma GPG, leggibile (testo) |
| `bal_easy_heirs_vX.Y.Z.zip.sig` | firma GPG, binaria |
| `SAFE21dev.asc` | la chiave pubblica di firma |

## Passi

### 1. Cambia il numero di versione (in tre punti)

Lo stesso `X.Y.Z` va scritto in:

- `bal_easy_heirs/VERSION`
- `bal_easy_heirs/manifest.json` (campo `"version"`)
- `bal_easy_heirs/core.py` (costante `RUNNING_VERSION`)

Il terzo e' il numero che il codice conosce di se' mentre gira, e serve ad
accorgersi che Electrum sta ancora usando la versione precedente. Se restasse
indietro, il plugin darebbe quell'avviso a sproposito a ogni avvio: per
questo `build_release.py` **rifiuta di costruire** se i tre non coincidono.

Fai il commit di questa modifica.

### 2. Costruisci ZIP e impronta (build riproducibile)

Dalla radice del repository:

```bash
python scripts/build_release.py
```

Scrive `dist/bal_easy_heirs_vX.Y.Z.zip` e il suo `.sha256`. La build e'
riproducibile: rieseguendola si ottiene uno ZIP identico byte per byte e la
stessa impronta, quindi chiunque puo' ricostruirlo e confrontare.

Vale anche fra computer diversi perche' lo script normalizza i file di testo
a LF prima di archiviarli. Git memorizza LF, ma una copia di lavoro su
Windows con `core.autocrlf=true` scrive CRLF sul disco: senza quella
normalizzazione lo stesso commit produrrebbe uno ZIP diverso, e un'impronta
diversa, a seconda di chi lo costruisce.

### 3. Fai provare lo ZIP prima di firmare

Si firma **solo cio' che e' stato provato**. Consegna lo ZIP, aspetta
conferma che funzioni, e solo allora prosegui. Se dopo la prova cambia anche
una riga di codice, cambia il numero di versione: due file diversi con lo
stesso numero rendono muto il controllo della versione obsoleta, e chi
installa il secondo crede di provarlo mentre sta usando ancora il primo.

### 4. Firma lo ZIP (solo chi cura la release)

Serve la chiave privata e la sua passphrase, quindi si fa a mano e non da
script. Su Windows la firma va fatta con il gpg di **Gpg4win**, non con
quello incluso in Git (che usa un portachiavi vuoto).

In Git Bash:

```bash
cd "dist"
"/c/Program Files/GnuPG/bin/gpg.exe" --local-user 206C20114CA96172 --armor --detach-sign bal_easy_heirs_vX.Y.Z.zip
"/c/Program Files/GnuPG/bin/gpg.exe" --local-user 206C20114CA96172 --detach-sign bal_easy_heirs_vX.Y.Z.zip
```

In PowerShell la sintassi e' diversa: il percorso con gli spazi va eseguito
con l'operatore di chiamata `&`.

```
cd "dist"
& "C:\Program Files\GnuPG\bin\gpg.exe" --local-user 206C20114CA96172 --armor --detach-sign bal_easy_heirs_vX.Y.Z.zip
& "C:\Program Files\GnuPG\bin\gpg.exe" --local-user 206C20114CA96172 --detach-sign bal_easy_heirs_vX.Y.Z.zip
```

Attenzione a non mescolare le due sintassi: in Bash la `&` iniziale significa
tutt'altro e il comando fallisce senza spiegare perche'.

Il primo comando produce il file `.asc` (leggibile), il secondo il `.sig`
(binario). La passphrase si digita nella finestra di Gpg4win.

### 5. Verifica prima di pubblicare

```bash
cd dist
sha256sum -c bal_easy_heirs_vX.Y.Z.zip.sha256
gpg --verify bal_easy_heirs_vX.Y.Z.zip.asc bal_easy_heirs_vX.Y.Z.zip
```

Atteso: `bal_easy_heirs_vX.Y.Z.zip: OK` e
`Good signature from "SAFE21dev <info@safe21.io>"`.

### 6. Applica il tag al commit

```bash
git tag -a vX.Y.Z -m "Easy Heirs vX.Y.Z"
git push origin vX.Y.Z
```

### 7. Crea la pagina della release

La CLI `gh` non e' installata, quindi si usa il sito:

1. Vai su <https://github.com/ManX-SAFE21/EasyHeirs/releases> → **Draft a new
   release**.
2. Scegli il tag `vX.Y.Z` dal menu **"Choose a tag"**, in alto a sinistra.
   E' un campo diverso dal titolo: scrivere il numero nel titolo non basta, e
   la pubblicazione fallisce con *"tag name can't be blank"*. Non usare la
   voce *"Create new tag ... on publish"*, che creerebbe un tag nuovo al posto
   di quello gia' pubblicato e verificato.
3. Carica i cinque allegati della tabella qui sopra (i quattro file in
   `dist/` piu' `SAFE21dev.asc`, che sta nella radice del repository).
4. Scrivi le note della release in italiano, con le novita' e il blocco di
   verifica (vedi il README).
5. Pubblica.

### 8. Ricontrolla dal sito

Scarica gli allegati **dalla pagina pubblicata** e rifai le verifiche del
punto 5, importando la chiave da `SAFE21dev.asc` scaricato anch'esso dalla
release. E' l'unico modo di controllare cio' che ricevera' davvero chi
scarica, invece di cio' che c'e' sul proprio disco.

## Note

- `dist/` e' escluso da git: gli allegati sono prodotti della build, non
  sorgenti. Nel repository stanno solo `SAFE21dev.asc`,
  `scripts/build_release.py` e questo documento.
- La chiave privata non va mai messa nel repository ne' caricata da nessuna
  parte. Si condivide soltanto `SAFE21dev.asc`, che e' quella pubblica.
