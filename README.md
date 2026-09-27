# Easy Heirs

A free companion plugin for [Electrum Wallet](https://electrum.org) that helps you prepare the heir list for **BAL — Bitcoin After Life**.

Easy Heirs lets you generate a printable, fold-in-three A4 sheet for each beneficiary: for people without their own wallet it creates a fresh address, BIP39 seed phrase and public key offline; for people who already have an address it produces a one-page summary card. Once ready, the heir list can be exported as JSON and imported directly into BAL.

## Features

- Add beneficiaries by generating a new offline wallet (address + BIP39 seed) or by entering an existing address
- Smart quota recalculation across beneficiaries (percentages or fixed amounts)
- Edit a beneficiary's quota after creation
- Remove a beneficiary, with an optional safety-gated seed deletion
- Export the beneficiary list to JSON for import into BAL
- Printable, styled A4 sheets matching the SAFE21 brand
- Print paper wallets: brand-new wallets to fund later, in BIP39 or Electrum's own seed format
- No internet connection required to generate seeds — no payment, no unlock step

## Paper wallets

Besides the heir sheets, Easy Heirs can print up to 20 **paper wallets** at a
time: fresh wallets, generated offline, meant to be printed first and funded
afterwards by sending coins to the address on the sheet. They are not
beneficiaries and never enter BAL's heir list.

Their seeds are **never stored** — not in the wallet file, not in a file of
their own. They exist in memory while the dialog is open and on paper after
that, so a lost or badly printed sheet means the funds sent to it are
unrecoverable. The dialog lets you reprint until you close it, and asks for
confirmation before discarding the words.

Each sheet can use **BIP39** (the default: restorable in almost any wallet,
but you must also type the derivation path, which is printed on the sheet) or
**Electrum's native format** (restorable essentially only in Electrum, with no
options to tick and no path to type — fewer things to get wrong). Beneficiary
sheets are always BIP39: they end up in someone else's hands.

The back of every paper wallet states how the key was generated — entropy
source and size, and whether the independent BIP39 reference check ran — so
the holder does not have to take anyone's word for it. See
[SECURITY.md](SECURITY.md) for the full threat model.

## Requirements

- Electrum Wallet 4.7 or later

## Installation

1. Download the latest release ZIP.
2. In Electrum, go to **Tools → Plugins → Load plugin from ZIP** (or place the extracted `bal_easy_heirs` folder in Electrum's `plugins` directory).
3. Enable **Easy Heirs** from the plugin list.

**You do not need to restart Electrum.** On enabling a plugin Electrum calls
`reload_windows()`, which re-runs the hooks this plugin uses, so the menu
entries and the status-bar icon appear straight away in the windows you
already have open.

The one case that *does* need a restart is **replacing an already-installed
ZIP with a newer one** — which in practice only happens while developing.
That is a Python limitation, not an Electrum one: once a module has been
imported it stays in `sys.modules`, and `zipimport` also caches the archive
index, so dropping in a new ZIP of the same name leaves the old code running.

It can be forced (purging our entries from `sys.modules` and clearing the
zipimport cache on disable) and we deliberately do not, because Qt objects
built by the old classes stay alive alongside new ones from the reloaded
code. That mostly works and occasionally produces a hybrid state that is very
hard to diagnose. On a plugin that handles seed phrases, a restart is a much
better trade than a puzzling bug.

## Verify your download

Every release is published with a SHA-256 checksum and a GPG signature, so
you can confirm the ZIP is authentic and untampered before loading it into
Electrum. Replace `X.Y.Z` with the version you downloaded.

**Check the SHA-256**

```bash
sha256sum -c bal_easy_heirs_vX.Y.Z.zip.sha256
```

Expected: `bal_easy_heirs_vX.Y.Z.zip: OK`.

**Verify the GPG signature**

Import the signing key (from the release assets, or from this repository):

```bash
gpg --import SAFE21dev.asc
```

Then verify:

```bash
gpg --verify bal_easy_heirs_vX.Y.Z.zip.asc bal_easy_heirs_vX.Y.Z.zip
```

Expected output:

```text
gpg: Good signature from "SAFE21dev <info@safe21.io>"
```

Signing key fingerprint: `33E3393DFB10F4C45AE6F1E8206C20114CA96172`

The build is reproducible: running `python scripts/build_release.py` on the
matching source tag produces a byte-identical ZIP, so you can confirm the
published checksum yourself. Maintainers: see [RELEASING.md](RELEASING.md).

## Security

See [SECURITY.md](SECURITY.md) for a review of seed generation and
storage, and a known limitation around the system print dialog.

## Related project

[BAL — Bitcoin After Life](https://bitcoin-after.life) is the main inheritance plugin that reads the JSON list exported here.

## License

MIT — see [LICENSE](bal_easy_heirs/LICENSE).
