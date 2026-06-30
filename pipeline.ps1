$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host ""
Write-Host "Reorganizando dados..." -ForegroundColor Cyan
python src/reorganize_twitter.py
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Lematizando featnames..." -ForegroundColor Cyan
python src/lemma_ego_network.py --no-clusters
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Clusterizando featnames..." -ForegroundColor Cyan
$env:GEMINI_API_KEY = "SUA_CHAVE_AQUI"
python src/run_gemini_cluster.py --all-exports
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Gerando banco de dados..." -ForegroundColor Cyan
python src/generate_ego_network_db.py
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Exportando grafos..." -ForegroundColor Cyan
python src/export_interactive_graph.py --todos
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "Pipeline finalizado!" -ForegroundColor Green
