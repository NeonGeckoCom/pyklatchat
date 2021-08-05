import requests

from typing import Optional
from fastapi import Response, Request, status, APIRouter
from fastapi.exceptions import HTTPException


router = APIRouter(
    prefix="/users",
    responses={'404': {"description": "Unknown user"}},
)


@router.get("/")
def get_user(response: Response, request: Request, user_id: Optional[str] = None):
    user_id = user_id or ''
    get_user_response = requests.get(f'http://127.0.0.1:8000/users_api/{user_id}', cookies=request.cookies)
    if get_user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=get_user_response.json()
        )
    else:
        for cookie in get_user_response.cookies:
            response.set_cookie(key=cookie.name, value=cookie.value, httponly=True)
        print(get_user_response.cookies)
        return get_user_response.json()

