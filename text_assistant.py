from voice_assistant import VoiceAssistant
from typing import NoReturn


class TextAssistant(VoiceAssistant):
    def input(self) -> str:
        """
        Получение текста, минуя голосовое распознование,
        из коммандной строки
        """
        return input("[Слушаю]")
        
        
    def speak(self, text: str, label: str) -> str:
        """
        Печать ответа в коммандную строку,
        вместо озвучивания
        """
        print(f"[Произношу] {text}")
        return text



TextAssistant().start_hear()
