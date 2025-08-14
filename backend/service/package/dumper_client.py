from datetime import datetime
import sys, os
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(current_dir)
from service.rpc_definition import knowledge_dump_pb2, knowledge_doc_online_dump_pb2
from util.async_http import async_post, async_proto_get
from util.down_stream_helper import generate_idem_id, DUMMY_IDEM_ID


class DumperClient:
    def __init__(self) -> None:
        return

    def submit(self, idem_id, kb_key, file_key, attrs):
        return

    def list_wiki(self, kb_key, page_size, page_num, in_stages):
        return

    def modify_wiki_state(self, kb_key, doc_key, stage=None):
        return
    
    def query_doc(self, kb_key, doc_key):
        return


class HttpAsyncDumperClient(DumperClient):
    def __init__(self, endpoint: str, tenant_id: str):
        super().__init__()
        self.submit_url = endpoint + "/api/v1/knowledge/dump/doc_online_default/tasks"
        self.list_url = endpoint + "/api/v1/knowledge/dump/doc_online_default/tasks"
        self.modify_url = endpoint + "/api/v1/knowledge/dump/doc_online_default/task-stage"
        self.query_url = endpoint + "/api/v1/knowledge/dump/doc_online_default/tasks/query"
        self.header = {
            "X-TenantID": tenant_id,
            "Content-Type": "application/x-protobuf",
            "Accept": "application/x-protobuf"
        }


    async def query(self, kb_key: str, doc_keys: list):
        self.build_common_header(idem_id=DUMMY_IDEM_ID, operator=kb_key)
        query_task_request = self.build_query_task_request(kb_key, doc_keys)
        proto_data = await async_post(url=self.query_url,
                                      data=query_task_request.SerializeToString(),
                                      headers=self.header,
                                      is_proto=True)
        query_task_result = knowledge_dump_pb2.QueryDocOnlineDumpTasksResponse()
        query_task_result.ParseFromString(proto_data)
        return query_task_result


    async def submit(self, idem_id, kb_key, file_key, attrs=None):
        self.build_common_header(idem_id=idem_id, operator=kb_key)
        create_wiki_request = self.build_create_wiki_request(kb_key, file_key, attrs)
        proto_data = await async_post(url=self.submit_url,
                                      data=create_wiki_request.SerializeToString(),
                                      headers=self.header,
                                      is_proto=True)
        create_wiki_result = knowledge_dump_pb2.CreateDocOnlineDumpTaskResponse()
        create_wiki_result.ParseFromString(proto_data)
        return create_wiki_result


    async def list_wiki(self, kb_key, page_size, page_num, in_stages=None):
        self.build_common_header(DUMMY_IDEM_ID, operator=kb_key)
        list_wiki_request = self.build_list_wiki_task_request(kb_key,
                                                              page_size,
                                                              page_num,
                                                              in_stages)
        proto_resp = await async_proto_get(url=self.list_url,
                                           proto_data=list_wiki_request,
                                           headers=self.header)
        list_wiki_result = knowledge_dump_pb2.ListDocOnlineDumpTasksResponse()
        list_wiki_result.ParseFromString(proto_resp)
        return list_wiki_result


    async def modify_wiki_state(self, kb_key, doc_key, stage=None):
        self.build_common_header(idem_id=generate_idem_id(doc_key), operator=kb_key)
        if stage is None:
            stage = knowledge_doc_online_dump_pb2.Stage.STG_DELETE
        modification_request = self.build_modification_task_request(kb_key,
                                                                    doc_key,
                                                                    stage)
        proto_data = await async_post(url=self.modify_url,
                                      data=modification_request.SerializeToString(),
                                      headers=self.header,
                                      is_proto=True)
        modification_response = knowledge_dump_pb2.ModifyDocOnlineDumpTaskStageResponse()
        modification_response.ParseFromString(proto_data)
        return modification_response


    def build_common_header(self, idem_id, operator):
        self.header.update({
            "X-IdemID": idem_id,
            "X-Operator": operator,
            "X-Request-ID": str(int(datetime.now().timestamp() * 1e9))
        })


    def build_create_wiki_request(self,
                                  kb_key: str,
                                  file_key: str,
                                  attrs: str = None) -> knowledge_dump_pb2.CreateDocOnlineDumpTaskRequest:
        launch_param = knowledge_doc_online_dump_pb2.LaunchParam()
        launch_param.file_key = file_key
        if attrs:
            launch_param.attrs = attrs
        create_request = knowledge_dump_pb2.CreateDocOnlineDumpTaskRequest()
        create_request.param.CopyFrom(launch_param)
        create_request.kb_key = kb_key
        create_request.import_type = knowledge_doc_online_dump_pb2.ImportType.IT_RAWFILE
        return create_request


    def build_list_wiki_task_request(self,
                                     kb_key: str,
                                     page_size: int,
                                     page_num: int,
                                     in_stages) -> knowledge_dump_pb2.ListDocOnlineDumpTasksRequest:
        list_wiki_request = knowledge_dump_pb2.ListDocOnlineDumpTasksRequest()
        list_wiki_request.kb_key = kb_key
        list_wiki_request.page_size = page_size
        list_wiki_request.page_num = page_num
        if in_stages is None or len(in_stages) == 0:
            list_wiki_request.in_stages.extend([knowledge_doc_online_dump_pb2.Stage.STG_ERROR,
                                                knowledge_doc_online_dump_pb2.Stage.STG_READY,
                                                knowledge_doc_online_dump_pb2.Stage.STG_PREPARE,
                                                knowledge_doc_online_dump_pb2.Stage.STG_PARSE,
                                                knowledge_doc_online_dump_pb2.Stage.STG_CHUNK,
                                                knowledge_doc_online_dump_pb2.Stage.STG_ADDDOC])
        else:
            list_wiki_request.in_stages.extend(in_stages)
        return list_wiki_request


    def build_modification_task_request(self,
                                        kb_key: str,
                                        doc_key: str,
                                        stage) -> knowledge_dump_pb2.ModifyDocOnlineDumpTaskStageRequest:
        modification_task_request = knowledge_dump_pb2.ModifyDocOnlineDumpTaskStageRequest()
        modification_task_request.kb_key = kb_key
        modification_task_request.doc_key = doc_key
        modification_task_request.stage = stage
        return modification_task_request


    def build_query_task_request(self, kb_key: str, doc_keys: list) -> knowledge_dump_pb2.QueryDocOnlineDumpTasksRequest:
        query_task_request = knowledge_dump_pb2.QueryDocOnlineDumpTasksRequest()
        query_task_request.kb_key = kb_key
        query_task_request.doc_keys.extend(doc_keys)
        return query_task_request
    

if __name__ == "__main__":

    dumper_client = HttpAsyncDumperClient("http://10.11.131.194:31410", "health")

    async def test_list_wiki():
        result = await dumper_client.list_wiki(kb_key="ka-gujiawei-dev-01", page_size=100, page_num=1)
        print(result)
    
    async def test_query_task():
        result = await dumper_client.query(kb_key="ka-gujiawei-dev-01", doc_keys=["73109ae2-467f-4085-87e8-3c89409f7c31"])
        print(result)

    async def test_download_task_file():
        result = await dumper_client.query(kb_key="ka-gujiawei-dev-01", doc_keys=["73109ae2-467f-4085-87e8-3c89409f7c31"])
        parsed_doc_key = result.data.tasks[0].parsed_doc_key
        print(f"parsed_doc_key={parsed_doc_key}")
        
        from service.package.file_service_client import HttpAsyncFileServiceClient
        file_service_client=HttpAsyncFileServiceClient(endpoint="http://10.11.131.194:30157")
        content = await file_service_client.download_file(operator="ka-gujiawei-dev-01", link=None, file_key=parsed_doc_key)
        print(f"content={content}")
    
    import asyncio
    #asyncio.run(test_list_wiki())
    asyncio.run(test_download_task_file())