# Easy Heirs

A free companion plugin for [Electrum Wallet](https://electrum.org) that helps you prepare the heir list for **BAL — Bitcoin After Life**.

BAL Easy Heirs lets you generate a printable, fold-in-three A4 sheet for each beneficiary: for people without their own wallet it creates a fresh address, BIP39 seed phrase and public key offline; for people who already have an address it produces a one-page summary card. Once ready, the heir list can be exported as JSON and imported directly into BAL.

## Features

- Add beneficiaries by generating a new offline wallet (address + BIP39 seed) or by entering an existing address
- Smart quota recalculation across beneficiaries (percentages or fixed amounts)
- Edit a beneficiary's quota after creation
- Remove a beneficiary, with an optional safety-gated seed deletion
- Export the beneficiary list to JSON for import into BAL
- Printable, styled A4 sheets matching the SAFE21 brand
- No internet connection required to generate seeds — no payment, no unlock step

## Requirements

- Electrum Wallet 4.7 or later

## Installation

1. Download the latest release ZIP.
2. In Electrum, go to **Tools → Plugins → Load plugin from ZIP** (or place the extracted `bal_easy_heirs` folder in Electrum's `plugins` directory).
3. Enable **BAL Easy Heirs** from the plugin list.

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
