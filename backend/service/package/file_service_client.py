import datetime
from typing import Optional, List

import aiohttp
from google.protobuf import json_format

from service.config.config import service_config
from service.rpc_definition import file_service_pb2
from util.async_http import async_post, async_get, async_proto_delete
from util.down_stream_helper import DUMMY_IDEM_ID, generate_idem_id


class FileServiceClient:
    def __init__(self) -> None:
        return

    def upload_file(self, user_id,
                    file_content,
                    file_name,
                    idem_id,
                    desc,
                    attrs=None) \
            -> Optional[file_service_pb2.UploadFileByPostResponse]:
        pass

    def batch_query_files(self, operator, file_keys: List[str]):
        pass

    def download_file(self, operator, link, file_key):
        pass

    def delete_file(self, operator, file_key):
        pass

    def get_temp_download_link(self,
                               idem_id,
                               operator,
                               file_key) \
            -> Optional[file_service_pb2.TempDownloadLinkResponse]:
        pass


class HttpAsyncFileServiceClient(FileServiceClient):
    def __init__(self, endpoint) -> None:
        super().__init__()
        self.upload_url = endpoint + "/api/v1/filesvc/collections/{}/files"
        self.download_url = endpoint + "/api/v1/filesvc/files/{}"
        self.batch_query_url = endpoint + "/api/v1/filesvc/files/query"
        self.delete_url = endpoint + "/api/v1/filesvc/files/{}"
        self.temp_link_download_url = endpoint + "/api/v1/filesvc/files/{}/tmplink"
        self.header = {}

    async def upload_file(self,
                          user_id,
                          file_content,
                          file_name,
                          idem_id,
                          desc,
                          attrs=None) \
            -> Optional[file_service_pb2.UploadFileByPostResponse]:
        self.build_common_header(idem_id=idem_id,
                                 operator=user_id,
                                 is_proto=False)
        request_data = self.build_upload_request(user_id, desc, attrs)
        data = aiohttp.FormData(charset="utf-8", quote_fields=False)
        data.add_field('create_param', json_format.MessageToJson(request_data.create_param))
        data.add_field('create_coll_if_need', str(request_data.create_coll_if_need))
        if request_data.attrs:
            data.add_field('attrs', request_data.attrs)
        if request_data.desc:
            data.add_field('desc', request_data.desc)

        data.add_field('uploadfile', file_content, filename=file_name)
        result = await async_post(url=self.upload_url.format(request_data.coll_key),
                                  data=data,
                                  headers=self.header)
        return result

    async def batch_query_files(self, operator, file_keys: List[str]):
        self.build_common_header(idem_id=DUMMY_IDEM_ID,
                                 operator=operator,
                                 is_proto=True)
        batch_request = self.build_batch_request(file_keys)
        proto_data = await async_post(url=self.batch_query_url,
                                      headers=self.header,
                                      data=batch_request.SerializeToString(),
                                      is_proto=True)
        batch_response = file_service_pb2.QueryFileMetasResponse()
        batch_response.ParseFromString(proto_data)
        return batch_response

    async def delete_file(self, operator, file_key):
        self.build_common_header(idem_id=generate_idem_id(file_key),
                                 operator=operator,
                                 is_proto=True)
        proto_data = await async_proto_delete(url=self.delete_url.format(file_key),
                                              headers=self.header)
        delete_response = file_service_pb2.DeleteFileResponse()
        delete_response.ParseFromString(proto_data)
        return delete_response

    async def download_file(self, link, operator, file_key):
        self.build_common_header(idem_id=DUMMY_IDEM_ID,
                                 operator=operator,
                                 is_proto=False)
        if link:
            result = await async_get(url=link,
                                     json=None,
                                     json_format=False)
        else:
            result = await async_get(url=self.download_url.format(file_key),
                                     json=None,
                                     json_format=False,
                                     headers=self.header)
        return result

    async def get_temp_download_link(self,
                                     idem_id,
                                     operator,
                                     file_key) \
            -> Optional[file_service_pb2.TempDownloadLinkResponse]:
        self.build_common_header(idem_id=idem_id, operator=operator, is_proto=True)
        download_link_request = file_service_pb2.TempDownloadLinkRequest()
        download_link_request.key = file_key
        download_link_request.expire_dur_s = 15_768_000
        proto_data = await async_post(url=self.temp_link_download_url.format(file_key),
                                      headers=self.header,
                                      data=download_link_request.SerializeToString(),
                                      is_proto=True)
        download_link_response = file_service_pb2.TempDownloadLinkResponse()
        download_link_response.ParseFromString(proto_data)
        return download_link_response

    def build_upload_request(self,
                             user_id: str,
                             desc: str = None,
                             attrs: str = None) -> file_service_pb2.UploadFileByPostRequest:
        upload_request = file_service_pb2.UploadFileByPostRequest()
        coll_key = user_id
        create_param = file_service_pb2.CreateCollectionParam()
        create_param.name = user_id
        create_param.owner_id = user_id

        upload_request.create_param.CopyFrom(create_param)
        upload_request.coll_key = coll_key
        upload_request.create_coll_if_need = True
        if desc:
            upload_request.desc = desc
        if attrs:
            upload_request.attrs = attrs
        return upload_request

    def build_batch_request(self, file_keys: List[str]) -> file_service_pb2.QueryFileMetasRequest:
        batch_request = file_service_pb2.QueryFileMetasRequest()
        batch_request.keys.extend(file_keys)
        return batch_request

    def build_common_header(self, idem_id, operator: str, is_proto=False):
        self.header.clear()
        self.header.update({
            "X-TenantID": service_config.tenant_id,
            "X-IdemID": str(idem_id),
            "X-Request-ID": str(int(datetime.datetime.now().timestamp() * 1e9)),
            "X-Operator": operator,
            "Accept": "application/json"
        })
        if is_proto:
            self.header.update({
                "Content-Type": "application/x-protobuf",
                "Accept": "application/x-protobuf"
            })
