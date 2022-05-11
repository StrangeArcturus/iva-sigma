from speaker import Speaker
from recognizer import Recognizer

from os.path import exists, isfile
from os import listdir, makedirs
from random import choice


class SpeechWorker(Speaker, Recognizer):
    """
    Объединяет полу-виртуальные классы и реализует их полностью.
    На его плечах и генерация речи, и её обработка
    """
    def _get_sound_path(self, title: str) -> str:
        """
        Генерация путей для кеширования аудиозаписей,
        дабы не запрашивать одно и то же по многу раз,
        а также для экономии трафика без применения оффлайн озвучки
        """
        if title == "dynamic-speech":
            path = './cache-sounds/dynamic-speech'
            makedirs(path, exist_ok=True)
            return f'{path}/1.mp3'
        path_in_cache = f'./cache-sounds/{title}'
        if exists(path_in_cache):
            files = list(filter(isfile, listdir(path_in_cache)))
            if files:
                if len(files) > 1:
                    return f'{path_in_cache}/{choice(files)}'
                else:
                    return f'{path_in_cache}/{files[0]}'
            else:
                return f'{path_in_cache}/1.mp3'
        else:
            makedirs(path_in_cache, exist_ok=True)
            return f'{path_in_cache}/1.mp3'
