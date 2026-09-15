from pydantic import BaseModel

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    login_id: str
    password: str


class LoginResponse(BaseModel):
    user: UserOut
