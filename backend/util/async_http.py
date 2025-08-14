from urllib.parse import urlencode

import aiohttp
import traceback
from metrics.meter_key import MeterKey
from metrics.meters import record_latency
from metrics.metrics import FIRST_TOKEN_LATENCY_FROM_LLM
from service.config.config import service_config
from service.config.config import config
from util.logger import service_logger
from util.timer import Timer
from util.model_types import ServiceException, StatusCode

default_request_timeout = service_config.request_time
llm_spliter: bytes = config.llm_spliter.encode()


async def async_get(url, json, timeout=default_request_timeout, auth: tuple[str, str] = None,
                    json_format: bool = True, headers=None):
    timer = Timer()
    timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        auth = aiohttp.BasicAuth(auth[0], auth[1]) if auth else None
        async with session.get(url, json=json, auth=auth, headers=headers) as rsp:
            if json_format:
                ret = await rsp.json()
            else:
                ret = await rsp.read()
            service_logger.info(f'GET {url} [status:{rsp.status} duration:{timer.duration()}s]')
            if rsp.status != 200:
                service_logger.warning(f"get downstream error, url: {url}, json: {json}")
                raise ServiceException(StatusCode.InternalError, f"search failed with {rsp}")
            return ret


async def async_post(url, timeout=default_request_timeout, auth: tuple[str, str] = None, headers=None,
                     data=None, json=None, is_proto=False):
    if headers is None:
        headers = {}
    timer = Timer()
    timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        auth = aiohttp.BasicAuth(auth[0], auth[1]) if auth else None
        async with session.post(url, json=json, auth=auth, headers=headers, data=data) as rsp:
            if is_proto:
                ret = await rsp.read()
            else:
                ret = await rsp.json()
            service_logger.info(f'POST {url} [status:{rsp.status} duration:{timer.duration()}s]')
            if rsp.status != 200:
                service_logger.warning(f"post downstream error, url: {url}, json: {json}")
                raise ServiceException(StatusCode.InternalError, f"search failed with {rsp}")
            return ret


async def async_proto_get(url, proto_data, headers, timeout=default_request_timeout, auth: tuple[str, str] = None):
    timer = Timer()
    url_with_params = build_url_proto(url, proto_data)
    timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        auth = aiohttp.BasicAuth(auth[0], auth[1]) if auth else None
        async with session.get(url_with_params, auth=auth, headers=headers) as rsp:
            ret = await rsp.read()
            service_logger.info(f"Proto get {url_with_params} [status:{rsp.status} duration:{timer.duration()}s]")
            return ret


async def async_proto_delete(url, headers, timeout=default_request_timeout, auth: tuple[str, str] = None):
    timer = Timer()
    timeout = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.delete(url, auth=auth, headers=headers) as rsp:
            ret = await rsp.read()
            service_logger.info(f"proto delete {url} [status:{rsp.status} duration:{timer.duration()}s]")
            return ret


async def async_stream_post(url, json, timeout=default_request_timeout, auth: tuple[str, str] = None, headers=None):
    timer = Timer()
    timeout = aiohttp.ClientTimeout(total=timeout)
    first_chunk = True
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, auth=auth, json=json) as response:
            #service_logger.info(f"url = {url}, headers = {headers}, auth = {auth}, json = {json}")
            if response.status != 200:
                service_logger.error(f'STREAM POST {url} [status:{response.status} duration:{timer.duration()}s] ')
                raise ServiceException(StatusCode.InternalError, f"request failed with {response}")
            chunks = []
            try:
                async for chunk, b in response.content.iter_chunks():
                    #service_logger.info(f"chunk = {chunk}")
                    if b'\n\n' in chunk:
                        parts = chunk.split(b'\n\n')
                        for part in parts:
                            chunks.append(part)
                            output = b''.join(chunks)
                            chunks = []
                            if len(output) == 0:
                                continue
                            assert output.startswith(llm_spliter)
                            if first_chunk:
                                record_latency(MeterKey(async_stream_post.__qualname__, async_stream_post.__name__),
                                               FIRST_TOKEN_LATENCY_FROM_LLM,
                                               timer.duration())
                                first_chunk = False
                            yield output[len(llm_spliter):].decode()
                    else:
                        chunks.append(chunk)

                output = b''.join(chunks)
                if len(output) > 0:
                    assert output.startswith(llm_spliter)
                    yield output[len(llm_spliter):].decode()
            except Exception as e:
                service_logger.error(f'async_stream_post exception: {e}, {traceback.format_exc()}') 
            finally:
                await session.close()


def build_url_proto(url: str, proto_data) -> str:
    fields_names_and_values = get_fields_names_and_values(proto_data)
    query_params = {}
    for field_name, info in fields_names_and_values.items():
        query_params[field_name] = str(info['value'])
    url_with_params = f"{url}?{urlencode(query_params)}"
    return url_with_params


def get_fields_names_and_values(proto_data):
    fields_names_and_values = {}
    for field_descriptor, value in proto_data.ListFields():
        field_name = field_descriptor.name
        field_number = field_descriptor.number

        fields_names_and_values[field_name] = {
            'number': field_number,
            'value': value,
        }

    return fields_names_and_values
