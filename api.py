import os
import tempfile
import base64
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import basic_pitch
from basic_pitch.inference import predict_and_save, predict
from basic_pitch import ICASSP_2022_MODEL_PATH

app = FastAPI(
    title="Basic Pitch API",
    description="Audio to MIDI conversion using Spotify's Basic Pitch model",
    version="1.0.0",
)


class PredictionResponse(BaseModel):
    midi_base64: str
    filename: str


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for container orchestration."""
    return HealthResponse(status="healthy", version=basic_pitch.__version__)


@app.post("/predict", response_model=PredictionResponse)
async def predict_audio(
    file: UploadFile = File(..., description="Audio file (wav, mp3, ogg, flac)"),
    onset_threshold: float = Query(0.5, ge=0.0, le=1.0, description="Onset threshold"),
    frame_threshold: float = Query(0.3, ge=0.0, le=1.0, description="Frame threshold"),
    minimum_note_length: float = Query(58.0, ge=0.0, description="Minimum note length in ms"),
    minimum_frequency: Optional[float] = Query(None, description="Minimum frequency in Hz"),
    maximum_frequency: Optional[float] = Query(None, description="Maximum frequency in Hz"),
):
    """
    Convert audio file to MIDI using Basic Pitch.

    Returns the MIDI file as base64-encoded data for easy integration with n8n.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / file.filename
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        content = await file.read()
        input_path.write_bytes(content)

        try:
            predict_and_save(
                audio_path_list=[str(input_path)],
                output_directory=str(output_dir),
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
                onset_threshold=onset_threshold,
                frame_threshold=frame_threshold,
                minimum_note_length=minimum_note_length,
                minimum_frequency=minimum_frequency,
                maximum_frequency=maximum_frequency,
                model_or_model_path=ICASSP_2022_MODEL_PATH,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

        midi_files = list(output_dir.glob("*.mid"))
        if not midi_files:
            raise HTTPException(status_code=500, detail="No MIDI file generated")

        midi_path = midi_files[0]
        midi_data = midi_path.read_bytes()
        midi_base64 = base64.b64encode(midi_data).decode("utf-8")

        output_filename = Path(file.filename).stem + ".mid"

        return PredictionResponse(midi_base64=midi_base64, filename=output_filename)


@app.post("/predict/file")
async def predict_audio_file(
    file: UploadFile = File(..., description="Audio file (wav, mp3, ogg, flac)"),
    onset_threshold: float = Query(0.5, ge=0.0, le=1.0),
    frame_threshold: float = Query(0.3, ge=0.0, le=1.0),
    minimum_note_length: float = Query(58.0, ge=0.0),
    minimum_frequency: Optional[float] = Query(None),
    maximum_frequency: Optional[float] = Query(None),
):
    """
    Convert audio file to MIDI and return the MIDI file directly.

    Use this endpoint when you need the raw MIDI file.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}",
        )

    tmpdir = tempfile.mkdtemp()
    input_path = Path(tmpdir) / file.filename
    output_dir = Path(tmpdir) / "output"
    output_dir.mkdir()

    content = await file.read()
    input_path.write_bytes(content)

    try:
        predict_and_save(
            audio_path_list=[str(input_path)],
            output_directory=str(output_dir),
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            onset_threshold=onset_threshold,
            frame_threshold=frame_threshold,
            minimum_note_length=minimum_note_length,
            minimum_frequency=minimum_frequency,
            maximum_frequency=maximum_frequency,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    midi_files = list(output_dir.glob("*.mid"))
    if not midi_files:
        raise HTTPException(status_code=500, detail="No MIDI file generated")

    midi_path = midi_files[0]
    output_filename = Path(file.filename).stem + ".mid"

    return FileResponse(
        path=str(midi_path),
        filename=output_filename,
        media_type="audio/midi",
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
