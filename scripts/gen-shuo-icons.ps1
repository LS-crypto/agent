Add-Type -AssemblyName System.Drawing
function New-ShuoIcon([int]$size, [string]$outPath, [bool]$transparent = $false) {
  $bmp = New-Object System.Drawing.Bitmap $size, $size
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
  if ($transparent) { $g.Clear([System.Drawing.Color]::Transparent) }
  else { $g.Clear([System.Drawing.Color]::FromArgb(255, 30, 30, 30)) }
  $fontSize = [math]::Round($size * ($(if ($transparent) { 0.62 } else { 0.52 })))
  $font = New-Object System.Drawing.Font("Microsoft YaHei UI", $fontSize, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
  $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 59, 130, 246))
  $sf = New-Object System.Drawing.StringFormat
  $sf.Alignment = [System.Drawing.StringAlignment]::Center
  $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
  $rect = New-Object System.Drawing.RectangleF(0, 0, $size, $size)
  $g.DrawString([char]0x70C0, $font, $brush, $rect, $sf)
  $dir = Split-Path $outPath -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose(); $font.Dispose(); $brush.Dispose()
}
$res = "D:\system\Sheldon-Shuo-Agent\sheldon-agent\apps\web\android\app\src\main\res"
New-ShuoIcon 108 (Join-Path $res "mipmap-mdpi\ic_launcher_foreground.png") $true
New-ShuoIcon 162 (Join-Path $res "mipmap-hdpi\ic_launcher_foreground.png") $true
New-ShuoIcon 216 (Join-Path $res "mipmap-xhdpi\ic_launcher_foreground.png") $true
New-ShuoIcon 324 (Join-Path $res "mipmap-xxhdpi\ic_launcher_foreground.png") $true
New-ShuoIcon 432 (Join-Path $res "mipmap-xxxhdpi\ic_launcher_foreground.png") $true
