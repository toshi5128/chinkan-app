# VOICEVOX エンジンを軽く起動する（CPU2スレッド・優先度「低め」・画面なし）。止める: -Stop
param([switch]$Stop, [int]$Threads = 2)
$exe = "C:\Users\st106\tools\voicevox\windows-cpu\run.exe"
if ($Stop) { Get-Process run -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe } | Stop-Process -Force; "stopped"; exit }
$p = Start-Process -FilePath $exe -ArgumentList "--host 127.0.0.1 --port 50021 --cpu_num_threads $Threads" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2; $p.PriorityClass = "BelowNormal"
for ($i = 0; $i -lt 60; $i++) { try { Invoke-RestMethod http://127.0.0.1:50021/version -TimeoutSec 2 | Out-Null; "ready pid=$($p.Id)"; exit } catch { Start-Sleep -Seconds 2 } }
"timeout"
