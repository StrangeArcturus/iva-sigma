from json import load as _load


class __Tokens:
    OWM: str

    def __init__(self) -> None:
        with open('./tokens.json', 'rt', encoding='utf-8') as file:
            for key, value in _load(file).items():
                setattr(self, key, value)


tokens = __Tokens()
