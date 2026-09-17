$ErrorActionPreference = "Stop"

$prompt = [Console]::In.ReadToEnd()

if ([string]::IsNullOrWhiteSpace($prompt)) {
    Write-Error "Executor prompt bos."
    exit 1
}

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:CODEX_PROJECT_ROOT = $projectRoot

$model = $env:CODEX_MODEL
if ([string]::IsNullOrWhiteSpace($model)) {
    $model = "gpt-5.3"
}

function Invoke-ConfiguredCommand {
    param(
        [string]$CommandText,
        [string]$InputText
    )

    if ([string]::IsNullOrWhiteSpace($CommandText)) {
        return $null
    }

    $tempPrompt = [System.IO.Path]::GetTempFileName()
    $tempScript = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), ".ps1")
    $tempStdout = [System.IO.Path]::GetTempFileName()
    $tempStderr = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempPrompt, $InputText, [System.Text.Encoding]::UTF8)
        $expanded = $CommandText.Replace("{prompt_file}", $tempPrompt).Replace("{model}", $model)
        [System.IO.File]::WriteAllText($tempScript, $expanded, [System.Text.Encoding]::UTF8)
        $proc = Start-Process `
            -FilePath "powershell.exe" `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $tempScript) `
            -Wait `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $tempStdout `
            -RedirectStandardError $tempStderr
        $code = $proc.ExitCode
        $stdoutText = [System.IO.File]::ReadAllText($tempStdout, [System.Text.Encoding]::UTF8).Trim()
        $stderrText = [System.IO.File]::ReadAllText($tempStderr, [System.Text.Encoding]::UTF8).Trim()
        $combined = @($stdoutText, $stderrText) -join [Environment]::NewLine
        return @{
            stdout = $combined.Trim()
            code = $code
        }
    }
    finally {
        Remove-Item -LiteralPath $tempPrompt -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $tempScript -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $tempStdout -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $tempStderr -ErrorAction SilentlyContinue
    }
}

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

$configured = $env:CODEX_EXECUTOR_INVOKE
if (-not [string]::IsNullOrWhiteSpace($configured)) {
    $result = Invoke-ConfiguredCommand -CommandText $configured -InputText $prompt
    if ($null -ne $result) {
        if ($result.code -eq 0 -and -not [string]::IsNullOrWhiteSpace($result.stdout)) {
            Write-Output $result.stdout
            exit 0
        }
        Write-Error ("Configured executor failed. ExitCode={0} Output={1}" -f $result.code, $result.stdout)
        exit ([Math]::Max(1, [int]$result.code))
    }
}

if ($env:AGENT_EXECUTOR_MOCK_RESULT) {
    Write-Output $env:AGENT_EXECUTOR_MOCK_RESULT
    exit 0
}

if (Test-CommandExists "codex") {
    try {
        $output = $prompt | codex exec -C $projectRoot -m $model - 2>&1
        $code = $LASTEXITCODE
        $joined = ($output -join [Environment]::NewLine).Trim()
        if ($code -eq 0 -and -not [string]::IsNullOrWhiteSpace($joined)) {
            Write-Output $joined
            exit 0
        }

        Write-Error (
            "codex exec cagrisi tamamlanamadi. " +
            "CODEX_EXECUTOR_INVOKE tanimlayin. Son cikti: $joined"
        )
        exit ([Math]::Max(1, [int]$code))
    }
    catch {
        Write-Error (
            "codex bulundu fakat wrapper cagrisi basarisiz oldu. " +
            "Gerekirse CODEX_EXECUTOR_INVOKE tanimlayin. Hata: $($_.Exception.Message)"
        )
        exit 2
    }
}

Write-Error (
    "Gercek executor calistirilamadi. " +
    "AGENT_EXECUTOR_COMMAND zaten bu wrapper'a isaret etmeli; " +
    "ek olarak CODEX_EXECUTOR_INVOKE veya AGENT_EXECUTOR_MOCK_RESULT tanimlanmali."
)
exit 2
