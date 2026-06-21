import logging
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import numpy as np
from pydantic import BaseModel
from scipy.io.wavfile import write as write_wav

try:
    from TTS.api import TTS
except ImportError as exc:
    TTS = None
    TTS_IMPORT_ERROR = str(exc)
else:
    TTS_IMPORT_ERROR = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Text to Voice", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tts_model = None

VCTK_SPEAKERS = {
    "emma_f": "p225",
    "lily_f": "p227",
    "john_m": "p230",
    "james_m": "p231",
    "robert_m": "p232",
    "michael_m": "p233",
    "david_m": "p234",
    "default": "p225",
}

VOICE_GROUPS = {
    "female_voices": [
        {"id": "emma_f", "name": "Emma", "gender": "Female"},
        {"id": "lily_f", "name": "Lily", "gender": "Female"},
    ],
    "male_voices": [
        {"id": "john_m", "name": "John", "gender": "Male"},
        {"id": "james_m", "name": "James", "gender": "Male"},
        {"id": "robert_m", "name": "Robert", "gender": "Male"},
        {"id": "michael_m", "name": "Michael", "gender": "Male"},
        {"id": "david_m", "name": "David", "gender": "Male"},
    ],
    "default": "emma_f",
}


class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "default"


def get_tts_model():
    global tts_model
    if tts_model is None:
        if TTS is None:
            raise RuntimeError(f"TTS package not available: {TTS_IMPORT_ERROR}")
        logger.info("Loading Coqui TTS VCTK multi-speaker model")
        tts_model = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False, gpu=False)
    return tts_model


def synthesize_wav_bytes(text: str, voice: str) -> bytes:
    model = get_tts_model()
    speaker = VCTK_SPEAKERS.get(voice, VCTK_SPEAKERS["default"])
    logger.info("Generating speech with speaker %s", speaker)

    wav_samples = model.tts(text=text.strip(), speaker=speaker)
    # Coqui may return a plain Python list; convert to float32 array for WAV writer.
    wav_samples = np.asarray(wav_samples, dtype=np.float32)

    if wav_samples.ndim != 1 or wav_samples.size == 0:
        raise RuntimeError("Generated audio samples are empty or malformed")

    sample_rate = int(getattr(model.synthesizer, "output_sample_rate", 22050))

    buffer = BytesIO()
    write_wav(buffer, sample_rate, wav_samples)
    buffer.seek(0)
    return buffer.read()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "tts_available": TTS is not None,
        "model_loaded": tts_model is not None,
    }


@app.get("/voices")
async def get_voices():
    return VOICE_GROUPS


@app.post("/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        audio_bytes = synthesize_wav_bytes(text, request.voice or "default")
        return Response(audio_bytes, media_type="audio/wav")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("TTS request failed")
        raise HTTPException(status_code=500, detail=f"Text-to-speech error: {exc}") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)