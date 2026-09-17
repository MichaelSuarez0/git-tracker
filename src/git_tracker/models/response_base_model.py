from pydantic import BaseModel


class ResponseBaseModel(BaseModel):
    """Modelo base para respuestas y entidades que soporta parseo de dict o instancia."""

    @classmethod
    def parse[T: BaseModel](cls: type[T], data: T | dict) -> T:
        if isinstance(data, dict):
            return cls(**data)
        if not isinstance(data, cls):
            raise TypeError(f"Expected {cls.__name__} or dict, got {type(data).__name__}")
        return data
