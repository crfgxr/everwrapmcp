param(
    [ValidateSet('en', 'tr', 'fr', 'de', 'es')]
    [string[]]$Languages
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$previousPythonPath = $env:PYTHONPATH
$previousPath = $env:PATH
Push-Location $repoRoot
try {
    $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
    $uvExe = if ($uvCommand) { $uvCommand.Source } else { Join-Path $repoRoot '.tools/uv.exe' }
    if (-not (Test-Path -LiteralPath $uvExe)) {
        throw 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/'
    }
    & $uvExe sync --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Runtime installation failed.' }
    $pythonExe = Join-Path $repoRoot '.venv/Scripts/python.exe'
    & $uvExe pip install --python $pythonExe -r requirements-live.txt
    if ($LASTEXITCODE -ne 0) { throw 'Live dependency installation failed.' }
    $env:PYTHONPATH = Join-Path $repoRoot 'src'
    $env:PATH = (Split-Path -Parent $uvExe) + [IO.Path]::PathSeparator + $env:PATH
    & $pythonExe -m everwrap.init_policy
    if ($LASTEXITCODE -ne 0) { throw 'Private policy initialization failed.' }
    if ($Languages) {
        & $pythonExe -m everwrap.setup --languages @Languages
    } else {
        & $pythonExe -m everwrap.setup
    }
    if ($LASTEXITCODE -ne 0) { throw 'Language setup failed; access settings were preserved.' }
    Write-Host 'Runtime ready. New installations keep note access blocked. Follow docs/WINDOWS.md.'
} finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:PATH = $previousPath
    Pop-Location
}
