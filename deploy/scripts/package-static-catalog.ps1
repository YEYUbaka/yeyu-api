[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = "E:\AI_projects\yeyu-api"
$StaticRoot = "E:\AI_projects\yeyu-api\deploy\static-catalog"
$PackageRoot = "E:\AI_projects\yeyu-api\deploy\packages"

if (-not (Test-Path -LiteralPath $StaticRoot -PathType Container)) {
    throw "静态产物目录不存在，请先运行 build:static-catalog：$StaticRoot"
}

$IndexPath = "E:\AI_projects\yeyu-api\deploy\static-catalog\index.html"
if (-not (Test-Path -LiteralPath $IndexPath -PathType Leaf)) {
    throw "静态产物缺少 index.html：$IndexPath"
}

$BuildMetadataPath = "E:\AI_projects\yeyu-api\deploy\static-catalog\build-meta.json"
if (-not (Test-Path -LiteralPath $BuildMetadataPath -PathType Leaf)) {
    throw "静态产物缺少 build-meta.json，请在干净 commit 上重新构建：$BuildMetadataPath"
}

$ForbiddenFilePattern = "(^|\.)((env)|(pem)|(key)|(p12)|(pfx))($|\.)|secret|token|password|private"
$Files = @(Get-ChildItem -LiteralPath $StaticRoot -Recurse -File)
foreach ($File in $Files) {
    if ($File.Name -match $ForbiddenFilePattern) {
        throw "发布目录包含禁止的敏感文件名：$($File.FullName)"
    }
}

$CommitSha = (& git -C $ProjectRoot rev-parse --verify HEAD).Trim()
if ($CommitSha -notmatch "^[0-9a-f]{7,64}$") {
    throw "无法取得可追溯的 Git commit SHA。"
}

$WorkingTreeStatus = (& git -C $ProjectRoot status --porcelain --untracked-files=all).Trim()
if ($WorkingTreeStatus) {
    throw "当前工作树不是 clean；请先提交变更，再重新构建和打包。"
}

try {
    $BuildMetadata = Get-Content -LiteralPath $BuildMetadataPath -Raw | ConvertFrom-Json
} catch {
    throw "build-meta.json 不是有效 JSON：$BuildMetadataPath"
}
if ($BuildMetadata.commit -ne $CommitSha) {
    throw "静态产物 commit 与当前 HEAD 不一致；请重新构建后再打包。"
}
if ($BuildMetadata.workingTreeClean -ne $true) {
    throw "静态产物来自非 clean 工作树；请在 clean commit 上重新构建。"
}

$PackagePath = "E:\AI_projects\yeyu-api\deploy\packages\static-catalog-$CommitSha.zip"
$ManifestPath = "E:\AI_projects\yeyu-api\deploy\packages\static-catalog-$CommitSha.manifest.json"
if (Test-Path -LiteralPath $PackagePath -PathType Leaf) {
    throw "该 commit 的发布包已存在，不覆盖已有包：$PackagePath"
}
if (Test-Path -LiteralPath $ManifestPath -PathType Leaf) {
    throw "该 commit 的 manifest 已存在，不覆盖已有清单：$ManifestPath"
}

New-Item -ItemType Directory -Force -Path $PackageRoot | Out-Null
Compress-Archive -Path "E:\AI_projects\yeyu-api\deploy\static-catalog\*" -DestinationPath $PackagePath -CompressionLevel Optimal

$ManifestEntries = @(
    foreach ($File in $Files) {
        [ordered]@{
            path = $File.FullName.Substring($StaticRoot.Length).TrimStart("\")
            sha256 = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            bytes = $File.Length
        }
    }
)

$Manifest = [ordered]@{
    project = "yeyu-api"
    commit = $CommitSha
    generatedAtUtc = [DateTime]::UtcNow.ToString("o")
    source = $StaticRoot
    archive = $PackagePath
    files = $ManifestEntries
}

$Manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ManifestPath -Encoding utf8
Write-Output "Static catalog package created: $PackagePath"
Write-Output "Manifest created: $ManifestPath"
