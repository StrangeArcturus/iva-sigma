from json import load as _load
from typing import Dict


class __Config:
    log_file: str
    say_errors: bool
    say_warnings: bool
    say_if_hearing: bool

    def __init__(self) -> None:
        with open('./config.json', 'rt', encoding='utf-8') as file:
            config_obj: Dict[str, str] = _load(file)
            for key in config_obj.keys():
                setattr(self, key, config_obj[key])


config = __Config()
