import torch

import time
import re
from os.path import exists, isfile

from config import config
from my_logger import logger

from num2words import num2words

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

    try: tts_model, _ = torch.hub.load(
        repo_or_dir="snakers4/silero-models",
        model="silero_tts",
        language=language,
        speaker=model_id
    )
    except: tts_model, _ = torch.hub.load(
        repo_or_dir="~/.cache/torch/hub/snakers4_silero-models_master",
        model="silero_tts",
        language=language,
        speaker=model_id
    )

    tts_model.to(tts_device)

    def _get_sound_path(self, title: str) -> str:
        ...

    def _num2word(self, string: str) -> str:
        def time_replacer(time_string: str) -> str:
            def replacer(match: re.Match[str]) -> str:
                words = tuple(map(int, match.group(0).split(":")))
                return f"{num2words(words[0], lang='ru')} часов {num2words(words[1], lang='ru')} минут"
            
            return re.sub(r"\d{1,2}:\d{1,2}", replacer, time_string)
        
        # TODO другие числовые значения
        
        def digit_replacer(digit_string: str) -> str:
            def replacer(match: re.Match[str]) -> str:
                digit = match.group(0)
                return num2words(digit, lang='ru')
            
            return re.sub(r"\d+", replacer, digit_string)
        
        # TODO доделать это до приемлемого вида

        while re.match(r".*\d+.*", string):
            if re.fullmatch(r".*\d{1,2}:\d{1,2}.*", string):
                string = time_replacer(string)
            string = digit_replacer(string)
        return string
    
    def _play_tensor(self, tensor: torch.Tensor) -> None:
        sd.play(tensor, self.sample_rate)
        time.sleep(len(tensor) / self.sample_rate)
        sd.stop()

    def speak(self, text: str, label: str) -> str:
        text = self._num2word(text)
        path = self._get_sound_path(label)
        while self.status != "pass":
            pass
        self.status = "play"

        logger.log(f"Произношу:\n{text}")

        try:
            if "dynamic-speech" in path:
                audio: torch.Tensor = self.tts_model.apply_tts(
                    text=text,
                    speaker=self.speaker,
                    sample_rate=self.sample_rate,
                    put_accent=self.put_accent,
                    put_yo=self.put_yo
                )

                self._play_tensor(audio)

                self.status = "pass"
                return text
            if exists(path):
                if isfile(path):
                    with open(path, "rt", encoding="utf-8") as file:
                        audio = torch.FloatTensor(eval(file.read()))
                    self._play_tensor(audio)

                    self.status = "pass"
                    return text
            else:
                audio: torch.Tensor = self.tts_model.apply_tts(
                    text=text,
                    speaker=self.speaker,
                    sample_rate=self.sample_rate,
                    put_accent=self.put_accent,
                    put_yo=self.put_yo
                )
                with open(path, "wt", encoding="utf-8") as file:
                    file.write(str(audio.tolist()))
                self._play_tensor(audio)

                self.status = "pass"
                return text
        except Exception as e:
            msg = "Что-то произошло с нейрогенерацией речи..."
            if config.say_errors:
                self.speak(msg, 'neural-generation-trouble')
            logger.error(msg)
        finally:
            self.status = "pass"
            return text
