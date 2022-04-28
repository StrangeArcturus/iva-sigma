from json import load

from termcolor import colored


class Translator:
    """
    Получение вшитого в приложение перевода строк для создания мультиязычного ассистента
    """
    current_lang: str

    with open("./translation.json", "rt", encoding="utf-8") as file:
        translations = load(file)
    
    def set_dependies(self) -> None:
        ...
    
    def get(self, text: str, language: str) -> str:
        """
        Получение перевода строки из файла на нужный язык (по его коду)
        :param text: текст, который требуется перевести
        :return: вшитый в приложение перевод текста
        """
        if text in self.translations:
            self.current_lang = language
            return self.translations[text][language]
        else:
            # в случае отсутствия перевода происходит вывод сообщения об этом в логах и возврат исходного текста
            print(colored("Not translated phrase: {}".format(text), "red"))
            return text


translator = Translator()
