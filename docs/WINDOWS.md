# Windows setup (preview)

Windows support selects Windows Credential Manager explicitly; macOS continues
to use Keychain. Unsupported platforms fail closed. No plaintext credential
fallback is used. Live Evernote verification is still required before treating
the Windows integration as production ready.

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).
In a regular PowerShell window, from the checkout:

```powershell
./scripts/setup-windows.ps1 -Languages en,tr
```

Omit `-Languages` for the interactive question. Options include Turkish and
English, or **other languages — for example French (`fr`), German (`de`), Spanish
(`es`), or any combination**. Include all languages used within mixed notes.
For example: `./scripts/setup-windows.ps1 -Languages en,tr,fr`.
Languages outside these five require additional models and validation.

The script creates a new private policy with content access **blocked**, preserves
existing policies, and installs/tests the selected masking packs. On Windows,
policy files receive a protected DACL granting full access only to their owner
and Local System. Updates apply that DACL to the temporary file before writing
private IDs. If permission changes fail, setup stops; do not bypass that error.
Use a local NTFS checkout where your account can change file permissions.
Restricted agent sandboxes may not have `WRITE_DAC`; run the script in your own
PowerShell session in that case. No administrator account should be necessary
for files you own. Turkish model files are stored in the ignored `.models/`
directory inside the checkout on Windows.

## Sign in and enable only a fictional test note

Create an Evernote note containing fictional names, an `example.org` email and
a fake secret. Obtain its internal link and use its first note UUID. Edit the
private `.everwrap-local.json`, preserving languages and any exclusions:

```json
{
  "allowed_note_id": "REPLACE_WITH_YOUR_DUMMY_NOTE_UUID",
  "blocked_note_ids": [],
  "access_mode": "single_note",
  "content_mode": "redacted",
  "languages": ["en", "tr"]
}
```

Resolve which notes to block before enabling broader access; titles alone do
not identify exclusions. Do not put private IDs or tokens in the repository.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& ./.venv/Scripts/python.exe -m everwrap.connect
```

Complete read-only Evernote consent in your browser on this computer. The callback
listens on `127.0.0.1:8766`. Tokens and OAuth client information go to Windows
Credential Manager under service `EverWrap:official-evernote-mcp`.

Windows limits each credential blob to [2560 bytes](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw).
Large OAuth records are stored as bounded chunks, all encrypted by Credential
Manager, with a generation and checksum manifest. New chunks are written before
the manifest replaces the previous record, so an interrupted write preserves the
previous grant. Missing or corrupt chunks are rejected. Records remain on this
machine; no plaintext token file or roaming credential fallback is used. Existing
single-record credentials are readable and migrate on their next update.

Configure your MCP client with the absolute `.venv/Scripts/python.exe` path,
arguments `-m everwrap.server`, and `PYTHONPATH` pointing to this checkout's `src`.
The stdio process is started by the client; it is not an HTTP service.

Verify discovery of all three safe tools, the synthetic note's redacted read,
a synthetic blocked-ID denial, and reconnect/token refresh before enabling
broader access. Do not disable masking to get past a failed check. Windows
credential-store and callback tests alone do not prove a live Evernote connection.

## Checks

Local Windows verification on 2026-09-18: **106 core tests passed**, including
native protected-DACL inspection after policy replacement, Credential Manager
write/read/delete, loopback OAuth callback validation, and subprocess stdio tool
discovery/denial, large Unicode credential roundtrips, refresh/reopen, interrupted
writes, corruption rejection and legacy migration. OAuth regression tests cover
expired persisted tokens, refresh without repeat consent, transient failures,
rejected refresh grants, issuer/endpoint validation, and read-only scope enforcement.

A live expired read-only grant was successfully refreshed and tool metadata was
retrieved without opening another consent page. English and Turkish synthetic
masking checks also passed locally. These checks do not prove real-note retrieval
or masking accuracy on every note.

When a saved access token receives HTTP 401, EverWrap tries one refresh against
the stored credential's validated Evernote issuer before allowing the SDK's
interactive setup flow. Temporary refresh failures preserve the saved grant;
rejected refresh grants still require connection setup. Write access is never
requested or accepted.

```powershell
& ./.venv/Scripts/python.exe -m pytest --ignore=tests/test_release_gate.py -q
```

The full suite requires all five language packs. The historical baseline in
`test_release_gate.py` deliberately retains known failures. The Windows tests
write/read/delete a uniquely named fictional credential and verify policy ACLs
after replacement. They never read existing credentials or Evernote notes.

To remove this installation, first remove its MCP entry from your client, then
remove only its `EverWrap:official-evernote-mcp` credentials and corresponding
`EverWrap:official-evernote-mcp:chunks:` entries using Windows
Credential Manager. Remove the checkout and its local models when no longer
needed. Never clear unrelated credentials.
