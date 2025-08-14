from service.exceptions.file_service_exceptions import ListFilesException
from service.package.dumper_client import DumperClient
from util.model_types import RpcStatusCode


class FileAdminister:
    def __init__(self,
                 max_files_per_wiki: int,
                 dumper_client: DumperClient = None) -> None:
        self.max_files_per_wiki = max_files_per_wiki
        self.dumper = dumper_client
        return

    async def is_full(self, kb_key) -> bool:
        list_result = await self.dumper.list_wiki(kb_key=kb_key,
                                                  page_num=200,
                                                  page_size=1,
                                                  in_stages=None)
        if list_result.code != RpcStatusCode.Success:
            raise ListFilesException("failed to list docs", list_result.code)
        cnt = list_result.data.tasks_cnt
        return cnt >= self.max_files_per_wiki
