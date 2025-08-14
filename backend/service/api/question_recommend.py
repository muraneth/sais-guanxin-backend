from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import JSONResponse
from service.package.auth import authenticate, check_user, CMS_USER
from util.random_question import get_random_questions
from util.timer import Timer
from util.model_types import User, AppResponse, StatusCode

router = APIRouter(
    prefix="/api"
)

@router.get('/question_recommend')
async def question_recommend(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    resp = {
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        "questions": get_random_questions(5),
    }
    return JSONResponse(resp)