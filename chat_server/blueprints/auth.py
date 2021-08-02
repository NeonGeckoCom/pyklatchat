import jwt

from fastapi import APIRouter, Depends, Form, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

from chat_server.config import db_connector
from chat_server.utils.auth import get_current_user, secret_key, jwt_encryption_algo, hash_password, \
    check_password_strength, generate_uuid

router = APIRouter(
    prefix="/auth",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.post("/signup")
def signup(response: Response,
           first_name: str = Form(...),
           last_name: str = Form(...),
           nickname: str = Form(...),
           password: str = Form(...)):
    existing_user = db_connector.exec_query(query={'command': 'find_one',
                                                   'document': 'users',
                                                   'data': {'nickname': nickname}})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Nickname is already in use"
        )
    password_check = check_password_strength(password)
    if password_check != 'OK':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=password_check
        )
    new_user_record = dict(_id=generate_uuid(length=20),
                           first_name=first_name,
                           last_name=last_name,
                           password=hash_password(password),
                           nickname=nickname,
                           creation_time=time(),
                           is_tmp=False)
    db_connector.exec_query(query=dict(document='users', command='insert_one', data=new_user_record))

    token = jwt.encode(payload={"sub": new_user_record['_id']}, key=secret_key, algorithm=jwt_encryption_algo)
    response.set_cookie("session", token, httponly=True)

    return {'signup': True}


@router.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...)):
    matching_user = db_connector.exec_query(query={'command': 'find_one',
                                                   'document': 'users',
                                                   'data': {}})
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
async def read_private(username: str = Depends(get_current_user)):
    return {"received_user_id:": username}
