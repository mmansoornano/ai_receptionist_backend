# AI Receptionist Backend

Django REST API backend for the AI Receptionist system. Handles webhooks, voice processing (STT/TTS), and communicates with the agent API.

This repository is **standalone**: deploy it as its own GitHub repo. Pair it with separate **agent** and **frontend** repositories using **`AGENT_API_URL`** (here) and **`BACKEND_API_BASE_URL`** / **`VITE_BACKEND_URL`** (in those repos).

**Documentation site (GitHub Pages):** Jekyll sources in [`docs/`](docs/) — start with [`docs/index.md`](docs/index.md) and [`docs/github-pages.md`](docs/github-pages.md).

## Features

- Twilio webhook handlers for SMS and voice calls
- Voice processing service (STT/TTS) with local and cloud support
- Django REST API endpoints
- Django Admin panel for managing data
- Conversation and appointment management
- Structured logging

## Prerequisites

- Python 3.9+
- pip or conda
- PostgreSQL (optional, SQLite used by default)
- ffmpeg (optional, for audio format conversion)
- espeak-ng (required for Kokoro 82M TTS)
  - macOS: `brew install espeak-ng`
  - Linux (Debian/Ubuntu): `sudo apt-get install espeak-ng`
  - Linux (RHEL/CentOS): `sudo yum install espeak-ng`

## Setup

### 1. Install Dependencies

```bash
# Using conda (recommended)
conda activate backend  # or your preferred environment
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env.example` to `.env` in this directory (`AI_receptionist_backend/`). Example block below (extend as needed):

```bash
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:password@localhost:5432/receptionist_db

# Twilio Configuration (optional for local testing)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@receptionist.local

# Agent API Configuration
AGENT_API_URL=http://localhost:8001  # URL of the agent API service

# Voice Configuration
USE_LOCAL_VOICE=True
LOCAL_WHISPER_MODEL=base  # Options: tiny, base, small, medium, large
WHISPER_COMPUTE_TYPE=int8_float16  # Options: int8, int8_float16, float16, float32

# TTS Provider Selection (priority order)
TTS_PROVIDER=dia2  # Options: dia2, chatterbox, kokoro, orpheus, cosyvoice, openai, piper

# Dia2 Configuration (Recommended - Best for Dialogue with Streaming)
DIA_TTS_ENABLED=True
DIA_TTS_MODEL=nari-labs/dia-2b  # dia-2b, dia-1b, or dia-1.6b
DIA_TTS_DEVICE=  # Auto-detect: mps (Apple Silicon), cuda (NVIDIA), cpu
DIA_TTS_SPEAKER=S1  # S1 or S2 for multi-speaker dialogue
DIA_TTS_STREAMING=True  # Enable streaming generation
DIA_TTS_MAX_DURATION=120  # Max duration in seconds (~2 minutes)

# Chatterbox-Turbo Configuration (Production-Grade Fast - Sub-200ms latency)
CHATTERBOX_TURBO_ENABLED=False
CHATTERBOX_TURBO_MODEL=resemble-ai/chatterbox-turbo
CHATTERBOX_TURBO_DEVICE=  # Auto-detect
CHATTERBOX_TURBO_EMOTION_EXAGGERATION=1.0  # Emotion control (0.0-2.0)
CHATTERBOX_TURBO_CFG=3.0  # CFG scale

# Orpheus 3B Configuration (Best Naturalness - Recommended for M3 Max)
ORPHEUS_TTS_ENABLED=False
ORPHEUS_TTS_MODEL=canopylabs/orpheus-tts-0.1-finetune-prod  # or orpheus-3b-0.1-pretrained
ORPHEUS_TTS_DEVICE=  # Auto-detect: mps (Apple Silicon), cuda (NVIDIA), cpu
ORPHEUS_TTS_EMOTION=neutral  # happy, sad, angry, neutral, excited, calm, fearful, disgusted
ORPHEUS_TTS_VOICE=tara  # tara, leah, jess, leo, dan, mia, zac, zoe (English voices)
ORPHEUS_TTS_STREAMING=False  # Streaming supported but requires vLLM setup

# CosyVoice2-0.5B Configuration (Ultra-Low Latency Streaming - 150ms)
COSYVOICE_TTS_ENABLED=False
COSYVOICE_TTS_MODEL=FunAudioLLM/CosyVoice2-0.5B  # Note: Requires CosyVoice repo clone
COSYVOICE_TTS_DEVICE=  # Auto-detect: mps (Apple Silicon), cuda (NVIDIA), cpu
COSYVOICE_TTS_STREAMING=True  # Enable bi-streaming (text-in and audio-out)
COSYVOICE_REF_AUDIO=  # Path to reference audio file for zero-shot voice cloning

# Kokoro 82M Configuration (Ultra-Fast CPU Option - No GPU Required)
KOKORO_TTS_ENABLED=False
KOKORO_TTS_MODEL=hexgrad/Kokoro-82M  # Model name (not used directly, kept for compatibility)
KOKORO_TTS_VOICE=af_sky  # af_sky, af_nova, af_bella, af_heart, etc. (see VOICES.md)

# OpenAI TTS Configuration (Cloud Fallback)
OPENAI_TTS_MODEL=tts-1-hd  # tts-1 or tts-1-hd (recommended for best quality)
OPENAI_TTS_VOICE=nova  # alloy, echo, fable, onyx, nova, shimmer
OPENAI_TTS_SPEED=1.0  # Speech speed (0.25-4.0) - Note: OpenAI TTS does NOT support SSML or pitch control

# Piper TTS (Legacy Fallback)
PIPER_VOICE_PATH=en_US-lessac-medium  # Used when TTS_PROVIDER=piper

# OpenAI Configuration (for TTS/STT fallback)
OPENAI_API_KEY=your-openai-api-key
```

