from abc import ABC, abstractmethod


class BaseFileHandler(ABC):
    @abstractmethod
    def process_files(self) -> None:
        ...
