param(
    # ghcr.io/gitleaks/gitleaks:v8.30.1
    [string]$Image = "ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"
)
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$sourcePaths = @(
    "/repo/backend/app",
    "/repo/backend/tests",
    "/repo/backend/scripts",
    "/repo/backend/evals",
    "/repo/frontend/src",
    "/repo/frontend/tests",
    "/repo/frontend/public",
    "/repo/.github",
    "/repo/hooks",
    "/repo/scripts"
)

function Invoke-Gitleaks {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & docker run --rm `
        -v "${repoRoot}:/repo" `
        $Image `
        @Arguments

    if ($LASTEXITCODE -ne 0) {
        throw "Gitleaks failed with exit code $LASTEXITCODE."
    }
}

Write-Host "[1/3] Scanning reachable Git history..."
Invoke-Gitleaks -Arguments @(
    "git",
    "--redact",
    "--no-banner",
    "--verbose",
    "/repo"
)

Write-Host "[2/3] Scanning the staged publication candidate..."
Invoke-Gitleaks -Arguments @(
    "git",
    "--pre-commit",
    "--staged",
    "--redact",
    "--no-banner",
    "--verbose",
    "/repo"
)

Write-Host "[3/3] Scanning project-owned source and test directories..."
foreach ($path in $sourcePaths) {
    Invoke-Gitleaks -Arguments @(
        "dir",
        "--redact",
        "--no-banner",
        $path
    )
}

Write-Host "Secret scan completed: no leaks found."
