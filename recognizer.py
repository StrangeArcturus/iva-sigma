import os
import json
import wave
import traceback

import speech_recognition as sr
from vosk import Model, KaldiRecognizer

from config import config
from my_logger import logger


class Recognizer:
    """
    Отвечает за распознавание речи и её преобразование в текст
    """
    __recognizer = sr.Recognizer()
    __micro = sr.Microphone()

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
        with self.__micro:
            recognized_data = ""
            # запоминание шумов окружения для последующей очистки звука от них
            self.__recognizer.adjust_for_ambient_noise(self.__micro, duration=2)

            try:
                # print(self.translator.get("Listening...", self.translator.current_lang))
                logger.log("Слушаю...")

                audio = self.__recognizer.listen(self.__micro, 5, 5)
                with open("microphone-results.wav", "wb") as file:
                    file.write(audio.get_wav_data())
                
            except sr.WaitTimeoutError:
                msg = "Пожалуйста, проверьте, что микрофон включен"
                if config.say_errors:
                    self.speak(msg, 'check-micro')

                logger.error(msg)
                traceback.print_exc()
                return ''

            # использование online-распознавания через Google (высокое качество распознавания)
            try:
                logger.log("Начато распознавание...")
                recognized_data = str(self.__recognizer.recognize_google(
                    audio,
                    language="ru"
                )).lower()
            
            except sr.UnknownValueError:
                # play_voice_assistant_speech("What did you say again?")
                msg = "Пожалуйста, повторите"
                if config.say_errors:
                    self.speak(msg, 'please-repeat')

                logger.error(msg)
                return ''
            
            # в случае проблем с доступом в Интернет происходит попытка использовать offline-распознавание через Vosk
            except sr.RequestError:
                msg = "Пытаюсь задействовать оффлайн распознавание..."
                if config.say_warnings:
                    self.speak(msg, 'try-offline-recognize')
                logger.warn(msg)
                recognized_data = self.use_offline_recognition()
            
            return recognized_data
    
    def use_offline_recognition(self) -> str:
        """
        Переключение на оффлайн-распознавание речи
        :return: распознанная фраза
        """
        recognized_data = ""
        try:
            # проверка наличия модели на нужном языке в каталоге приложения
            if not os.path.exists("models/vosk-model-small-ru-0.22"):
                msg = (
                    "Пожалуйста, скачайте модели распознавания речи по ссылке:\n"
                    "https://alphacephei.com/vosk/models и распакуйте как 'model' в текущую директорию."
                )
                if config.say_warnings:
                    self.speak(msg.split('\n')[0][:-1], 'please-get-models')
                logger.warn(msg)
                return ''

            # анализ записанного в микрофон аудио (чтобы избежать повторов фразы)
            with wave.open("microphone-results.wav", "rb") as wave_audio_file:
                model = Model("models/vosk-model-small-ru-0.22")
                offline_recognizer = KaldiRecognizer(model, wave_audio_file.getframerate())

                data = wave_audio_file.readframes(wave_audio_file.getnframes())
            if len(data) > 0:
                if offline_recognizer.AcceptWaveform(data):
                    recognized_data = offline_recognizer.Result()

                    # получение данных распознанного текста из JSON-строки (чтобы можно было выдать по ней ответ)
                    recognized_data = json.loads(recognized_data)
                    recognized_data = recognized_data["text"]
        except:
            traceback.print_exc()
            msg = "Простите, у меня не получается распознать речь, попробуйте позже..."
            if config.say_errors:
                self.speak(msg, 'impossible-to-recognize')
            logger.error(msg)

        return recognized_data
