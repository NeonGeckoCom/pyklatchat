import jwt

from fastapi import APIRouter, Depends, Form, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

from chat_server.utils import db_connector
from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, hash_password

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
    users = db_connector.exec_query(query={'command': 'find_one',
                                           'document': 'users',
                                           'data': {}})
    filtered_records = list(filter(lambda user: user['nickname'] == username, users))
    matching_user = None
    if filtered_records:
        matching_user = filtered_records.pop()
    if not matching_user or matching_user['is_tmp']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    db_password = matching_user["password"]
    if hash_password(password) != db_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    token = jwt.encode(payload={"sub": matching_user['_id']}, key=secret_key, algorithm=jwt_encryption_algo)
    response.set_cookie("session", token, httponly=True)
    return {"login": True}


@router.get("/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"logout": True}


@router.get("/test")
def read_private(username: str = Depends(get_current_user)):
    return {"received_user_id:": username}
