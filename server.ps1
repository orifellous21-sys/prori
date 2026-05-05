param(
  [int]$Port = 5173
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Prefix = "http://127.0.0.1:$Port/"
$Types = @{
  ".html" = "text/html; charset=utf-8"
  ".css" = "text/css; charset=utf-8"
  ".js" = "text/javascript; charset=utf-8"
  ".json" = "application/json; charset=utf-8"
  ".wav" = "audio/wav"
  ".mp3" = "audio/mpeg"
  ".webm" = "audio/webm"
}

$Listener = [System.Net.HttpListener]::new()
$Listener.Prefixes.Add($Prefix)
$Listener.Start()
Set-Content -LiteralPath (Join-Path $Root "server.ready") -Value $Prefix

while ($Listener.IsListening) {
  $Context = $Listener.GetContext()
  $Response = $Context.Response

  try {
    $RequestedPath = [System.Uri]::UnescapeDataString($Context.Request.Url.AbsolutePath)
    if ($RequestedPath -eq "/") {
      $RelativePath = "index.html"
    } else {
      $RelativePath = $RequestedPath.TrimStart("/").Replace("/", [System.IO.Path]::DirectorySeparatorChar)
    }

    $FullPath = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($Root, $RelativePath))
    if (-not $FullPath.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $FullPath -PathType Leaf)) {
      $Response.StatusCode = 404
      $Bytes = [System.Text.Encoding]::UTF8.GetBytes("Not found")
    } else {
      $Response.StatusCode = 200
      $Extension = [System.IO.Path]::GetExtension($FullPath)
      $Response.ContentType = if ($Types.ContainsKey($Extension)) { $Types[$Extension] } else { "application/octet-stream" }
      $Bytes = [System.IO.File]::ReadAllBytes($FullPath)
    }

    $Response.ContentLength64 = $Bytes.Length
    $Response.OutputStream.Write($Bytes, 0, $Bytes.Length)
  } catch {
    $Response.StatusCode = 500
    $Bytes = [System.Text.Encoding]::UTF8.GetBytes("Server error")
    $Response.ContentLength64 = $Bytes.Length
    $Response.OutputStream.Write($Bytes, 0, $Bytes.Length)
  } finally {
    $Response.OutputStream.Close()
  }
}
