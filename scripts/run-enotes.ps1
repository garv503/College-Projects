[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('build', 'start', 'stop')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$javaHome = 'C:\Program Files\Java\jdk-17'
$mavenHome = Join-Path $workspaceRoot '.tools\apache-maven-3.9.16'
$tomcatHome = Join-Path $workspaceRoot '.tools\apache-tomcat-9.0.120'
$mavenCommand = Join-Path $mavenHome 'bin\mvn.cmd'
$mavenRepository = Join-Path $workspaceRoot '.tools\maven-repository'
$startupCommand = Join-Path $tomcatHome 'bin\startup.bat'
$shutdownCommand = Join-Path $tomcatHome 'bin\shutdown.bat'
$warFile = Join-Path $workspaceRoot 'target\enotes.war'
$deployedWar = Join-Path $tomcatHome 'webapps\enotes.war'

function Require-Path([string]$Path, [string]$Description) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Description was not found at '$Path'. Run the project setup first."
    }
}

function Set-JavaEnvironment {
    Require-Path $javaHome 'Java 17'
    $env:JAVA_HOME = $javaHome
    $env:JRE_HOME = $javaHome
    $env:Path = "$javaHome\bin;$env:Path"
}

function Build-Project {
    Require-Path $mavenCommand 'Project-local Maven'
    & $mavenCommand "-Dmaven.repo.local=$mavenRepository" 'clean' 'package'
    if ($LASTEXITCODE -ne 0) {
        throw "Maven build failed with exit code $LASTEXITCODE."
    }
    Require-Path $warFile 'Generated WAR file'
}

function Invoke-TomcatBatch([string]$Command, [switch]$Wait) {
    # startup.bat launches Tomcat via "start", a long-lived detached process.
    # Start-Process -Wait blocks until that whole job (including Tomcat itself)
    # exits, so it must never be used for startup - only for shutdown, whose
    # java process runs in the foreground and exits as soon as it signals stop.
    $arguments = @('/c', "`"$Command`"")
    $workingDirectory = Split-Path -Parent $Command
    if ($Wait) {
        $process = Start-Process -FilePath 'cmd.exe' -ArgumentList $arguments -WorkingDirectory $workingDirectory -WindowStyle Hidden -PassThru -Wait
        if ($process.ExitCode -ne 0) {
            throw "Tomcat command failed with exit code $($process.ExitCode)."
        }
    } else {
        Start-Process -FilePath 'cmd.exe' -ArgumentList $arguments -WorkingDirectory $workingDirectory -WindowStyle Hidden | Out-Null
    }
}

function Get-ProjectTomcatListener {
    $listener = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
        if ($process.CommandLine -notlike "*$tomcatHome*") {
            throw "Port 8080 is already used by another application (PID $($listener.OwningProcess)). Stop that application before starting E-Notes."
        }
    }
    return $listener
}

function Stop-Tomcat {
    $listener = Get-ProjectTomcatListener
    if ($listener) {
        Invoke-TomcatBatch $shutdownCommand -Wait
        Start-Sleep -Seconds 2
    }
}

function Start-Tomcat {
    $env:CATALINA_HOME = $tomcatHome
    $env:CATALINA_BASE = $tomcatHome
    Invoke-TomcatBatch $startupCommand

    $deadline = (Get-Date).AddSeconds(30)
    do {
        try {
            $response = Invoke-WebRequest -Uri 'http://localhost:8080/enotes/' -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                Write-Host 'E-Notes is running at http://localhost:8080/enotes/'
                return
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    } while ((Get-Date) -lt $deadline)

    throw 'Tomcat started but E-Notes did not become available within 30 seconds. Check .tools\apache-tomcat-9.0.120\logs.'
}

Set-JavaEnvironment

if ($Action -eq 'build') {
    Build-Project
    exit 0
}

Require-Path $tomcatHome 'Project-local Tomcat 9'
Require-Path $shutdownCommand 'Tomcat shutdown script'

if ($Action -eq 'stop') {
    Stop-Tomcat
    exit 0
}

Stop-Tomcat
Build-Project
Copy-Item -LiteralPath $warFile -Destination $deployedWar -Force
Start-Tomcat
