@echo off
echo ======================================================================
echo OpenVoice V2 Environment Setup
echo ======================================================================

REM Check for Conda
where conda >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Conda detected. Creating/Updating 'openvoice' environment...
    call conda create -n openvoice python=3.9 -y
    call conda activate openvoice
) else (
    echo [WARN] Conda not found. Proceeding with system Python...
    echo [INFO] It is highly recommended to use a virtual environment.
)

echo [INFO] Installing PyTorch (CUDA 11.8 version recommended for Windows)...
echo        If you rely on CPU, this might download the wrong version. 
echo        Please check https://pytorch.org/get-started/locally/ for your specific setup.
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

echo [INFO] Installing Dependencies from requirements.txt...
pip install -r requirements.txt

echo [INFO] Downloading Unidic (Required for Japanese support in V2)...
python -m unidic download

echo.
echo ======================================================================
echo Setup Complete!
echo 1. Ensure you have downloaded the checkpoints as per the instructions.
echo    - V1: OpenVoice/checkpoints
echo    - V2: OpenVoice/checkpoints_v2
echo 2. Run the application using: python app_v2.py
echo ======================================================================
pause
