from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import verify_password
from app.deps import get_db
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.login_id == payload.login_id, User.active.is_(True)).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(
            code="INVALID_CREDENTIALS",
            message="IDまたはパスワードが違います",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return LoginResponse(user=UserOut.model_validate(user))
