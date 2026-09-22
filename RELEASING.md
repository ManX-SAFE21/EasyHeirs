# Releasing Easy Heirs

This is the fixed procedure for cutting a signed, verifiable release. Follow
it every time; it always produces the same set of assets.

The signing key for this project is **SAFE21dev `<info@safe21.io>`**,
fingerprint `33E3393DFB10F4C45AE6F1E8206C20114CA96172`
(short key id `206C20114CA96172`). Its public key lives in the repository as
[`SAFE21dev.asc`](SAFE21dev.asc) and is uploaded with every release.

## What each release publishes

For version `X.Y.Z`, the GitHub Release carries these assets:

| File | What it is |
|------|------------|
| `bal_easy_heirs_vX.Y.Z.zip` | the plugin, loadable in Electrum |
| `bal_easy_heirs_vX.Y.Z.zip.sha256` | SHA-256 checksum of the ZIP |
| `bal_easy_heirs_vX.Y.Z.zip.asc` | GPG signature, armored (text) |
| `bal_easy_heirs_vX.Y.Z.zip.sig` | GPG signature, binary |
| `SAFE21dev.asc` | the signing public key |

## Steps

### 1. Bump the version (one source of truth in two files)

Set the same `X.Y.Z` in:

- `bal_easy_heirs/VERSION`
- `bal_easy_heirs/manifest.json` (the `"version"` field)

Commit that change.

### 2. Build the ZIP + checksum (reproducible)

From the repository root:

```bash
python scripts/build_release.py
```

This writes `dist/bal_easy_heirs_vX.Y.Z.zip` and its `.sha256`. The build is
reproducible: re-running it yields a byte-identical ZIP and the same hash, so
anyone can rebuild and confirm the published checksum.

### 3. Sign the ZIP (release manager only)

Signing needs the private key and its passphrase, so it is done by hand, not
by any script. On Windows this is easiest in **PowerShell** (Gpg4win shows
the passphrase dialog):

```bash
cd dist
gpg --local-user 206C20114CA96172 --armor --detach-sign bal_easy_heirs_vX.Y.Z.zip
gpg --local-user 206C20114CA96172 --detach-sign bal_easy_heirs_vX.Y.Z.zip
```

The first command makes the armored `.asc`, the second the binary `.sig`.

### 4. Verify locally before publishing

```bash
cd dist
sha256sum -c bal_easy_heirs_vX.Y.Z.zip.sha256
gpg --verify bal_easy_heirs_vX.Y.Z.zip.asc bal_easy_heirs_vX.Y.Z.zip
```

Expected: `bal_easy_heirs_vX.Y.Z.zip: OK` and
`Good signature from "SAFE21dev <info@safe21.io>"`.

### 5. Tag the commit

```bash
git tag -a vX.Y.Z -m "Easy Heirs vX.Y.Z"
git push origin vX.Y.Z
```

### 6. Create the GitHub Release

`gh` CLI is not installed, so use the web UI:

1. Go to <https://github.com/ManX-SAFE21/EasyHeirs/releases> → **Draft a
   new release**.
2. Choose the tag `vX.Y.Z`.
3. Upload the five assets from the table above (the four `dist/` files plus
   `SAFE21dev.asc` from the repo root).
4. Paste the verification block (see README) into the release notes.
5. Publish.

## Notes

- `dist/` is git-ignored: release artifacts are build outputs, not source.
  Only `SAFE21dev.asc`, `scripts/build_release.py` and this document live in
  the repository.
- Never commit or upload the private key. Only `SAFE21dev.asc` (public) is
  ever shared.
