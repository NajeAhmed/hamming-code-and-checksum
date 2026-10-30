# Simple zero-dependency HTTP server for Windows PowerShell
$port = 8000
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")

try {
    $listener.Start()
} catch {
    $port = 8080
    $listener = New-Object System.Net.HttpListener
    $listener.Prefixes.Add("http://localhost:$port/")
    $listener.Start()
}

$url = "http://localhost:$port/"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Localhost server active at: $url" -ForegroundColor Green
Write-Host " Serving files from: $PSScriptRoot" -ForegroundColor Yellow
Write-Host " Press Ctrl+C in this window to stop the server." -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

# Open in browser
Start-Process $url

$dir = $PSScriptRoot
while ($listener.IsListening) {
    try {
        $context = $listener.GetContext()
        $req = $context.Request
        $res = $context.Response

        $relPath = $req.Url.LocalPath
        if ($relPath -eq "/" -or [string]::IsNullOrWhiteSpace($relPath)) {
            $relPath = "/index.html"
        }

        $localPath = Join-Path $dir ($relPath.TrimStart('/').Replace('/', '\'))

        if (Test-Path $localPath -PathType Leaf) {
            $contentBytes = [System.IO.File]::ReadAllBytes($localPath)
            if ($localPath.EndsWith(".html")) { $res.ContentType = "text/html; charset=utf-8" }
            elseif ($localPath.EndsWith(".js")) { $res.ContentType = "application/javascript; charset=utf-8" }
            elseif ($localPath.EndsWith(".css")) { $res.ContentType = "text/css; charset=utf-8" }
            elseif ($localPath.EndsWith(".json")) { $res.ContentType = "application/json; charset=utf-8" }
            else { $res.ContentType = "text/plain; charset=utf-8" }

            $res.ContentLength64 = $contentBytes.Length
            $res.OutputStream.Write($contentBytes, 0, $contentBytes.Length)
        } else {
            $res.StatusCode = 404
            $msg = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found")
            $res.OutputStream.Write($msg, 0, $msg.Length)
        }
        $res.OutputStream.Close()
    } catch {
        # continue loop
    }
}

