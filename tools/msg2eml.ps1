<#
msg2eml.ps1: convert Outlook .msg files to .eml through Outlook desktop's object model. Windows only.

UNTESTED IN THE BUILD CONTAINER (no Windows and no Outlook there). Verify on the work machine
before relying on it: convert tools\fixtures\sample.msg and check the Message-ID with
bash tools/unpack-email.

Usage (from the workspace root, in PowerShell or cmd):
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\msg2eml.ps1 FILE.msg [FILE2.msg ...] [-OutDir DIR]
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\msg2eml.ps1 -Path FILE.msg,FILE2.msg

Writes <stem>.eml beside each .msg, or into -OutDir. Keeps the .msg. An existing .eml is kept.
Headers: PR_TRANSPORT_MESSAGE_HEADERS (proptag 0x007D001F), read through PropertyAccessor, with the
MIME headers dropped; anything missing (all of it for sent items) is rebuilt from the item:
From, To, Cc, Subject, Date, Message-ID, In-Reply-To, References.
Body: the plain text body as UTF-8, base64. Attachments: base64; hidden ones with a Content-ID stay inline.
The caller writes the JOURNAL line (converted), as with bash tools/msg2eml.
Exit: 0 ok, 2 usage error, 3 Outlook not available or a file not converted.
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $Path,
    [string] $OutDir = ""
)

$ErrorActionPreference = "Stop"
$TagBase = "http://schemas.microsoft.com/mapi/proptag/"
$PR_TRANSPORT_MESSAGE_HEADERS = $TagBase + "0x007D001F"
$PR_SENDER_SMTP_ADDRESS = $TagBase + "0x5D01001F"
$PR_SMTP_ADDRESS = $TagBase + "0x39FE001F"
$PR_INTERNET_MESSAGE_ID = $TagBase + "0x1035001F"
$PR_IN_REPLY_TO_ID = $TagBase + "0x1042001F"
$PR_INTERNET_REFERENCES = $TagBase + "0x1039001F"
$PR_ATTACH_CONTENT_ID = $TagBase + "0x3712001F"
$PR_ATTACHMENT_HIDDEN = $TagBase + "0x7FFE000B"
$DropHeaders = @("content-type", "content-transfer-encoding", "mime-version", "content-disposition",
    "content-id", "content-description", "content-length")
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$Invariant = [System.Globalization.CultureInfo]::InvariantCulture

function Get-Prop($Accessor, [string]$Tag) {
    try {
        $v = $Accessor.GetProperty($Tag)
        if ($null -ne $v) { return [string]$v }
    } catch { }
    return ""
}

function Encode-Word([string]$Text, [int]$Chunk = 20) {
    # RFC 2047 encoded words for non-ASCII header text. $Chunk 0 means one word (file names).
    if ($null -eq $Text) { return "" }
    if ($Text -notmatch '[^\x20-\x7E]') { return $Text }
    if ($Chunk -le 0) { $Chunk = $Text.Length }
    $parts = New-Object System.Collections.Generic.List[string]
    $i = 0
    while ($i -lt $Text.Length) {
        $n = [Math]::Min($Chunk, $Text.Length - $i)
        if ($n -lt ($Text.Length - $i) -and [char]::IsHighSurrogate($Text[$i + $n - 1])) { $n++ }
        $piece = $Text.Substring($i, $n)
        $parts.Add("=?utf-8?B?" + [Convert]::ToBase64String($Utf8.GetBytes($piece)) + "?=")
        $i += $n
    }
    return ($parts -join " ")
}

function Format-Address([string]$Name, [string]$Address) {
    if (-not $Address) { return (Encode-Word $Name) }
    if (-not $Name -or $Name -eq $Address) { return $Address }
    $clean = $Name.Replace('"', "'")
    if ($clean -match '[^\x20-\x7E]') { return (Encode-Word $clean) + " <" + $Address + ">" }
    return '"' + $clean + '" <' + $Address + '>'
}

function Get-SenderSmtp($Item) {
    $a = Get-Prop $Item.PropertyAccessor $PR_SENDER_SMTP_ADDRESS
    if ($a) { return $a }
    try {
        if ($Item.SenderEmailType -eq "EX") {
            $u = $Item.Sender.GetExchangeUser()
            if ($u -and $u.PrimarySmtpAddress) { return [string]$u.PrimarySmtpAddress }
        }
    } catch { }
    $a = [string]$Item.SenderEmailAddress
    if ($a -match '@') { return $a }
    return ""
}

