from typing import Dict, List, NoReturn, Optional
from datetime import datetime as dt, timedelta
from random import choice, random, shuffle
from json import load as _load
from os import remove
import webbrowser
import requests
import re

from speech_worker import SpeechWorker
from my_logger import logger
from tokens import tokens
from config import config
from owner import owner

from wikipediaapi import Wikipedia, ExtractFormat
from fuzzywuzzy.fuzz import token_sort_ratio
from pyowm.weatherapi25.weather import Weather
from pyowm import OWM


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

    __DYNAMIC = "dynamic-speech"

    started_over_hear: Optional[dt] = None
    is_over_hear: bool = False

    __MORNING = "MORNING"
    __DAY = "DAY"
    __EVENING = "EVENING"
    __NIGHT = "NIGHT"
    __EARLY = "EARLY"

    wiki = Wikipedia(
        language='ru',
        extract_format=ExtractFormat.WIKI
    )

    translate_url = "https://translated-mymemory---translation-memory.p.rapidapi.com/api/get"

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
    
    def __get_translate(self, text: str) -> str:
        """
        Перевод текста с английского на русский
        """
        query = {
            "q": text,
            "langpair": "en|ru"
        }
        headers = {
            "X-RapidAPI-Host": "translated-mymemory---translation-memory.p.rapidapi.com",
            "X-RapidAPI-Key": tokens.translate
        }

        response = requests.request("GET", self.translate_url, headers=headers, params=query)
        return response.text

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
            if any({re.match(trigger + ' .+' if trigger.endswith(' .+') else trigger, arguments) for trigger in triggers}):
                self.__getattribute__(skill)(arguments, triggers)
                break
    
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
                owner_speech = self.input()
                logger.log(f'Произнесено:\n{owner_speech}')
                if not self.is_over_hear:
                    if not owner_speech.startswith(self.name.lower()) and not owner_speech.endswith(self.name.lower()):
                        continue
                    # owner_speech = owner_speech.replace(self.name.lower(), '', 1)
                    if owner_speech.lower() != self.name.lower():
                        if owner_speech.startswith(self.name.lower()):
                            owner_speech = (owner_speech[len(self.name):]).strip()
                        if owner_speech.endswith(self.name.lower()):
                            owner_speech = (owner_speech[:-len(self.name)]).strip()
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

    #thank
    def thanks(self, *args) -> None:
        """
        Ответ на благодарение пользователя
        """
        self.speak("рада служить, хозяин", 'thank')
    #endthank

    #greeting
    def hello(self, *args) -> None:
        """
        Приветствие. По воле случая либо просто "привет", либо с указанием времени суток
        """
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
        """
        Для так называемого, (моего) раннего времени, когда обычно я не бодрствую, но скоро начал бы
        """
        self.speak("что-то вы сегодня рано, хозяин. доброе утро", 'greeting/early-morning')

    def good_morning(self, *args) -> None:
        """
        Доброе утро. Но если на момент вызова не утро, то об этом сообщат
        """
        times_of_day = self.__get_times_of_day()
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
        """
        Добрый день. И тут тоже сообщат о несоответствии
        """
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
        """
        Добрый вечер. Так же, с указанием
        """
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

    #exit
    def bye(self, *args) -> None:
        """
        Завершение работы Яны
        """
        self.speak(
            "хорошо, хозяин, завершаю свою программу. спасибо, что пользуетесь моей помощью и придаёте мне смысл. делайте это почаще, мне приятно",
            'bye/thanks-and-exit'
        )
        exit(0)
    #endexit

    #random
    def toss_coin(self, *args) -> None:
        """
        Подбросить монетку
        """
        self.speak("подкидываю монетку", 'toss-coin/tossing')
        flips_count = 3
        heads = 0
        tails = 0
        for _ in range(flips_count):
            if round(random()):
                heads += 1
            else:
                tails += 1
        if tails > heads:
            self.speak("выпала решка", 'toss-coin/tails-win')
        else:
            self.speak("выпали орлы", 'toss-coin/heads-win')
    #endrandom

    #games
    def city(self, *args) -> None:
        """
        Игра в города в классическом понимании:
        следующее слово в игре должно начинаться на последнюю букву последнего сказанного слова,
        а все слова в игре должны быть реальными городами. Если последняя буква не произносится,
        то используется предпоследняя, и так далее до первой произносимой буквы с конца
        """
        cancel = ('Отмена', 'Стоп', 'Хватит', 'Достаточно')
        self.speak(
            "навык игры в города. подготавливаю данные, хозяин, подождите пожалуйста. если вы захотите прервать игру или у вас не будет вариантов ответа, просто скажите отмена, стоп, хватит или достаточно",
            'city/prepare-data'
        )
        with open('./.citys.txt', 'rt', encoding='utf-8') as file:
            citys = set(file.read().splitlines())
            used_citys = set()
        now_step = 'me' if round(random()) else 'user'

        letter = ''
        answer = ''
        end_char = ''
        user_city = ''

        if now_step == 'me':
            self.speak("хозяин, по воле случайности первый ход за мной", 'city/my-step-first')
            letter = chr(choice(tuple(
                filter(
                    lambda digit: chr(digit) not in 'ьъ',
                    tuple(range(1072, 1104)) + (1105,)
                )
            )))
            answer = choice(tuple(filter(
                lambda city: city.lower().startswith(letter),
                citys
            )))
            citys.discard(answer)
            used_citys.add(answer)
            end_char = answer.replace('ь', '').replace('ъ', '')[-1]
            self.speak(
                f'мне выпала буква "{letter}", а потому я начну с города {answer}. Вам на "{end_char}"',
                self.__DYNAMIC
            )
        else:
            self.speak(
                "хозяин, ваш ход первый. назовите город",
                'city/user-step-first'
            )
            user_city = self.input().capitalize()
            if user_city in cancel:
                self.speak(
                    "вы решили сдаться на первом же шаге? я разочарована, хозяин. завершение игры",
                    'city/cancel-on-start'
                )
                return
            while user_city.lower() not in map(lambda city: city.lower(), citys):
                if user_city.lower() not in map(lambda city: city.lower(), used_citys):
                    self.speak(
                        f"города {user_city} не обнаружено в моей базе даннных из {len(citys) + len(used_citys)} городов, попробуйте снова",
                        self.__DYNAMIC
                    )
                else:
                    self.speak(
                        f"город {user_city} уже был использован в этой игре. попробуйте снова",
                        self.__DYNAMIC
                    )
                user_city = self.input().capitalize()
                if user_city in cancel:
                    self.speak(
                        "вы решили сдаться на первом же шаге? я разочарована, хозяин. завершение игры",
                        'city/cancel-on-start'
                    )
                    return
            citys.discard(user_city)
            used_citys.add(user_city)
            end_char = user_city.replace('ь', '').replace('ъ', '')[-1]
            letter = end_char[::]
        now_step = 'user' if now_step == 'me' else 'me'
        while True:
            if now_step == 'me':
                self.speak("теперь мой черёд", 'city/next-is-me')
                answer = choice(tuple(filter(
                    lambda city: city.lower().startswith(letter),
                    citys
                )))
                end_char = answer.replace('ь', '').replace('ъ', '')[-1]
                self.speak(
                    f'мне на букву "{letter}", а потому я начну с города {answer}. Вам на "{end_char}"',
                    self.__DYNAMIC
                )
                citys.discard(answer)
                used_citys.add(answer)
            else:
                self.speak(
                    "хозяин, теперь ходите вы. каков ваш ответ?",
                    'city/next-is-user'
                )
                user_city = self.input().capitalize()
                if user_city in cancel:
                    self.speak(
                        "я вас поняла, хозяин. завершение игрового навыка",
                        'city/cancel-game'
                    )
                    return
                while user_city.lower() not in map(lambda city: city.lower(), citys):
                    if user_city.lower() not in map(lambda city: city.lower(), used_citys):
                        self.speak(
                            f"города {user_city} не обнаружено в моей базе даннных из {len(citys) + len(used_citys)} городов, попробуйте снова",
                            self.__DYNAMIC
                        )
                    else:
                        self.speak(
                            f"город {user_city} уже был использован в этой игре. попробуйте снова",
                            self.__DYNAMIC
                        )
                    user_city = self.input().capitalize()
                    if user_city in cancel:
                        self.speak(
                            "я вас поняла, хозяин. завершение игрового навыка",
                            'city/cancel-game'
                        )
                        return
                citys.discard(user_city)
                used_citys.add(user_city)
                end_char = user_city.replace('ь', '').replace('ъ', '')[-1]
                letter = end_char[::]
            now_step = 'user' if now_step == 'me' else 'me'
    #endgames

    #internet
    def search_on_wikipedia(self, *args) -> None:
        """
        Поиск определения в Википедии
        """
        request: str = args[0]
        patterns: List[str] = args[1]
        for pattern in patterns:
            if re.match(pattern, request):
                request = re.sub(pattern[:-2], '', request)
                break
        result = self.wiki.page(request).text.split('\n\n')[0]
        result = (
            "простите, хозяин, по всей видимости произошли неполадки во время запроса к википедии, "
            "или же мой модуль распознавания речи дал сбой. "
            "попробуйте снова или же попросите бездарную слугу о чём-нибудь ином что ей под силу"
            if not result else result
        )
        self.speak('хозяин, вот что мне удалось найти по вашему запросу в википедии', self.__DYNAMIC)
        self.speak(result, self.__DYNAMIC)
    
    def get_weather(self, *args) -> None:
        """
        Получение прогноза погоды
        """
        self.speak(
            "конечно, хозяин, выполняю запрос о погоде. подождите немного, пожалуйста",
            self.__DYNAMIC
        )
        city = owner.home_city
        weather: Weather = OWM(tokens.OWM).weather_manager().weather_at_place(city).weather

        status: str = weather.detailed_status
        temp: int = round(weather.temperature('celsius')["temp"])
        wind: int = round(weather.wind()["speed"])
        
        status = self.__get_translate(status)

        # self.speak(f"текущий статус погоды: {status}", self.__DYNAMIC)
        # {"message":"You are not subscribed to this API."}
        # :/
        self.speak(
            f"скорость ветра составляет приблизительно {wind} метров в секунду",
            self.__DYNAMIC
        )
        self.speak(
            f"а температура за окном примерно {temp} градусов цельсия",
            self.__DYNAMIC
        )
    
    def search_google(self, *args) -> None:
        """
        Поиск в гугл и открытие браузера
        """
        request: str = args[0]
        patterns: List[str] = args[1]
        for pattern in patterns:
            if re.match(pattern, request):
                request = re.sub(pattern[:-2], '', request)
                break
        url = f"https://google.com/search?q={request}"
        self.speak(
            f"конечно, хозяин, выполняю поиск в гугле по вашему запросу {request}",
            "dynamic-speech"
        )
        webbrowser.get().open(url)
        self.speak(f"в вашем браузере открыты результаты поиска по запросу {request}, хозяин", self.__DYNAMIC)
    #endinternet
