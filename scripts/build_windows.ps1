[CmdletBinding()]
param(
    [string]$Python = ".venv\Scripts\python.exe",
    [string]$OutputDirectory = "."
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repositoryRoot

if (-not (Test-Path $Python)) {
    throw "Python do ambiente virtual não encontrado em '$Python'."
}

Write-Host "Compilando a interface com pnpm..."
pnpm --filter job-finder-web build
if ($LASTEXITCODE -ne 0) {
    throw "O build do frontend falhou."
}

& $Python -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller não está instalado. Execute: $Python -m pip install -r packaging\requirements-build.txt"
}

$outputPath = Join-Path $repositoryRoot $OutputDirectory
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$outputPath = (Resolve-Path $outputPath).Path
$workPath = Join-Path $repositoryRoot "build\pyinstaller"
& $Python -m PyInstaller --clean --noconfirm `
    --distpath $outputPath `
    --workpath $workPath `
    packaging\job-finder.spec
if ($LASTEXITCODE -ne 0) {
    throw "O build do executável falhou."
}

$releasePath = $outputPath
$executable = Join-Path $releasePath "JobFinder.exe"
$deadline = (Get-Date).AddSeconds(120)
while (-not (Test-Path -LiteralPath $executable -PathType Leaf) -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 1
}
Start-Sleep -Seconds 1
if (-not (Test-Path -LiteralPath $releasePath -PathType Container) -or
    -not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "A pasta de release não foi criada pelo PyInstaller: $releasePath"
}
if ($releasePath -ne $repositoryRoot) {
    Copy-Item -Path @("README.md", "LICENSE") -Destination $releasePath -Force
}
$hash = $null
for ($attempt = 0; $attempt -lt 30 -and -not $hash; $attempt++) {
    try {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $executable).Hash
    } catch {
        Start-Sleep -Milliseconds 200
    }
}
if (-not $hash) {
    throw "Não foi possível calcular o SHA-256 de $executable"
}
$hash = $hash.ToLowerInvariant()
$pythonVersion = "Python runtime from $Python"
$pyinstallerVersion = "PyInstaller 6.11.0 (packaging/requirements-build.txt)"
$manifest = [ordered]@{
    product = "Job Finder"
    version = "0.1.0"
    builtAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    executable = "JobFinder.exe"
    sha256 = $hash
    python = $pythonVersion
    pyinstaller = $pyinstallerVersion
}
$manifest | ConvertTo-Json | Set-Content (Join-Path $releasePath "release-manifest.json") -Encoding UTF8
Write-Host "Release criada em $releasePath"
Write-Host "SHA-256: $hash"
