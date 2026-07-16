param(
    [string]$PythonExe = "python",
    [switch]$Cpu
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$requirements = if ($Cpu) { "requirements.txt" } else { "requirements-cuda.txt" }

Set-Location $projectRoot
if (-not (Test-Path $venvPython)) {
    Write-Host "Criando ambiente virtual com Python 3.10 ou 3.11..."
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente virtual." }
}

$pythonVersion = (& $venvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
if ($pythonVersion -notin @("3.10", "3.11")) {
    throw "Python $pythonVersion não é compatível. Use Python 3.10 ou 3.11."
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar o pip." }
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências." }
& $venvPython -m pip install -e . --no-deps
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o Ninja Narrator." }

& $venvPython -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('Dispositivo:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

Write-Host ""
Write-Host "Instalação concluída. Execute:"
Write-Host "  .\.venv\Scripts\python.exe .\interface.py"
