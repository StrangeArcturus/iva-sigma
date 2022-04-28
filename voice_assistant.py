from typing import Dict, NoReturn
from json import load as _load
from os import remove

from speech_worker import SpeechWorker
from my_logger import logger
from config import config


class VoiceAssistant(SpeechWorker):
    """
    Помимо реализации работы с речью и текстом,
    будет реализовывать работу голосового ассистента
    """
    name: str
    sex: str
    speech_language: str
    recognition_language: str
    scheme: Dict[str, str]

    def __init__(self) -> None:
        with open('./assistant.json', 'rt', encoding='utf-8') as file:
            owner_obj: Dict[str, str] = _load(file)
            for key in owner_obj.keys():
                setattr(self, key, owner_obj[key])

        with open('./assistant-scheme.json', 'rt', encoding='utf-8') as file:
            self.scheme = _load(file)

    def execute_command(self, arguments: str) -> None:
        for key in self.scheme.keys():
            if key == arguments or arguments.startswith(key) or key.startswith(arguments):
                self.__getattribute__(self.scheme[arguments])()
    
    def start_hear(self) -> NoReturn:
        while True:
            try:
                owner_speech = self.record_and_recognize_audio().lower()
                remove('microphone-results.wav')
                logger.log(f'Произнесено:\n{owner_speech}')
                words = owner_speech.split()
                # command, *arguments = words
                command = owner_speech
                self.execute_command(command)# , arguments)
            except Exception as e:
                msg = "Упс, возникла ошибка..."
                if config.say_errors:
                    self.speak(msg, "runtime-error")
                print(msg)
                print(e)

    def greeting(self, *args) -> None:
        self.speak("Привет, мой хозяин", self._get_sound_path("greeting/hello"))
