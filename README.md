# AI Receptionist Backend

Django REST API backend for the AI Receptionist system. Handles webhooks, voice processing (STT/TTS), and communicates with the agent API.

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

## Setup

### 1. Install Dependencies

```bash
# Using conda (recommended)
conda activate backend  # or your preferred environment
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the `backend/` directory:

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
LOCAL_TTS_MODEL=coqui  # Options: coqui, piper
COQUI_TTS_MODEL=tts_models/en/ljspeech/tacotron2-DDC
WHISPER_COMPUTE_TYPE=int8_float16  # Options: int8, int8_float16, float16, float32

# OpenAI Configuration (optional - for TTS/STT fallback)
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

The backend includes a voice service (`backend/services/voice_service.py`) that supports:

### Local Options:
- **STT**: faster-whisper (offline speech-to-text)
- **TTS**: Coqui TTS or Piper TTS (offline text-to-speech)

### Cloud Options:
- **STT/TTS**: OpenAI API (requires API key)

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
│   └── logger.py       # Structured logging
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

- **Coqui TTS**: First run will download models automatically
- **faster-whisper**: Models are downloaded automatically on first use
- **ffmpeg**: Install separately: `brew install ffmpeg` (macOS) or `apt-get install ffmpeg` (Linux)

### Database Issues

- SQLite is used by default (good for development)
- For production, switch to PostgreSQL via `DATABASE_URL`
- Run migrations: `python manage.py migrate`

## License

Proprietary - All rights reserved
