from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
import whisper
import wave
import io
import threading
import time
import asyncio
import logging
import numpy as np
from typing import AsyncGenerator
import soundfile as sf
import tempfile
from pydub import AudioSegment
import os
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logging.getLogger("whisper").setLevel(logging.ERROR)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Whisper Model Parameters (adjust as needed)
WHISPER_MODEL_SIZE = "medium"  # Options: "tiny", "base", "small", "medium", "large"
WHISPER_LANGUAGE = (
    "en"  # Language code (e.g., "en" for English) or None for multilingual
)
# Load Whisper model to a data directory in the same directory as the app.py file
logging.info(f"Loading Whisper model: {WHISPER_MODEL_SIZE}")
model = whisper.load_model(
    WHISPER_MODEL_SIZE, 
    download_root=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
)
buffer_queue = []
lock = threading.Lock()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    contents = await audio.read()
    logging.info(f"Received audio of size: {len(contents)} bytes")

    with (
        tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as temp_webm,
        tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_wav,
    ):
        temp_webm.write(contents)
        logging.info(f"Saved audio to temporary file: {temp_webm.name}")
        try:
            webm_audio = AudioSegment.from_file(temp_webm.name, format="webm")
        except Exception:
            logging.error("Error loading audio as webm format. likely due to an invalid file")
            return PlainTextResponse("Error loading audio")
        webm_audio.export(temp_wav.name, format="wav")
        result = model.transcribe(temp_wav.name, language=WHISPER_LANGUAGE, fp16=False)
        transcription = result["text"]
        logging.info(f"Transcribed audio: {transcription}")
        return PlainTextResponse(transcription)
    
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "model": WHISPER_MODEL_SIZE}
