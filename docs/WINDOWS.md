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

Configure your MCP client with the absolute `.venv/Scripts/python.exe` path,
arguments `-m everwrap.server`, and `PYTHONPATH` pointing to this checkout's `src`.
The stdio process is started by the client; it is not an HTTP service.

Verify discovery of all three safe tools, the synthetic note's redacted read,
a synthetic blocked-ID denial, and reconnect/token refresh before enabling
broader access. Do not disable masking to get past a failed check. Windows
credential-store and callback tests alone do not prove a live Evernote connection.

## Checks

Local Windows verification on 2026-09-18: **80 core tests passed**, including
native protected-DACL inspection after policy replacement, Credential Manager
write/read/delete, loopback OAuth callback validation, and subprocess stdio tool
discovery/denial. This does not verify live Evernote authorization or model-based
masking; those remain separate installation checks.

```powershell
& ./.venv/Scripts/python.exe -m pytest --ignore=tests/test_release_gate.py -q
```

The full suite requires all five language packs. The historical baseline in
`test_release_gate.py` deliberately retains known failures. The Windows tests
write/read/delete a uniquely named fictional credential and verify policy ACLs
after replacement. They never read existing credentials or Evernote notes.

To remove this installation, first remove its MCP entry from your client, then
remove only its `EverWrap:official-evernote-mcp` credentials using Windows
Credential Manager. Remove the checkout and its local models when no longer
needed. Never clear unrelated credentials.
