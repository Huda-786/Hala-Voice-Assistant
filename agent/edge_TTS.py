from livekit.agents import tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
import wave
import edge_tts
import tempfile
import subprocess
import os
from deep_translator import GoogleTranslator


def translate_to_user_lang(text: str, target_lang: str) -> str:
    if target_lang == "en":
        return text
    
    try:
        if target_lang == "zh":
            translated = GoogleTranslator(source="auto", target="zh-CN").translate(text)
        else:
            translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return translated
    except Exception as e:
        print("Translation error:", e)
        return text  # fallback to English

LANGUAGE_VOICE_MAP = {
    # Main East Asian
    "zh": "zh-CN-YunxiNeural",         # Chinese
    "en": "en-US-AndrewNeural",        # English
    "ja": "ja-JP-KeitaNeural",         # Japanese
    "ko": "ko-KR-InJoonNeural",        # Korean

    # A
    "af": "af-ZA-WillemNeural",        # Afrikaans
    "am": "am-ET-AmehaNeural",         # Amharic
    "ar": "ar-SA-HamedNeural",         # Arabic
    # B
    "bn": "bn-BD-PradeepNeural",       # Bengali

    # E/F
    "tl": "fil-PH-AngeloNeural",      # Tagalog
    "fr": "fr-FR-HenriNeural",         # French

    # G
    "de": "de-DE-ConradNeural",        # German

    # H/I
    "hi": "hi-IN-MadhurNeural",        # Hindi
    "id": "id-ID-ArdiNeural",          # Indonesian

    # M/N
    "ml": "ml-IN-MidhunNeural",        # Malayalam
    "ne": "ne-NP-SagarNeural",         # Nepali

    # P
    "ps": "ps-AF-GulNawazNeural",      # Pashto
    "pt": "pt-PT-DuarteNeural",        # Portuguese

    # R/S
    "ru": "ru-RU-DmitryNeural",        # Russian
    "si": "si-LK-SameeraNeural",       # Sinhala
    "so": "so-SO-MuuseNeural",         # Somali
    "es": "es-ES-AlvaroNeural",        # Spanish
    "sw": "sw-KE-RafikiNeural",        # Swahili

    # T/U/V/W/Z
    "ta": "ta-IN-ValluvarNeural",      # Tamil
    "th": "th-TH-NiwatNeural",         # Thai
    "tr": "tr-TR-AhmetNeural",         # Turkish
    "ur": "ur-PK-AsadNeural",          # Urdu
    "uz": "uz-UZ-SardorNeural",        # Uzbek
    "zu": "zu-ZA-ThembaNeural",        # Zulu
}


class EdgeTTSPlugin(tts.TTS):
    def __init__(self, get_lang=None, sample_rate: int = 24000):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )

        self.get_lang = get_lang or (lambda: "en")
        self._sample_rate = sample_rate

    def synthesize(
        self,
        text: str,
        *,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
    ) -> tts.ChunkedStream:
        return EdgeTTSChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )

    @property
    def name(self):
        return "EdgeTTS-Dynamic"


class EdgeTTSChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: EdgeTTSPlugin,
        input_text: str,
        conn_options,
    ):
        super().__init__(
            tts=tts,
            input_text=input_text,
            conn_options=conn_options,
        )
        self._tts = tts
        self._audio_generated = False

    async def _run(self, output_emitter: tts.AudioEmitter):
        if self._audio_generated:
            return

        if not self.input_text.strip():
            return

        mp3_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

        try:
            lang = self._tts.get_lang()
            
            voice = LANGUAGE_VOICE_MAP.get(lang, "en-US-AndrewNeural")
            text = translate_to_user_lang(self.input_text.strip(), lang)
            print("Edge TTS text:", text)

            print("TTS detected language:", lang)
            print("Using Edge voice:", voice)
            
            communicate = edge_tts.Communicate(
                text=text, 
                voice=voice,
            )

            await communicate.save(mp3_file)

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", mp3_file,
                    "-ac", "1",
                    "-ar", str(self._tts._sample_rate),
                    "-sample_fmt", "s16",
                    wav_file,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            with wave.open(wav_file, "rb") as wf:
                pcm_audio = wf.readframes(wf.getnframes())

            # REQUIRED LIVEKIT AUDIO EMITTER LIFECYCLE
            output_emitter.initialize(
                request_id=str(id(self)),
                sample_rate=self._tts._sample_rate,
                num_channels=1,
                mime_type="audio/pcm",
            )

            output_emitter.push(pcm_audio)
            output_emitter.flush()

            self._audio_generated = True

        except Exception as e:
            raise RuntimeError(f"Edge TTS synthesis failed: {e}")

        finally:
            try:
                output_emitter.end_input()
            except Exception:
                pass

            for file_path in [mp3_file, wav_file]:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass