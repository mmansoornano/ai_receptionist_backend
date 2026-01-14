"""Backend-specific configuration utilities."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend directory
backend_root = Path(__file__).parent
env_path = backend_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Also try parent directory .env for backward compatibility (monorepo setup)
parent_env = backend_root.parent / '.env'
if parent_env.exists():
    load_dotenv(parent_env)

# Fallback to system environment
load_dotenv()

# Common configuration
PROJECT_ROOT = backend_root

# Voice Configuration
# - faster-whisper (STT) - local speech-to-text
# - Piper TTS or Coqui TTS (TTS) - local text-to-speech
USE_LOCAL_VOICE = os.getenv('USE_LOCAL_VOICE', 'True').lower() == 'true'
LOCAL_WHISPER_MODEL = os.getenv('LOCAL_WHISPER_MODEL', 'base')  # base, small, medium
LOCAL_TTS_MODEL = os.getenv('LOCAL_TTS_MODEL', 'coqui')  # piper or coqui (default: coqui)
PIPER_VOICE_PATH = os.getenv('PIPER_VOICE_PATH', 'en_US-lessac-medium')  # Piper voice model name or path
COQUI_TTS_MODEL = os.getenv('COQUI_TTS_MODEL', 'tts_models/en/ljspeech/tacotron2-DDC')  # Coqui TTS model
COQUI_VOICE_ID = os.getenv('COQUI_VOICE_ID', None)  # Optional voice ID for multi-voice models
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8_float16')  # Compute type for faster-whisper

# OpenAI Configuration (for TTS/STT fallback)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
