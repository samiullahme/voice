@echo off
setlocal
echo ======================================================================
echo OpenVoice V2 Setup - FIX SCRIPT (Attempt 2)
echo ======================================================================

REM 1. Fix PyTorch
echo [STEP 1] Installing PyTorch...
if exist "torch-*.whl" (
    echo [INFO] Found local PyTorch wheel. Installing from local file...
    for %%f in (torch-*.whl) do pip install "%%f"
    echo [INFO] Installing torchvision/torchaudio - Network download...
    pip install torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo [INFO] Local file not found. attempting network download...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --default-timeout=1000 --no-cache-dir
)

REM 2. Install Requirements (Dependencies)
echo [STEP 2] Installing requirements...
REM Using --prefer-binary to avoid compiling av/others from source
pip install -r requirements.txt --prefer-binary

REM 3. Fix MeloTTS (Git connection issue)
echo [STEP 3] Installing MeloTTS...
pip install melotts --no-deps
if %errorlevel% neq 0 (
    echo [WARN] PyPI install failed, retrying git...
    pip install git+https://github.com/myshell-ai/MeloTTS.git --default-timeout=1000
)

REM 4. Install basic MeloTTS deps manually if no-deps was used
pip install txtsplit
pip install cached_path
pip install transformers==4.27.4
pip install num2words==0.5.12
pip install unidic-lite
pip install mecab-python3
pip install pykakasi
pip install fugashi
pip install g2p_en
pip install anyascii
pip install jamo
pip install gruut[de,es,fr]==2.2.3
pip install g2pkk>=0.1.1

REM 5. Finalize Unidic
echo [STEP 4] Downloading Unidic...
python -m unidic download

echo.
echo ======================================================================
echo Setup Attempt 2 Complete.
echo Please run 'python app_v2.py' to test.
echo ======================================================================
pause
