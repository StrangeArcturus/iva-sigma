from speaker import Speaker
from recognizer import Recognizer

from os.path import exists
from os import listdir, makedirs
from random import choice


class SpeechWorker(Speaker, Recognizer):
    """
    Объединяет полу-виртуальные классы и реализует их полностью.
    На его плечах и генерация речи, и её обработка
    """
    def _get_sound_path(self, title: str) -> str:
        path_in_cache = f'./cache-sounds/{title}'
        if exists(path_in_cache):
            files = listdir(path_in_cache)
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
