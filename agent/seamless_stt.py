from livekit.agents import stt
from livekit.agents.utils import AudioBuffer, merge_frames
import numpy as np
import torch
from scipy.signal import resample_poly
from math import gcd


SEAMLESS_LANG_MAP = {

    "zh": "cmn",
    "en": "eng",
    "ja": "jpn",
    "ko": "kor",

    "af": "afr",
    "am": "amh",
    "ar": "arb",

    "bn": "ben",
    "hi": "hin",
    "ml": "mal",
    "ne": "npi",
    "ta": "tam",
    "ur": "urd",
    "ps": "pbt",
    "si": "sin",

    "id": "ind",
    "tl": "tgl",
    "th": "tha",

    "fr": "fra",
    "de": "deu",
    "es": "spa",
    "pt": "por",
    "ru": "rus",
    "tr": "tur",

    "sw": "swh",
    "so": "som",
    "zu": "zul",

    "uz": "uzn",
    "so": "som", 
}

class SeamlessSTT(stt.STT):
    def __init__(self, processor, model, device="cpu", selected_lang = "en"):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False,
            )
        )

        self.processor = processor
        self.seamless_model = model
        self.device = device
        self.selected_lang = selected_lang

        self.last_language = selected_lang
        self.last_text_original = ""
        self.last_text_english = ""

    def resample_audio(self, audio: np.ndarray, original_rate: int, target_rate: int = 16000):
        if original_rate == target_rate:
            return audio

        common = gcd(original_rate, target_rate)
        up = target_rate // common
        down = original_rate // common

        return resample_poly(audio, up, down).astype(np.float32)

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: str | None = None,
        **kwargs
    ) -> stt.SpeechEvent:

        print("SeamlessM4T STT called")

        buffer = merge_frames(buffer)

        audio = np.frombuffer(buffer.data, dtype=np.int16).astype(np.float32) / 32768.0

        if buffer.num_channels > 1:
            audio = audio.reshape(-1, buffer.num_channels)[:, 0]

        audio = self.resample_audio(
            audio,
            original_rate=buffer.sample_rate,
            target_rate=16000,
        )
        
        src_lang = SEAMLESS_LANG_MAP.get(self.selected_lang, "eng")
        inputs = self.processor(
            audio=audio,
            sampling_rate=16000,
            src_lang = src_lang,
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = self.seamless_model.generate(
                **inputs,
                tgt_lang="eng",
                generate_speech=False,
                do_sample = False,
            )

        if hasattr(generated_ids, "sequences"):
            text_tokens = generated_ids.sequences
        
        elif isinstance(generated_ids, tuple):
            text_tokens = generated_ids[0]
        
        else:
            text_tokens = generated_ids

        english_text = self.processor.batch_decode(
            text_tokens,
            skip_special_tokens=True,
        )[0].strip()

        self.last_language = self.selected_lang
        self.last_text_original = english_text
        self.last_text_english = english_text

        print("Seamless English Output:", english_text)

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(
                    text=english_text,
                    language=self.last_language,
                    confidence=1.0,
                )
            ],
        )