#Requires -Version 5.1
<#
.SYNOPSIS
    套组发货业绩（按日）定时任务：Python BI 计算 + 可选 SSAS 刷新 + BIN_BatchLog 日志

.DESCRIPTION
    1. 执行 run.py bi -t suite_ship_performance_daily（默认近 7 天窗口增量）
    2. 刷新 SSAS Tabular 模型中的 bi_suite_ship_performance_daily 分区（若存在）
    3. 写入 BI_LQX.dbo.BIN_BatchLog

    SQL Agent / 任务计划程序示例：
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\project\hjy_data_pull_test\scripts\run_suite_ship_performance_daily.ps1"

.PARAMETER ProjectRoot
    项目根目录（含 run.py）

.PARAMETER PythonExe
    Python 可执行文件路径

.PARAMETER PastDays
    重算最近 N 天（闭区间）

.PARAMETER Mode
    BI 模式：auto / full / window

.PARAMETER SkipSsaRefresh
    跳过 SSAS 模型刷新
#>
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$PythonExe = 'python',
    [int]$PastDays = 7,
    [ValidateSet('auto', 'full', 'window')]
    [string]$Mode = 'auto',
    [string]$SsaServer = 'localhost',
    [string]$SsaDatabase = 'BI_Model',
    [string]$SsaTableName = 'bi_suite_ship_performance_daily',
    [string]$SsaPartitionName = 'Partition',
    [string]$BatchLogConnectionString = 'Data Source=.;Initial Catalog=BI_LQX;Integrated Security=SSPI;',
    [switch]$SkipSsaRefresh
)

$JobId = 'SSAS'
$JobName = 'BI数据定时导入'
$StepName = '套组发货业绩按日'
$PgmName = 'suite_ship_performance_daily'
$CreatePgm = 'bi_suite_ship_performance_daily'

$current = Get-Date
$endTime = $null
$ErrorMessage = ''
$server = $null
$rowsWritten = $null

function Write-BatchLog {
    param(
        [datetime]$StarTime,
        [datetime]$EndTime,
        [string]$Status,
        [string]$ErrorMsg
    )

    $conn = New-Object System.Data.SqlClient.SqlConnection
    $conn.ConnectionString = $BatchLogConnectionString
    try {
        $conn.Open()
        $cmd = New-Object System.Data.SqlClient.SqlCommand
        $cmd.Connection = $conn
        $cmd.CommandText = @"
INSERT INTO BIN_BatchLog(
    BIN_OrganizationInfoID, BIN_BrandInfoID, JobID, JobName, StepID, StepName,
    PGMID, PGMName, StarTime, EndTime, Status, ValidFlag, ErrorMsg,
    CreateTime, CreatedBy, CreatePGM, UpdateTime, UpdatedBy, UpdatePGM, ModifyCount
) VALUES (
    @org, @brand, @jobId, @jobName, @stepId, @stepName,
    @pgmId, @pgmName, @starTime, @endTime, @status, @validFlag, @errorMsg,
    @createTime, @createdBy, @createPgm, @updateTime, @updatedBy, @updatePgm, @modifyCount
)
"@
        $null = $cmd.Parameters.AddWithValue('@org', 1)
        $null = $cmd.Parameters.AddWithValue('@brand', 1)
        $null = $cmd.Parameters.AddWithValue('@jobId', $JobId)
        $null = $cmd.Parameters.AddWithValue('@jobName', $JobName)
        $null = $cmd.Parameters.AddWithValue('@stepId', '')
        $null = $cmd.Parameters.AddWithValue('@stepName', $StepName)
        $null = $cmd.Parameters.AddWithValue('@pgmId', '')
        $null = $cmd.Parameters.AddWithValue('@pgmName', $PgmName)
        $null = $cmd.Parameters.AddWithValue('@starTime', $StarTime)
        $null = $cmd.Parameters.AddWithValue('@endTime', $EndTime)
        $null = $cmd.Parameters.AddWithValue('@status', $Status)
        $null = $cmd.Parameters.AddWithValue('@validFlag', '')
        $null = $cmd.Parameters.AddWithValue('@errorMsg', $(if ($ErrorMsg) { $ErrorMsg } else { [DBNull]::Value }))
        $null = $cmd.Parameters.AddWithValue('@createTime', $StarTime)
        $null = $cmd.Parameters.AddWithValue('@createdBy', 'System')
        $null = $cmd.Parameters.AddWithValue('@createPgm', $CreatePgm)
        $null = $cmd.Parameters.AddWithValue('@updateTime', $EndTime)
        $null = $cmd.Parameters.AddWithValue('@updatedBy', 'System')
        $null = $cmd.Parameters.AddWithValue('@updatePgm', $CreatePgm)
        $null = $cmd.Parameters.AddWithValue('@modifyCount', 1)
        [void]$cmd.ExecuteNonQuery()
    }
    finally {
        if ($conn.State -eq 'Open') { $conn.Close() }
        $conn.Dispose()
    }
}

