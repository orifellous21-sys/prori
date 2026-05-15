Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LatestDir = Join-Path $Root "output\latest"
$TempDir = Join-Path $Root "output\temp"
New-Item -ItemType Directory -Force -Path $LatestDir, $TempDir | Out-Null

$Hashtags = "#shorts #viral #didyouknow #storytime"
$RedditSources = @("todayilearned", "YouShouldKnow", "technology", "Futurology", "AskReddit", "Showerthoughts")

function Clean-Text {
  param([AllowNull()][string]$Text, [int]$Max = 700)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $value = $Text -replace "https?://\S+", ""
  $value = $value -replace "[<>]", ""
  $value = $value -replace "[^\x20-\x7E]", ""
  $value = $value -replace "\s+", " "
  $value = $value.Trim()
  if ($value.Length -le $Max) { return $value }
  $cut = $value.Substring(0, $Max)
  $lastSpace = $cut.LastIndexOf(" ")
  if ($lastSpace -gt 20) { return $cut.Substring(0, $lastSpace).Trim() }
  return $cut.Trim()
}

function Find-FFmpeg {
  $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  if ($env:LOCALAPPDATA) {
    $installed = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
    if (Test-Path -LiteralPath $installed) { return $installed }
  }

  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "ffmpeg is missing. Installing free ffmpeg now..."
    winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements | Out-Host
    if ($env:LOCALAPPDATA) {
      $installed = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
      if (Test-Path -LiteralPath $installed) { return $installed }
    }
  }

  throw "ffmpeg was not found. Install it with: winget install Gyan.FFmpeg"
}

function Get-Topic {
  $topics = @()
  $headers = @{ "User-Agent" = "automatic-shorts-channel/1.0" }

  foreach ($source in $RedditSources) {
    try {
      $url = "https://www.reddit.com/r/$source/hot.json?limit=20"
      $body = Invoke-RestMethod -Uri $url -Headers $headers -TimeoutSec 15
      foreach ($child in $body.data.children) {
        $post = $child.data
        if ($post.stickied -or $post.over_18 -or [string]::IsNullOrWhiteSpace($post.title)) { continue }
        $created = [DateTimeOffset]::FromUnixTimeSeconds([int64]$post.created_utc)
        $ageHours = [Math]::Max(1, ([DateTimeOffset]::UtcNow - $created).TotalHours)
        $score = [double]$post.ups + ([double]$post.num_comments * 3) - ($ageHours * 8)
        $text = if ($post.selftext) { $post.selftext } else { $post.link_flair_text }
        $topics += [pscustomobject]@{
          Title = Clean-Text $post.title 110
          Text = Clean-Text $text 500
          Source = "reddit/r/$source"
          Url = "https://reddit.com$($post.permalink)"
          Score = $score
        }
      }
    } catch {
      Write-Host "Skipped reddit/r/$source"
    }
  }

  if ($topics.Count -eq 0) {
    return [pscustomobject]@{
      Title = "Why short videos grab attention so fast"
      Text = "The first seconds create an open loop, then each line gives one small reward. That pattern keeps people watching longer than a normal explanation."
      Source = "fallback"
      Url = ""
      Score = 1
    }
  }

  return $topics | Sort-Object Score -Descending | Select-Object -First 1
}

function New-ShortScript {
  param($Topic)
  $title = Clean-Text ($Topic.Title -replace "^TIL\s+", "") 90
  $text = $Topic.Text
  if ([string]::IsNullOrWhiteSpace($text) -or $text.Length -lt 80) {
    $text = "People are reacting because the idea is simple, surprising, and easy to repeat. That is the exact combination short-form platforms love."
  }
  $openers = @(
    "This sounds fake, but it is real.",
    "Most people would scroll past this, but wait for the twist.",
    "Here is the part nobody expects.",
    "This tiny detail changes the whole story."
  )
  $opener = $openers | Get-Random
  return Clean-Text "$opener $title. At first, that sounds like a random fact. But here is why it actually matters. $text And the strange part is this: people remember stories like this because they feel unfinished until the final detail lands. So if you only remember one thing, remember this story was hiding in plain sight." 950
}

function Write-Voice {
  param([string]$Script, [string]$WavPath)
  $voice = New-Object -ComObject SAPI.SpVoice
  $voices = @($voice.GetVoices())
  $preferred = $voices | Where-Object { $_.GetDescription() -match "David|Mark|Guy|Jenny|Aria|Zira" } | Select-Object -First 1
  if ($preferred) { $voice.Voice = $preferred }
  $stream = New-Object -ComObject SAPI.SpFileStream
  $stream.Open($WavPath, 3)
  $voice.AudioOutputStream = $stream
  $voice.Rate = 2
  $voice.Volume = 100
  $voice.Speak($Script) | Out-Null
  $stream.Close()
}

function Format-AssTime {
  param([double]$Seconds)
  $total = [Math]::Floor($Seconds)
  $cs = [Math]::Floor(($Seconds - $total) * 100)
  $h = [Math]::Floor($total / 3600)
  $m = [Math]::Floor(($total % 3600) / 60)
  $s = $total % 60
  return "{0}:{1:00}:{2:00}.{3:00}" -f $h, $m, $s, $cs
}

