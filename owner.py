from json import load as _load
from typing import Dict


class __Owner:
    """
    Класс, определяющий необходимые сведения о владельце (хозяине)
    """
    name: str
    home_city: str
    native_language: str
    target_language: str

    def __init__(self) -> None:
        with open('./owner.json', 'rt', encoding='utf-8') as file:
            owner_obj: Dict[str, str] = _load(file)
            for key in owner_obj.keys():
                setattr(self, key, owner_obj[key])


owner = __Owner()
