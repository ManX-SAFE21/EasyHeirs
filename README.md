# Easy Heirs di SAFE21

Plugin gratuito per [Electrum Wallet](https://electrum.org) che prepara **i fogli di carta per i beneficiari** di un'eredita' in bitcoin, e i **paper wallet**.

Per ogni beneficiario crea un foglio A4 da stampare e piegare in tre: per chi non ha un portafoglio proprio genera offline indirizzo, frase di recupero BIP39 e chiave pubblica; per chi un indirizzo lo ha gia' fornito produce una scheda di una pagina. Ogni foglio riporta l'indirizzo anche come **codice QR**.

Easy Heirs **non legge e non modifica** la lista eredi o il testamento di nessun altro plugin. Gli eredi si aggiungono poi nel plugin di eredita' (per esempio [Àncòra](https://safe21.io/ancora)): nella finestra del nuovo erede si inquadra con la fotocamera il QR dell'indirizzo stampato sul foglio, senza ricopiarlo a mano. Le quote e la data di consegna si decidono li'.

## Cosa fa

- Aggiunge beneficiari generando un portafoglio nuovo offline (indirizzo + seed BIP39) oppure inserendo un indirizzo gia' esistente
- Stampa fogli A4 curati, nello stile SAFE21, con il QR dell'indirizzo
- Stampa il riepilogo per l'esecutore: nomi, indirizzi e QR, senza segreti
- Tiene i seed generati nel wallet, protetti dalla sua password, per ristampare un foglio smarrito
- Rimuove un beneficiario, con cancellazione del seed protetta da conferma
- Stampa paper wallet: portafogli nuovi da alimentare in seguito, in formato BIP39 o nel formato nativo di Electrum
- Non serve alcuna connessione a internet per generare i seed: nessun pagamento, nessuno sblocco

## Paper wallet

Oltre ai fogli degli eredi, Easy Heirs stampa fino a 20 **paper wallet** per
volta: portafogli nuovi, generati offline, pensati per essere prima stampati
e poi alimentati inviando fondi all'indirizzo sul foglio. Non sono
beneficiari e non entrano mai nella lista dei beneficiari.

I loro seed **non vengono salvati da nessuna parte**: ne' nel file del
wallet, ne' in un file proprio. Esistono in memoria finche' la finestra resta
aperta e, dopo la stampa, solo sulla carta. Percio' un foglio perso o
stampato male significa che i fondi inviati a quell'indirizzo non sono piu'
recuperabili. Finche' la finestra e' aperta si puo' ristampare, e alla
chiusura viene chiesta conferma prima di dimenticare le parole.

Ogni foglio puo' usare **BIP39** (predefinito: si ripristina in quasi tutti i
portafogli, ma bisogna anche digitare il percorso di derivazione, che e'
stampato sul foglio) oppure il **formato nativo di Electrum** (si ripristina
praticamente solo in Electrum, senza opzioni da spuntare e senza percorsi da
digitare: ci sono meno cose da sbagliare). I fogli dei beneficiari sono
sempre BIP39, perche' finiscono in mano ad altri.

Il retro di ogni paper wallet dichiara **come e' stata generata la chiave**:
sorgente di casualita', bit di entropia e se il controllo indipendente con la
libreria BIP39 di riferimento e' stato eseguito davvero. Chi tiene il foglio
non deve credere a nessuno sulla parola. Il quadro completo dei rischi e' in
[SECURITY.md](SECURITY.md).

## Requisiti

- Electrum Wallet **4.8.3 o successivo**. Su versioni più vecchie il plugin non si attiva e lo dice con un messaggio: è stato provato solo da Electrum 4.8.3 in poi, fino alla 4.8.4.

## Installazione

1. Scarica lo ZIP dell'ultima release.
2. In Electrum vai su **Strumenti → Plugin → Carica plugin da ZIP** (oppure copia la cartella `safe21_easy_heirs` scompattata nella cartella `plugins` di Electrum).
3. Abilita **Easy Heirs di SAFE21** dall'elenco dei plugin.

**Non serve riavviare Electrum.** Abilitando un plugin Electrum chiama
`reload_windows()`, che riesegue gli hook usati da questo plugin: le voci di
menu e l'icona nella barra di stato compaiono subito nelle finestre gia'
aperte.

L'unico caso che **richiede il riavvio** e' sostituire uno ZIP gia'
installato con uno piu' recente. E' un limite di Python, non di Electrum: una
volta importato, un modulo resta in `sys.modules`, e `zipimport` tiene in
cache anche l'indice dell'archivio, quindi mettere al suo posto uno ZIP nuovo
lascia in esecuzione il codice vecchio. Il plugin se ne accorge e te lo dice,
invece di lasciarti lavorare con la versione precedente credendo di usare
quella nuova.

Si potrebbe forzare il ricaricamento (togliendo le nostre voci da
`sys.modules` e svuotando la cache di zipimport alla disattivazione) e
deliberatamente non lo facciamo: gli oggetti Qt costruiti dalle classi
vecchie resterebbero vivi accanto a quelli nuovi. Il piu' delle volte
funziona, ogni tanto produce uno stato ibrido difficilissimo da diagnosticare.
Su un plugin che maneggia frasi di recupero, un riavvio e' un prezzo molto
piu' basso di un guasto incomprensibile.

## Verifica del file scaricato

Ogni release e' pubblicata con l'impronta SHA-256 e la firma GPG, cosi' puoi
accertarti che lo ZIP sia autentico e integro prima di caricarlo in Electrum.
Sostituisci `X.Y.Z` con la versione che hai scaricato.

**Controlla l'impronta SHA-256**

```bash
sha256sum -c safe21_easy_heirs_vX.Y.Z.zip.sha256
```

Risultato atteso: `safe21_easy_heirs_vX.Y.Z.zip: OK`.

**Verifica la firma GPG**

Importa la chiave di firma (dagli allegati della release, oppure da questo
repository):

```bash
gpg --import SAFE21dev.asc
```

Poi verifica:

```bash
gpg --verify safe21_easy_heirs_vX.Y.Z.zip.asc safe21_easy_heirs_vX.Y.Z.zip
```

Risultato atteso:

```text
gpg: Good signature from "SAFE21dev <info@safe21.io>"
```

Impronta della chiave di firma: `33E3393DFB10F4C45AE6F1E8206C20114CA96172`

La build e' riproducibile: eseguendo `python scripts/build_release.py` sul tag
corrispondente si ottiene uno ZIP identico byte per byte, quindi l'impronta
pubblicata la puoi ricalcolare da solo. Per chi cura le release:
[RELEASING.md](RELEASING.md).

## Sicurezza

In [SECURITY.md](SECURITY.md) trovi l'analisi di come vengono generati e
custoditi i seed, il modello di rischio dei paper wallet e un limite noto
legato alla finestra di stampa del sistema operativo.

## Insieme a un plugin di eredita'

Easy Heirs prepara solo la carta. Il testamento vero e proprio (eredi,
quote, data di consegna, will-executor) si fa in un plugin di eredita', per
esempio [Àncòra](https://safe21.io/ancora), aggiungendo ogni erede con il QR
stampato sul suo foglio. I due plugin non si scambiano dati: nessuno dei due
puo' modificare quelli dell'altro.

## Licenza

MIT — vedi [LICENSE](safe21_easy_heirs/LICENSE).
