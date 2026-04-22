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
# - Multiple TTS providers available (Dia2, Chatterbox-Turbo, Orpheus 3B, Kokoro 82M, etc.)
USE_LOCAL_VOICE = os.getenv('USE_LOCAL_VOICE', 'True').lower() == 'true'
LOCAL_WHISPER_MODEL = os.getenv('LOCAL_WHISPER_MODEL', 'base')  # base, small, medium
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8_float16')  # Compute type for faster-whisper

# TTS Provider Selection (priority order)
TTS_PROVIDER = os.getenv('TTS_PROVIDER', 'dia2')  # dia2, chatterbox, kokoro, orpheus, cosyvoice, openai, piper

# Dia2 Configuration (Recommended - Best for Dialogue with Streaming)
DIA_TTS_ENABLED = os.getenv('DIA_TTS_ENABLED', 'True').lower() == 'true'
DIA_TTS_MODEL = os.getenv('DIA_TTS_MODEL', 'nari-labs/Dia2-2B')  # Dia2-2B, Dia2-1B, or Dia2-1.6B (case-sensitive)
DIA_TTS_DEVICE = os.getenv('DIA_TTS_DEVICE', None)  # None = auto-detect (mps/cuda/cpu)
DIA_TTS_SPEAKER = os.getenv('DIA_TTS_SPEAKER', 'S1')  # S1 or S2 for multi-speaker
DIA_TTS_STREAMING = os.getenv('DIA_TTS_STREAMING', 'True').lower() == 'true'
DIA_TTS_MAX_DURATION = int(os.getenv('DIA_TTS_MAX_DURATION', '120'))  # seconds (~2 minutes for Dia2)
DIA_TTS_TEMPERATURE = float(os.getenv('DIA_TTS_TEMPERATURE', '0.4'))  # Lower = more consistent voice (0.3-0.5 recommended)
DIA_TTS_SEED = os.getenv('DIA_TTS_SEED')  # Random seed for reproducibility (set to None or empty for variation)
if DIA_TTS_SEED:
    DIA_TTS_SEED = int(DIA_TTS_SEED)
else:
    DIA_TTS_SEED = None

# Chatterbox-Turbo Configuration (Production-Grade Fast)
CHATTERBOX_TURBO_ENABLED = os.getenv('CHATTERBOX_TURBO_ENABLED', 'False').lower() == 'true'
CHATTERBOX_TURBO_MODEL = os.getenv('CHATTERBOX_TURBO_MODEL', 'resemble-ai/chatterbox-turbo')
CHATTERBOX_TURBO_DEVICE = os.getenv('CHATTERBOX_TURBO_DEVICE', None)  # None = auto-detect
CHATTERBOX_TURBO_EMOTION_EXAGGERATION = float(os.getenv('CHATTERBOX_TURBO_EMOTION_EXAGGERATION', '1.0'))
CHATTERBOX_TURBO_CFG = float(os.getenv('CHATTERBOX_TURBO_CFG', '3.0'))

# Orpheus 3B Configuration (Best Naturalness)
ORPHEUS_TTS_ENABLED = os.getenv('ORPHEUS_TTS_ENABLED', 'False').lower() == 'true'
ORPHEUS_TTS_MODEL = os.getenv('ORPHEUS_TTS_MODEL', 'canopylabs/orpheus-3b-0.1-pretrained')
ORPHEUS_TTS_DEVICE = os.getenv('ORPHEUS_TTS_DEVICE', None)  # None = auto-detect
ORPHEUS_TTS_EMOTION = os.getenv('ORPHEUS_TTS_EMOTION', 'neutral')  # happy, sad, angry, neutral
ORPHEUS_TTS_STREAMING = os.getenv('ORPHEUS_TTS_STREAMING', 'False').lower() == 'true'

# CosyVoice2-0.5B Configuration (Ultra-Low Latency Streaming)
COSYVOICE_TTS_ENABLED = os.getenv('COSYVOICE_TTS_ENABLED', 'False').lower() == 'true'
COSYVOICE_TTS_MODEL = os.getenv('COSYVOICE_TTS_MODEL', 'FunAudioLLM/CosyVoice2-0.5B')  # Note: Requires CosyVoice repo clone
COSYVOICE_TTS_DEVICE = os.getenv('COSYVOICE_TTS_DEVICE', None)  # None = auto-detect
COSYVOICE_TTS_STREAMING = os.getenv('COSYVOICE_TTS_STREAMING', 'True').lower() == 'true'

# Kokoro 82M Configuration (Fast CPU Alternative)
KOKORO_TTS_ENABLED = os.getenv('KOKORO_TTS_ENABLED', 'False').lower() == 'true'
KOKORO_TTS_MODEL = os.getenv('KOKORO_TTS_MODEL', 'hexgrad/Kokoro-82M')
KOKORO_TTS_USE_ONNX = os.getenv('KOKORO_TTS_USE_ONNX', 'True').lower() == 'true'
KOKORO_TTS_VOICE = os.getenv('KOKORO_TTS_VOICE', 'af_sky')  # af_sky, af_nova, af_bella, etc.

# OpenAI TTS Configuration (Cloud Fallback)
OPENAI_TTS_MODEL = os.getenv('OPENAI_TTS_MODEL', 'tts-1-hd')  # tts-1 or tts-1-hd
OPENAI_TTS_VOICE = os.getenv('OPENAI_TTS_VOICE', 'nova')  # alloy, echo, fable, onyx, nova, shimmer
OPENAI_TTS_USE_SSML = os.getenv('OPENAI_TTS_USE_SSML', 'True').lower() == 'true'
OPENAI_TTS_SPEED = float(os.getenv('OPENAI_TTS_SPEED', '1.0'))
OPENAI_TTS_PITCH = os.getenv('OPENAI_TTS_PITCH', '0%')

# Piper TTS (Keep as fallback)
LOCAL_TTS_MODEL = os.getenv('LOCAL_TTS_MODEL', 'piper')  # Legacy: piper or coqui (deprecated)
PIPER_VOICE_PATH = os.getenv('PIPER_VOICE_PATH', 'en_US-lessac-medium')  # Piper voice model name or path

# Coqui TTS (DEPRECATED - kept for backward compatibility only)
# ⚠️ WARNING: Coqui TTS is deprecated and will be removed in a future version.
# Please migrate to one of these recommended alternatives:
#   - Dia2 (TTS_PROVIDER=dia2): Best for dialogue/receptionist use cases
#   - Chatterbox-Turbo (TTS_PROVIDER=chatterbox): Production-grade speed
#   - Orpheus 3B (TTS_PROVIDER=orpheus): Best naturalness
#   - Kokoro 82M (TTS_PROVIDER=kokoro): Ultra-fast CPU option
COQUI_TTS_MODEL = os.getenv('COQUI_TTS_MODEL', 'tts_models/en/ljspeech/vits')  # Deprecated
COQUI_VOICE_ID = os.getenv('COQUI_VOICE_ID', None)  # Deprecated

# OpenAI Configuration (for TTS/STT fallback)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
