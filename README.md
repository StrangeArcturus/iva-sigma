# IVA Яна

## Яна является Интегрированным Голосовым Помощником, aka Integrated Voice Assistant. Её цель заключается в помощи пользователю, выполнении той рутины, которую можно положить на машину, а также в небольшой поддержке пользователя

### Установка
#### Python
Для работы необходим язык программирования Python версии не ниже 3.8.
<br>
Если вы читаете это, по всей видимости, подробности по его загрузке и установке излишни
#### Зависимости
Рекомендуется использовать вирутальное окружение, дабы не засорять глобальный интерпретатор лишними библиотеками. <br>
Установка библиотек:
- *Nix
`pip3 install -r requirements.txt`
- Windows
`pip install -r requirements.txt`
<br>
Для установки PyAudio на Windows можно найти и скачать нужный в зависимости от архитектуры и версии Python whl-файл [здесь](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) в папку с проектом. После чего его можно установить при помощи подобной команды:

`pip install PyAudio-0.2.11-cp38-cp38m-win_amd64.whl`

В случае проблем с установкой PyAudio на MacOS может помочь [данное решение](https://stackoverflow.com/questions/33851379/pyaudio-installation-on-mac-python-3).

    Для использования SpeechRecognition в offline-режиме (без доступа к Интернету), 
    потребуется дополнительно установить Vosk (качество моделей близко к Google)
    
    В проекте преимущественно используется Google при наличии доступа в Интернет и
    предусмотрено переключение на Vosk в случае отсутствия доступа к сети.

Для избежания проблем с установкой Vosk на Windows, я предлагаю скачать whl-файл в зависимости от требуемой архитектуры и версии Python. Его можно найти [здесь](https://github.com/alphacep/vosk-api/releases/). Загрузив файл в папку с проектом, установку можно будет запустить с помощью подобной команды: 

`pip install vosk-0.3.7-cp38-cp38-win_amd64.whl`

Модели для распознавания речи с помощью Vosk можно найти [здесь](https://alphacephei.com/vosk/models).

### Запуск
- *Nix
`python3 main.py`
- Windows
`python main.py`

### Настройка
В одной папке со всеми скриптами должны находиться файлы:
- `assistant.json` описание **характеристик** Яны: её имя (да, может перестать быть Яной); пол (по той же причине); ~~язык, на котором говорит Яна; язык, на который она будет переводить~~; время __внимательного__ слуха в минутах
- `assistant-scheme.json` содержит схему навыков Яны в формате объекта
```json
"название_навыка_в_классе": [
    "список из всех", "подходящих фраз-триггеров",
    "для этого навыка",
    "а также регулярные выражения",
    "(к примеру|например){0,1} вот так (вот)?"
]
```
- `config.json` с указанием файла для логов (если пусто -- не писать логи в файл); флаги на проговаривание предупреждений и ошибок
- `owner.json` содержит информацию о пользователе
- `translation.json` пока ~~болтается без смысла для сущемтвования~~ не реализован

### Использование
После запуска основного скрипта Яна циклично прослушивает окружение и распознаёт речь вокруг, пока не среагирует на первый подходящий навык. Также применяется нечёткое сравнение реплик пользователя и триггеров навыка, в связи с чем возможна реакция на фразы, похожие на фразы в `схеме`.
<br>
Статичные (не требующие разных формулировок и слов) фразы, к примеру "доброе утро" кешируются в папку `cache-sounds`, а для большей интерактивности в будущем будет реализована утилита для увеличения подобных фраз

### Добавление навыков
Исполняется весьма просто: в конец файла `voice_assistant.py` с учётом табуляции и отступов Python дописываются **методы** с тем же названием, что и в `схеме`. В целом, структура метода такова:
```python
class VoiceAssistant:
    ...
    # много необходимого кода
    def название_метода(self, *args) -> None:
        """
        Док-строки с описанием по желанию 
        (рекомендуется)
        """
        ...
        # различная логика, код и прочие сложные вещи
        # первым аргументом в кортеже args будет лежать фраза пользователя,
        # заранее очищенная от обращения к Яне по имени
        # а метод `speak` будет обеспечивать произношение и кеширование фраз,
        # где первым аргументом подаётся фраза
        # а вторым её метка (если метка равна "dynamic-speech", то кеширование будет пропускаться)
        # метод может возвращать какие-то значения,
        # однако использоваться им негде,
        # поэтому рекомендуется возвращать None (как явно, так и неявно)
```

###### Sigma