function Get-RecipientSmtp($Recipient) {
    $a = Get-Prop $Recipient.PropertyAccessor $PR_SMTP_ADDRESS
    if ($a) { return $a }
    try {
        $u = $Recipient.AddressEntry.GetExchangeUser()
        if ($u -and $u.PrimarySmtpAddress) { return [string]$u.PrimarySmtpAddress }
    } catch { }
    $a = [string]$Recipient.Address
    if ($a -match '@') { return $a }
    return ""
}

function Format-RfcDate([datetime]$When) {
    $offset = [System.TimeZoneInfo]::Local.GetUtcOffset($When)
    $sign = "+"
    if ($offset.Ticks -lt 0) { $sign = "-" }
    $abs = $offset.Duration()
    return $When.ToString("ddd, dd MMM yyyy HH:mm:ss", $Invariant) + " " + $sign +
        $abs.Hours.ToString("00") + $abs.Minutes.ToString("00")
}

function Wrap-Base64([byte[]]$Bytes) {
    $s = [Convert]::ToBase64String($Bytes)
    $sb = New-Object System.Text.StringBuilder
    for ($i = 0; $i -lt $s.Length; $i += 76) {
        [void]$sb.Append($s.Substring($i, [Math]::Min(76, $s.Length - $i))).Append("`r`n")
    }
    return $sb.ToString()
}

function Get-MimeType([string]$Name) {
    $ext = [System.IO.Path]::GetExtension($Name).ToLowerInvariant()
    $map = @{
        ".pdf" = "application/pdf"; ".doc" = "application/msword"; ".xls" = "application/vnd.ms-excel"
        ".docx" = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ".xlsx" = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ".pptx" = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ".txt" = "text/plain"; ".csv" = "text/csv"; ".htm" = "text/html"; ".html" = "text/html"
        ".png" = "image/png"; ".jpg" = "image/jpeg"; ".jpeg" = "image/jpeg"; ".gif" = "image/gif"
        ".ics" = "text/calendar"; ".zip" = "application/zip"; ".msg" = "application/vnd.ms-outlook"
    }
    if ($map.ContainsKey($ext)) { return $map[$ext] }
    return "application/octet-stream"
}

