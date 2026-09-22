# Security notes

This document summarizes a security review of Easy Heirs (code as of
v0.6.9), covering how it generates and stores beneficiary seeds, and where
that material can leave the wallet file.

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
