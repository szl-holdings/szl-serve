# Publish-Ollama.ps1 — SZL-Khipu-1.5B GGUF -> ollama.com/szlholdings/szl-khipu-1.5b
# Windows PowerShell 5.1, run as Administrator, no prior shell state required.
# Order: preflight (read-only) -> download + SHA-256 verify -> create -> smoke -> push -> verify -> receipt.
# Stops before the first push unless every earlier gate passed. Nothing on Hugging Face or GitHub is modified.
# A11OY-MINI is deliberately NOT published: its Hub card states publication_eligible=false.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProgressPreference = "SilentlyContinue"

$Stamp   = Get-Date -Format "yyyyMMdd-HHmmss"
$Root    = Join-Path $env:USERPROFILE "szl-ollama"
New-Item -ItemType Directory -Force -Path $Root, (Join-Path $Root "receipts") | Out-Null
Set-Location -LiteralPath $Root
$Receipt = Join-Path $Root ("receipts\ollama-publish-" + $Stamp + ".json")
$Log     = Join-Path $Root ("receipts\ollama-publish-" + $Stamp + ".log")
Start-Transcript -LiteralPath $Log | Out-Null

$Namespace = "szlholdings"
$Model     = "szl-khipu-1.5b"
$HfRepo    = "SZLHOLDINGS/SZL-Khipu-1.5B-GGUF"
$HfRev     = "d9731f1d586c7f615790163a759dc0f14872b523"
$Files = @(
  @{ tag = "q4_k_m"; file = "SZL-Khipu-1.5B-Q4_K_M.gguf"; sha256 = "13c1a1993063e1dff92f7413ccf48eaca6d48efc8801ae9af35961ae3396623a"; bytes = 986047904 },
  @{ tag = "q5_k_m"; file = "SZL-Khipu-1.5B-Q5_K_M.gguf"; sha256 = "3bf460ac163c5dc952c273999c38a41349e3e6d666e4b713aed22c996860fd4c"; bytes = 1125049760 },
  @{ tag = "q8_0";   file = "SZL-Khipu-1.5B-Q8_0.gguf";   sha256 = "6aff1087f64631679f4cdf032613aee6911dbde38cd3bac6b81bf63741a56f0d";   bytes = 1646572448 }
)
$Modelfiles = @{
  "q4_k_m" = @'
# SZL-Khipu-1.5B (Q4_K_M) — Ollama Modelfile
# Source bytes: hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF @ d9731f1d586c7f615790163a759dc0f14872b523, file SZL-Khipu-1.5B-Q4_K_M.gguf
# Base: Qwen/Qwen2.5-1.5B-Instruct (Apache-2.0). Fine-tune: SZLHOLDINGS/SZL-Khipu-1.5B (Apache-2.0), QLoRA.
# Doctrine: proposal-only navigator. Output is a JSON plan to be validated by an external controller
# against khipu.schema.json; it is not an action and not a signed checkpoint. Λ = Conjecture 1.
FROM ./SZL-Khipu-1.5B-Q4_K_M.gguf

# Qwen2.5 ChatML template, byte-identical to the Ollama library qwen2.5 template (blob eb4402837c78).
TEMPLATE """{{- if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}"""

PARAMETER temperature 0
PARAMETER num_ctx 8192
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"

LICENSE """Apache License 2.0 — https://www.apache.org/licenses/LICENSE-2.0
Base model Qwen2.5-1.5B-Instruct © Alibaba Cloud, Apache-2.0. Fine-tune © 2026 SZL Holdings, Apache-2.0.
GGUF quantization changes numerics; the signed evaluation receipt on the Hub covers the pre-quantized checkpoint, not this file."""

'@
  "q5_k_m" = @'
# SZL-Khipu-1.5B (Q5_K_M) — Ollama Modelfile
# Source bytes: hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF @ d9731f1d586c7f615790163a759dc0f14872b523, file SZL-Khipu-1.5B-Q5_K_M.gguf
# Base: Qwen/Qwen2.5-1.5B-Instruct (Apache-2.0). Fine-tune: SZLHOLDINGS/SZL-Khipu-1.5B (Apache-2.0), QLoRA.
# Doctrine: proposal-only navigator. Output is a JSON plan to be validated by an external controller
# against khipu.schema.json; it is not an action and not a signed checkpoint. Λ = Conjecture 1.
FROM ./SZL-Khipu-1.5B-Q5_K_M.gguf

# Qwen2.5 ChatML template, byte-identical to the Ollama library qwen2.5 template (blob eb4402837c78).
TEMPLATE """{{- if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}"""

PARAMETER temperature 0
PARAMETER num_ctx 8192
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"

LICENSE """Apache License 2.0 — https://www.apache.org/licenses/LICENSE-2.0
Base model Qwen2.5-1.5B-Instruct © Alibaba Cloud, Apache-2.0. Fine-tune © 2026 SZL Holdings, Apache-2.0.
GGUF quantization changes numerics; the signed evaluation receipt on the Hub covers the pre-quantized checkpoint, not this file."""

'@
  "q8_0"   = @'
# SZL-Khipu-1.5B (Q8_0) — Ollama Modelfile
# Source bytes: hf.co/SZLHOLDINGS/SZL-Khipu-1.5B-GGUF @ d9731f1d586c7f615790163a759dc0f14872b523, file SZL-Khipu-1.5B-Q8_0.gguf
# Base: Qwen/Qwen2.5-1.5B-Instruct (Apache-2.0). Fine-tune: SZLHOLDINGS/SZL-Khipu-1.5B (Apache-2.0), QLoRA.
# Doctrine: proposal-only navigator. Output is a JSON plan to be validated by an external controller
# against khipu.schema.json; it is not an action and not a signed checkpoint. Λ = Conjecture 1.
FROM ./SZL-Khipu-1.5B-Q8_0.gguf

# Qwen2.5 ChatML template, byte-identical to the Ollama library qwen2.5 template (blob eb4402837c78).
TEMPLATE """{{- if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}"""

PARAMETER temperature 0
PARAMETER num_ctx 8192
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"

LICENSE """Apache License 2.0 — https://www.apache.org/licenses/LICENSE-2.0
Base model Qwen2.5-1.5B-Instruct © Alibaba Cloud, Apache-2.0. Fine-tune © 2026 SZL Holdings, Apache-2.0.
GGUF quantization changes numerics; the signed evaluation receipt on the Hub covers the pre-quantized checkpoint, not this file."""

'@
}
$R = [ordered]@{ ts = (Get-Date).ToUniversalTime().ToString("o"); host = $env:COMPUTERNAME; root = $Root
                 hf_repo = $HfRepo; hf_revision = $HfRev; target = "$Namespace/$Model"; state = "STARTED"; steps = @() }