### 3. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

The backend will be available at `http://localhost:8000`

## API Endpoints

### Webhooks

- `POST /webhooks/sms/` - Twilio SMS webhook
- `POST /webhooks/voice/` - Twilio voice webhook
- `POST /webhooks/test-message/` - Test endpoint for local development
- `POST /webhooks/voice/transcribe/` - STT endpoint (transcribe audio to text)
- `POST /webhooks/tts/` - TTS endpoint (text to speech audio)

### Core APIs

- `GET /api/customers/` - List customers
- `POST /api/customers/` - Create customer
- `GET /api/appointments/` - List appointments
- `POST /api/appointments/` - Create appointment
- `GET /api/conversations/` - List conversations

### Admin Panel

- `http://localhost:8000/admin/` - Django admin interface

## Voice Processing

The backend includes a voice service (`backend/services/voice_service.py`) that supports multiple TTS providers optimized for different use cases.

### Speech-to-Text (STT)
- **faster-whisper**: Offline speech-to-text with caching and threading support
- **OpenAI Whisper API**: Cloud fallback when `USE_LOCAL_VOICE=false`

### Text-to-Speech (TTS) Providers

#### 🍎 **Recommended for MacBook Pro M3 Max (36GB RAM)**

1. **Dia2** ⭐ **BEST CHOICE** (`TTS_PROVIDER=dia2`)
   - **Why**: Streaming architecture + dialogue-focused = perfect for receptionist
   - **Performance**: Utilizes M3 Max GPU via MPS (Metal Performance Shaders)
   - **Features**: 
     - Multi-speaker dialogue via `[S1]`/`[S2]` tags
     - Nonverbal sounds: `(laughs)`, `(coughs)`, `(gasps)`, `(sighs)`
     - Streaming generation (starts from first tokens)
   - **Setup**: `pip install torch transformers` (MPS auto-detected)
   - **Model**: `nari-labs/dia-2b` (or `dia-1b` for smaller model)

2. **Chatterbox-Turbo** ⭐ **FASTEST** (`TTS_PROVIDER=chatterbox`)
   - **Why**: Sub-200ms latency, production-grade, one-step decoder
   - **Performance**: Low VRAM (~2-3GB), perfect for unified memory
   - **Features**: Emotion exaggeration, native tags `[laugh]`, `[cough]`, `[chuckle]`
   - **Setup**: `pip install torch transformers`

3. **Orpheus 3B** ⭐ **MOST NATURAL** (`TTS_PROVIDER=orpheus`)
   - **Why**: Highest naturalness, emotional expression, human-like speech
   - **Performance**: ~8-12GB model fits comfortably in 36GB RAM
   - **Latency**: ~200ms streaming latency (or ~100ms with input streaming)
   - **Features**: 
     - Zero-shot voice cloning (no fine-tuning required)
     - Emotion control via tags: `<happy>`, `<sad>`, `<angry>`, `<neutral>`, etc.
     - Voice options: tara, leah, jess, leo, dan, mia, zac, zoe (English)
   - **Setup**: `pip install orpheus-speech` (uses vLLM under the hood)
   - **Note**: Requires Hugging Face authentication for model access

