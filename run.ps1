# Starts Masar: API on http://localhost:8000 and web app on http://localhost:3000
# First time only:  .\.venv\Scripts\python.exe -m masar.pipeline   (run inside .\backend)  -> builds 100k customers + models
$root = $PSScriptRoot
$node = Get-ChildItem "C:\Users\ebi\tools" -Directory -Filter "node-v24*" | Select-Object -First 1
if ($node) { $env:Path = "$($node.FullName);$env:Path" }
if (-not (Test-Path "$root\data\masar.duckdb")) {
  Push-Location "$root\backend"; & "$root\.venv\Scripts\python.exe" -m masar.pipeline; Pop-Location
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; & '$root\.venv\Scripts\python.exe' -m uvicorn masar.api:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:Path='$($node.FullName);'+`$env:Path; cd '$root\web'; npm run dev"
Start-Sleep 8
Start-Process "http://localhost:3000"
