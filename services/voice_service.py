"""Voice processing service with local and cloud options."""
from typing import Optional, Dict, Tuple
import os
import tempfile
import subprocess
import threading
import hashlib
from pathlib import Path
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import time

# Import compatibility shim for Python 3.9 (must be before TTS import)
try:
    from services.tts_compat import *  # Applies Python 3.9 compatibility patches
except ImportError:
    pass  # If compat module doesn't exist, continue (might be Python 3.10+)

from config import (
    USE_LOCAL_VOICE, OPENAI_API_KEY, LOCAL_WHISPER_MODEL, WHISPER_COMPUTE_TYPE, PIPER_VOICE_PATH,
    TTS_PROVIDER, DIA_TTS_ENABLED, DIA_TTS_MODEL, DIA_TTS_DEVICE, DIA_TTS_SPEAKER, 
    DIA_TTS_STREAMING, DIA_TTS_MAX_DURATION, DIA_TTS_TEMPERATURE, DIA_TTS_SEED,
    CHATTERBOX_TURBO_ENABLED, CHATTERBOX_TURBO_MODEL, CHATTERBOX_TURBO_DEVICE,
    CHATTERBOX_TURBO_EMOTION_EXAGGERATION, CHATTERBOX_TURBO_CFG,
    ORPHEUS_TTS_ENABLED, ORPHEUS_TTS_MODEL, ORPHEUS_TTS_DEVICE, ORPHEUS_TTS_EMOTION, ORPHEUS_TTS_STREAMING,
    COSYVOICE_TTS_ENABLED, COSYVOICE_TTS_MODEL, COSYVOICE_TTS_DEVICE, COSYVOICE_TTS_STREAMING,
    KOKORO_TTS_ENABLED, KOKORO_TTS_MODEL, KOKORO_TTS_USE_ONNX, KOKORO_TTS_VOICE,
    OPENAI_TTS_MODEL, OPENAI_TTS_VOICE, OPENAI_TTS_USE_SSML, OPENAI_TTS_SPEED, OPENAI_TTS_PITCH,
    # Deprecated
    LOCAL_TTS_MODEL, COQUI_TTS_MODEL, COQUI_VOICE_ID
)

# Coqui TTS model cache (shared across requests); init guarded by _coqui_tts_lock.
# DEPRECATED: Coqui TTS is deprecated in favor of Dia2, Chatterbox-Turbo, etc.
_coqui_tts_model = None
_coqui_tts_lock = threading.Lock()

# Dia2 TTS model cache (shared across requests); init guarded by _dia2_lock.
_dia2_model_cache = None
_dia2_lock = threading.Lock()

# TTS model locks for thread-safe initialization
_chatterbox_lock = threading.Lock()
_kokoro_lock = threading.Lock()
_orpheus_lock = threading.Lock()
_cosyvoice_lock = threading.Lock()

# STT transcription cache (LRU cache with thread safety)
_stt_cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
_stt_cache_lock = threading.Lock()
_stt_cache_max_size = int(os.getenv('STT_CACHE_SIZE', '100'))  # Max cached transcriptions
_stt_cache_ttl = float(os.getenv('STT_CACHE_TTL', '3600'))  # Cache TTL in seconds (1 hour default)

# Thread pool for concurrent STT processing
_stt_executor: Optional[ThreadPoolExecutor] = None
_stt_executor_lock = threading.Lock()
_stt_max_workers = int(os.getenv('STT_MAX_WORKERS', '4'))  # Max concurrent STT operations


def _get_device(device_override: Optional[str] = None) -> str:
    """Auto-detect best device for PyTorch operations.
    
    Priority:
    1. Device override (if provided)
    2. MPS (Metal Performance Shaders) for Apple Silicon (M3 Max, etc.)
    3. CUDA for NVIDIA GPUs
    4. CPU fallback
    
    Args:
        device_override: Optional device string ('mps', 'cuda', 'cpu')
    
    Returns:
        Device string: 'mps', 'cuda', or 'cpu'
    """
    if device_override:
        return device_override
    
    # Check for MPS (Apple Silicon)
    try:
        import torch
        if torch.backends.mps.is_available():
            return 'mps'
    except (ImportError, AttributeError):
        pass
    
    # Check for CUDA
    try:
        import torch
        if torch.cuda.is_available():
            return 'cuda'
    except ImportError:
        pass
    
    # Fallback to CPU
    return 'cpu'


