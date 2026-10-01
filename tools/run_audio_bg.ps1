# 音声作りを独立したプロセスで（優先度「低め」）。ログは audio_build.log
$env:VV_SPEAKER = "30"; $env:PYTHONIOENCODING = "utf-8"
$p = Start-Process -FilePath "python" -ArgumentList "tools\make_audio_vv.py" -WorkingDirectory "C:\Users\st106\chinkan-app" -WindowStyle Hidden -RedirectStandardOutput "C:\Users\st106\chinkan-app\tools\audio_build.log" -RedirectStandardError "C:\Users\st106\chinkan-app\tools\audio_build.err" -PassThru
Start-Sleep -Seconds 1; $p.PriorityClass = "BelowNormal"; "started pid=$($p.Id)"
