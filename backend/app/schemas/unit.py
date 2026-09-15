from pydantic import BaseModel, ConfigDict


class UnitCreate(BaseModel):
    name: str
    order_no: int


class UnitUpdate(BaseModel):
    name: str
    order_no: int


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    textbook_id: int
    name: str
    order_no: int


class UnitImportRow(BaseModel):
    name: str
    order_no: int


class UnitImportRequest(BaseModel):
    rows: list[UnitImportRow]
