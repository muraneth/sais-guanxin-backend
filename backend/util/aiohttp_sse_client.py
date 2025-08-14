#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 代码来源：https://github.com/ebraminio/aiosseclient
# 基于该项目进行了少部分修正
# 
#import sys, os
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re
import aiohttp
import asyncio
import json
from typing import List, Dict, Optional, AsyncGenerator, Final

from util.logger import algo_logger

_SSE_LINE_PATTERN: Final[re.Pattern] = re.compile('(?P<name>[^:]*):?( ?(?P<value>.*))?')

# Good parts of the below class is adopted from:
#   https://github.com/btubbs/sseclient/blob/db38dc6/sseclient.py
class Event:
    '''The object created as the result of received events'''
    data: str
    event: str
    id: Optional[str]
    retry: Optional[bool]
    data_json: dict

    def __init__(
        self,
        data: str = '',
        event: str = 'message',
        id: Optional[str] = None,
        retry: Optional[bool] = None
    ):
        self.data = data
        self.event = event
        self.id = id
        self.retry = retry
        self.data_json = {}

    def dump(self) -> str:
        '''Serialize the event object to a string'''
        lines = []
        if self.id:
            lines.append(f'id: {self.id}')

        # Only include an event line if it's not the default already.
        if self.event != 'message':
            lines.append(f'event: {self.event}')

        if self.retry:
            lines.append(f'retry: {self.retry}')

        lines.extend(f'data: {d}' for d in self.data.split('\n'))
        return '\n'.join(lines) + '\n\n'

    def encode(self) -> bytes:
        '''Serialize the event object to a bytes object'''
        return self.dump().encode('utf-8')

    @classmethod
    def parse(cls, raw_lines: list):
        '''
        Given a possibly-multiline string representing an SSE message, parse it
        and return a Event object.
        '''
        msg = cls()
        for line in raw_lines:
            m = _SSE_LINE_PATTERN.match(line)
            if m is None:
                # Malformed line.  Discard but warn.
                algo_logger.warning('Invalid SSE line: %s', line)
                continue

            name = m.group('name')
            if name == '':
                # line began with a ':', so is a comment.  Ignore
                continue
            value = m.group('value')

            if name == 'data':
                # If we already have some data, then join to it with a newline.
                # Else this is it.
                if msg.data:
                    msg.data = f'{msg.data}\n{value}'
                else:
                    msg.data = value
            elif name == 'event':
                msg.event = value
            elif name == 'id':
                msg.id = value
            elif name == 'retry':
                msg.retry = int(value)

        msg.data_json = json.loads(msg.data)
        return msg

    def __str__(self) -> str:
        return self.data


async def aiosseclient(
    url: str,
    data: dict,
    last_id: Optional[str] = None,
    valid_http_codes: List[int] = [200, 301, 307],
    exit_events: List[str] = [],
    timeout_total: Optional[float] = 5 * 60,
    headers: Optional[Dict[str, str]] = {},
) -> AsyncGenerator[Event, None]:
    '''aiohttp sse client'''
    # The SSE spec requires making requests with Cache-Control: nocache
    headers['Cache-Control'] = 'no-cache'
    headers['Accept'] = 'text/event-stream' # Optional

    if last_id:
        headers['Last-Event-ID'] = last_id

    # Override default timeout of 5 minutes
    timeout = aiohttp.ClientTimeout(total=timeout_total, connect=2*60, sock_connect=2*60, sock_read=2*60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        response = await session.post(url, headers=headers, json=data)
        if response.status not in valid_http_codes:
            algo_logger.error('Invalid HTTP response.status: %s', response.status)
            raise RuntimeError("Invalid HTTP response.status")
        ## Fix Bug: "ValueError: Chunk too big"
        response.content._high_water = response.content._low_water * 10240
        lines = []
        async for line in response.content:
            line = line.decode('utf8')
            if line in {'\n', '\r', '\r\n'}:
                if lines[0] == ':ok\n':
                    lines = []
                    continue

                current_event = Event.parse(lines)
                yield current_event
                if current_event.event in exit_events:
                    algo_logger.info("final_lines|lines=%s, current_event=%s", ''.join(lines), current_event)
                    await session.close()
                lines = []
            else:
                lines.append(line)


# 测试
if __name__ == '__main__':
    
    async def call():
        async for event in aiosseclient(
            url='http://10.21.72.159:32737/assistant/rag_chat',
            data = {
                "config": {},
                "sources": [],
                "chat_history":[
                    {
                        "role": "user",
                        "content": "感冒退热颗粒适合小孩子使用吗？"
                    }
                ]
            },
        ):
            print(f"rag response event.data_json={event.data_json}")
            print('--------------------------------------------------------------')
            print()
    
    asyncio.run(call())