from datetime import datetime
from typing import List

import pytz
from fastapi import APIRouter, Depends, UploadFile
from fastapi.params import File, Form
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from service.config.config import service_config
from service.exceptions import BackendServiceExceptionReasonCode
from service.exceptions.file_service_exceptions import DownloadFileException, DeleteDocException, ListFilesException, \
    UploadFileException, CreateDumpTaskException
from service.package.auth import authenticate, check_user
from service.package.dumper_client import HttpAsyncDumperClient
from service.package.file_service_client import HttpAsyncFileServiceClient
from service.package.fille_administer import FileAdminister
from util.execution_context import ExecutionContext
from util.timer import Timer
from util.model_types import User, AppResponse, StatusCode, RpcStatusCode, Wiki

router = APIRouter(
    prefix="/api/self"
)
file_client = HttpAsyncFileServiceClient(service_config.file_service.url)
dumper_client = HttpAsyncDumperClient(service_config.dump_service.url, service_config.tenant_id)
file_administer = FileAdminister(service_config.dump_service.max_files_per_wiki, dumper_client)
LACK_FILE_FORMAT_ERROR = JSONResponse(content={"code": 1, "message": "Lack file format"}, status_code=400)
FULL_KNOWLEDGE_BASE_ERROR = JSONResponse(content={"code": 1, "message": "Knowledge base is full"}, status_code=400)
BAD_FILE_FORMAT_ERROR = JSONResponse(content={"code": 1, "message": "Bad file type"}, status_code=400)


@router.post("/upload")
async def upload_file(idem_id: str = Form(...),
                      desc: str = Form(...),
                      file: UploadFile = File(...),
                      requester: User = Depends(authenticate)):
    timer = Timer()
    # 鉴权
    check_user(requester)
    # 判断是否是 PDF 格式
    file_first_content = await file.read(1024)
    if not file_first_content.startswith(b'%PDF-'):
        raise UploadFileException(BackendServiceExceptionReasonCode.Invalid_Format.value,
                                  ExecutionContext.current())
    await file.seek(0)
    file_content = await file.read()
    # 判断知识库是否已满
    is_full = await file_administer.is_full(requester.id)
    if is_full:
        raise UploadFileException(BackendServiceExceptionReasonCode.Quota_Exceeded.value,
                                  ExecutionContext.current())
    # 上传文件
    file_upload_response = await file_client.upload_file(user_id=requester.id,
                                                         file_content=file_content,
                                                         file_name=file.filename,
                                                         idem_id=idem_id,
                                                         desc=desc,
                                                         attrs=None)
    if file_upload_response["code"] != RpcStatusCode.Success:
        raise UploadFileException(file_upload_response["code"],
                                  ExecutionContext.current())
    # dump
    file_key = file_upload_response["data"]["file"]["key"]
    create_wiki_response = await dumper_client.submit(idem_id, requester.id, file_key, None)
    if create_wiki_response.code != RpcStatusCode.Success:
        raise CreateDumpTaskException(file_key, create_wiki_response.code,
                                      ExecutionContext.current())
    else:
        return JSONResponse({
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: "upload file ok",
            AppResponse.latency: timer.duration(),
            "doc_key": create_wiki_response.data.task.doc_key
        })


@router.get("/list")
async def list_files(request: Request, requester: User = Depends(authenticate)):
    timer = Timer()
    check_user(requester)
    list_response = await dumper_client.list_wiki(kb_key=requester.id,
                                                  page_size=200,
                                                  page_num=1)
    if list_response.code != RpcStatusCode.Success:
        raise ListFilesException("failed to list docs", list_response.code,
                                 ExecutionContext.current())
    file_keys = []
    for each in list_response.data.tasks:
        file_keys.append(each.raw_file_key)
    if file_keys:
        batch_response = await file_client.batch_query_files(operator=requester.id, file_keys=file_keys)
        if batch_response.code != RpcStatusCode.Success:
            raise ListFilesException("failed to batch query files",
                                     batch_response.code,
                                     ExecutionContext.current())
        files_after_merge = merge_list_from_file_and_dump(list_response,
                                                          batch_response,
                                                          request.query_params.get('keyword'))
        return JSONResponse({
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: "list wiki state ok",
            AppResponse.latency: timer.duration(),
            "data": files_after_merge
        })
    else:
        return JSONResponse({
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: "list wiki state ok",
            AppResponse.latency: timer.duration(),
            "data": []
        })


@router.post("/delete")
async def delete_file(request: Request, requester: User = Depends(authenticate)):
    timer = Timer()
    check_user(requester)
    data = await request.json()
    stage = data.get("stage", None)
    doc_key = data.get("doc_key")
    delete_response = await dumper_client.modify_wiki_state(requester.id,
                                                            data.get("doc_key"),
                                                            stage)
    if delete_response.code == RpcStatusCode.Success:
        msg = "delete ok"
        file_key = delete_response.data.task.raw_file_key
        await file_client.delete_file(requester.id, file_key)
        return JSONResponse({
            AppResponse.status_code: StatusCode.Success,
            AppResponse.message: msg,
            AppResponse.latency: timer.duration(),
        })
    else:
        raise DeleteDocException(doc_key, delete_response.code, ExecutionContext.current())


@router.get("/download")
async def download_file(request: Request, requester: User = Depends(authenticate)):
    check_user(requester)
    file_key = request.query_params.get("file_key", None)
    link = request.query_params.get("link", None)
    file_content = await file_client.download_file(link=link,
                                                   file_key=file_key,
                                                   operator=requester.id)
    media_type = "application/octet-stream"
    file_format = request.query_params.get("file_format")
    if file_format is None:
        raise DownloadFileException(file_key,
                                    BackendServiceExceptionReasonCode.Lack_of_Format.value,
                                    ExecutionContext.current())
    if file_format.lower() == "pdf":
        media_type = "application/pdf"
    elif file_format.lower() == "markdown":
        media_type = "text/markdown"
    return Response(content=file_content, media_type=media_type, headers={"Content-Length": str(len(file_content))})


def merge_list_from_file_and_dump(dump_list_result, file_batch_response, keyword) -> List[dict]:
    wikis = []
    if keyword is None:
        keyword = ""
    for each in file_batch_response.data.files:
        wiki = Wiki()
        wiki.file_name = each.name
        wiki.file_key = each.key
        wiki.desc = each.desc
        find_doc_key_and_stage(wiki, each.key, dump_list_result)
        if wiki.doc_key and wiki.file_name.find(keyword) != -1:
            wikis.append(wiki.__dict__)
    return wikis


def find_doc_key_and_stage(wiki, file_key, dump_list_result):
    for each in dump_list_result.data.tasks:
        if each.raw_file_key == file_key and each.stage <= 5:
            wiki.doc_key = each.doc_key
            if 2 <= each.stage <= 5:
                wiki.stage = 2
            else:
                wiki.stage = each.stage
            wiki.stage_hint = each.stage_hint.msg
            wiki.create_time = convert_2_beijing_datetime(each.create_ts)
            return


def convert_2_beijing_datetime(ts):
    utc_datetime = datetime.utcfromtimestamp(ts)
    utc_timezone = pytz.timezone("UTC")
    utc_datetime = utc_timezone.localize(utc_datetime)
    beijing_timezone = pytz.timezone("Asia/Shanghai")
    beijing_datetime = utc_datetime.astimezone(beijing_timezone)
    return beijing_datetime.strftime("%Y-%m-%d %H:%M:%S")
