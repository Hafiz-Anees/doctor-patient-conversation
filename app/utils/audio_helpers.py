"""
audio_helpers.py — file handling & cleanup for uploaded audio and raw PCM streams.
"""

import os
import shutil
import struct
from pathlib import Path
from fastapi import UploadFile

# PCM stream markers (from device spec)
START_SIGNAL = b"\xFF\xFF\xFF\xFF"
END_SIGNAL = b"\xEE\xEE\xEE\xEE"

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


def save_upload(file: UploadFile, dest_path: str) -> str:
    """Save UploadFile to disk, return path."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    file.file.seek(0)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest)


def strip_pcm_markers(raw_bytes: bytes) -> bytes:
    """
    Remove START_SIGNAL and END_SIGNAL from a raw PCM stream
    received from the BLE/Wi-Fi device.
    """
    if raw_bytes.startswith(START_SIGNAL):
        raw_bytes = raw_bytes[len(START_SIGNAL):]
    if raw_bytes.endswith(END_SIGNAL):
        raw_bytes = raw_bytes[:-len(END_SIGNAL)]
    return raw_bytes


def pcm_to_wav_bytes(pcm_bytes: bytes) -> bytes:
    """Wrap raw PCM bytes in a proper WAV header."""
    data_size = len(pcm_bytes)
    byte_rate = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH
    block_align = CHANNELS * SAMPLE_WIDTH

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,   # PCM fmt chunk size
        1,    # PCM format
        CHANNELS,
        SAMPLE_RATE,
        byte_rate,
        block_align,
        SAMPLE_WIDTH * 8,
        b"data",
        data_size,
    )
    return header + pcm_bytes


def cleanup_file(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass