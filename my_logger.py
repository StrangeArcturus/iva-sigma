from termcolor import colored

from config import config


class __MyLogger:
    log_file = config.log_file

    def warn(self, text: str) -> str:
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as file:
                file.write(f"{text}\n")
        print(colored(text, "yellow"))
        return text
    
    def error(self, text: str) -> str:
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as file:
                file.write(f"{text}\n")
        print(colored(text, "red"))
        return text
    
    def log(self, text: str) -> str:
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as file:
                file.write(f"{text}\n")
        print(text)
        return text


logger = __MyLogger()
