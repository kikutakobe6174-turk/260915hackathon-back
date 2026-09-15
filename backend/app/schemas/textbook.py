from pydantic import BaseModel, ConfigDict


class TextbookCreate(BaseModel):
    publisher: str
    title: str
    subject: str


class TextbookUpdate(BaseModel):
    publisher: str
    title: str
    subject: str


class TextbookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    publisher: str
    title: str
    subject: str
