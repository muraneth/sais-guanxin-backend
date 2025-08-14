import asyncio
import base64
import json
import traceback
from enum import Enum
from typing import Optional
from urllib import parse

import requests
import jwt
from authing.v2.authentication import AuthenticationClient, AuthenticationClientOptions
from authing.v2.management import ManagementClient, ManagementClientOptions
from starlette.requests import Request
from starlette.responses import JSONResponse
from metrics.meter_key import MeterKey
from metrics.meters import record_latency
from metrics.metrics import AUTH_LATENCY
from service.config.config import service_config
from service.exceptions.auth_exception import AuthFailedException
from util.logger import service_logger, access_logger
from util.timer import Timer
from util.model_types import User
from util.logger import service_logger

class UserAuthType(Enum):
    Authing = "authing"
    Keycloak = "keycloak"
    Dummy = "dummy"
    KeyAuth = "key_auth"
    Other = "other"


DUMMY_USER = User(**{
    "id": "ka-gujiawei-dev-01",
    "username": "test",
    "email": "tests@inftech.ai",
    "company": "INF",
    "is_admin": False,
    "tenant_id": service_config.auth.inf_dep_id,
    "deps": {},
    "groups": ["内部"],
    "type": UserAuthType.Dummy.value
})
CMS_USER = User(**{
    "id": "cms",
    "username": "cms-PoC",
    "email": "cms@cms.com",
    "company": "CMS",
    "is_admin": False,
    "tenant_id": "CMS",
    "type": UserAuthType.Other.value
})
AUTH_FAILED_RESPONSE = JSONResponse(content={"code": 1, "message": "Authentication Failed"}, status_code=401)


def get_auth(token=None, redirect_uri=service_config.auth.authing_redirect_url):
    auth_client = AuthenticationClient(options=AuthenticationClientOptions(
        app_id=service_config.auth.authing_app_id,
        app_host=service_config.auth.authing_app_host,
        protocol='oidc',
        user_pool_id=service_config.auth.test_user_pool,
        token=token,
        redirect_uri=redirect_uri,
        secret=service_config.auth.authing_app_secret,
        token_endpoint_auth_method='client_secret_post'))
    return auth_client


def get_auth_manage():
    management_client = ManagementClient(options=ManagementClientOptions(
        user_pool_id=service_config.auth.test_user_pool,
        secret=service_config.auth.pool_secret,
    ))
    return management_client


async def get_dep_list():
    management = get_auth_manage()
    parent_dep_id = '656d3f427369958b3cecff64'
    deps = await asyncio.get_event_loop().run_in_executor(None,
                                                          management.org.list_children,
                                                          parent_dep_id)
    return deps


async def async_get_user(req: Request) -> Optional[User]:
    token = req.cookies.get(service_config.auth.cookie_key)
    auth_client = get_auth(token=token)
    user = await asyncio.get_event_loop().run_in_executor(None, auth_client.get_current_user, token)
    user['username'] = user['name'] or user['username']
    user['tenant_id'] = ''
    user['is_admin'] = False
    try:
        manager = get_auth_manage()
        deps = await (asyncio.get_event_loop().run_in_executor(None,
                                                               manager.users.list_department,
                                                               user["id"]))
        deps = deps['departments']['list']
        user['deps'] = deps
        is_admin = False
        tenant_id = ''
        for dep in deps:
            department = dep['department']
            org_id = department['orgId']
            dep_id = department['id']
            if org_id == service_config.auth.inf_org_id:
                is_admin = True
            if tenant_id == '':
                tenant_id = dep_id

        user['tenant_id'] = tenant_id
        user['is_admin'] = is_admin
        user['type'] = UserAuthType.Authing.value
        return User(**user)
    except Exception:
        service_logger.warning(traceback.print_exc())
        return None


async def check_token(token):
    url = '{}/oidc/token/introspection'.format(service_config.auth.authing_app_host)
    data = {
        'client_id': service_config.auth.authing_app_id,
        'client_secret': service_config.auth.authing_app_secret,
        'token': token
    }
    data = parse.urlencode(data)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    res = await asyncio.get_event_loop().run_in_executor(None,
                                                         requests.post,
                                                         url,
                                                         data,
                                                         headers)
    result = res.json()
    print('authing introspection', url, data, result, flush=True)
    return result['active']


async def authenticate(request: Request) -> Optional[User]:
    if service_config.auth.auth_type == "authing":
        timer = Timer()
        token = request.cookies.get(service_config.auth.cookie_key)
        auth_client = get_auth(token)
        login_status = await asyncio.get_event_loop().run_in_executor(None,
                                                                      auth_client.check_login_status,
                                                                      token)
        record_latency(MeterKey(authenticate.__qualname__, authenticate.__name__), AUTH_LATENCY, timer.duration())
        if login_status['status']:
            get_user_timer = Timer()
            checked_user = await async_get_user(request)
            service_logger.debug(f'get_user cost: {get_user_timer.duration()}')
            return checked_user
        else:
            return None

    token = request.headers.get("Authorization", "")
    if token:
        # AI Doctor 小程序端认证，带 token 过来
        # token 格式：Bearer <token>
        token_split = token.split(" ")
        if len(token_split) == 2 and token_split[0] == "Bearer":
            token = token_split[1]
        else:
            token = None
        if token:
            try:
                identity = jwt.decode(token, service_config.jwt.secret_key, algorithms=['HS256'])
            except jwt.InvalidTokenError:
                return None
            if identity:
                decoded_dict = {
                    "dialog_id": identity["dialog_id"],
                    "treatment_id": identity["treatment_id"]
                }
                service_logger.info(f"ai doctor user({decoded_dict['dialog_id']}/{decoded_dict['treatment_id']}) login successfully")
                return User(**decoded_dict)

    # mock auth 的优先级大于 keycloak 认证
    if service_config.auth.mock_auth:
        return DUMMY_USER
    
    user_info = request.headers.get("X-Userinfo", "")
    if user_info:
        # keycloak 认证
        decoded_bytes = base64.b64decode(user_info)
        decoded_string = decoded_bytes.decode('utf-8')
        decoded_dict = json.loads(decoded_string)
        user_id = decoded_dict.get("authing_id", decoded_dict.get("sub", ""))
        if user_id:
            decoded_dict["id"] = user_id
            preferred_username = decoded_dict.get("preferred_username", "")
            if preferred_username:
                if "company" not in decoded_dict:
                    decoded_dict["company"] = "INF"
                decoded_dict["username"] = preferred_username
                decoded_dict["type"] = UserAuthType.Keycloak.value
                #service_logger.info(f'user decoded_dict={decoded_dict}')
                return User(**decoded_dict)

    else:
        # 小程序端转发 medical_app 请求过来，携带 userinfo 参数
        userinfo_str = request.headers.get("userinfo", None)
        if len(userinfo_str) > 0:
            userinfo_dict = json.loads(userinfo_str)
            # {
            #     "id": user_id,
            #     "username": username,
            #     "company": company,
            #     "groups": [],
            #     "type": "keycloak"
            # }
            if userinfo_dict:
                return User(**userinfo_dict)
    
    return None


def check_user(user: User):
    if user is None or (not hasattr(user, 'id')):
        raise AuthFailedException()

def check_user_dialog_id(user: User, dialog_id: str):
    if user is None or (not hasattr(user, 'dialog_id')):
        raise AuthFailedException()
    if user.dialog_id != dialog_id:
        raise AuthFailedException()
