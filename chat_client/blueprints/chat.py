import jwt

from fastapi import APIRouter, Depends, Form, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException

router = APIRouter(
    prefix="/conversation",
    responses={'404': {"description": "Unknown authorization endpoint"}},
)


@router.get("/new", response_class=HTMLResponse)
async def read_item(request: Request, chat_id: str):
    return templates.TemplateResponse("item.html", {"request": request, "id": id})


@router.get("/{chat_id}", response_class=HTMLResponse)
async def read_item(request: Request, chat_id: str):
    return templates.TemplateResponse("item.html", {"request": request, "id": id})
