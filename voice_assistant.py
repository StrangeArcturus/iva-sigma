from typing import Dict, List, NoReturn, Optional
from datetime import datetime as dt, timedelta
from random import choice, random, shuffle
from json import load as _load
from os import remove
import webbrowser
import re

from speech_worker import SpeechWorker
from my_logger import logger
from tokens import tokens
from config import config
from owner import owner

from data import db_session
from data.notes import Notes

from wikipediaapi import Wikipedia, ExtractFormat
from pyowm.weatherapi25.weather import Weather
from fuzzywuzzy.fuzz import token_sort_ratio
from translate import Translator
from click import clear
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

    daemons: List[str]

    session: db_session.Session

    __DYNAMIC = "dynamic-speech"

    started_over_hear: Optional[dt] = None
    is_over_hear: bool = False

    is_sleeping: bool = False
    started_sleeping: Optional[dt] = None
    sleeping_interval: Optional[timedelta] = None

    __MORNING = "MORNING"
    __DAY = "DAY"
    __EVENING = "EVENING"
    __NIGHT = "NIGHT"
    __EARLY = "EARLY"

    wiki = Wikipedia(
        language='ru',
        extract_format=ExtractFormat.WIKI
    )
    translator = Translator(
        from_lang="en",
        to_lang="ru"
    )

    class __Argument:
        """
        Вспомогательный класс, чтобы упроситить передачу аргументов в навыки
        и не сопоставлять длину `*args` с командой и триггерами-регексами
        """
        user_command: str
        triggers: List[str] = []
        triggered: bool = bool(triggers)
        
        def __init__(self, command: str, triggers: List[str] = [], triggered: bool = bool(triggers)) -> None:
            self.user_command = command
            self.triggers = triggers
            self.triggered = triggered

    def __init__(self) -> None:
        with open('./assistant.json', 'rt', encoding='utf-8') as file:
            owner_obj: Dict[str, str] = _load(file)
            for key in owner_obj.keys():
                setattr(self, key, owner_obj[key])

        with open('./assistant-scheme.json', 'rt', encoding='utf-8') as file:
            self.scheme = _load(file)
        
        self.over_hear_delta = timedelta(minutes=self.over_hear_minutes)

        db_session.global_init("db/assistant.db")
        self.session = db_session.create_session()
    
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
        return self.translator.translate(text)

    def __get_request_from_argument(self, argument: __Argument) -> str:
        """
        Получение запроса из аргумента при использовании регулярного выражения.
        Соблюдаем DRY хотя бы тут
        """
        request: str = argument.user_command #args[0]
        patterns: List[str] = argument.triggers #args[1]
        for pattern in patterns:
            if re.match(pattern, request):
                request = re.sub(pattern[:-2], '', request)
                break
        return request

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
                self.call(self.__Argument(arguments))
                break
            if arguments.lower() in map(lambda trigger: trigger.lower(), triggers):
                #self.__getattribute__(skill)(arguments)
                getattr(self, skill)(self.__Argument(arguments))
                break
            if any({token_sort_ratio(trigger, arguments) >= 75 for trigger in triggers}):
                #self.__getattribute__(skill)(arguments)
                getattr(self, skill)(self.__Argument(arguments))
                break
            if any({re.match(trigger + ' .+' if trigger.endswith(' .+') else trigger, arguments) for trigger in triggers}):
                #self.__getattribute__(skill)(arguments, triggers)
                getattr(self, skill)(self.__Argument(arguments, triggers))
                break
    
    def start_hear(self) -> NoReturn:
        """
        Цикличное прослушивание окружающей среды,
        управление программой не возвращает
        """
        clear()
        while True:
            try:
                for title in self.daemons:
                    getattr(self, '_' + title)()
                owner_speech = self.input()
                if self.is_sleeping:
                    if owner_speech.replace(self.name.lower(), "").strip() not in self.scheme["awake"]:
                        continue
                    self.awake(self.__Argument(owner_speech))
                    continue
                if self.started_over_hear:
                    if dt.now() >= self.started_over_hear + self.over_hear_delta:
                        self.is_over_hear = False
                        self.started_over_hear = None
                if not self.is_over_hear:
                    if not owner_speech.startswith(self.name.lower()) and not owner_speech.endswith(self.name.lower()):
                        continue
                    if owner_speech.lower() != self.name.lower():
                        if owner_speech.startswith(self.name.lower()):
                            owner_speech = (owner_speech[len(self.name):]).strip()
                        if owner_speech.endswith(self.name.lower()):
                            owner_speech = (owner_speech[:-len(self.name)]).strip()
                remove('microphone-results.wav')
                command = owner_speech
                self.execute_command(command)
            except Exception as e:
                msg = "Упс, возникла ошибка..."
                if config.say_errors:
                    self.speak(msg, "runtime-error")
                logger.error(msg)
                print(e)
    
    #name
    def call(self, argument: __Argument) -> None:
        """
        Задействуется, если пользователь позвал ассистента по имени
        """
        if not self.is_over_hear:
            self.is_over_hear = True
            self.started_over_hear = dt.now()
            self.speak("да, хозяин, слушаю вас внимательно", 'carefull-hear')
        else:
            self.speak("хозяин, я вас уже внимательно слушаю", 'already-carefull')

    def relax(self, argument: __Argument) -> None:
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
    def thanks(self, argument: __Argument) -> None:
        """
        Ответ на благодарение пользователя
        """
        self.speak("рада служить, хозяин", 'thank')
    #endthank

    #greeting
    def hello(self, argument: __Argument) -> None:
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
                self.early_morning(argument)
            elif times_of_day == self.__MORNING:
                self.good_morning(argument)
            elif times_of_day == self.__DAY:
                self.good_day(argument)
            elif times_of_day == self.__EVENING:
                self.good_evening(argument)
        
    def early_morning(self, argument: __Argument) -> None:
        """
        Для так называемого, (моего) раннего времени, когда обычно я не бодрствую, но скоро начал бы
        """
        self.speak("что-то вы сегодня рано, хозяин. доброе утро", 'greeting/early-morning')

    def good_morning(self, argument: __Argument) -> None:
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
            self.early_morning(argument)
        elif times_of_day == self.__MORNING:
            self.speak("доброе утро хозяин", "greeting/good_morning")
        elif times_of_day == self.__DAY:
            self.speak("хозяин, но ведь сейчас день?", 'greeting/from-morning-to-day')
        elif times_of_day == self.__EVENING:
            self.speak(
                "мой хозяин, сейчас ведь вечер, совсем не утро",
                'greeting/from-morning-to-evening'
            )
    
    def good_day(self, argument: __Argument) -> None:
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
    
    def good_evening(self, argument: __Argument) -> None:
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

    #datetime
    def time(self, argument: __Argument) -> None:
        """
        Сообщает нынешнее время
        """
        now = dt.now()
        hour = now.hour
        minute = now.minute
        self.speak(
            f"хозяин, сейчас {hour}:{minute} относительно вашего локального времени",
            self.__DYNAMIC
        )
    
    def date(self, argument: __Argument) -> None:
        """
        Сообщает нынешнюю дату
        """
        now = dt.now()
        day = now.day
        month = now.month
        year = now.year
        self.speak(
            f"хозяин, сегодня у нас с вами {day}.{month}.{year}",
            self.__DYNAMIC
        )
    #enddatetime

    #exit
    def bye(self, argument: __Argument) -> None:
        """
        Завершение работы Яны
        """
        self.speak(
            "хорошо, хозяин, завершаю свою программу.",
            'bye/thanks'
        )
        exit(0)
    #endexit

    #random
    def toss_coin(self, argument: __Argument) -> None:
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
    def city(self, argument: __Argument) -> None:
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
    def search_on_wikipedia(self, argument: __Argument) -> None:
        """
        Поиск определения в Википедии
        """
        request = self.__get_request_from_argument(argument)
        result = self.wiki.page(request).text.split('\n\n')[0]
        result = (
            "простите, хозяин, по всей видимости произошли неполадки во время запроса к википедии, "
            "или же мой модуль распознавания речи дал сбой. "
            "попробуйте снова или же попросите бездарную слугу о чём-нибудь ином что ей под силу"
            if not result else result
        )
        self.speak('хозяин, вот что мне удалось найти по вашему запросу в википедии', self.__DYNAMIC)
        self.speak(result, self.__DYNAMIC)
    
    def get_weather(self, argument: __Argument) -> None:
        """
        Получение прогноза погоды
        """
        self.speak(
            "конечно, хозяин, выполняю запрос о погоде. подождите немного, пожалуйста",
            self.__DYNAMIC
        )
        city = owner.home_city
        weather: Weather = OWM(tokens.OWM).weather_manager().weather_at_place(city).weather # type: ignore

        status: str = weather.detailed_status
        temp: int = round(weather.temperature('celsius')["temp"])
        wind_speed: int = round(weather.wind()["speed"])
        wind_deg: int = weather.wind()["deg"]

        status = self.__get_translate(status)

        self.speak(f"текущий статус погоды: {status}", self.__DYNAMIC)
        self.speak(
            f"скорость ветра составляет приблизительно {wind_speed} метров в секунду",
            self.__DYNAMIC
        )
        self.speak(
            f"направление ветра: угол {wind_deg} градусов от северного направления",
            self.__DYNAMIC
        )
        self.speak(
            f"а температура за окном примерно {temp} градусов цельсия",
            self.__DYNAMIC
        )
    
    def search_google(self, argument: __Argument) -> None:
        """
        Поиск в гугл и открытие браузера
        """
        request = self.__get_request_from_argument(argument)
        url = f"https://google.com/search?q={request}"
        self.speak(
            f"конечно, хозяин, выполняю поиск в гугле по вашему запросу {request}",
            self.__DYNAMIC
        )
        webbrowser.get().open(url)
        self.speak(f"в вашем браузере открыты результаты поиска по запросу {request}, хозяин", self.__DYNAMIC)
    #endinternet

    #sleep
    def sleep(self, argument: __Argument) -> None:
        """
        Переход в сон по команде
        """
        self.speak("вас поняла, на сколько минут мне уснуть?", "sleep/ask-minutes")
        text = re.sub(r"\D", "", self.input())
        minutes = int(text)
        self.speak("хорошо, хозяин, подготовка ко сну", "sleep/getting-sleep")
        self.started_sleeping = dt.now()
        self.sleeping_interval = timedelta(minutes=minutes)
        when_awake = self.started_sleeping + self.sleeping_interval
        awake_hour = when_awake.hour
        awake_minute = when_awake.minute
        self.speak(f"перехожу в сон до {awake_hour:02}:{awake_minute:02} или до пробуждения вами", self.__DYNAMIC)
        self.is_sleeping = True
        self._say_if_hearing = False
    
    def _check_on_sleep(self) -> None:
        """
        Проверка на состояние сна.
        Приватный метод-демон
        """
        if not self.is_sleeping:
            return
        if not ((dt.now()) >= (self.started_sleeping + self.sleeping_interval)): # type: ignore
            return
        self.awake(self.__Argument(""))
    
    def awake(self, argument: __Argument) -> None:
        """
        Пробуждение по команде или по истечение времени
        """
        if not self.is_sleeping:
            self.speak("но хозяин, я же не сплю", "sleep/already-awake")
            return
        if argument.user_command:
            self.speak("а? да-да, я здесь и готова работать", "sleep/awake-from-user")
        else:
            self.speak("хозяин, по истечение заданного времени я проснулась и готова к работе", "sleep/awake-from-self")
        self.sleeping_interval = None
        self.started_sleeping = None
        self.is_sleeping = False
        self._say_if_hearing = config.say_if_hearing
    #endsleep

    #note
    def new_note(self, argument: __Argument) -> None:
        """
        Создание долгосрочной заметки во время диалога, а не из команды
        """
        self.speak("конечно, хозяин, диктуйте заметку", "note/get-new-from-dialog")
        text = self.input()
        note = Notes(text=text)
        self.session.add(note)
        self.session.commit()
        self.speak("ваша заметка без срока хранения добавлена в базу данных, хозяин", "note/added-new")
        count = self.session.query(Notes).count()
        self.speak(f"общее количество заметок в моей базе данных: {count}", self.__DYNAMIC)
    
    def read_notes(self, argument: __Argument) -> None:
        """
        Чтение и произношение заметок по очереди
        """
        self.speak("подождите, подготовка и запрос имеющихся заметок", "note/querying")

        STOP = ("стоп", "хватит", "достаточно")
        NEXT = ("далее", "следующая")
        BACK = ("назад", "предыдущая")
        AGAIN = ("повтори", "ещё раз")
        DELETE = ("удали", "удали эту", "удали текущую")
        UPDATE = (
            "обнови", "обнови эту", "обнови текущую",
            "замени", "замени эту", "замени текущую",
            "перепиши", "перепиши эту", "перепиши текущую"
        )
        NEW = ("создай", "сделай", "добавь")

        notes: List[Notes] = self.session.query(Notes).all()
        index = 0

        self.speak("начну чтение с начала списка", "note/get-from-start")
        if not notes:
            self.speak("простите, хозяин, но на данный момент заметок не имеется", "note/db-is-empty")
        while True:
            if index >= len(notes):
                index = 0
            """
            if index < -len(notes):
                index = len(notes) - 1
            """
            index %= len(notes)
            if not notes:
                self.speak("простите, хозяин, но на данный момент заметок не имеется", "note/db-is-empty")
                self.speak("завершаю чтение заметок за неимением таковых", "note/ending-read-when-empty")
                break
            self.speak(
                f"заметка номер {index + 1}. Содержание: {notes[index].text}",
                self.__DYNAMIC
            )
            text = self.input()
            if text in STOP:
                self.speak("хорошо, хозяин, завершаю чтение заметок", "note/ending-read")
                break
            elif text in NEXT:
                self.speak("отлично, переходим к следующей записи", "note/next")
                index += 1
                continue
            elif text in BACK:
                self.speak("вас поняла, хозяин, переход к предыдущей запиcи", "note/back")
                index -= 1
                continue
            elif text in AGAIN:
                self.speak("хорошо, повторю текущую запись снова", "note/again")
                continue
            elif text in DELETE:
                self.speak(
                    f"удаляю заметку номер {index + 1}, подождите",
                    self.__DYNAMIC
                )
                self.session.query(Notes).filter(Notes.id == notes[index].id).delete()
                self.session.commit()
                del notes[index]
                self.speak("запись очищена успешно", "note/success-delete")
            elif text in UPDATE:
                self.speak(
                    f"задача понятна. хозяин, диктуйте новое содержимое заме́тки под номером {index + 1}",
                    self.__DYNAMIC
                )
                text = self.input()
                self.session.query(Notes).filter(Notes.id == notes[index].id).update({
                    Notes.text: text
                })
                notes[index].text = text # type: ignore
                self.session.commit()
                self.speak("запись обновлена́ успешно", "note/success-update")
            elif text in NEW:
                self.new_note(argument)
                notes: List[Notes] = self.session.query(Notes).all()
    #endnote
