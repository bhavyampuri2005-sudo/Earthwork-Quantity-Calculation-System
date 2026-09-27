import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from database import get_db

router = APIRouter()

# Set JWT_SECRET_KEY in the environment for anything beyond local dev -
# this fallback is only safe on a machine nobody else can reach.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 8 * 60  # 8 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Standard OAuth2 password-flow login: POST username+password as
    form data (not JSON), get a bearer token back. Using FastAPI's
    OAuth2PasswordRequestForm here (rather than a plain Pydantic model)
    is what makes the auto-generated /docs page show a working "Authorize"
    button, and is what the frontend's fetch call needs to match -
    Content-Type: application/x-www-form-urlencoded, not JSON.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT username, password_hash, role FROM Users WHERE username = %s",
            (form_data.username,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not row or not bcrypt.checkpw(form_data.password.encode(), row[1].encode()):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token(row[0], row[2])
    return TokenResponse(access_token=token, role=row[2])


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Decodes and validates the bearer token. Add as a dependency to any
    route that just needs "someone logged in", regardless of role.
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return {"username": username, "role": role}


def require_role(*allowed_roles: str):
    """
    Dependency factory - use as Depends(require_role("admin")) or
    Depends(require_role("admin", "engineer")) on any route. Checks
    the token is valid (via get_current_user) AND that its role is
    one of allowed_roles; 401 for no/bad token, 403 for a valid token
    with the wrong role.
    """

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user['role']}' is not permitted to perform this action.",
            )
        return user

    return checker
