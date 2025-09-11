@echo off
chcp 65001 >nul
echo.
echo ===============================================
echo       MediaCrawler 项目启动助手
echo ===============================================
echo.
echo 请选择要执行的操作：
echo.
echo [1] 启动Web监控界面
echo [2] 抓取抖音评论数据
echo [3] 抓取小红书评论数据
echo [4] 安装/更新项目依赖
echo [5] 查看项目状态
echo [0] 退出
echo.
set /p choice=请输入选项 (0-5): 

if "%choice%"=="1" goto start_web
if "%choice%"=="2" goto crawl_douyin
if "%choice%"=="3" goto crawl_xiaohongshu
if "%choice%"=="4" goto install_deps
if "%choice%"=="5" goto check_status
if "%choice%"=="0" goto exit
echo 无效选项，请重新选择
pause
goto start

:start_web
echo.
echo 🎯 正在启动Web监控界面...
uv run python start_web_auto_port.py
goto end

:crawl_douyin
echo.
echo 📱 正在抓取抖音评论数据...
uv run main.py --platform dy --lt qrcode --type detail
goto end

:crawl_xiaohongshu
echo.
echo 🌺 正在抓取小红书评论数据...
uv run main.py --platform xhs --lt qrcode --type detail
goto end

:install_deps
echo.
echo 📦 正在安装/更新项目依赖...
uv sync
echo ✅ 依赖安装完成
goto end

:check_status
echo.
echo 📊 项目状态检查：
echo.
echo 🔍 Python版本：
uv run python --version
echo.
echo 🔍 UV版本：
uv --version
echo.
echo 🔍 项目依赖状态：
uv run python -c "import aiomysql, fastapi, playwright; print('✅ 核心依赖正常')"
echo.
goto end

:exit
echo.
echo 👋 再见！
exit /b 0

:end
echo.
pause
goto start