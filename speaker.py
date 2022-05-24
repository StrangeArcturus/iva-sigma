from pyttsx3 import init

from gtts import gTTS, gTTSError
from playsound import playsound

from my_logger import logger
from config import config

from os.path import exists, isfile


class Speaker:
    """
    Отвечает за генерацию речи из текста
    """
    __tts_engine = init()
    __tts_engine.setProperty('rate', 150)
    __tts_engine.setProperty("voice", "russian")

    def _get_sound_path(self, title: str) -> str:
        ...

    def speak(self, text: str, label: str) -> str:
        """
        Получение текста и его озвучивание от гугла
        """
        path = self._get_sound_path(label)
        logger.log(f"Произношу вслух:\n{text}")
        try:
            if path == './cache-sounds/dynamic-speech/1.mp3':
                gtts = gTTS(text=text, lang="ru")
                gtts.save(path)
                playsound(path)
                return text
            if exists(path):
                if isfile(path):
                    playsound(path)
                    return text
            else:
                gtts = gTTS(text=text, lang="ru")
                gtts.save(path)
                playsound(path)
                return text
        except gTTSError:
            msg = "Что-то произошло с генерацией речи google..."
            if config.say_errors:
                self.speak(msg, 'google-generation-trouble')
            logger.error(msg)
        except:
            self.offline_speak(text)
        finally:
            return text
        
    def offline_speak(self, text: str) -> str:
        try:
            self.__tts_engine.say(text)
            self.__tts_engine.runAndWait()
        except:
            msg = "Что-то пошло не так с генерацией речи оффлайн..."
            if config.say_errors:
                self.speak(msg, 'offline-generation-trouble')
            logger.error(msg)
        finally:
            return text
