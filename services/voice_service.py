"""Voice processing service with local and cloud options."""
from typing import Optional
import os
import tempfile
import subprocess
from pathlib import Path

# Import compatibility shim for Python 3.9 (must be before TTS import)
try:
    from services.tts_compat import *  # Applies Python 3.9 compatibility patches
except ImportError:
    pass  # If compat module doesn't exist, continue (might be Python 3.10+)

from config import (
    USE_LOCAL_VOICE, OPENAI_API_KEY, LOCAL_WHISPER_MODEL, LOCAL_TTS_MODEL,
    COQUI_TTS_MODEL, COQUI_VOICE_ID, WHISPER_COMPUTE_TYPE, PIPER_VOICE_PATH
)


class VoiceService:
    """Service for voice processing (STT/TTS) with local and cloud support."""
    
    def __init__(self):
        self.use_local = USE_LOCAL_VOICE
        self.openai_key = OPENAI_API_KEY
        self.whisper_model = LOCAL_WHISPER_MODEL or "base"
        self.tts_model = LOCAL_TTS_MODEL or "piper"
        self._whisper_model_instance = None
    
    def _get_whisper_model(self):
        """Get or create Whisper model instance (cached)."""
        if self._whisper_model_instance is None:
            try:
                from faster_whisper import WhisperModel
                
                # Use CPU for M3 Max (can use "cuda" if you have GPU)
                # For Apple Silicon (M3 Max), use "cpu" with optimized compute type
                device = "cpu"
                # Try int8_float16 first, fallback to int8 if it fails
                compute_type = WHISPER_COMPUTE_TYPE or os.getenv('WHISPER_COMPUTE_TYPE', 'int8_float16')
                
                # Try to initialize WhisperModel with fallback compute types
                try:
                    self._whisper_model_instance = WhisperModel(
                        self.whisper_model,
                        device=device,
                        compute_type=compute_type,
                        num_workers=1,  # Single worker for CPU
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
                                num_workers=1,
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
            
            # Convert to WAV, 16kHz, mono
            subprocess.run([
                'ffmpeg',
                '-i', input_path,
                '-ar', '16000',  # Sample rate: 16kHz
                '-ac', '1',      # Mono channel
                '-f', 'wav',     # WAV format
                '-y',            # Overwrite output
                output_path
            ], check=True, capture_output=True)
            
            return output_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            # ffmpeg not available or conversion failed
            # faster-whisper can handle many formats, so return original
            return input_path
    
    def speech_to_text(self, audio_file_path: str) -> str:
        """Convert speech to text.
        
        Options:
        1. faster-whisper (local, if USE_LOCAL_VOICE=True)
        2. OpenAI Whisper API (if OPENAI_API_KEY provided and USE_LOCAL_VOICE=False)
        
        Args:
            audio_file_path: Path to audio file (any format supported by ffmpeg or Whisper)
        
        Returns:
            Transcribed text string
        """
        if self.use_local:
            # Use local faster-whisper
            converted_path = None
            try:
                # Convert audio format if needed (optimizes for Whisper)
                converted_path = self._convert_audio_format(audio_file_path)
                
                model = self._get_whisper_model()
                
                # Optimized transcription parameters for M3 Max
                segments, info = model.transcribe(
                    converted_path,
                    language="en",
                    beam_size=5,           # Balance between speed and accuracy
                    vad_filter=True,        # Voice activity detection (removes silence)
                    vad_parameters=dict(
                        min_silence_duration_ms=500,  # Minimum silence to split
                        threshold=0.5                 # VAD threshold
                    ),
                    initial_prompt="This is a conversation with an AI receptionist for a service business.",  # Context hint
                    condition_on_previous_text=True,  # Use previous context
                    compression_ratio_threshold=2.4,     # Detect repetition
                    log_prob_threshold=-1.0,            # Filter low-confidence
                    no_speech_threshold=0.6             # Detect no speech
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
                
                return text
            except Exception as e:
                # Clean up on error
                if converted_path and converted_path != audio_file_path:
                    try:
                        os.unlink(converted_path)
                    except:
                        pass
                raise RuntimeError(f"Error in local STT: {str(e)}")
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
            return transcript.text
    
    def text_to_speech(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Convert text to speech.
        
        Options:
        1. Piper TTS (local, fast) - if USE_LOCAL_VOICE=True and LOCAL_TTS_MODEL=piper
        2. Coqui TTS (local, high quality) - if USE_LOCAL_VOICE=True and LOCAL_TTS_MODEL=coqui
        3. OpenAI TTS (cloud) - if OPENAI_API_KEY provided
        
        Returns: Audio bytes (WAV format)
        """
        if self.use_local:
            if self.tts_model.lower() == 'coqui':
                return self._coqui_tts(text, output_path)
            else:
                # Default to Piper TTS
                return self._piper_tts(text, output_path)
        else:
            # Use OpenAI TTS
            return self._openai_tts(text)
    
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
    
    def _coqui_tts(self, text: str, output_path: Optional[str] = None) -> bytes:
        """Use Coqui TTS for text-to-speech."""
        try:
            from TTS.api import TTS
            
            # Create temporary output file if not provided
            output_wav = output_path or tempfile.mktemp(suffix='.wav')
            
            # Initialize TTS model
            # First run will download the model automatically
            tts = TTS(model_name=COQUI_TTS_MODEL, progress_bar=False)
            
            # Synthesize speech
            if COQUI_VOICE_ID:
                # Use specific voice ID for multi-voice models
                tts.tts_to_file(
                    text=text,
                    file_path=output_wav,
                    speaker=COQUI_VOICE_ID
                )
            else:
                # Use default voice
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
            # Fallback to OpenAI TTS if available
            if self.openai_key:
                return self._openai_tts(text)
            raise RuntimeError(f"Error in Coqui TTS: {str(e)}")
    
    def _openai_tts(self, text: str) -> bytes:
        """Use OpenAI TTS."""
        if not self.openai_key:
            raise ValueError("OPENAI_API_KEY required for cloud TTS")
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_key)
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        return response.content
