# QA TR-20260815-010 - Python gate runner (HEAD 944a996)
# Paths derived from $PSScriptRoot (ASCII-only script body).
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
$results['uv_sync'] = Gate 'uv-sync' { uv sync --locked --group dev }
$results['validate_repository'] = Gate 'validate_repository' { uv run python -m scripts.validate_repository }
$results['ruff_format_check'] = Gate 'ruff_format_check' { uv run ruff format --check packages scripts tests apps }
$results['ruff_check'] = Gate 'ruff_check' { uv run ruff check . }
$results['mypy_scripts'] = Gate 'mypy_scripts' { uv run mypy scripts }
$results['mypy_strict'] = Gate 'mypy_strict' { uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api apps/desktop }
$results['pytest'] = Gate 'pytest' { uv run python -m pytest -q }

"--- RESULTS ---"
$results.GetEnumerator() | Sort-Object Key | ForEach-Object { "$($_.Key)=$($_.Value)" }
