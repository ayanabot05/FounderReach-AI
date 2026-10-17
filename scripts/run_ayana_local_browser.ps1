# Isolated AYANA browser integration: localhost PostgreSQL, API and React only.
# Run from an approved local shell; no production .env or paid services.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pg = 'C:\Program Files\PostgreSQL\18\bin'
$data = Join-Path $root '.local_pg_ayana'
$backend = 'C:\Users\gunak\Downloads\ayana_whatsapp\backend'
$frontend = 'C:\Users\gunak\Downloads\ayana_whatsapp\frontend'
if (-not (Test-Path (Join-Path $data 'PG_VERSION'))) { throw 'Isolated local PostgreSQL cluster is missing' }
# Never let production provider credentials inherited from the shell enter tests.
Get-ChildItem Env: | Where-Object { $_.Name -match '^(SUPABASE|DATABASE|RAZORPAY|STRIPE|DODO|OPENAI|ANTHROPIC|META|WHATSAPP|REDIS|S3|AWS|GOOGLE|SMTP|SENDGRID|RESEND|TWILIO)_' } |
    ForEach-Object { Remove-Item -LiteralPath ("Env:" + $_.Name) }
$env:APP_ENV = 'test'
$env:PYTHON_DOTENV_DISABLED = '1'
$env:SUPABASE_DB_URL = 'postgresql://ayana_test@127.0.0.1:55439/ayana_delivery_local'
$env:DATABASE_URL = $env:SUPABASE_DB_URL
$env:JWT_SECRET = 'local-test-only-jwt-secret-with-no-production-access'
$env:ADMIN_EMAIL = 'admin@example.com'
$env:ADMIN_PASSWORD = 'LocalTestOnly123!'
$env:WHATSAPP_ENABLED = 'false'
$env:PAYMENTS_ENABLED = 'false'
$env:SCHEDULER_ENABLED = 'false'
$env:CORS_ORIGINS = 'http://localhost:3005'
$env:DB_MIN_POOL_SIZE = '1'
$env:DB_MAX_POOL_SIZE = '5'
$env:REACT_APP_BACKEND_URL = 'http://localhost:8005'
$env:LOCAL_CHROME_EXECUTABLE = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
& (Join-Path $pg 'pg_ctl.exe') -D $data -l (Join-Path $data 'server.log') -o '-h 127.0.0.1 -p 55439' -w start
if ($LASTEXITCODE -ne 0) { throw 'Local PostgreSQL did not start' }
$api = $null
try {
    $api = Start-Process -FilePath 'python' -ArgumentList @('-m','uvicorn','server:app','--host','127.0.0.1','--port','8005') -WorkingDirectory $backend -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root 'ayana_local_api.stdout.log') -RedirectStandardError (Join-Path $root 'ayana_local_api.stderr.log')
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 1
        if ($api.HasExited) { throw 'Local API exited before readiness' }
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8005/docs' -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
    }
    if (-not $ready) { throw 'Local API did not become ready' }
    Push-Location $frontend
    try {
        & .\node_modules\.bin\playwright.cmd test tests/e2e/guide-attribution-local.spec.js --config playwright.config.js --reporter=list
        if ($LASTEXITCODE -ne 0) { throw 'Local browser test failed' }
    } finally { Pop-Location }
} finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
    & (Join-Path $pg 'pg_ctl.exe') -D $data -m immediate -w stop
}