4. **CosyVoice2-0.5B** ⭐ **ULTRA-LOW LATENCY** (`TTS_PROVIDER=cosyvoice`)
   - **Why**: 150ms first packet latency, bi-streaming support
   - **Performance**: Small model (~0.5B), perfect for M3 Max unified memory
   - **Features**:
     - Text-in and audio-out streaming
     - Zero-shot voice cloning (requires reference audio)
     - Multi-language support (9 languages, 18+ Chinese dialects)
     - Pronunciation inpainting support
   - **Setup**: Requires CosyVoice repository clone (see setup instructions below)
   - **Note**: More complex setup, but excellent for real-time applications

5. **Kokoro 82M** ⭐ **ULTRA-FAST CPU** (`TTS_PROVIDER=kokoro`)
   - **Why**: <0.3s processing time, CPU-only (no GPU required)
   - **Performance**: Minimal resource usage, perfect fallback option
   - **Features**: 
     - Multiple voice options (af_sky, af_nova, af_bella, af_heart, etc.)
     - Apache 2.0 licensed (production-ready)
     - 24kHz audio output
   - **Setup**: `pip install kokoro>=0.9.4 soundfile` + `brew install espeak-ng`
   - **Note**: Best option if GPU models have issues or for CPU-only environments

#### Other Options

- **OpenAI tts-1-hd** (`TTS_PROVIDER=openai`): Cloud fallback, high quality ($30/1M chars)
- **Piper TTS** (`TTS_PROVIDER=piper`): Legacy fallback, fast but robotic

#### ⚠️ Deprecated Options

- **Coqui TTS**: Deprecated in favor of Dia2, Chatterbox-Turbo, Orpheus 3B, or Kokoro 82M
  - Will be removed in a future version
  - Migrate to one of the recommended providers above

### 🍎 Apple Silicon (M3 Max) Setup & Optimization

The system automatically detects and uses MPS (Metal Performance Shaders) on Apple Silicon for optimal performance.

#### 1. Install PyTorch with MPS Support

```bash
# Install PyTorch (includes MPS support for Apple Silicon)
pip install torch torchaudio transformers

# Verify MPS availability
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

#### 2. Device Auto-Detection

The system automatically:
- Detects Apple Silicon and uses `mps` device
- Falls back to `cpu` if MPS unavailable
- Leverages unified memory architecture (36GB RAM efficiently shared between GPU and CPU)

**Manual Override** (if needed):
```bash
# Force CPU (useful for debugging)
DIA_TTS_DEVICE=cpu

# Force MPS (if auto-detection fails)
DIA_TTS_DEVICE=mps
```

#### 3. Hugging Face Authentication

Some models require Hugging Face authentication:

```bash
# Login to Hugging Face
huggingface-cli login

