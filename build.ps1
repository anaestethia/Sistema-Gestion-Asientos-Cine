$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ProjectRoot

try {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        throw "No se encontró Python. Instala Python 3 y asegúrate de que 'python' esté en PATH."
    }

    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creando entorno virtual..."
        & $PythonCommand.Source -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "No se pudo crear el entorno virtual."
        }
    }

    Write-Host "Instalando el proyecto y PyInstaller..."
    & $VenvPython -m pip install -e ".[build]"
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron instalar las dependencias de compilación."
    }

    Write-Host "Compilando la aplicación..."
    $BuildArguments = @(
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "GestionAsientosCine",
        "--paths", "src",
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", "build",
        "launcher.py"
    )
    & $VenvPython -m PyInstaller @BuildArguments
    if ($LASTEXITCODE -ne 0) {
        throw "La compilación falló. Revisa los mensajes anteriores."
    }

    Write-Host ""
    Write-Host "Compilación completada: $ProjectRoot\dist\GestionAsientosCine.exe"
    Write-Host "Los datos se guardarán en dist\cine_data.json junto al ejecutable."
}
finally {
    Pop-Location
}
