from pydantic import BaseModel, ConfigDict


class FormatCreate(BaseModel):
    name: str


class FormatUpdate(BaseModel):
    name: str


class FormatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
