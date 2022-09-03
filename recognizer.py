import sounddevice as sd
import vosk
import sys
import queue
import json

from config import config
from my_logger import logger


class Recognizer:
    """
    Отвечает за распознавание речи и её преобразование в текст
    """
    status = "pass"

    stt_model = vosk.Model("models/vosk-model-small-ru-0.22")
    samplerate = 48_000
    stt_device = 0
    q: queue.Queue[bytes] = queue.Queue()

    def callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    _say_if_hearing = config.say_if_hearing

    def speak(self, text: str, path: str) -> str:
        ...
    
    def offline_speak(self, text: str) -> str:
        ...

    def _get_sound_path(self, title: str) -> str:
        ...

    def record_and_recognize_audio(self, *args: tuple) -> str:
        """
        Запись и распознавание аудио
        """
        print("Слушаю...")
        while self.status != "pass":
            pass
        self.status = "record"
        with sd.RawInputStream(
            samplerate=self.samplerate, blocksize=8_000 * 6,
            device=self.stt_device, dtype="int16",
            channels=1, callback=self.callback
        ):
            result = ""
            rec = vosk.KaldiRecognizer(self.stt_model, self.samplerate)
            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data): result = json.loads(rec.Result())["text"]
                else: result = json.loads(rec.PartialResult()).get("text", "")
                if result:
                    self.status = "pass"
                    return result

    def input(self) -> str:
        result = self.record_and_recognize_audio().lower()
        logger.log(f'Произнесено:\n{result}')
        return result
