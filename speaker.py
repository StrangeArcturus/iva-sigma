import torch

import time
import re
from os.path import exists, isfile

from config import config
from my_logger import logger

from num2words import num2words
from pymorphy2 import MorphAnalyzer as MA

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
    torch.set_num_threads(16)
    _morph = MA()

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
                hours = words[0]
                minutes = words[1]
                result_hour = (
                    'час' if hours in (
                        1, 21
                    ) else 'часа' if hours in (
                        2, 3, 4, 22, 23
                    ) else 'часов'
                )
                result_minute = (
                    'минута' if minutes in (
                        1, 21, 31, 41, 51
                    ) else 'минуты' if minutes in (
                        2, 3, 4,
                        22, 23, 24,
                        32, 33, 34,
                        42, 43, 44,
                        52, 53, 54
                    ) else 'минут'
                )
                return (
                    f"{num2words(hours, lang='ru')} {result_hour} {num2words(minutes, lang='ru')} {result_minute}"
                )
            
            return re.sub(r"\d{1,2}:\d{1,2}", replacer, time_string)
        
        def date_replacer(date_string: str) -> str:
            def replacer(match: re.Match[str]) -> str:
                words = tuple(map(int, match.group(0).split('.')))
                months = {
                    1: 'января',
                    2: 'февраля',
                    3: 'марта',
                    4: 'апреля',
                    5: 'мая',
                    6: 'июня',
                    7: 'июля',
                    8: 'августа',
                    9: 'сентября',
                    10: 'октября',
                    11: 'ноября',
                    12: 'декабря'
                }
                day = words[0]
                month = words[1]
                year = words[2]
                result_day = self._morph.parse(
                    num2words(day, lang='ru', ordinal=True, to='cardinal'))[0].inflect({ # type: ignore
                        'ADJF', 'neut', 'sing', 'nomn'
                }).word # type: ignore
                result_month = months[month]
                result_year = num2words(year, lang='ru', ordinal=True, to='year')
                return (
                    f"{result_day} {result_month} {result_year}"
                )
            
            return re.sub(r"\d{1,2}\.\d{1,2}\.\d{1,2}", replacer, date_string)
        
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
            if re.fullmatch(r".*\d{1,2}\.\d{1,2}\.\d{1,2}.*", string):
                string = date_replacer(string)
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

        logger.log(f"[Произношу]:\n{text}")

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