class VoiceService:
    """Service for voice processing (STT/TTS) with local and cloud support."""
    
    def __init__(self):
        self.use_local = USE_LOCAL_VOICE
        self.openai_key = OPENAI_API_KEY
        self.whisper_model = LOCAL_WHISPER_MODEL or "base"
        self.tts_model = LOCAL_TTS_MODEL or "piper"  # Legacy, use TTS_PROVIDER instead
        self._whisper_model_instance = None
        self._whisper_model_lock = threading.Lock()  # Thread-safe model initialization
        
        # Initialize TTS model caches (lazy loading)
        # Note: Dia2 model is cached at module level (_dia2_model_cache) for reuse across requests
        self._dia2_processor = None  # Deprecated, not used
        self._chatterbox_model = None
        self._chatterbox_processor = None
        self._kokoro_model = None
        self._orpheus_pipeline = None
        self._cosyvoice_model = None
        self._cosyvoice_processor = None
    
    def _get_whisper_model(self):
        """Get or create Whisper model instance (cached, thread-safe)."""
        if self._whisper_model_instance is None:
            with self._whisper_model_lock:
                # Double-check pattern
                if self._whisper_model_instance is None:
                    try:
                        from faster_whisper import WhisperModel
                        
                        # Use CPU for M3 Max (can use "cuda" if you have GPU)
                        # For Apple Silicon (M3 Max), use "cpu" with optimized compute type
                        device = "cpu"
                        # Try int8_float16 first, fallback to int8 if it fails
                        compute_type = WHISPER_COMPUTE_TYPE or os.getenv('WHISPER_COMPUTE_TYPE', 'int8_float16')
                        
                        # Optimize num_workers based on CPU cores (but cap at 4 for stability)
                        import multiprocessing
                        num_workers = min(multiprocessing.cpu_count(), 4)
                        
                        # Try to initialize WhisperModel with fallback compute types
                        try:
                            self._whisper_model_instance = WhisperModel(
                                self.whisper_model,
                                device=device,
                                compute_type=compute_type,
                                num_workers=num_workers,  # Use multiple workers for better performance
                                download_root=None  # Use default cache location
                            )
                        except Exception as init_error:
                            error_str = str(init_error)
                            
                            # Check if it's a corrupted model cache issue
                            if 'Unable to open file' in error_str or 'model.bin' in error_str:
                                # Try to clear cache and retry once
                                import shutil
                                cache_path = os.path.expanduser('~/.cache/huggingface/hub')
                                model_cache_pattern = f"models--Systran--faster-whisper-{self.whisper_model}"
                                try:
                                    for item in os.listdir(cache_path):
                                        if model_cache_pattern in item:
                                            full_path = os.path.join(cache_path, item)
                                            if os.path.isdir(full_path):
                                                shutil.rmtree(full_path)
                                except Exception as cache_error:
                                    pass  # Ignore cache clearing errors
                            
                            # Fallback to int8 if int8_float16 fails
                            if compute_type == 'int8_float16':
                                compute_type = 'int8'
                                try:
                                    self._whisper_model_instance = WhisperModel(
                                        self.whisper_model,
                                        device=device,
                                        compute_type=compute_type,
                                        num_workers=num_workers,
                                        download_root=None
                                    )
                                except Exception as fallback_error:
                                    # If fallback also fails, re-raise with helpful message
                                    raise RuntimeError(
                                        f"Failed to initialize Whisper model '{self.whisper_model}'. "
                                        f"Original error: {error_str}. "
                                        f"Fallback error: {str(fallback_error)}. "
                                        f"Try clearing cache: rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-{self.whisper_model}"
                                    ) from fallback_error
                            else:
                                # Re-raise if fallback also fails or if already using fallback
                                raise
                    except ImportError as e:
                        raise ImportError(
                            "faster-whisper not installed. Install with: pip install faster-whisper"
                        )
                    except Exception as e:
                        raise
        return self._whisper_model_instance
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for caching."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            # If hashing fails, use file path + mtime as fallback
            try:
                mtime = os.path.getmtime(file_path)
                return hashlib.sha256(f"{file_path}:{mtime}".encode()).hexdigest()
            except Exception:
                # Last resort: use path only
                return hashlib.sha256(file_path.encode()).hexdigest()
    
    def _get_stt_cache_key(self, audio_file_path: str) -> str:
        """Generate cache key for STT transcription."""
        file_hash = self._get_file_hash(audio_file_path)
        return f"stt:{self.whisper_model}:{file_hash}"
    
    def _get_cached_transcription(self, cache_key: str) -> Optional[str]:
        """Get cached transcription if available and not expired."""
        with _stt_cache_lock:
            if cache_key in _stt_cache:
                text, timestamp = _stt_cache[cache_key]
                # Check if cache entry is still valid
                if time.time() - timestamp < _stt_cache_ttl:
                    # Move to end (most recently used)
                    _stt_cache.move_to_end(cache_key)
                    return text
                else:
                    # Expired, remove it
                    del _stt_cache[cache_key]
        return None
    
    def _set_cached_transcription(self, cache_key: str, text: str):
        """Cache transcription with LRU eviction."""
        with _stt_cache_lock:
            # Remove oldest entries if cache is full
            while len(_stt_cache) >= _stt_cache_max_size:
                _stt_cache.popitem(last=False)  # Remove oldest (first) item
            
            # Add new entry
            _stt_cache[cache_key] = (text, time.time())
    
    def _get_stt_executor(self) -> ThreadPoolExecutor:
        """Get or create thread pool executor for STT operations."""
        global _stt_executor
        if _stt_executor is None:
            with _stt_executor_lock:
                if _stt_executor is None:
                    _stt_executor = ThreadPoolExecutor(max_workers=_stt_max_workers, thread_name_prefix="stt")
        return _stt_executor
    
    def _convert_audio_format(self, input_path: str, output_path: str = None) -> str:
        """Convert audio to WAV format with proper sample rate for Whisper.
        
        Whisper works best with:
        - Format: WAV (PCM)
        - Sample rate: 16kHz (16000 Hz)
        - Channels: Mono
        
        Uses ffmpeg if available, otherwise returns original path.
        """
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.wav')
        
        try:
            # Check if ffmpeg is available
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, 
                         check=True)
            
            # Convert to WAV, 16kHz, mono (with optimized settings for speed)
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-ar', '16000',  # Sample rate: 16kHz
                '-ac', '1',      # Mono channel
                '-f', 'wav',     # WAV format
                '-y',            # Overwrite output
                '-threads', '2', # Use 2 threads for faster conversion
                output_path
            ], check=True, capture_output=True, timeout=30)
            
            return output_path
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # ffmpeg not available or conversion failed
            # faster-whisper can handle many formats, so return original
            return input_path
    
    def speech_to_text(self, audio_file_path: str, use_cache: bool = True, use_threading: bool = True) -> str:
        """Convert speech to text with caching and optional threading.
        
        Options:
        1. faster-whisper (local, if USE_LOCAL_VOICE=True)
        2. OpenAI Whisper API (if OPENAI_API_KEY provided and USE_LOCAL_VOICE=False)
        
        Args:
            audio_file_path: Path to audio file (any format supported by ffmpeg or Whisper)
            use_cache: Whether to use transcription cache (default: True)
            use_threading: Whether to process in background thread (default: True)
        
        Returns:
            Transcribed text string
        """
        # Check cache first
        if use_cache:
            cache_key = self._get_stt_cache_key(audio_file_path)
            cached_text = self._get_cached_transcription(cache_key)
            if cached_text is not None:
                return cached_text
        
        if self.use_local:
            # Use local faster-whisper
            if use_threading:
                # Submit to thread pool for concurrent processing
                executor = self._get_stt_executor()
                future = executor.submit(self._speech_to_text_local, audio_file_path, use_cache)
                return future.result()  # Wait for result
            else:
                return self._speech_to_text_local(audio_file_path, use_cache)
        else:
            # Use OpenAI Whisper API
            if not self.openai_key:
                raise ValueError(
                    "OPENAI_API_KEY required when USE_LOCAL_VOICE=False. "
                    "Set USE_LOCAL_VOICE=true for local STT or provide OPENAI_API_KEY"
                )
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_key)
            with open(audio_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    prompt="This is a conversation with an AI receptionist for a service business."  # Context hint
                )
            text = transcript.text
            # Cache OpenAI results too
            if use_cache:
                cache_key = self._get_stt_cache_key(audio_file_path)
                self._set_cached_transcription(cache_key, text)
            return text
    
    def _speech_to_text_local(self, audio_file_path: str, use_cache: bool = True) -> str:
        """Internal method for local STT processing."""
        converted_path = None
        cache_key = self._get_stt_cache_key(audio_file_path) if use_cache else None
        
        try:
            # Convert audio format if needed (optimizes for Whisper)
            converted_path = self._convert_audio_format(audio_file_path)
            
            model = self._get_whisper_model()
            
            # Optimized transcription parameters for speed and accuracy
            segments, info = model.transcribe(
                converted_path,
                language="en",
                beam_size=3,           # Reduced from 5 for faster processing
                vad_filter=True,        # Voice activity detection (removes silence)
                vad_parameters=dict(
                    min_silence_duration_ms=500,  # Minimum silence to split
                    threshold=0.5                 # VAD threshold
                ),
                initial_prompt="This is a conversation with an AI receptionist for a service business.",  # Context hint
                condition_on_previous_text=False,  # Disable for faster processing
                compression_ratio_threshold=2.4,     # Detect repetition
                log_prob_threshold=-1.0,            # Filter low-confidence
                no_speech_threshold=0.6,            # Detect no speech
                temperature=0.0,                    # Deterministic output
                best_of=1                            # Faster decoding
            )
            
            # Combine all segments with proper spacing
            text_parts = []
            for segment in segments:
                if segment.text.strip():  # Skip empty segments
                    text_parts.append(segment.text.strip())
            
            text = " ".join(text_parts).strip()
            
            # Clean up converted file if different from original
            if converted_path and converted_path != audio_file_path:
                try:
                    os.unlink(converted_path)
                except:
                    pass
            
            if not text:
                raise RuntimeError("No speech detected in audio")
            
            # Cache the result
            if use_cache and cache_key:
                self._set_cached_transcription(cache_key, text)
            
            return text
        except Exception as e:
            # Clean up on error
            if converted_path and converted_path != audio_file_path:
                try:
                    os.unlink(converted_path)
                except:
                    pass
            raise RuntimeError(f"Error in local STT: {str(e)}")
    
    def text_to_speech(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Convert text to speech with multiple provider support.
        
        Provider priority (based on TTS_PROVIDER config):
        1. Dia2 (if enabled) - Recommended for dialogue/receptionist
        2. Chatterbox-Turbo (if enabled) - Production-grade speed
        3. Kokoro 82M (if enabled) - Ultra-fast CPU option
        4. Orpheus 3B (if enabled) - Best naturalness
        5. CosyVoice2-0.5B (if enabled) - Ultra-low latency streaming
        6. OpenAI tts-1-hd (if API key provided) - Cloud fallback
        7. Piper TTS (fallback) - Legacy option
        
        Returns: Audio bytes (WAV format)
        """
        provider = TTS_PROVIDER.lower() if TTS_PROVIDER else 'dia2'
        errors = []  # Collect errors for better error messages
        
        # Try Dia2 first (recommended)
        if DIA_TTS_ENABLED and provider in ('dia2', 'dia'):
            try:
                return self._dia2_tts(text, output_path)
            except Exception as e:
                error_msg = f"Dia2 TTS failed: {str(e)}"
                errors.append(error_msg)
                # Log error for debugging
                try:
                    from utils.logger import log_error
                    log_error(e, f"Dia2 TTS error (falling back to next provider)")
                except:
                    pass
        
        # Try Chatterbox-Turbo
        if CHATTERBOX_TURBO_ENABLED and provider == 'chatterbox':
            try:
                return self._chatterbox_turbo_tts(text, output_path)
            except Exception as e:
                errors.append(f"Chatterbox-Turbo TTS failed: {str(e)}")
        
        # Try Kokoro 82M
        if KOKORO_TTS_ENABLED and provider == 'kokoro':
            try:
                return self._kokoro_tts(text, output_path)
            except Exception as e:
                errors.append(f"Kokoro TTS failed: {str(e)}")
        
        # Try Orpheus 3B
        if ORPHEUS_TTS_ENABLED and provider == 'orpheus':
            try:
                return self._orpheus_tts(text, output_path)
            except Exception as e:
                errors.append(f"Orpheus TTS failed: {str(e)}")
        
        # Try CosyVoice2-0.5B
        if COSYVOICE_TTS_ENABLED and provider == 'cosyvoice':
            try:
                return self._cosyvoice_tts(text, output_path)
            except Exception as e:
                errors.append(f"CosyVoice TTS failed: {str(e)}")
        
        # Try OpenAI tts-1-hd (cloud fallback) - always try if API key is available
        if self.openai_key:
            try:
                return self._openai_tts(text)
            except Exception as e:
                errors.append(f"OpenAI TTS failed: {str(e)}")
        
        # Fallback to Piper TTS (legacy)
        if self.use_local:
            try:
                return self._piper_tts(text, output_path)
            except Exception as e:
                errors.append(f"Piper TTS failed: {str(e)}")
        
        # Build comprehensive error message
        error_summary = "All TTS providers failed:\n" + "\n".join(f"  - {err}" for err in errors)
        
        # Add helpful suggestions
        suggestions = []
        if not self.openai_key:
            suggestions.append("Set OPENAI_API_KEY in your .env file for cloud TTS fallback")
        if DIA_TTS_ENABLED and provider in ('dia2', 'dia'):
            suggestions.append("Install Dia2 library: pip install git+https://github.com/nari-labs/dia2.git")
            suggestions.append("Or follow installation guide: https://github.com/nari-labs/dia2")
            suggestions.append("Dia2 requires torch: pip install torch")
            suggestions.append("Alternative: Use OpenAI TTS by setting OPENAI_API_KEY in .env")
        if self.use_local and not any('Piper' in err for err in errors):
            suggestions.append("Install Piper TTS: brew install piper-tts (macOS) or download from https://github.com/rhasspy/piper/releases")
        
        if suggestions:
            error_summary += "\n\nSuggestions:\n" + "\n".join(f"  - {s}" for s in suggestions)
        
        raise RuntimeError(error_summary)
    
    def _dia2_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use Dia2 TTS for text-to-speech (dialogue-focused, streaming support).
        
        Dia2 is optimized for conversational AI and supports:
        - Multi-speaker dialogue via [S1]/[S2] tags
        - Nonverbal sounds: (laughs), (coughs), (gasps), (sighs)
        - Streaming generation (can start from first tokens)
        
        Note: Requires the 'dia2' library. Install with: pip install dia2
        """
        try:
            from dia2 import Dia2, GenerationConfig, SamplingConfig
            import torch
            
            device = _get_device(DIA_TTS_DEVICE)
            
            # Initialize Dia2 model (module-level cache, shared across all requests)
            global _dia2_model_cache
            if _dia2_model_cache is None:
                with _dia2_lock:
                    # Double-check pattern
                    if _dia2_model_cache is None:
                        model_name = DIA_TTS_MODEL
                        # Determine dtype based on device
                        if device == 'cpu':
                            dtype = 'float32'
                        elif device == 'mps':
                            # MPS: use 'auto' to let Dia2 choose appropriate dtype
                            # Dia2 will handle MPS dtype selection automatically
                            dtype = 'auto'
                        else:
                            dtype = 'bfloat16'  # CUDA default
                        
                        _dia2_model_cache = Dia2.from_repo(
                            model_name,
                            device=device,
                            dtype=dtype
                        )
            
            dia2_model = _dia2_model_cache
            
            # Process text with speaker tags
            # Ensure speaker tags are properly formatted
            if DIA_TTS_SPEAKER and f'[{DIA_TTS_SPEAKER}]' not in text:
                text = f'[{DIA_TTS_SPEAKER}] {text}'
            
            # Create generation config with consistent settings for voice stability
            # Lower temperature (0.3-0.5) for more consistent voice
            # Set seed for reproducibility (ensures same text produces same voice)
            import random
            if DIA_TTS_SEED is not None:
                seed = DIA_TTS_SEED
                random.seed(seed)
                torch.manual_seed(seed)
                if device == 'cuda':
                    torch.cuda.manual_seed(seed)
                elif device == 'mps':
                    # MPS doesn't have manual_seed, but we set the global seed
                    pass
            
            # Lower temperature for more consistent voice (0.3-0.5 range)
            temperature = DIA_TTS_TEMPERATURE
            config = GenerationConfig(
                cfg_scale=2.0,  # Default CFG scale
                audio=SamplingConfig(temperature=temperature, top_k=50),
                use_cuda_graph=(device == 'cuda'),  # Only use CUDA graphs on CUDA
            )
            
            # Generate audio
            # Use temporary file if output_path not provided
            temp_file = None
            if output_path is None:
                output_path = tempfile.mktemp(suffix='.wav')
                temp_file = output_path
            
            result = dia2_model.generate(
                text,
                config=config,
                output_wav=output_path,
                verbose=False
            )
            
            # Read generated WAV file
            with open(output_path, 'rb') as f:
                audio_data = f.read()
            
            # Cleanup temporary file if we created it
            if temp_file:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            
            return audio_data
            
        except ImportError as e:
            raise ImportError(
                "Dia2 TTS requires the 'dia2' library.\n"
                "Installation options:\n"
                "  1. From GitHub: pip install git+https://github.com/nari-labs/dia2.git\n"
                "  2. Using uv (recommended): Install uv (https://docs.astral.sh/uv/), then clone the repo\n"
                "  3. Use OpenAI TTS fallback: Set OPENAI_API_KEY in your .env file\n"
                "Note: Dia2 also requires torch. Install with: pip install torch"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Error in Dia2 TTS: {str(e)}")
    
    def _chatterbox_turbo_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use Chatterbox-Turbo TTS for text-to-speech (production-grade speed).
        
        Features:
        - Sub-200ms latency
        - One-step decoder (ultra-fast)
        - Emotion exaggeration control
        - Native paralinguistic tags: [laugh], [cough], [chuckle]
        """
        try:
            import torch
            from transformers import AutoProcessor, AutoModel
            
            device = _get_device(CHATTERBOX_TURBO_DEVICE)
            
            # Initialize model (thread-safe)
            if not hasattr(self, '_chatterbox_model') or self._chatterbox_model is None:
                with _chatterbox_lock:
                    if not hasattr(self, '_chatterbox_model') or self._chatterbox_model is None:
                        model_name = CHATTERBOX_TURBO_MODEL
                        self._chatterbox_model = AutoModel.from_pretrained(
                            model_name,
                            torch_dtype=torch.float16 if device != 'cpu' else torch.float32,
                            trust_remote_code=True
                        ).to(device)
                        self._chatterbox_processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
            
            # Generate audio with emotion exaggeration
            inputs = self._chatterbox_processor(text=text, return_tensors="pt").to(device)
            
            with torch.no_grad():
                audio = self._chatterbox_model.generate(
                    **inputs,
                    cfg=CHATTERBOX_TURBO_CFG,
                    exaggeration=CHATTERBOX_TURBO_EMOTION_EXAGGERATION
                )
            
            # Convert to WAV bytes
            import numpy as np
            audio_np = audio.cpu().numpy().squeeze()
            audio_np = audio_np / np.max(np.abs(audio_np)) * 0.95
            
            import wave
            import io
            sample_rate = 24000
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes((audio_np * 32767).astype(np.int16).tobytes())
            
            return wav_buffer.getvalue()
            
        except ImportError:
            raise ImportError(
                "Chatterbox-Turbo requires transformers and torch. Install with: pip install torch transformers"
            )
        except Exception as e:
            raise RuntimeError(f"Error in Chatterbox-Turbo TTS: {str(e)}")
    
    def _kokoro_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use Kokoro 82M TTS for text-to-speech (ultra-fast CPU option).
        
        Kokoro 82M is an ultra-fast TTS model optimized for CPU inference.
        Features:
        - <0.3s processing time
        - CPU-friendly (no GPU required)
        - Multiple voice options (af_sky, af_nova, af_bella, etc.)
        - 24kHz audio output
        """
        try:
            from kokoro import KPipeline
            
            # Initialize pipeline (cached, thread-safe)
            # 'a' = American English (lang_code)
            if not hasattr(self, '_kokoro_model') or self._kokoro_model is None:
                with _kokoro_lock:
                    if not hasattr(self, '_kokoro_model') or self._kokoro_model is None:
                        # KPipeline uses lang_code, not model name
                        # 'a' = American English, 'b' = British English, etc.
                        self._kokoro_model = KPipeline(lang_code='a')  # American English
            
            # Generate audio using generator API
            # Voice options: af_sky, af_nova, af_bella, af_heart, etc.
            generator = self._kokoro_model(text, voice=KOKORO_TTS_VOICE)
            
            # Collect all audio chunks
            audio_chunks = []
            for gs, ps, audio in generator:
                audio_chunks.append(audio)
            
            # Concatenate all chunks
            import numpy as np
            if audio_chunks:
                audio = np.concatenate(audio_chunks)
            else:
                raise RuntimeError("No audio generated from Kokoro TTS")
            
            # Normalize audio
            audio = audio / np.max(np.abs(audio)) * 0.95
            
            # Convert to WAV bytes
            import wave
            import io
            
            sample_rate = 24000  # Kokoro outputs 24kHz
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                audio_int16 = (audio * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            return wav_buffer.getvalue()
            
        except ImportError:
            raise ImportError(
                "Kokoro TTS requires kokoro package. Install with: pip install kokoro>=0.9.4 soundfile\n"
                "Also install espeak-ng: brew install espeak-ng (macOS) or apt-get install espeak-ng (Linux)"
            )
        except Exception as e:
            raise RuntimeError(f"Error in Kokoro TTS: {str(e)}")
    
    def _orpheus_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use Orpheus 3B TTS for text-to-speech (best naturalness, emotional expression).
        
        Orpheus 3B features:
        - Human-like speech with natural intonation and emotion
        - Zero-shot voice cloning capabilities
        - Guided emotion control via tags: <happy>, <sad>, <angry>, <neutral>, etc.
        - Low latency: ~200ms streaming latency (or ~100ms with input streaming)
        - Voice options: tara, leah, jess, leo, dan, mia, zac, zoe (for English)
        
        Note: Requires orpheus-speech package. Install with: pip install orpheus-speech
        """
        try:
            from orpheus_tts import OrpheusModel
            
            device = _get_device(ORPHEUS_TTS_DEVICE)
            
            # Initialize model (cached, thread-safe)
            if not hasattr(self, '_orpheus_pipeline') or self._orpheus_pipeline is None:
                with _orpheus_lock:
                    if not hasattr(self, '_orpheus_pipeline') or self._orpheus_pipeline is None:
                        model_name = ORPHEUS_TTS_MODEL
                        # OrpheusModel uses vLLM under the hood for fast inference
                        # max_model_len controls the maximum sequence length
                        self._orpheus_pipeline = OrpheusModel(
                            model_name=model_name,
                            max_model_len=2048  # Adjust based on available memory
                        )
            
            # Add emotion tag to text if specified
            emotion_tag = ORPHEUS_TTS_EMOTION.lower()
            if emotion_tag in ['happy', 'sad', 'angry', 'neutral', 'excited', 'calm', 'fearful', 'disgusted']:
                # Orpheus uses XML-like tags for emotion control
                text_with_emotion = f"<{emotion_tag}>{text}</{emotion_tag}>"
            else:
                text_with_emotion = text
            
            # Default voice (can be configured via env var)
            voice = os.getenv('ORPHEUS_TTS_VOICE', 'tara')  # tara is most conversational
            
            # Generate speech (returns generator for streaming)
            syn_tokens = self._orpheus_pipeline.generate_speech(
                prompt=text_with_emotion,
                voice=voice,
            )
            
            # Collect audio chunks (streaming)
            audio_chunks = []
            for audio_chunk in syn_tokens:
                audio_chunks.append(audio_chunk)
            
            if not audio_chunks:
                raise RuntimeError("No audio generated from Orpheus TTS")
            
            # Concatenate chunks
            import numpy as np
            # Audio chunks are bytes, convert to numpy array
            audio_data = b''.join(audio_chunks)
            # Orpheus outputs 16-bit PCM at 24kHz
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
            
            # Normalize
            audio_np = audio_np / np.max(np.abs(audio_np)) * 0.95
            
            # Convert to WAV bytes
            import wave
            import io
            
            sample_rate = 24000  # Orpheus outputs 24kHz
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes((audio_np * 32767).astype(np.int16).tobytes())
            
            return wav_buffer.getvalue()
            
        except ImportError:
            raise ImportError(
                "Orpheus TTS requires orpheus-speech package. Install with: pip install orpheus-speech\n"
                "Note: Uses vLLM under the hood. If you encounter issues, try: pip install vllm==0.7.3"
            )
        except Exception as e:
            raise RuntimeError(f"Error in Orpheus TTS: {str(e)}")
    
    def _cosyvoice_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use CosyVoice2-0.5B TTS for text-to-speech (ultra-low latency streaming).
        
        CosyVoice2-0.5B features:
        - Ultra-low latency: 150ms first packet synthesis latency
        - Streaming support (text-in and audio-out streaming)
        - Zero-shot voice cloning
        - Multi-language support (9 languages, 18+ Chinese dialects)
        
        Note: Requires CosyVoice repository to be cloned. See README.md for setup instructions.
        """
        try:
            import sys
            import os
            from pathlib import Path
            
            # Try to import CosyVoice (requires repo to be cloned)
            # Add common paths where CosyVoice might be installed
            cosyvoice_paths = [
                Path(__file__).parent.parent / 'CosyVoice',
                Path(__file__).parent.parent.parent / 'CosyVoice',
                Path.home() / 'CosyVoice',
            ]
            
            cosyvoice_found = False
            for path in cosyvoice_paths:
                if path.exists() and (path / 'cosyvoice').exists():
                    if str(path) not in sys.path:
                        sys.path.insert(0, str(path))
                    # Also add third_party/Matcha-TTS if it exists
                    matcha_path = path / 'third_party' / 'Matcha-TTS'
                    if matcha_path.exists() and str(matcha_path) not in sys.path:
                        sys.path.insert(0, str(matcha_path))
                    cosyvoice_found = True
                    break
            
            if not cosyvoice_found:
                raise ImportError(
                    "CosyVoice repository not found. Please clone it:\n"
                    "git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git\n"
                    "See README.md for full setup instructions."
                )
            
            from cosyvoice.cli.cosyvoice import AutoModel
            import torchaudio
            
            device = _get_device(COSYVOICE_TTS_DEVICE)
            
            # Initialize model (thread-safe, cached)
            if not hasattr(self, '_cosyvoice_model') or self._cosyvoice_model is None:
                with _cosyvoice_lock:
                    if not hasattr(self, '_cosyvoice_model') or self._cosyvoice_model is None:
                        # Model directory - check common locations
                        model_dir = os.getenv('COSYVOICE_MODEL_DIR', None)
                        if not model_dir:
                            # Try common paths
                            for base_path in [Path(__file__).parent.parent, Path.home()]:
                                potential_dir = base_path / 'pretrained_models' / 'CosyVoice2-0.5B'
                                if potential_dir.exists():
                                    model_dir = str(potential_dir)
                                    break
                        
                        if not model_dir:
                            raise RuntimeError(
                                "CosyVoice2-0.5B model not found. Please download it:\n"
                                "from huggingface_hub import snapshot_download\n"
                                "snapshot_download('FunAudioLLM/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')"
                            )
                        
                        self._cosyvoice_model = AutoModel(model_dir=model_dir)
                        self._cosyvoice_sample_rate = self._cosyvoice_model.sample_rate
            
            # Generate audio using zero-shot inference (requires a reference audio file)
            # For now, use default voice or provide a reference audio path via env var
            ref_audio_path = os.getenv('COSYVOICE_REF_AUDIO', None)
            
            if ref_audio_path and os.path.exists(ref_audio_path):
                # Zero-shot voice cloning
                generator = self._cosyvoice_model.inference_zero_shot(
                    text, '', ref_audio_path
                )
            else:
                # Use default voice (if supported) or raise error
                raise RuntimeError(
                    "CosyVoice2 requires a reference audio file for zero-shot voice cloning.\n"
                    "Set COSYVOICE_REF_AUDIO environment variable to path of reference audio file."
                )
            
            # Collect audio chunks (streaming)
            audio_chunks = []
            for i, result in enumerate(generator):
                if 'tts_speech' in result:
                    audio_chunks.append(result['tts_speech'])
            
            if not audio_chunks:
                raise RuntimeError("No audio generated from CosyVoice2")
            
            # Concatenate chunks
            import torch
            audio = torch.cat(audio_chunks, dim=-1) if len(audio_chunks) > 1 else audio_chunks[0]
            
            # Convert to numpy
            import numpy as np
            if isinstance(audio, torch.Tensor):
                audio_np = audio.cpu().numpy().squeeze()
            else:
                audio_np = np.array(audio).squeeze()
            
            # Normalize
            audio_np = audio_np / np.max(np.abs(audio_np)) * 0.95
            
            # Convert to WAV bytes
            import wave
            import io
            
            sample_rate = self._cosyvoice_sample_rate if hasattr(self, '_cosyvoice_sample_rate') else 24000
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes((audio_np * 32767).astype(np.int16).tobytes())
            
            return wav_buffer.getvalue()
            
        except ImportError as e:
            raise ImportError(
                f"CosyVoice2 requires the CosyVoice repository. Error: {str(e)}\n"
                "Installation:\n"
                "1. git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git\n"
                "2. cd CosyVoice && pip install -r requirements.txt\n"
                "3. Download model: from huggingface_hub import snapshot_download; "
                "snapshot_download('FunAudioLLM/CosyVoice2-0.5B', local_dir='pretrained_models/CosyVoice2-0.5B')\n"
                "See README.md for full setup instructions."
            )
        except Exception as e:
            raise RuntimeError(f"Error in CosyVoice2 TTS: {str(e)}")
    
    def _piper_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use Piper TTS for text-to-speech."""
        piper_error = None
        try:
            import subprocess
            
            # Create temporary text file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(text)
                temp_text = f.name
            
            # Create temporary output file
            output_wav = output_path or tempfile.mktemp(suffix='.wav')
            
            # Get piper model path from config or use default
            piper_model = PIPER_VOICE_PATH or os.getenv('PIPER_VOICE_PATH', 'en_US-lessac-medium')
            
            # Run piper TTS
            # Note: Adjust command based on your piper installation
            # If piper is in PATH: just 'piper'
            # If using python wrapper: 'python -m piper'
            try:
                result = subprocess.run(
                    ['piper', '--model', piper_model, '--output_file', output_wav, temp_text],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Piper TTS failed: {result.stderr}")
            except FileNotFoundError:
                # Try python wrapper
                try:
                    import piper_tts
                    # Use piper_tts library if available
                    audio_data = piper_tts.synthesize(text, model=piper_model)
                    # Cleanup temp file
                    try:
                        os.unlink(temp_text)
                    except:
                        pass
                    return audio_data
                except ImportError:
                    piper_error = ImportError(
                        "Piper TTS not found. Install with: brew install piper-tts\n"
                        "Or download from: https://github.com/rhasspy/piper/releases"
                    )
                    raise piper_error
            
            # Read generated audio file
            with open(output_wav, 'rb') as f:
                audio_data = f.read()
            
            # Cleanup
            try:
                os.unlink(temp_text)
            except:
                pass
            if not output_path:
                try:
                    os.unlink(output_wav)
                except:
                    pass
            
            return audio_data
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            piper_error = e
            # Fallback to OpenAI TTS if available
            if self.openai_key:
                try:
                    return self._openai_tts(text)
                except Exception as openai_error:
                    # If OpenAI also fails, raise original error with context
                    raise RuntimeError(
                        f"Piper TTS failed: {str(piper_error)}\n"
                        f"OpenAI TTS fallback also failed: {str(openai_error)}"
                    ) from openai_error
            # No OpenAI key, raise original error
            raise RuntimeError(f"Error in Piper TTS: {str(piper_error)}")
        except Exception as e:
            # Catch-all for other errors
            if self.openai_key:
                try:
                    return self._openai_tts(text)
                except Exception as openai_error:
                    raise RuntimeError(
                        f"Piper TTS failed: {str(e)}\n"
                        f"OpenAI TTS fallback also failed: {str(openai_error)}"
                    ) from openai_error
            raise RuntimeError(f"Error in Piper TTS: {str(e)}")
    
    def _get_coqui_tts(self):
        """Return cached Coqui TTS model; lazy-init with lock (thread-safe).
        
        DEPRECATED: Coqui TTS is deprecated in favor of Dia2, Chatterbox-Turbo, Orpheus 3B, etc.
        This method is kept for backward compatibility only and will be removed in a future version.
        """
        import warnings
        warnings.warn(
            "Coqui TTS is deprecated. Please migrate to Dia2, Chatterbox-Turbo, Orpheus 3B, "
            "or Kokoro 82M. Coqui TTS support will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )
        global _coqui_tts_model
        if _coqui_tts_model is not None:
            return _coqui_tts_model
        with _coqui_tts_lock:
            if _coqui_tts_model is not None:
                return _coqui_tts_model
            from TTS.api import TTS
            new_model = TTS(model_name=COQUI_TTS_MODEL, progress_bar=False)
            _coqui_tts_model = new_model
            return _coqui_tts_model

    def _coqui_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use Coqui TTS for text-to-speech. Model is cached and reused.
        
        DEPRECATED: Coqui TTS is deprecated in favor of better alternatives:
        - Dia2: Best for dialogue/receptionist use cases
        - Chatterbox-Turbo: Production-grade speed (sub-200ms latency)
        - Orpheus 3B: Best naturalness and emotional expression
        - Kokoro 82M: Ultra-fast CPU option
        
        This method is kept for backward compatibility only and will be removed in a future version.
        """
        import warnings
        warnings.warn(
            "Coqui TTS is deprecated. Please migrate to Dia2, Chatterbox-Turbo, Orpheus 3B, "
            "or Kokoro 82M. Coqui TTS support will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )
        try:
            tts = self._get_coqui_tts()
            
            # Create temporary output file if not provided
            output_wav = output_path or tempfile.mktemp(suffix='.wav')
            
            # Synthesize speech
            if COQUI_VOICE_ID:
                tts.tts_to_file(
                    text=text,
                    file_path=output_wav,
                    speaker=COQUI_VOICE_ID
                )
            else:
                tts.tts_to_file(
                    text=text,
                    file_path=output_wav
                )
            
            # Read generated audio file
            with open(output_wav, 'rb') as f:
                audio_data = f.read()
            
            # Cleanup if temporary file
            if not output_path:
                os.unlink(output_wav)
            
            return audio_data
        except ImportError:
            raise ImportError(
                "Coqui TTS not installed. Install with: pip install TTS\n"
                "Note: First run will download the model automatically."
            )
        except Exception as e:
            error_str = str(e)
            # Check for espeak backend error and provide helpful guidance
            if 'espeak' in error_str.lower() or 'No espeak backend found' in error_str:
                helpful_msg = (
                    f"Coqui TTS requires espeak-ng or espeak to be installed on your system.\n"
                    f"Install it with:\n"
                    f"  macOS: brew install espeak-ng\n"
                    f"  Linux: sudo apt-get install espeak-ng (Debian/Ubuntu) or sudo yum install espeak-ng (RHEL/CentOS)\n"
                    f"  Or: sudo apt-get install espeak (alternative)\n"
                    f"Original error: {error_str}"
                )
                # Fallback to OpenAI TTS if available
                if self.openai_key:
                    try:
                        return self._openai_tts(text)
                    except Exception as openai_error:
                        raise RuntimeError(
                            f"{helpful_msg}\n"
                            f"OpenAI TTS fallback also failed: {str(openai_error)}"
                        ) from openai_error
                raise RuntimeError(helpful_msg)
            # Fallback to OpenAI TTS if available
            if self.openai_key:
                try:
                    return self._openai_tts(text)
                except Exception as openai_error:
                    raise RuntimeError(
                        f"Error in Coqui TTS: {error_str}\n"
                        f"OpenAI TTS fallback also failed: {str(openai_error)}"
                    ) from openai_error
            raise RuntimeError(f"Error in Coqui TTS: {error_str}")
    
    def _openai_tts(self, text: str) -> bytes:
        """Use OpenAI TTS with tts-1-hd and configurable voice and speed.
        
        OpenAI TTS features:
        - High-quality neural voices (tts-1-hd recommended)
        - 6 built-in voices: alloy, echo, fable, onyx, nova, shimmer
        - Speed control: 0.25 to 4.0 (1.0 = normal speed)
        - Cost: $30/1M characters for tts-1-hd
        
        Note: OpenAI TTS does not support SSML. Speed and pitch are controlled via API parameters.
        """
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY required for cloud TTS")
        
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_key)
        
        # Use configured model and voice
        model = OPENAI_TTS_MODEL or "tts-1-hd"  # Default to tts-1-hd for better quality
        voice = OPENAI_TTS_VOICE or "nova"  # Default to nova (most natural)
        
        # OpenAI TTS supports speed parameter (0.25 to 4.0)
        # Note: OpenAI TTS does NOT support SSML or pitch control via API
        # The OPENAI_TTS_USE_SSML and OPENAI_TTS_PITCH configs are kept for
        # backward compatibility but are not used (OpenAI TTS doesn't support them)
        speed = OPENAI_TTS_SPEED
        if speed < 0.25:
            speed = 0.25
        elif speed > 4.0:
            speed = 4.0
        
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed  # Speed control (0.25 to 4.0)
        )
        return response.content


# Module-level utility functions
def clear_stt_cache():
    """Clear the STT transcription cache."""
    global _stt_cache
    with _stt_cache_lock:
        _stt_cache.clear()


def get_stt_cache_stats() -> Dict[str, int]:
    """Get statistics about the STT cache."""
    with _stt_cache_lock:
        return {
            'size': len(_stt_cache),
            'max_size': _stt_cache_max_size,
            'ttl_seconds': int(_stt_cache_ttl)
        }


def shutdown_stt_executor():
    """Shutdown the STT thread pool executor (call on application shutdown)."""
    global _stt_executor
    with _stt_executor_lock:
        if _stt_executor is not None:
            _stt_executor.shutdown(wait=True)
            _stt_executor = None