function Build-Eml($Item) {
    $pa = $Item.PropertyAccessor
    $lines = New-Object System.Collections.Generic.List[string]
    $present = @{}
    $transport = Get-Prop $pa $PR_TRANSPORT_MESSAGE_HEADERS
    if ($transport) {
        $keep = $false
        foreach ($line in ($transport -split "`r?`n")) {
            if ($line -eq "") { if ($lines.Count -gt 0) { break } else { continue } }
            if ($line -match '^[ \t]') { if ($keep) { $lines.Add($line) }; continue }
            $idx = $line.IndexOf(":")
            if ($idx -lt 1) { $keep = $false; continue }
            $name = $line.Substring(0, $idx).Trim().ToLowerInvariant()
            $keep = -not ($DropHeaders -contains $name)
            if ($keep) { $lines.Add($line); $present[$name] = $true }
        }
    }
    if (-not $present["from"]) { $lines.Add("From: " + (Format-Address ([string]$Item.SenderName) (Get-SenderSmtp $Item))) }
    $to = @(); $cc = @()
    foreach ($r in $Item.Recipients) {
        $f = Format-Address ([string]$r.Name) (Get-RecipientSmtp $r)
        if ($r.Type -eq 2) { $cc += $f } elseif ($r.Type -eq 1) { $to += $f }
    }
    if (-not $present["to"] -and $to.Count -gt 0) { $lines.Add("To: " + ($to -join ", ")) }
    if (-not $present["cc"] -and $cc.Count -gt 0) { $lines.Add("Cc: " + ($cc -join ", ")) }
    if (-not $present["subject"]) { $lines.Add("Subject: " + (Encode-Word ([string]$Item.Subject))) }
    if (-not $present["date"]) {
        $when = $Item.SentOn
        if ($when.Year -gt 4000) { $when = $Item.ReceivedTime }
        if ($when.Year -gt 4000) { $when = $Item.CreationTime }
        $lines.Add("Date: " + (Format-RfcDate $when))
    }
    $extra = @(@("message-id", "Message-ID", $PR_INTERNET_MESSAGE_ID), @("in-reply-to", "In-Reply-To", $PR_IN_REPLY_TO_ID),
        @("references", "References", $PR_INTERNET_REFERENCES))
    foreach ($e in $extra) {
        if (-not $present[$e[0]]) {
            $v = Get-Prop $pa $e[2]
            if ($v) { $lines.Add($e[1] + ": " + $v) }
        }
    }
    $boundary = "----=_msg2eml_" + [Guid]::NewGuid().ToString("N")
    $lines.Add("MIME-Version: 1.0")
    $lines.Add("Content-Type: multipart/mixed; boundary=`"$boundary`"")
    $sb = New-Object System.Text.StringBuilder
    foreach ($l in $lines) { [void]$sb.Append($l).Append("`r`n") }
    [void]$sb.Append("`r`n--$boundary`r`n")
    [void]$sb.Append("Content-Type: text/plain; charset=utf-8`r`nContent-Transfer-Encoding: base64`r`n`r`n")
    [void]$sb.Append((Wrap-Base64 ($Utf8.GetBytes([string]$Item.Body))))
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("msg2eml-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    try {
        $i = 0
        foreach ($att in $Item.Attachments) {
            $i++
            $name = [string]$att.FileName
            if (-not $name) { $name = "attachment-$i.bin" }
            $file = Join-Path $tmp ("{0}-{1}" -f $i, ($name -replace '[\\/:*?"<>|]', '_'))
            try { $att.SaveAsFile($file) } catch { Write-Host "warning: attachment $name could not be saved; left out"; continue }
            $bytes = [System.IO.File]::ReadAllBytes($file)
            $cid = Get-Prop $att.PropertyAccessor $PR_ATTACH_CONTENT_ID
            $hidden = (Get-Prop $att.PropertyAccessor $PR_ATTACHMENT_HIDDEN) -eq "True"
            $disposition = "attachment"
            if ($cid -and $hidden) { $disposition = "inline" }
            $encoded = Encode-Word $name 0
            [void]$sb.Append("--$boundary`r`n")
            [void]$sb.Append("Content-Type: " + (Get-MimeType $name) + "; name=`"$encoded`"`r`n")
            [void]$sb.Append("Content-Transfer-Encoding: base64`r`n")
            if ($cid) { [void]$sb.Append("Content-ID: <" + $cid.Trim("<", ">") + ">`r`n") }
            [void]$sb.Append("Content-Disposition: $disposition; filename=`"$encoded`"`r`n`r`n")
            [void]$sb.Append((Wrap-Base64 $bytes))
        }
    } finally {
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    [void]$sb.Append("--$boundary--`r`n")
    return $sb.ToString()
}

if (-not $Path -or $Path.Count -eq 0) {
    Write-Host "Usage: powershell -NoProfile -ExecutionPolicy Bypass -File tools\msg2eml.ps1 FILE.msg [...] [-OutDir DIR]"
    exit 2
}
if ($OutDir -and -not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

try {
    $outlook = New-Object -ComObject Outlook.Application
    $session = $outlook.Session
} catch {
    Write-Host "Outlook desktop is not available here: $($_.Exception.Message)"
    Write-Host "Ask the human to open the email in new Outlook or Outlook on the web and save it as .eml."
    exit 3
}

$failed = 0
foreach ($p in $Path) {
    $resolved = Resolve-Path -LiteralPath $p -ErrorAction SilentlyContinue
    if (-not $resolved -or -not $p.ToLowerInvariant().EndsWith(".msg")) {
        Write-Host "no .msg file: $p"
        $failed++
        continue
    }
    $full = $resolved.ProviderPath
    $dir = Split-Path -Parent $full
    if ($OutDir) { $dir = (Resolve-Path -LiteralPath $OutDir).ProviderPath }
    $dest = Join-Path $dir ([System.IO.Path]::GetFileNameWithoutExtension($full) + ".eml")
    if (Test-Path -LiteralPath $dest) { Write-Host "exists, kept: $dest"; continue }
    $item = $null
    try {
        $item = $session.OpenSharedItem($full)
        $eml = Build-Eml $item
        [System.IO.File]::WriteAllText($dest, $eml, $Utf8)
        Write-Host "converted: $p -> $dest (outlook)"
    } catch {
        Write-Host "not converted: $p ($($_.Exception.Message))"
        $failed++
    } finally {
        if ($null -ne $item) {
            try { $item.Close(1) } catch { }
            [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($item)
        }
    }
}
if ($failed -gt 0) {
    Write-Host "Some files were not converted. Ask the human to save those emails as .eml from new Outlook or Outlook on the web."
    exit 3
}
exit 0
