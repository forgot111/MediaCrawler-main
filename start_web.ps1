#!/usr/bin/env pwsh
Write-Host "🎯 启动抖音Web监控界面..." -ForegroundColor Green
Write-Host "📋 使用 uv 环境运行 Python 脚本" -ForegroundColor Yellow
try {
    uv run python start_web_auto_port.py
} catch {
    Write-Host "❌ 启动失败: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "按回车键退出"
}