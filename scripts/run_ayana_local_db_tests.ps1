# Run only AYANA guide attribution tests against the disposable localhost DB.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pg = 'C:\Program Files\PostgreSQL\18\bin'
$data = Join-Path $root '.local_pg_ayana'
if (-not (Test-Path (Join-Path $data 'PG_VERSION'))) { throw 'Isolated local PostgreSQL cluster is missing' }
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
$env:DB_MIN_POOL_SIZE = '1'
$env:DB_MAX_POOL_SIZE = '5'
$env:PYTHONDONTWRITEBYTECODE = '1'
& (Join-Path $pg 'pg_ctl.exe') -D $data -l (Join-Path $data 'server.log') -o '-h 127.0.0.1 -p 55439' -w start
if ($LASTEXITCODE -ne 0) { throw 'Local PostgreSQL did not start' }
try {
    Push-Location 'C:\Users\gunak\Downloads\ayana_whatsapp\backend'
    try {
        python -m pytest tests/test_guide_attribution_integration.py -n 0 -q -p no:cacheprovider
        if ($LASTEXITCODE -ne 0) { throw 'Local database integration suite failed' }
    } finally { Pop-Location }
} finally {
    & (Join-Path $pg 'pg_ctl.exe') -D $data -m immediate -w stop
}
