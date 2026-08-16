# QA TR-20260815-010 - pnpm gate runner (HEAD 944a996)
$ErrorActionPreference = "Continue"
$dir = $PSScriptRoot
$repo = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
Set-Location $repo

"PSVersion=$($PSVersionTable.PSVersion) Repo=$repo"
$top = git rev-parse --show-toplevel
"GitTop=$top"

function Gate($name, [scriptblock]$body) {
    $log = Join-Path $dir "$name.log"
    "# GATE: $name | $(Get-Date -Format o) | cwd=$repo" | Out-File -FilePath $log -Encoding Unicode
    $start = Get-Date
    & $body *>> $log
    $code = $LASTEXITCODE
    $dur = ((Get-Date) - $start).TotalSeconds
    "EXIT=$code DURATION_S=$([math]::Round($dur,1))" | Out-File -FilePath $log -Append -Encoding Unicode
    return $code
}

$results = @{}
$results['pnpm_install'] = Gate 'pnpm-install' { pnpm install --frozen-lockfile }
$results['pnpm_peers'] = Gate 'pnpm-peers' { pnpm peers check }
$results['pnpm_check'] = Gate 'pnpm-check' { pnpm check }
$results['pnpm_build'] = Gate 'pnpm-build' { pnpm build }
$results['contracts_ts'] = Gate 'contracts-ts-check' { pnpm --filter @knowledge-tree/contracts-ts check }

"--- RESULTS ---"
$results.GetEnumerator() | Sort-Object Key | ForEach-Object { "$($_.Key)=$($_.Value)" }
