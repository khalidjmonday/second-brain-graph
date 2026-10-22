<#
Bootstrap a project-local Python runtime, install this project's packages,
and generate the interactive graph. No administrator-wide installation is
performed. Run from PowerShell with:
  .\setup_and_run.ps1
  .\setup_and_run.ps1 -VaultPath 'C:\path\to\my\vault'
#>

[CmdletBinding()]
param(
    [string]$VaultPath = (Join-Path $PSScriptRoot 'demo_notes'),
    [string]$OutputPath = (Join-Path $PSScriptRoot 'index.html')
)

$ErrorActionPreference = 'Stop'

$pythonVersion = '3.14.8'
$runtimeDirectory = Join-Path $PSScriptRoot '.runtime\python'
$installerPath = Join-Path $PSScriptRoot '.runtime\python-installer.exe'
$pythonExe = Join-Path $runtimeDirectory 'python.exe'
$installerUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$expectedSha256 = '759be887b96e736a3ca886daf8d575f18fcae1a09efab6902f42d59e8999f8ef'

New-Item -ItemType Directory -Path (Split-Path -Parent $installerPath) -Force | Out-Null

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Host "Downloading Python $pythonVersion from python.org..."
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

    $actualSha256 = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $expectedSha256) {
        throw "Python installer checksum mismatch. Expected $expectedSha256; got $actualSha256."
    }

    Write-Host "Installing Python into $runtimeDirectory..."
    $installerArguments = @(
        '/quiet'
        'InstallAllUsers=0'
        "TargetDir=`"$runtimeDirectory`""
        'Include_pip=1'
        'Include_launcher=0'
        'PrependPath=0'
        'Shortcuts=0'
        'Include_test=0'
    )
    $install = Start-Process -FilePath $installerPath -ArgumentList $installerArguments -Wait -PassThru
    if ($install.ExitCode -ne 0) {
        throw "Python installer failed with exit code $($install.ExitCode)."
    }
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Python installation did not create $pythonExe."
}

Write-Host 'Installing project dependencies...'
& $pythonExe -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE."
}

Write-Host 'Generating the interactive graph...'
& $pythonExe (Join-Path $PSScriptRoot 'main.py') build $VaultPath --output $OutputPath
if ($LASTEXITCODE -ne 0) {
    throw "Graph generation failed with exit code $LASTEXITCODE."
}

Write-Host "Done. Open $((Resolve-Path -LiteralPath $OutputPath).Path) in your browser."