function Step($name, $result, $detail) { $script:R.steps += [ordered]@{ step = $name; result = $result; detail = $detail; ts = (Get-Date).ToUniversalTime().ToString("o") }; Write-Host ("[{0}] {1} — {2}" -f $result, $name, $detail) }
function Save() { $script:R | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Receipt -Encoding UTF8 }

try {
  # ---------- PREFLIGHT (read-only) ----------
  if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "ollama is not installed. Install from https://ollama.com/download/windows and rerun." }
  $OllamaVersion = (& ollama --version 2>&1 | Out-String).Trim()
  Step "ollama_present" "OK" $OllamaVersion
  $KeyPub = Join-Path $env:USERPROFILE ".ollama\id_ed25519.pub"
  if (-not (Test-Path -LiteralPath $KeyPub -PathType Leaf)) { throw "No Ollama key at $KeyPub. Start the Ollama app once (it generates the key), then rerun." }
  $PubKey = (Get-Content -LiteralPath $KeyPub -Raw).Trim()
  Step "ollama_key_present" "OK" $PubKey
  try { $null = Invoke-WebRequest -UseBasicParsing -Uri ("https://ollama.com/" + $Namespace) -TimeoutSec 30
        Step "namespace_exists" "OK" ("https://ollama.com/" + $Namespace) }
  catch { Step "namespace_exists" "BLOCKED" "ollama.com/$Namespace does not exist yet"
          throw "Create the account/org '$Namespace' at https://ollama.com/signup, then add this public key at https://ollama.com/settings/keys :`n$PubKey`nThen rerun this script." }
  $Free = (Get-PSDrive -Name ($Root.Substring(0,1))).Free
  if ($Free -lt 6GB) { throw "Need about 6 GB free on drive $($Root.Substring(0,1)): (have $([math]::Round($Free/1GB,1)) GB)." }
  Step "disk_space" "OK" ("{0:N1} GB free" -f ($Free/1GB))

  # ---------- DOWNLOAD + VERIFY ----------
  foreach ($f in $Files) {
    $dest = Join-Path $Root $f.file
    if (Test-Path -LiteralPath $dest -PathType Leaf) {
      $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $dest).Hash.ToLower()
      if ($h -eq $f.sha256) { Step ("download_" + $f.tag) "SKIP_ALREADY_VERIFIED" $f.file; continue } else { Remove-Item -LiteralPath $dest -Force }
    }
    $uri = "https://huggingface.co/$HfRepo/resolve/$HfRev/$($f.file)"
    Write-Host "Downloading $($f.file) ($([math]::Round($f.bytes/1MB)) MB) from $uri"
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $dest -TimeoutSec 3600
    $len = (Get-Item -LiteralPath $dest).Length
    $h = (Get-FileHash -Algorithm SHA256 -LiteralPath $dest).Hash.ToLower()
    if ($len -ne $f.bytes -or $h -ne $f.sha256) { Step ("verify_" + $f.tag) "FAILED" "len=$len sha256=$h"; throw "SHA-256/size mismatch for $($f.file); refusing to publish unverified bytes." }
    Step ("verify_" + $f.tag) "MEASURED" "sha256=$h bytes=$len (matches Hub card)"
  }

  # ---------- CREATE ----------
  foreach ($f in $Files) {
    $mfPath = Join-Path $Root ("Modelfile." + $f.tag)
    [System.IO.File]::WriteAllText($mfPath, $Modelfiles[$f.tag], (New-Object System.Text.UTF8Encoding($false)))
    $name = "$Namespace/$Model" + ":" + $f.tag
    $out = & ollama create $name -f $mfPath 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { Step ("create_" + $f.tag) "FAILED" $out.Trim(); throw "ollama create failed for $name" }
    Step ("create_" + $f.tag) "OK" $name
  }
  $out = & ollama cp ("$Namespace/$Model" + ":q4_k_m") ("$Namespace/$Model" + ":latest") 2>&1 | Out-String
  if ($LASTEXITCODE -ne 0) { throw "ollama cp latest failed: $out" }
  Step "tag_latest" "OK" "latest -> q4_k_m"

  # ---------- SMOKE (temperature 0, documented synthetic prompt; not an evaluation) ----------
  $prompt = '{"query": "Which handle records the rolling 24h spend-cap policy?", "candidates": [{"nodeId": "node://khipu-synthetic/0000000000000000", "nodeKind": "CLAIM", "label": "DECLARED", "note": "synthetic handle - topic tag policy-spend-cap; no node content."}]}'
  $smoke = & ollama run ("$Namespace/$Model" + ":q4_k_m") $prompt 2>&1 | Out-String
  $smoke = $smoke.Trim()
  $parsed = $null
  try { $parsed = $smoke | ConvertFrom-Json } catch { }
  if ($null -ne $parsed -and $parsed.PSObject.Properties.Name -contains "decision") {
    Step "smoke_q4_k_m" "MEASURED" ("decision=" + $parsed.decision + " output=" + $smoke)
  } elseif ($smoke.Length -gt 0) {
    Step "smoke_q4_k_m" "OUTPUT_NOT_SCHEMA_JSON" $smoke
    throw "Smoke output is not a JSON plan with a 'decision' field. Stopping before push so an off-contract runtime is not published. Inspect $Log; rerun after fixing the Modelfile."
  } else { Step "smoke_q4_k_m" "FAILED" "no output"; throw "No output from ollama run; stopping before push." }

  # ---------- PUSH ----------
  foreach ($tag in @("q4_k_m","q5_k_m","q8_0","latest")) {
    $name = "$Namespace/$Model" + ":" + $tag
    $out = & ollama push $name 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { Step ("push_" + $tag) "FAILED" $out.Trim(); throw "ollama push failed for $name (is the public key above registered at ollama.com/settings/keys?)" }
    Step ("push_" + $tag) "PUSHED" $name
  }

  # ---------- VERIFY (public read-back) ----------
  Start-Sleep -Seconds 5
  $page = Invoke-WebRequest -UseBasicParsing -Uri ("https://ollama.com/" + $Namespace + "/" + $Model) -TimeoutSec 60
  if ($page.StatusCode -ne 200) { throw "Model page not readable: HTTP $($page.StatusCode)" }
  Step "public_readback" "MEASURED" ("https://ollama.com/" + $Namespace + "/" + $Model + " HTTP 200")
  $show = & ollama show ("$Namespace/$Model" + ":q4_k_m") 2>&1 | Out-String
  Step "ollama_show" "OK" $show.Trim()
  $R.state = "PUBLISHED_VERIFIED"
  $R.next_owner_step = "Paste kit/OLLAMA_PAGE.md into the model page README at https://ollama.com/$Namespace/$Model/edit (the push does not carry a README)."
}
catch {
  if ($R.state -eq "STARTED") { $R.state = "INCOMPLETE" }
  $R.error = $_.Exception.Message
  Write-Host ("INCOMPLETE — " + $_.Exception.Message) -ForegroundColor Yellow
}
finally {
  Save
  Stop-Transcript | Out-Null
  Write-Host ""
  Write-Host ("Receipt: " + $Receipt)
  Write-Host ("Log:     " + $Log)
  Write-Host ("State:   " + $R.state)
  if ($R.state -ne "PUBLISHED_VERIFIED") { exit 1 }
}
