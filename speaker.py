import torch

import time

import sounddevice as sd

"""
from num2words import num2words
import re
"""


class Speaker:
    """
    Отвечает за генерацию речи из текста
    """
    status = "pass"

    language = "ru"
    model_id = "v3_1_ru"
    sample_rate = 48_000
    speaker = "kseniya" # aidar, baya, kseniya, xenia, random
    put_accent = True
    put_yo = True
    tts_device = torch.device('cpu')
    torch.set_num_threads(4)

    tts_model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language=language,
        speaker=model_id
    )

    tts_model.to(tts_device)

    def _get_sound_path(self, title: str) -> str:
        ...

    """
    def _num2word(self, string: str) -> str:
        while re.fullmatch(r"\d+", string):
            if re.fullmatch(r"\d{1,2}:\d{1,2}", string):
                string = re.sub(
                    r"\d{1,2}:\d{1,2}",
                    lambda match: f"{num2words((words := match.group(0))[0], lang='ru')} часов {num2words(words[1], lang='ru')} минут",
                    string
                )
            string = re.sub(r"\d+", lambda match: str(num2words(match.group(0), lang="ru")), string)
        return string
    """
    
    def speak(self, text: str, label: str) -> str:
        #text = self._num2word(text)
        while self.status != "pass":
            pass
        self.status = "play"
        print(f"Произношу:\n{text}")
        audio = self.tts_model.apply_tts(
            text=text,
            speaker=self.speaker,
            sample_rate=self.sample_rate,
            put_accent=self.put_accent,
            put_yo=self.put_yo
        )

        sd.play(audio, self.sample_rate)
        time.sleep(len(audio) / self.sample_rate)
        sd.stop()

        self.status = "pass"
        return text
