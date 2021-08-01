import jwt

from fastapi import APIRouter, Depends, Form, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, users

router = APIRouter(
    prefix="/auth",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.get("/login")
def login_page():
    return HTMLResponse(
        """
        <form action="/auth/login" method="post">
        Username: <input type="text" name="username" required>
        <br>
        Password: <input type="password" name="password" required>
        <input type="submit" value="Login">
        </form>
        """)


@router.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password"
        )
    db_password = users[username]["password"]
    if not password == db_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user or password"
        )
    token = jwt.encode(payload={"sub": username}, key=secret_key, algorithm=jwt_encryption_algo)
    response.set_cookie("session", token, httponly=True)
    return {"login": True}


@router.get("/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"logout": True}


@router.get("/test")
def read_private(username: str = Depends(get_current_user)):
    return {"received_user_id:": username}
