# 読み上げ音声をWAVに書き出す。jobs.json = [{ "out": "x.wav", "parts": [ {"t":"文章"} | {"b":秒} ] }]
param([string]$Jobs, [string]$Voice = "Microsoft Haruka", [int]$Rate = 0)
Add-Type -AssemblyName System.Speech
$list = Get-Content -Raw -Encoding UTF8 $Jobs | ConvertFrom-Json
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice($Voice); $s.Rate = $Rate
foreach ($j in $list) {
  $pb = New-Object System.Speech.Synthesis.PromptBuilder([System.Globalization.CultureInfo]::GetCultureInfo("ja-JP"))
  foreach ($p in $j.parts) {
    if ($null -ne $p.b) { $pb.AppendBreak([TimeSpan]::FromSeconds([double]$p.b)) } else { $pb.AppendText([string]$p.t) }
  }
  $s.SetOutputToWaveFile($j.out)
  $s.Speak($pb)
  $s.SetOutputToNull()
  Write-Output ("done " + $j.out)
}
