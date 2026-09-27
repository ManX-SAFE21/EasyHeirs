# Note di sicurezza

Questo documento riassume l'esame di sicurezza di Easy Heirs (codice alla
v0.6.9): come vengono generati e custoditi i seed dei beneficiari, e da dove
quel materiale puo' uscire dal file del wallet. La sezione **Paper wallet**
e' stata aggiunta in seguito, per la funzione introdotta nella v0.8.0.

## Cosa e' solido

- **Generazione dei seed.** `generate_mnemonic()` usa `os.urandom`, il
  generatore crittografico del sistema operativo, calcola correttamente
  entropia e checksum BIP39 e rivalida il checksum prima di restituire la
  frase. Il modulo `random` non viene mai usato per questo: sarebbe
  prevedibile. Vedi [`core.py`](bal_easy_heirs/core.py).
- **Custodia dei seed.** `add_generated()` si rifiuta di salvare il seed di
  un beneficiario se il wallet non ha una password. Senza password il file
  del wallet di Electrum non e' cifrato, quindi il plugin blocca
  l'operazione invece di scrivere le parole di recupero in chiaro.
- **Nessuna connessione di rete.** Il plugin funziona interamente offline: il
  vecchio passaggio di pagamento e sblocco e' stato rimosso proprio perche'
  generare un seed non richiedesse mai una connessione a internet.
- **Appunti.** Negli appunti finisce solo l'indirizzo pubblico (il comando
  "Copia indirizzo"). La frase di recupero non viene mai copiata.
- **Blocco del salvataggio in PDF.** Salvare in PDF i fogli dei beneficiari
  e' impedito in due modi indipendenti: l'interfaccia disattiva il pulsante e
  spiega perche', e il metodo `_save_pdf()` si rifiuta comunque di scrivere
  qualsiasi file se nella selezione c'e' un beneficiario il cui seed e' stato
  generato dal plugin — anche se la protezione dell'interfaccia venisse
  aggirata.

## L'unica falla vera emersa

Il normale percorso di **stampa** apre la finestra di stampa del sistema
operativo (`QPrintDialog`), che elenca tutte le stampanti installate sul
computer, comprese quelle virtuali: "Microsoft Print to PDF", stampanti di
rete, stampanti condivise o collegate al cloud (OneNote e simili).

Oggi l'unica protezione e' un **avviso testuale** mostrato prima che quella
finestra si apra ("usa una stampante collegata direttamente, mai di rete o
cloud"). Tecnicamente nulla impedisce di scegliere "Stampa su PDF" e
ritrovarsi comunque un file con le parole di recupero sul disco: lo stesso
rischio che il blocco del salvataggio in PDF serviva a evitare, raggiunto da
un'altra porta.

**Possibile mitigazione, non ancora realizzata per scelta:** mostrare un
secondo avviso *dopo* che l'utente ha scelto la stampante invece che prima,
nominando la stampante scelta ed evidenziandola in rosso se il nome
corrisponde ai casi tipici di stampante virtuale o di rete ("PDF", "XPS",
"OneNote", "Fax", "Invia a", "Microsoft Print"). Non sarebbe una garanzia:
Qt non ha un modo affidabile per riconoscere ogni stampante virtuale. Ma
richiamerebbe l'attenzione nel momento decisivo.

## Paper wallet

I paper wallet sono portafogli nuovi, generati solo per essere stampati e
alimentati in seguito. Non sono beneficiari e non hanno nulla a che vedere
con la lista eredi di BAL; il loro modello di rischio e' diverso da quello
dei fogli qui sopra, quindi vengono esaminati a parte.

- **Non viene salvato nulla, da nessuna parte.** `generate_paper_wallets()`
  non riceve nemmeno l'oggetto wallet — lo si vede dalla firma della funzione
  — e non scrive niente: ne' nel file del wallet, ne' nella configurazione di
  Electrum, ne' in un file proprio. I seed esistono nella memoria della
  finestra aperta e, dopo la stampa, sulla carta. Chiudendo la finestra
  spariscono.
- **La conseguenza e' voluta ed e' grave.** Non esiste una seconda copia. Se
  un foglio si perde, si rovina o esce stampato male, i fondi inviati a
  quell'indirizzo non sono piu' recuperabili da nessuno, nemmeno da chi lo ha
  creato. La finestra lo dice prima di generare, il foglio lo ripete, si puo'
  ristampare finche' la finestra resta aperta e alla chiusura viene chiesta
  conferma esplicita.
- **Non serve la password del wallet, e non e' un indebolimento.** Il
  requisito della password sui seed dei beneficiari esiste perche' quei seed
  vengono scritti nel file del wallet; qui non si scrive nulla, quindi non
  c'e' niente che una password debba proteggere.
- **Generazione.** Le frasi BIP39 seguono esattamente il percorso esaminato
  sopra (`os.urandom`, checksum verificato) e, quando la libreria di
  riferimento `mnemonic` fornita con Electrum e' importabile, vengono
  convalidate anche da quella: un'implementazione indipendente, che non
  condivide codice con la nostra. Una frase rifiutata da una delle due non
  viene mai stampata. Il formato alternativo, nativo di Electrum, e' prodotto
  da `make_seed` di Electrum con la casualita' di Electrum, e il plugin si
  rifiuta di stamparlo se Electrum stesso non conferma che la frase e' un
  seed segwit valido.
- **Il foglio dichiara la propria provenienza.** Sul retro sono stampati la
  sorgente di entropia, il numero di bit e se quel secondo controllo
  indipendente e' stato eseguito davvero: chi tiene il foglio non deve
  credere a nessuno sulla parola. (Se le istruzioni sopra occupassero troppo
  spazio, quella nota viene omessa invece di finire stampata sopra la banda
  di protezione, dove sarebbe comunque illeggibile.)
- **Stessa falla della stampa, ed e' l'unica uscita.** La stampa passa per la
  stessa finestra di sistema descritta sopra, con gli stessi avvisi e lo
  stesso rischio irrisolto di scegliere una stampante virtuale "Stampa su
  PDF". Nella finestra dei paper wallet non esiste alcun salvataggio in PDF,
  e non viene mai copiato nulla negli appunti.
- **I due limiti strutturali qui sotto non si applicano.** I seed dei paper
  wallet non stanno nel file `.wallet`, quindi non possono viaggiare in un
  backup del wallet ne' essere esposti togliendo in seguito la password.

## Punti minori da conoscere (limiti strutturali, non difetti)

1. **Backup del wallet.** I seed generati per i beneficiari stanno cifrati
   dentro lo stesso file `.wallet` che contiene le chiavi del proprietario.
   Se quel file finisce in un backup automatico nel cloud (Dropbox, Google
   Drive e simili), i seed cifrati viaggiano con lui.
2. **Password rimossa in un secondo momento.** Se la password del wallet
   viene tolta dopo aver generato dei seed, quei seed restano nel file e
   diventano leggibili in chiaro. E' il comportamento di Electrum, non una
   particolarita' di questo plugin.

## Stato

Da quell'esame non sono derivate modifiche al codice: la falla della finestra
di stampa e' documentata qui per riferimento futuro ed e' stata lasciata
com'e' per decisione del titolare del progetto (14 agosto 2026).
