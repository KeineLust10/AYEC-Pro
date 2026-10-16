"""Offline Turkish speech recognition using a local faster-whisper model."""

import os
import logging
import tempfile
import wave
from pathlib import Path

from src.utils.path_helper import PathHelper

logger = logging.getLogger(__name__)


class OfflineTurkishASR:
    MODEL_NAME = "small"
    MODEL_REPOSITORY = "Systran/faster-whisper-small"

    def __init__(self):
        from faster_whisper import WhisperModel

        required_files = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")
        app_data_model = Path(PathHelper.get_app_data_dir()) / "Speech" / "whisper-small"
        bundled_model = Path(PathHelper.get_resource_path("Speech", "whisper-small"))
        self.model_path = next(
            (
                candidate
                for candidate in (app_data_model, bundled_model)
                if candidate.is_dir()
                and all((candidate / filename).is_file() for filename in required_files)
            ),
            app_data_model,
        )
        if not self.model_path.is_dir() or any(
            not (self.model_path / filename).is_file() for filename in required_files
        ):
            raise FileNotFoundError(
                "Offline Turkish speech model is missing at "
                f"{self.model_path}. Run tools/setup/prepare_offline_asr.py from the application folder."
            )

        cpu_threads = max(1, min(4, os.cpu_count() or 1))
        self.model = WhisperModel(
            str(self.model_path),
            device="cpu",
            compute_type="int8",
            cpu_threads=cpu_threads,
        )

    @staticmethod
    def confidence_score(avg_logprob, no_speech_prob):
        """Return a conservative ASR quality score, not a calibrated probability."""
        log_quality = max(0.0, min(1.0, (float(avg_logprob) + 2.0) / 1.6))
        speech_quality = max(0.0, min(1.0, 1.0 - float(no_speech_prob)))
        return round(log_quality * speech_quality, 4)

    def transcribe_with_confidence(self, audio_data):
        pcm_data = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
        fd, audio_path = tempfile.mkstemp(prefix="ayec_asr_", suffix=".wav")
        os.close(fd)
        try:
            with wave.open(audio_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm_data)
            segments, _info = self.model.transcribe(
                audio_path,
                language="tr",
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            segments = list(segments)
            if not segments:
                logger.info("Speech VAD returned no segments; retrying without VAD")
                segments, _info = self.model.transcribe(
                    audio_path,
                    language="tr",
                    beam_size=5,
                    vad_filter=False,
                    condition_on_previous_text=False,
                )
                segments = list(segments)
            text = " ".join(segment.text.strip() for segment in segments).strip()
            if not segments:
                return {"text": text, "confidence": 0.0}
            avg_logprob = sum(float(segment.avg_logprob) for segment in segments) / len(segments)
            no_speech_prob = sum(float(segment.no_speech_prob) for segment in segments) / len(segments)
            return {
                "text": text,
                "confidence": self.confidence_score(avg_logprob, no_speech_prob),
            }
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass

    def transcribe(self, audio_data):
        """Preserve the original text-only API for existing callers."""
        return self.transcribe_with_confidence(audio_data)["text"]
