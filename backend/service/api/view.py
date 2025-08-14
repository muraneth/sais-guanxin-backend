import asyncio
import time

from fastapi import APIRouter, Depends
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse

from service.config.config import service_config
from service.package.auth import get_auth, authenticate, check_user
from util.timer import Timer
from util.model_types import AppResponse, StatusCode, User

router = APIRouter()
templates = Jinja2Templates(directory="./templates")
redirect_from_host = {
    'localhost': 'http://localhost:8088',
    '127.0.0.1': 'http://127.0.0.1:8088',
    'financial-report.infly.tech': 'http://financial-report.infly.tech/ai-investment',
    'fin.infly.work': 'http://fin.infly.work/ai-investment',
    'fin.infly.tech': 'http://fin.infly.tech/ai-investment'
}
production_host = 'https://fin.infly.cn/ai-investment'


@router.get("/")
async def main_view(request: Request, requester: User = Depends(authenticate)):
    if requester:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return RedirectResponse(url=service_config.path_prefix + "/signin", status_code=302)


@router.get('/logout.html')
async def logout_view(request: Request):
    return templates.TemplateResponse("logout.html", {"request": request})


def get_auth_host(host):
    if host in redirect_from_host:
        return redirect_from_host[host]
    else:
        return production_host


@router.get('/signin')
async def signin(request: Request):
    client_id = service_config.auth.authing_app_id
    response_type = 'code'
    redirect_host = get_auth_host(request.url.hostname)
    redirect_uri = redirect_host + '/login'
    scope = 'openid tenant_id'
    state = str(time.time())
    redirect_url = '{}/oidc/auth?client_id={}&response_type={}&redirect_uri={}&scope={}&state={}'.format(
        service_config.auth.authing_app_host, client_id, response_type, redirect_uri, scope, state)
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/login")
async def login(request: Request):
    redirect_host = get_auth_host(request.url.hostname)
    redirect_uri = redirect_host + '/login'
    code = request.query_params.get('code')
    auth_client = get_auth(redirect_uri=redirect_uri)
    data = await asyncio.get_event_loop().run_in_executor(None,
                                                          auth_client.get_access_token_by_code,
                                                          code)
    access_token = data.get('access_token')
    id_token = data.get('id_token')
    response = RedirectResponse(url="/ai-investment")
    response.set_cookie(service_config.auth.cookie_key, access_token, httponly=True)
    if id_token:
        response.set_cookie(service_config.auth.cookie_key + '_id', id_token, httponly=True)
    return response


@router.get('/logout')
async def logout(request: Request):
    id_token = request.cookies.get(service_config.auth.cookie_key + "_id")
    redirect_host = get_auth_host(request.url.hostname)
    logout_url = redirect_host + '/logout.html'
    response = RedirectResponse(
        "{}/oidc/session/end?id_token_hint={}&post_logout_redirect_uri={}".format(
            service_config.auth.authing_app_host, id_token, logout_url
        )
    )
    response.delete_cookie(service_config.auth.cookie_key, httponly=True)
    return response


@router.get("/api/user")
async def user(requester: User = Depends(authenticate)):
    check_user(requester)
    timer = Timer()
    resp = {
        AppResponse.status_code: StatusCode.Success,
        AppResponse.latency: timer.duration(),
        "user": requester.__dict__
    }
    return JSONResponse(resp)
