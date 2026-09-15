from pydantic import BaseModel, ConfigDict


class SchoolCreate(BaseModel):
    name: str


class SchoolUpdate(BaseModel):
    name: str


class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
