from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter()


@router.get("/healthz")
async def health():
    return JSONResponse(content={
        "code": 0,
        "message": "ok"
    }, status_code=200)