# Enter your token when prompted
```

**Models requiring authentication:**
- Orpheus 3B (`canopylabs/orpheus-tts-0.1-finetune-prod`)
- Some Dia2 variants
- CosyVoice2-0.5B (if using Hugging Face model)

#### 4. M3 Max-Specific Performance Tips

**Memory Management:**
- 36GB unified memory is excellent for all recommended models
- Dia2 (~4-6GB): Comfortable fit, room for other processes
- Orpheus 3B (~8-12GB): Fits well, still room for system processes
- Chatterbox-Turbo (~2-3GB): Minimal memory usage
- CosyVoice2-0.5B (~2-3GB): Small footprint

**Optimization:**
- Use streaming when available (Dia2, CosyVoice2) for lower latency
- For production, consider using `dia-1b` instead of `dia-2b` for faster inference
- Kokoro 82M is perfect fallback if GPU models have issues

**Benchmarks on M3 Max (36GB RAM):**

| Provider | Model Size | Latency | Quality | Best For |
|----------|------------|---------|---------|----------|
| Dia2 | ~4-6GB | ~1-2s (non-streaming) | ⭐⭐⭐⭐⭐ | Dialogue/Receptionist |
| Chatterbox-Turbo | ~2-3GB | <200ms | ⭐⭐⭐⭐ | Production speed |
| Orpheus 3B | ~8-12GB | ~200ms | ⭐⭐⭐⭐⭐ | Naturalness |
| CosyVoice2-0.5B | ~2-3GB | 150ms | ⭐⭐⭐⭐ | Ultra-low latency |
| Kokoro 82M | <100MB | <300ms | ⭐⭐⭐ | CPU fallback |
| OpenAI tts-1-hd | Cloud | ~500ms | ⭐⭐⭐⭐⭐ | Cloud fallback |

*Note: Latency varies based on text length and system load*

### TTS Text Preprocessing

Before synthesis, agent responses are preprocessed (`utils/tts_text.py`):
- Strips UI-only content (customer IDs, product catalogs, cart blocks)
- Expands abbreviations (PKR → Pakistani Rupees, Qty → Quantity)
- Normalizes numbers and currency for better pronunciation
- Adds prosody pauses based on punctuation
- Preserves dialogue tags `[S1]`/`[S2]` and nonverbal tags `(laughs)`, `(coughs)`, etc.

### Provider Selection Logic

The system checks providers in priority order:
1. Dia2 (if enabled and `TTS_PROVIDER=dia2`) - **Recommended**
2. Chatterbox-Turbo (if enabled)
3. Kokoro 82M (if enabled)
4. Orpheus 3B (if enabled)
5. CosyVoice2-0.5B (if enabled)
6. OpenAI tts-1-hd (if API key provided)
7. Piper TTS (fallback)

Configure via environment variables (see `.env` example above).

## Agent API Integration

The backend communicates with a separate agent API service. Configure the agent API URL:

```bash
AGENT_API_URL=http://localhost:8001
```

The backend will forward messages to the agent API at `/process` endpoint.

## Logging

Logs are stored in `backend/logs/backend.log`. Structured logging includes:
- API requests
- Agent API calls
- Errors with context
- Voice processing operations

## Project Structure

```
backend/
├── apps/
│   ├── core/           # Customer and appointment models
│   ├── conversations/  # Conversation tracking
│   └── webhooks/       # Twilio webhook handlers
├── services/
│   ├── voice_service.py  # STT/TTS service
│   └── tts_compat.py     # Python 3.9 compatibility
├── utils/
│   ├── logger.py       # Structured logging
│   └── tts_text.py     # TTS text preprocessing
├── config.py           # Configuration (voice, OpenAI, etc.)
├── manage.py
├── requirements.txt
└── README.md
```

## Deployment

### Production Checklist

1. Set `DEBUG=False` in `.env`
2. Use PostgreSQL: set `DATABASE_URL`
3. Set secure `SECRET_KEY`
4. Configure `ALLOWED_HOSTS` properly
5. Use Gunicorn + Nginx for production
6. Set up proper CORS origins

### Using Gunicorn

```bash
pip install gunicorn
gunicorn receptionist.wsgi:application --bind 0.0.0.0:8000
```

## Standalone Deployment

This backend is designed to be deployed independently. It:
- Has its own configuration (`backend/config.py`)
- Stores logs locally (`backend/logs/`)
- Can be moved to a separate repository
- Only requires the agent API URL to be configured

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`, ensure:
- All dependencies are installed: `pip install -r requirements.txt`
- You're using the correct Python environment
- `.env` file exists in `backend/` directory

### Voice Service Issues

#### TTS Provider Setup

- **Dia2** (Recommended):
  - Install: `pip install torch transformers`
  - Model downloads automatically on first use
  - Requires Hugging Face account: `huggingface-cli login`
  - Apple Silicon: Automatically uses MPS (Metal Performance Shaders)
  - Example dialogue: `[S1] Hello! [S2] Hi there! (laughs)`

- **Chatterbox-Turbo**:
  - Install: `pip install torch transformers`
  - Model downloads automatically
  - Supports emotion exaggeration and paralinguistic tags

