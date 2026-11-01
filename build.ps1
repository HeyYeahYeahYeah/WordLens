# 一键打包 WordLens 单文件 exe
# 用法：在仓库根目录执行  pwsh -File build.ps1
# 需要：已安装 pyinstaller 的 Python 环境（必须带 tkinter）

$ErrorActionPreference = 'Stop'

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host '未找到 pyinstaller，正在安装...'
    python -m pip install --upgrade pyinstaller
}

# 先跑离线测试，测试不过就不打包
python tests/test_core.py
if ($LASTEXITCODE -ne 0) { throw '单元测试未通过，已中止打包' }

pyinstaller --onefile --noconsole --name WordLens --clean main.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 打包失败' }

Write-Host "`n完成：dist\WordLens.exe"
