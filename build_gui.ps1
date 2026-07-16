param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe",
    [switch]$OneFile,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path $PythonExe)) {
    throw "Python não encontrado em '$PythonExe'. Execute install.ps1 primeiro."
}
if (-not $SkipInstall) {
    & $PythonExe -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o PyInstaller." }
}

$mode = if ($OneFile) { "--onefile" } else { "--onedir" }
$assetSeparator = [IO.Path]::PathSeparator
$logoSource = Join-Path $projectRoot "ninja_narrator\assets"
$logoTarget = "ninja_narrator\assets"

$arguments = @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", $mode,
    "--name", "NinjaNarrator",
    "--add-data", "${logoSource}${assetSeparator}${logoTarget}",
    "--collect-all", "customtkinter",
    "--collect-all", "TTS",
    "--collect-all", "trainer",
    "--collect-all", "coqpit",
    "--collect-all", "librosa",
    "--collect-all", "transformers",
    "--collect-all", "torch",
    "--collect-all", "torchaudio",
    "--collect-all", "torchcodec",
    "--hidden-import", "TTS.tts.configs.xtts_config",
    "--hidden-import", "TTS.tts.models.xtts",
    ".\interface.py"
)

& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o executável." }

$packageRoot = Join-Path $projectRoot "dist\NinjaNarrator"
if ($OneFile) {
    New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
    Copy-Item -LiteralPath ".\dist\NinjaNarrator.exe" -Destination $packageRoot -Force
}
foreach ($directory in @("input_texts", "reference_audio", "output_audio")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $packageRoot $directory) | Out-Null
}
Copy-Item -LiteralPath ".\config.example.toml" -Destination $packageRoot -Force

Write-Host "Pacote pronto em: $packageRoot"