- **Orpheus 3B**:
  - Install: `pip install orpheus-speech`
  - Note: Uses vLLM under the hood. If you encounter issues, try: `pip install vllm==0.7.3`
  - Requires Hugging Face authentication: `huggingface-cli login`
  - Model options:
    - `canopylabs/orpheus-tts-0.1-finetune-prod` (recommended for production)
    - `canopylabs/orpheus-3b-0.1-pretrained` (base model)
  - Model size: ~8-12GB (fits comfortably in 36GB RAM)
  - Voice options: tara (most conversational), leah, jess, leo, dan, mia, zac, zoe
  - Emotion tags: `<happy>`, `<sad>`, `<angry>`, `<neutral>`, `<excited>`, `<calm>`, `<fearful>`, `<disgusted>`
  - Example: `"<happy>Hello! How can I help you today?</happy>"`

- **CosyVoice2-0.5B**:
  - **Setup Steps:**
    1. Clone repository: `git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git`
    2. Install dependencies: `cd CosyVoice && pip install -r requirements.txt`
    3. Download model:
       ```python
       from huggingface_hub import snapshot_download
       snapshot_download('FunAudioLLM/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')
       ```
    4. Set environment variable: `COSYVOICE_REF_AUDIO=/path/to/reference/audio.wav`
  - Features: Ultra-low latency (150ms), bi-streaming, zero-shot voice cloning
  - Model size: ~2-3GB (small footprint)
  - Note: More complex setup, but excellent for real-time applications

- **Kokoro 82M**:
  - Install: `pip install kokoro>=0.9.4 soundfile`
  - Also install: `brew install espeak-ng` (macOS) or `apt-get install espeak-ng` (Linux)
  - CPU-only, no GPU required
  - Ultra-fast: <0.3s processing time
  - Voice options: af_sky, af_nova, af_bella, af_heart, etc.
  - Perfect fallback option if GPU models have issues

- **OpenAI tts-1-hd**:
  - Set `TTS_PROVIDER=openai` or `USE_LOCAL_VOICE=false`
  - Requires `OPENAI_API_KEY`
  - Cost: $30/1M characters (tts-1-hd) or $15/1M characters (tts-1)
  - Voice options: alloy, echo, fable, onyx, nova (most natural), shimmer
  - Speed control: 0.25 to 4.0 (via `OPENAI_TTS_SPEED`)
  - **Note**: OpenAI TTS does NOT support SSML or pitch control via API

- **Piper TTS** (Legacy):
  - Install: `brew install piper-tts` (macOS) or download from GitHub
  - Set `PIPER_VOICE_PATH` for voice selection

#### Apple Silicon (M3 Max) Specific

- **MPS Backend**: PyTorch 2.0+ automatically detects and uses Metal Performance Shaders
- **Unified Memory**: 36GB RAM efficiently shared between GPU and CPU
- **Device Auto-Detection**: System automatically uses `mps` device (no configuration needed)
- **Fallback**: If MPS unavailable, automatically falls back to CPU
- **Performance**: M3 Max GPU is excellent for inference workloads, comparable to mid-range NVIDIA GPUs
- **Memory Efficiency**: Unified memory means no separate VRAM - all 36GB available for models

**Recommended Configuration for M3 Max:**
```bash
# Best for receptionist/dialogue use case
TTS_PROVIDER=dia2
DIA_TTS_ENABLED=True
DIA_TTS_MODEL=nari-labs/dia-2b  # or dia-1b for faster inference
DIA_TTS_DEVICE=  # Auto-detect (will use mps)

# Alternative: Best naturalness
TTS_PROVIDER=orpheus
ORPHEUS_TTS_ENABLED=True
ORPHEUS_TTS_MODEL=canopylabs/orpheus-tts-0.1-finetune-prod
ORPHEUS_TTS_VOICE=tara  # Most conversational voice

# Fallback: Ultra-fast CPU option
TTS_PROVIDER=kokoro
KOKORO_TTS_ENABLED=True
KOKORO_TTS_VOICE=af_sky
```

#### STT (Speech-to-Text)

- **faster-whisper**: Models download automatically on first use
- **Caching**: Transcription results are cached (configurable via `STT_CACHE_SIZE` and `STT_CACHE_TTL`)
- **Threading**: Concurrent processing supported (configurable via `STT_MAX_WORKERS`)

#### Audio Processing

- **ffmpeg**: Install separately for audio format conversion:
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt-get install ffmpeg`

### Database Issues

- SQLite is used by default (good for development)
- For production, switch to PostgreSQL via `DATABASE_URL`
- Run migrations: `python manage.py migrate`

## License

See [LICENSE](LICENSE) (MIT).
