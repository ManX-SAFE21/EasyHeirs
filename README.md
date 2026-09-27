# Easy Heirs

Plugin gratuito per [Electrum Wallet](https://electrum.org) che aiuta a preparare la lista degli eredi per **BAL — Bitcoin After Life**.

Easy Heirs crea per ogni beneficiario un foglio A4 da stampare e piegare in tre: per chi non ha un portafoglio proprio genera offline indirizzo, frase di recupero BIP39 e chiave pubblica; per chi un indirizzo lo ha gia' fornito produce una scheda di una pagina. Quando la lista e' pronta si esporta in JSON e si importa direttamente in BAL.

## Cosa fa

- Aggiunge beneficiari generando un portafoglio nuovo offline (indirizzo + seed BIP39) oppure inserendo un indirizzo gia' esistente
- Ricalcola le quote fra i beneficiari (percentuali o importi fissi)
- Permette di modificare la quota di un beneficiario dopo la creazione
- Rimuove un beneficiario, con cancellazione del seed protetta da conferma
- Esporta la lista in JSON da importare in BAL
- Stampa fogli A4 curati, nello stile SAFE21
- Stampa paper wallet: portafogli nuovi da alimentare in seguito, in formato BIP39 o nel formato nativo di Electrum
- Non serve alcuna connessione a internet per generare i seed: nessun pagamento, nessuno sblocco

## Paper wallet

Oltre ai fogli degli eredi, Easy Heirs stampa fino a 20 **paper wallet** per
volta: portafogli nuovi, generati offline, pensati per essere prima stampati
e poi alimentati inviando fondi all'indirizzo sul foglio. Non sono
beneficiari e non entrano mai nella lista eredi di BAL.

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

- Electrum Wallet 4.7 o successivo

## Installazione

1. Scarica lo ZIP dell'ultima release.
2. In Electrum vai su **Strumenti → Plugin → Carica plugin da ZIP** (oppure copia la cartella `bal_easy_heirs` scompattata nella cartella `plugins` di Electrum).
3. Abilita **Easy Heirs** dall'elenco dei plugin.

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
sha256sum -c bal_easy_heirs_vX.Y.Z.zip.sha256
```

Risultato atteso: `bal_easy_heirs_vX.Y.Z.zip: OK`.

**Verifica la firma GPG**

Importa la chiave di firma (dagli allegati della release, oppure da questo
repository):

```bash
gpg --import SAFE21dev.asc
```

Poi verifica:

```bash
gpg --verify bal_easy_heirs_vX.Y.Z.zip.asc bal_easy_heirs_vX.Y.Z.zip
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

## Progetto collegato

[BAL — Bitcoin After Life](https://bitcoin-after.life) e' il plugin di
successione vero e proprio: legge la lista JSON esportata da qui.

## Licenza

MIT — vedi [LICENSE](bal_easy_heirs/LICENSE).