function Escape-Ass {
  param([string]$Text)
  return ($Text -replace "\\", "\\" -replace "\{", "(" -replace "\}", ")" -replace "`r?`n", " ")
}

function Split-Sentences {
  param([string]$Text)
  $clean = Clean-Text $Text 2000
  $matches = [regex]::Matches($clean, "[^.!?]+[.!?]?")
  $sentences = @()
  foreach ($match in $matches) {
    $sentence = $match.Value.Trim()
    if ($sentence.Length -gt 0) { $sentences += $sentence }
  }
  if ($sentences.Count -eq 0) { return @($clean) }
  return $sentences
}

function Write-Subtitles {
  param([string]$Script, [string]$AssPath, [double]$Duration)
  $chunks = Split-Sentences $Script

  $weights = @()
  foreach ($chunk in $chunks) {
    $weights += [Math]::Max(5, (($chunk -split "\s+" | Where-Object { $_ }).Count))
  }
  $totalWeight = ($weights | Measure-Object -Sum).Sum
  $events = @()
  $cursor = 0.0
  for ($i = 0; $i -lt $chunks.Count; $i++) {
    $segment = [Math]::Max(2.0, ($Duration * $weights[$i] / $totalWeight))
    $start = $cursor
    $end = if ($i -eq $chunks.Count - 1) { $Duration } else { [Math]::Min($Duration, $cursor + $segment) }
    $override = if ($i -eq 0) { "{\an5\pos(540,730)\fs82\b1}" } else { "{\an5\pos(540,910)\fs68\b1}" }
    $events += "Dialogue: 0,$(Format-AssTime $start),$(Format-AssTime $end),Main,,0,0,0,,$override$(Escape-Ass $chunks[$i])"
    $cursor = $end
    if ($cursor -ge $Duration) { break }
  }

  @"
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Arial,72,&H00FFFFFF,&H003DF2E3,&H00000000,&H88000000,-1,0,0,0,100,100,0,0,1,7,3,5,70,70,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
$($events -join "`r`n")
"@ | Set-Content -LiteralPath $AssPath -Encoding UTF8
}

function Convert-AssPathForFFmpeg {
  param([string]$Path)
  return ($Path -replace "\\", "/" -replace ":", "\:")
}

$ffmpeg = Find-FFmpeg
$topic = Get-Topic
$script = New-ShortScript $topic
$wordCount = ($script -split "\s+" | Where-Object { $_ }).Count
$duration = [Math]::Min(58, [Math]::Max(24, [Math]::Ceiling($wordCount * 0.42)))

$wavPath = Join-Path $TempDir "voice.wav"
$assPath = Join-Path $TempDir "captions.ass"
$videoPath = Join-Path $LatestDir "video.mp4"
$captionPath = Join-Path $LatestDir "caption.txt"
$detailsPath = Join-Path $LatestDir "details.json"

Remove-Item -LiteralPath $wavPath, $assPath, $videoPath, $captionPath, $detailsPath -Force -ErrorAction SilentlyContinue

Write-Host "Creating voice..."
Write-Voice -Script $script -WavPath $wavPath

Write-Host "Creating captions..."
Write-Subtitles -Script $script -AssPath $assPath -Duration $duration

Write-Host "Rendering video..."
$filter = "subtitles='$(Convert-AssPathForFFmpeg $assPath)',drawbox=x=0:y=0:w=iw:h=180:color=black@0.28:t=fill,drawbox=x=70:y=1540:w=940:h=8:color=white@0.45:t=fill"
$music = "aevalsrc=0.020*sin(2*PI*110*t)+0.016*sin(2*PI*220*t)+0.012*sin(2*PI*277.18*t)+0.010*sin(2*PI*329.63*t)+0.006*sin(2*PI*659.25*t):s=44100:d=$duration"
& $ffmpeg -hide_banner -loglevel error -y -f lavfi -i "color=c=0x101820:s=1080x1920:r=30:d=$duration" -i $wavPath -f lavfi -i $music -filter_complex "[1:a]volume=1.0,dynaudnorm=f=150:g=8[voice];[2:a]volume=0.13,afade=t=in:st=0:d=0.8,afade=t=out:st=$([Math]::Max(0, $duration - 1.2)):d=1.2[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.92[aout]" -map 0:v -map "[aout]" -vf $filter -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 160k -shortest $videoPath | Out-Null
if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed while rendering the video." }

$title = Clean-Text $topic.Title 90
$caption = "$title`r`n`r`n$Hashtags"
$caption | Set-Content -LiteralPath $captionPath -Encoding UTF8

[pscustomobject]@{
  createdAt = (Get-Date).ToString("o")
  title = $title
  caption = $caption
  source = $topic.Source
  sourceUrl = $topic.Url
  video = $videoPath
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $detailsPath -Encoding UTF8

Remove-Item -LiteralPath $wavPath, $assPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "DONE. Upload this video:"
Write-Host $videoPath
Write-Host ""
Write-Host "Copy this caption:"
Write-Host $captionPath
