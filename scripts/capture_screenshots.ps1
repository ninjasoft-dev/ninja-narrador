param(
    [string]$Pythonw = ".\.venv\Scripts\pythonw.exe"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class NarratorWindowCapture {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr handle, out RECT rectangle);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr handle, IntPtr deviceContext, uint flags);
}
"@

function Save-NarratorScreenshot {
    param(
        [ValidateSet("dark", "light")]
        [string]$Theme,
        [string]$Destination
    )

    $env:NINJA_NARRATOR_THEME = $Theme
    $startedAt = Get-Date
    $launcher = Start-Process $Pythonw -ArgumentList "interface.py" -WorkingDirectory $PWD -PassThru
    $windowProcess = $null

    try {
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            Start-Sleep -Milliseconds 200
            $windowProcess = Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object {
                $_.StartTime -ge $startedAt.AddSeconds(-1) -and
                $_.MainWindowTitle -eq "NinjaSoft Narrator"
            } | Select-Object -First 1
            if ($windowProcess) { break }
        }
        if (-not $windowProcess) {
            throw "A janela do tema $Theme não foi encontrada."
        }

        Start-Sleep -Milliseconds 700
        $rectangle = New-Object NarratorWindowCapture+RECT
        [NarratorWindowCapture]::GetWindowRect(
            $windowProcess.MainWindowHandle,
            [ref]$rectangle
        ) | Out-Null
        $width = $rectangle.Right - $rectangle.Left
        $height = $rectangle.Bottom - $rectangle.Top
        $bitmap = New-Object System.Drawing.Bitmap($width, $height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $deviceContext = $graphics.GetHdc()

        try {
            $captured = [NarratorWindowCapture]::PrintWindow(
                $windowProcess.MainWindowHandle,
                $deviceContext,
                2
            )
            if (-not $captured) {
                throw "O Windows não conseguiu capturar o tema $Theme."
            }
        }
        finally {
            $graphics.ReleaseHdc($deviceContext)
        }

        $path = Join-Path $PWD $Destination
        $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        Get-Item $path | Select-Object Name, Length
    }
    finally {
        if ($windowProcess) {
            Stop-Process -Id $windowProcess.Id -Force -ErrorAction SilentlyContinue
        }
        Stop-Process -Id $launcher.Id -Force -ErrorAction SilentlyContinue
    }
}

try {
    Save-NarratorScreenshot "dark" "docs\assets\ninja-narrator-escuro.png"
    Save-NarratorScreenshot "light" "docs\assets\ninja-narrator-claro.png"
}
finally {
    Remove-Item Env:NINJA_NARRATOR_THEME -ErrorAction SilentlyContinue
}
