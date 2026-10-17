# Read-only: inspect public AYANA HTML. No DNS or production changes.
$ErrorActionPreference = 'Stop'
$guides = @(
  @{ Path = ''; Heading = '' },
  @{ Path = 'whatsapp-check-ins-for-parents'; Heading = 'WhatsApp check-ins for parents who live far away' },
  @{ Path = 'medicine-reminders-for-parents'; Heading = 'Medicine reminders for parents on WhatsApp' },
  @{ Path = 'nri-parent-care'; Heading = 'Stay close to parents in India while living abroad' }
)
$results = foreach ($guide in $guides) {
  $url = 'https://www.ayanabott.com/' + $guide.Path
  try {
    $response = Invoke-WebRequest -Uri $url -TimeoutSec 15 -UseBasicParsing
    $html = [string]$response.Content
    $title = [regex]::Match($html, '(?is)<title[^>]*>(.*?)</title>').Groups[1].Value.Trim()
    $h1 = [regex]::Match($html, '(?is)<h1[^>]*>(.*?)</h1>').Groups[1].Value.Trim()
    $canonical = [regex]::Match($html, '(?is)<link\b[^>]*rel=["'']canonical["''][^>]*href=["'']([^"'']+)').Groups[1].Value
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
      $digest = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($html))).Replace('-', '').Substring(0, 16)
    } finally {
      $sha.Dispose()
    }
    [pscustomobject]@{
      Url = $url
      Status = [int]$response.StatusCode
      Title = $title
      H1 = $h1
      Canonical = $canonical
      ExpectedHeadingInHtml = if ($guide.Path) { $html.Contains($guide.Heading) } else { $null }
      HtmlHashPrefix = $digest
    }
  } catch {
    [pscustomobject]@{ Url = $url; Status = 'unreachable'; ErrorType = $_.Exception.GetType().Name }
  }
}
$results | Format-List
