$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$reportsDir = Join-Path $projectRoot "reports"

New-Item -ItemType Directory -Force $reportsDir | Out-Null

npm exec newman -- run postman/Demo_API_Testing.postman_collection.json `
  -e postman/Demo_API_Testing.postman_environment.json `
  --working-dir $projectRoot `
  --reporters cli,junit,htmlextra `
  --reporter-junit-export reports/newman-report.xml `
  --reporter-htmlextra-export reports/newman-report.html
