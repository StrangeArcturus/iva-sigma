from gtts import gTTS
from playsound import playsound

from os import makedirs, listdir
from os.path import exists

from argparse import ArgumentParser as ArgParser


def make_sound(text: str, path: str, play_now: bool = False):
    """
    `path` -- путь строго ДО КАТАЛОГА,
    название выстроится автоматически
    """
    gtts = gTTS(text, lang="ru")
    makedirs(path, exist_ok=True)
    if listdir(path):
        last_audio_number = max(map(int, map(lambda x: x[:-4], listdir(path))))
        path += f"/{last_audio_number + 1}.mp3"
    else:
        path += "/1.mp3"
    gtts.save(path)
    if play_now:
        playsound(path)


def make_cache_from_txt(path_to_txt: str, path_to_cache: str, play_now: bool = False):
    """
    `path_to_txt` -- путь только до КАТАЛОГА
    нумерацию функция выстроит сама
    """
    with open(path_to_txt, 'rt', encoding='utf-8') as file:
        data = file.read()
    make_sound(data, path_to_cache, play_now=play_now)


def _get_sound_path(title: str) -> str:
    path_in_cache = f'./cache-sounds/{title}'
    if exists(path_in_cache):
        #files = list(filter(isfile, listdir(path_in_cache)))
        files = list(map(
            lambda file: int(file[:-4]),
            filter(
                lambda file: file.endswith('.mp3'),
                listdir(path_in_cache)
            )
        ))
        if files:
            return f'{path_in_cache}/{max(files) + 1}.mp3'
        else:
            return f'{path_in_cache}/1.mp3'
    else:
        makedirs(path_in_cache, exist_ok=True)
        return f'{path_in_cache}/1.mp3'


def test():
    _get_sound_path('test/test-repeat')


from_file_help = """
enter if text to generate speech in .txt-file \\
введите, если текст для генерации речи находится в .txt-файле
"""

play_now_help = """
enter if you want to play speech after generate \\
введите, если хотите воспроизвести сгенерированную речь сразу после генерации
"""

argument_help = """
enter text of speech if without --from-file flag, else path to .txt-file \\
введите текст для генерации речи, если нет флага --from-file, иначе путь к .txt-файлу с текстом речи
"""

label_help = """
enter label of folder-set of files in cache-sounds \\
введите название папки-множества файлов в папке кеша cache-sounds
"""


def main():
    parser = ArgParser()
    parser.add_argument(
        "--from-file", '-f', nargs='?', default=False,
        type=bool, help=from_file_help
    )
    parser.add_argument(
        "--play-now", '-p', nargs='?', default=False,
        type=bool, help=play_now_help
    )
    parser.add_argument(
        "argument", nargs=1,
        type=str, help=argument_help
    )
    parser.add_argument(
        "label", nargs=1,
        type=str, help=label_help
    )
    args = parser.parse_args()
    label = './cache-sounds/' + args.label[0]
    if args.from_file:
        make_cache_from_txt(args.argument, label, args.play_now)
    else:
        make_sound(args.argument[0], label, args.play_now)


if __name__ == "__main__":
    main()
