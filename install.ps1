# llm-instill-wiki installer (Windows PowerShell)
# Usage:
#   irm https://raw.githubusercontent.com/Laggom/llm-instill-wiki/main/install.ps1 | iex
# Or, after cloning the repo manually:
#   ./install.ps1

$ErrorActionPreference = 'Stop'
$RepoUrl = 'https://github.com/Laggom/llm-instill-wiki.git'
$TargetDir = 'llm-instill-wiki'

# --- Step 1: ensure we're inside the repo --------------------------------
$inRepo = $false
if (Test-Path 'CLAUDE.md') {
    $head = Get-Content 'CLAUDE.md' -TotalCount 5 -ErrorAction SilentlyContinue
    if ($head -match 'LLM Wiki Operating Schema') {
        $inRepo = $true
    }
}

if (-not $inRepo) {
    if (Test-Path $TargetDir) {
        Write-Error "Directory '$TargetDir' already exists. cd into it and rerun, or remove it first."
        exit 1
    }
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Write-Error "git is required but not found in PATH."
        exit 1
    }
    Write-Host "Cloning into .\$TargetDir ..."
    git clone --quiet $RepoUrl $TargetDir
    Set-Location $TargetDir
}

# --- Step 2: verify Python 3.10+ -----------------------------------------
$py = $null
foreach ($cmd in 'python3', 'python') {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        try { & $found.Source -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>$null }
        catch { continue }
        if ($LASTEXITCODE -eq 0) { $py = $found.Source; break }
    }
}
if (-not $py) {
    Write-Error "Python 3.10+ is required but was not found in PATH."
    exit 1
}
Write-Host "Python: $(& $py --version)"

# --- Step 3: create content directories ----------------------------------
'raw', 'wiki/sources', 'wiki/concepts', 'wiki/entities', 'instill' | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}

# --- Step 4: scaffold wiki/index.md and wiki/log.md (only if missing) ---
if (-not (Test-Path 'wiki/index.md')) {
    @'
# Index

## Sources

## Concepts

## Entities
'@ | Out-File -FilePath 'wiki/index.md' -Encoding utf8
    Write-Host "Created wiki/index.md"
}

if (-not (Test-Path 'wiki/log.md')) {
    "# Log" | Out-File -FilePath 'wiki/log.md' -Encoding utf8
    Write-Host "Created wiki/log.md"
}

# --- Step 5: smoke-test the scheduler ------------------------------------
& $py 'tools/instill_sched.py' stats | Out-Null

# --- Done ----------------------------------------------------------------
$here = Split-Path -Leaf (Get-Location)
@"

✓ Setup complete.

Next steps:
  1. cd $here   (if not already)
  2. Drop a source file into raw/
  3. Open this directory in Claude Code, or any AGENTS.md / GEMINI.md compatible agent
  4. Tell the agent: "raw/<your-file>.md ingest 해줘"

See README.md for the full guide.
"@ | Write-Host
