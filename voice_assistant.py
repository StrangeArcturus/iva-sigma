from typing import Dict, List, NoReturn, Optional
from datetime import datetime as dt, timedelta
from random import random, shuffle
from json import load as _load
from os import remove
import re

from speech_worker import SpeechWorker
from my_logger import logger
from config import config

from fuzzywuzzy.fuzz import token_sort_ratio


class VoiceAssistant(SpeechWorker):
    """
    Помимо реализации работы с речью и текстом,
    будет реализовывать работу голосового ассистента
    """
    name: str
    sex: str
    speech_language: str
    recognition_language: str
    over_hear_minutes: float
    scheme: Dict[str, List[str]]

    started_over_hear: Optional[dt] = None
    is_over_hear: bool = False

    __MORNING = "MORNING"
    __DAY = "DAY"
    __EVENING = "EVENING"
    __NIGHT = "NIGHT"
    __EARLY = "EARLY"

    def __init__(self) -> None:
        with open('./assistant.json', 'rt', encoding='utf-8') as file:
            owner_obj: Dict[str, str] = _load(file)
            for key in owner_obj.keys():
                setattr(self, key, owner_obj[key])

        with open('./assistant-scheme.json', 'rt', encoding='utf-8') as file:
            self.scheme = _load(file)
        
        self.over_hear_delta = timedelta(minutes=self.over_hear_minutes)
    
    def __get_times_of_day(self) -> str:
        """
        Получение текущего состояния: утро, день, вечер, ночь или раннее утро сейчас
        """
        now_hour = dt.now().time().hour

        if now_hour in range(0, 4):
            return self.__NIGHT
        elif now_hour in (4, 5):
            return self.__EARLY
        elif now_hour in range(6, 12):
            return self.__MORNING
        elif now_hour in range(12, 17):
            return self.__DAY
        elif now_hour in range(17, 24):
            return self.__EVENING
        return self.__EVENING

    def execute_command(self, arguments: str) -> None:
        """
        Пробегает по схеме ассистента и ищет совпадение токен-фразы с ключом.
        Ключ является названием метода, который имеется в данном классе
        """
        sheme = list(self.scheme.items())
        shuffle(sheme)
        for skill, triggers in sheme:
            if not arguments:
                break
            if arguments.lower() == self.name.lower():
                self.call(arguments)
                break
            if arguments.lower() in map(lambda trigger: trigger.lower(), triggers):
                self.__getattribute__(skill)(arguments)
                break
            if any({token_sort_ratio(trigger, arguments) >= 75 for trigger in triggers}):
                self.__getattribute__(skill)(arguments)
                break
        """
        for key in self.scheme.keys():
            if not arguments:
                break
            if arguments.lower() == self.name.lower():
                self.call(arguments)
                break
            if key == arguments or arguments.startswith(key) or key.startswith(arguments):
                self.__getattribute__(self.scheme[arguments])(arguments)
                break
            if token_sort_ratio(key, arguments) >= 75:
                self.__getattribute__(self.scheme[key])(arguments)
        """
    
    def start_hear(self) -> NoReturn:
        """
        Цикличное прослушивание окружающей среды,
        управление программой не возвращает
        """
        while True:
            try:
                if self.started_over_hear:
                    if dt.now() - self.started_over_hear >= self.over_hear_delta:
                        self.is_over_hear = False
                        self.started_over_hear = None
                owner_speech = self.record_and_recognize_audio().lower()
                logger.log(f'Произнесено:\n{owner_speech}')
                if not self.is_over_hear:
                    if not owner_speech.startswith(self.name.lower()):
                        continue
                    # owner_speech = owner_speech.replace(self.name.lower(), '', 1)
                    if owner_speech.lower() != self.name.lower():
                        owner_speech = re.sub(rf'{self.name.lower()} ?,?', '', owner_speech, 1)
                if re.match(rf'{self.name.lower()}.', owner_speech):
                    owner_speech = re.sub(rf'{self.name.lower()} ?,?', '', owner_speech, 1)
                # вариант с регексом
                remove('microphone-results.wav')
                words = owner_speech.split()
                # command, *arguments = words
                command = owner_speech
                self.execute_command(command)# , arguments)
            except Exception as e:
                msg = "Упс, возникла ошибка..."
                if config.say_errors:
                    self.speak(msg, "runtime-error")
                logger.error(msg)
                print(e)
    
    #name
    def call(self, *args) -> None:
        """
        Задействуется, если пользователь позвал ассистента по имени
        """
        if not self.is_over_hear:
            self.is_over_hear = True
            self.started_over_hear = dt.now()
            self.speak("да, хозяин, слушаю вас внимательно", 'carefull-hear')
        else:
            self.speak("хозяин, я вас уже внимательно слушаю", 'already-carefull')
    
    def relax(self, *args) -> None:
        """
        Если пользователь попросил отдохнуть
        """
        if not self.is_over_hear:
            self.speak("хозяин, я ведь уже отдыхаю", 'relax/already-relax')
        else:
            self.is_over_hear = False
            self.started_over_hear = None
            self.speak("конечно, хозяин, отдыхаю", 'relax/go-to-relax')
    #endname

    #greeting
    def hello(self, *args) -> None:
        if round(random()):
            self.speak("Привет, мой хозяин", "greeting/hello")
        else:
            times_of_day = self.__get_times_of_day()
            if times_of_day == self.__NIGHT:
                self.speak(
                    "хозяин, мне кажется, сейчас время подходит больше для сна и отдыха. "
                    "пожалуйста, позвольте позаботиться о вас и попросить ложиться спать поскорее",
                    "greeting/from-hello-to-night"
                )
            elif times_of_day == self.__EARLY:
                self.early_morning(*args)
            elif times_of_day == self.__MORNING:
                self.good_morning(*args)
            elif times_of_day == self.__DAY:
                self.good_day(*args)
            elif times_of_day == self.__EVENING:
                self.good_evening(*args)
        
    def early_morning(self, *args) -> None:
        self.speak("что-то вы сегодня рано, хозяин. доброе утро", 'greeting/early-morning')

    def good_morning(self, *args) -> None:
        times_of_day = self.__get_times_of_day()
        """
        [0-4) ночь 4
        [4-12) утро 8 
        [12-17) день 5
        [17-24) вечер 7
        [24-4) ночь 4
        по общепринятым меркам

        и ниже для меня
        """
        if times_of_day == self.__NIGHT:
            self.speak(
                "хозяин, мне кажется вы перепутали ночь и утро, вам разве не пора спать?",
                'greeting/from-morning-to-night'
            )
        elif times_of_day == self.__EARLY:
            self.early_morning(*args)
        elif times_of_day == self.__MORNING:
            self.speak("доброе утро хозяин", "greeting/good_morning")
        elif times_of_day == self.__DAY:
            self.speak("хозяин, но ведь сейчас день?", 'greeting/from-morning-to-day')
        elif times_of_day == self.__EVENING:
            self.speak(
                "мой хозяин, сейчас ведь вечер, совсем не утро",
                'greeting/from-morning-to-evening'
            )
    
    def good_day(self, *args) -> None:
        times_of_day = self.__get_times_of_day()
        if times_of_day == self.__NIGHT:
            self.speak(
                "хозяин, мне кажется вы перепутали ночь и день, вам разве не пора спать?",
                'greeting/from-day-to-night'
            )
        elif times_of_day == self.__EARLY:
            self.speak(
                "я думаю, для дня сейчас ещё слишком рано, хозяин. доброе утро",
                'greeting/from-day-to-early'
            )
        elif times_of_day == self.__MORNING:
            self.speak(
                "хозяин, некуда спешить, ведь сейчас только утро",
                'greeting/from-day-to-morning'
            )
        elif times_of_day == self.__DAY:
            self.speak(
                "вам тоже добрый день, мой хозяин",
                'greeting/good_day'
            )
        elif times_of_day == self.__EVENING:
            self.speak(
                "мой хозяин, вы немножко припозднились. добрый вечер",
                'greeting/from-day-to-evening'
            )        
    
    def good_evening(self, *args) -> None:
        times_of_day = self.__get_times_of_day()
        if times_of_day == self.__NIGHT:
            self.speak(
                "сейчас ведь ночь, а вовсе не вечер, хозяин",
                'greeting/from-evening-to-night'
            )
        elif times_of_day == self.__EARLY:
            self.speak(
                "простите, хозяин, но до вечера пол дня. конечно решать вам, ещё или уже",
                'greeting/from-evening-to-early'
            )
        elif times_of_day == self.__MORNING:
            self.speak(
                "хозяин, извините, но мне показалось, что вы спутали восход и заход. ведь сейчас утро",
                'greeting/from-evening-to-morning'
            )
        elif times_of_day == self.__DAY:
            self.speak(
                "не торопите события, хозяин, сейчас только день",
                'greeting/from-evening-to-day'
            )
        elif times_of_day == self.__EVENING:
            self.speak(
                "добрый вечер, мой хозяин",
                'greeting/good_evening'
            )
    #endgreeting
