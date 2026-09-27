# Security notes

This document summarizes a security review of Easy Heirs (code as of
v0.6.9), covering how it generates and stores beneficiary seeds, and where
that material can leave the wallet file. The **Paper wallets** section below
was added later, for the feature introduced in v0.8.0.

## What is solid

- **Seed generation.** `generate_mnemonic()` uses `os.urandom` (the
  operating system's cryptographic RNG), computes BIP39 entropy/checksum
  correctly, and independently re-validates the checksum before returning
  the phrase. The `random` module is never used for this — it would be
  predictable. See [`core.py`](bal_easy_heirs/core.py).
- **Seed storage.** `add_generated()` refuses to store a beneficiary's
  seed unless the wallet has a password set. Without a password, Electrum's
  wallet file is stored unencrypted, so the plugin blocks the operation
  rather than writing recovery words in the clear.
- **No network calls.** The plugin is fully offline — the earlier
  payment/unlock step was removed specifically so generating seeds never
  requires an internet connection.
- **Clipboard.** Only the public address is ever copied to the clipboard
  (the "Copy address" action). The seed phrase is never copied.
- **PDF export guard.** Saving beneficiary sheets to PDF is blocked in two
  independent ways: the UI grays out the button and explains why (with a
  tooltip), and the underlying `_save_pdf()` method itself refuses to write
  any file if the selection includes a beneficiary whose seed the plugin
  generated — even if the UI guard were somehow bypassed.

## The one real gap found

The regular **"Print selected"** flow opens the operating system's native
print dialog (`QPrintDialog`), which lists every printer installed on the
machine — including virtual ones: "Microsoft Print to PDF", network
printers, shared or cloud-connected printers (OneNote, etc.).

Today the only safeguard is a **text warning** shown before that dialog
opens ("use a directly connected printer, never a network or cloud one").
Nothing technically prevents choosing "Print to PDF" and ending up with a
file containing recovery words on disk anyway — the same risk the PDF-save
block above was built to prevent, reached through a different door.

**Possible mitigation (not yet implemented, by request):** show a second,
printer-specific warning *after* the user picks a printer rather than
before, naming the chosen printer and highlighting it in red if its name
matches common virtual/PDF/network printer patterns (e.g. "PDF", "XPS",
"OneNote", "Fax", "Send to", "Microsoft Print"). This is not a hard
guarantee — Qt has no fully reliable way to detect every virtual printer —
but it would raise attention at the critical moment.

## Paper wallets

Paper wallets are fresh wallets generated only to be printed and later
funded. They are not beneficiaries and have nothing to do with BAL's heir
list, and their threat model is different from the sheets above, so they are
reviewed separately here.

- **Nothing is stored, anywhere.** `generate_paper_wallets()` never receives
  the wallet object — the signature itself makes that visible — and writes
  nothing to the wallet file, to Electrum's config, or to any file of its
  own. The seeds exist in the process memory of the open dialog and, after
  printing, on paper. Closing the dialog drops them.
- **The consequence is by design and is severe.** There is no second copy.
  If a sheet is lost, destroyed or printed badly, the funds sent to that
  address are unrecoverable by anyone, including the person who created it.
  The dialog says so before generating, the sheet repeats it, reprinting
  stays available while the dialog is open, and closing asks for explicit
  confirmation.
- **No wallet password is required, and that is not a weakening.** The
  password requirement on beneficiary seeds exists because those seeds are
  written into the wallet file; here nothing is written, so there is nothing
  for a password to protect.
- **Seed generation.** BIP39 phrases follow exactly the path reviewed above
  (`os.urandom`, checksum verified) and, when the reference `mnemonic`
  library shipped with Electrum is importable, are additionally validated by
  it — an independent implementation that shares no code with ours. A phrase
  either library rejects is never printed. The alternative Electrum-native
  format is produced by Electrum's own `make_seed`, with Electrum's
  randomness, and the plugin refuses to print it unless Electrum itself
  confirms the phrase is a valid segwit seed.
- **The sheet states its own provenance.** The back prints the entropy
  source, the number of bits, and whether that second independent check
  actually ran — so the person holding the sheet does not have to take
  anyone's word for how the key was made. (If the instructions above it ever
  leave too little room, that note is dropped rather than printed over the
  protection band, where it would be unreadable anyway.)
- **Same print-dialog gap, and it is the only exit.** Printing goes through
  the same native `QPrintDialog` described above, with the same warnings and
  the same unresolved risk of choosing a virtual "Print to PDF" printer.
  There is no PDF-save action in the paper wallet dialog at all, and nothing
  is ever copied to the clipboard there.
- **The two structural limits below do not apply.** Paper wallet seeds are
  never in the `.wallet` file, so they cannot travel in a wallet backup and
  cannot be exposed by removing the wallet password later.

## Minor points worth being aware of (structural limits, not bugs)

1. **Wallet backups.** Generated seeds live encrypted inside the same
   `.wallet` file as the owner's own keys. If that file is included in an
   automatic cloud backup (Dropbox, Google Drive, etc.), the encrypted
   seeds travel with it.
2. **Removing the wallet password later.** If the wallet password is
   removed after seeds have been generated, those seeds remain in the file
   and become readable in the clear — this is Electrum's own behavior, not
   specific to this plugin.

## Status

No code changes were made as a result of this review; the print-dialog
gap is documented here for future reference and left as-is per the
project owner's decision (2026-08-14).