try {
    $runPy = Join-Path $ProjectRoot 'run.py'
    if (-not (Test-Path -LiteralPath $runPy)) {
        throw "未找到 run.py: $runPy"
    }

    Push-Location $ProjectRoot
    $biOutput = & $PythonExe -u $runPy bi `
        -t suite_ship_performance_daily `
        --past $PastDays `
        --past-unit day `
        --mode $Mode 2>&1
    $exitCode = $LASTEXITCODE
    Pop-Location

    if ($exitCode -ne 0) {
        $text = ($biOutput | Out-String).Trim()
        throw "BI 任务失败 (exit=$exitCode): $text"
    }

    if ($biOutput -match '写入\s+(\d+)\s+行') {
        $rowsWritten = [int]$Matches[1]
    }

    if (-not $SkipSsaRefresh) {
        [void][System.Reflection.Assembly]::LoadWithPartialName('Microsoft.AnalysisServices.Tabular')

        $server = New-Object Microsoft.AnalysisServices.Tabular.Server
        $saveOptions = New-Object Microsoft.AnalysisServices.Tabular.SaveOptions
        $saveOptions.MaxParallelism = 8
        $server.Connect($SsaServer)

        $model = $server.Databases.GetByName($SsaDatabase).Model
        if (-not $model.HasLocalChanges) {
            $table = $model.Tables.Find($SsaTableName)
            if ($null -eq $table) {
                Write-Warning "SSAS 模型中未找到表 $SsaTableName，跳过刷新"
            }
            else {
                $partition = $table.Partitions.Find($SsaPartitionName)
                if ($null -eq $partition) {
                    Write-Warning "表 $SsaTableName 中未找到分区 $SsaPartitionName，跳过刷新"
                }
                else {
                    $partition.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
                    $model.SaveChanges($saveOptions)
                }
            }
        }
        else {
            Write-Warning 'SSAS 模型存在未保存的本地变更，跳过刷新'
        }
    }

    $endTime = Get-Date
}
catch {
    $ErrorMessage = $_.Exception.Message
    $endTime = Get-Date
}
finally {
    if ($null -ne $server) {
        try { $server.Disconnect() } catch { }
    }

    $status = if ($ErrorMessage) { 'Failed' } else { 'Success' }
    $logMsg = $ErrorMessage
    if (-not $logMsg -and $null -ne $rowsWritten) {
        $logMsg = "写入 $rowsWritten 行"
    }

    Write-BatchLog -StarTime $current -EndTime $(if ($endTime) { $endTime } else { Get-Date }) `
        -Status $status -ErrorMsg $logMsg

    if ($ErrorMessage) {
        Write-Error $ErrorMessage
        exit 1
    }
}

Write-Host "suite_ship_performance_daily 完成$(if ($rowsWritten -ne $null) { "，写入 $rowsWritten 行" })"
exit 0
