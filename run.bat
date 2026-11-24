@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo  人行横道行人违规穿行识别系统 - 一键运行
echo ============================================
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 Python。请先安装 Python 3.9+，安装时勾选 "Add Python to PATH"。
  echo 下载地址：https://www.python.org/downloads/
  pause
  exit /b 1
)
echo [1/2] 安装依赖（首次运行较慢，请耐心等待）...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo 依赖安装失败，请检查网络后重试。
  pause
  exit /b 1
)
echo [2/2] 启动服务，请在浏览器访问：http://127.0.0.1:5000
python app.py
pause
