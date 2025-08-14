import redis
import logging
import os
import traceback
if 'REDIS_HOST' in os.environ:
    redis_host = os.environ['REDIS_HOST']
else:
    redis_host = '0.0.0.0'

redis_conf = {
    "host": redis_host,
    "port": 6379,
    "password": "INFtech123",
    "db": 16,
    "decode_responses": True
}

if redis_host == '0.0.0.0':
    del redis_conf['password']
    redis_conf['db'] = 0


class RedisClient():

    def __init__(self):
        self._redis = redis.Redis(**redis_conf)

    def set(self, key, value):
        self._redis.set(key, value)

    def get(self, key):
        return self._redis.get(key)

    def close(self):
        self._redis.close()


class MessageClient:
    GROUP = 'default'

    def __init__(self,
                 in_channel: str = None,
                 consumer_id: str = None,
                 read_pending: bool = False):
        self._in_channel = in_channel
        self._redis = redis.Redis(**redis_conf)
        self._read_pending = read_pending
        self._consumer_id = consumer_id
        if self._in_channel:
            try:
                self._redis.xgroup_create(name=self._in_channel,
                                          groupname=self.GROUP,
                                          id='0',
                                          mkstream=True)
            except redis.exceptions.ResponseError as e:
                logging.log(logging.DEBUG, f"create consumer group {e}, {traceback.format_exc()}")

    def send(self, msg: dict):
        channel = self._in_channel
        resp = self._redis.xadd(name=channel, fields=msg)
        logging.log(
            logging.DEBUG,
            f"send channel: {channel} message: {msg} with resp:{resp}")
        return resp

    def receive(self):

        def read_msg(last_id, block):
            resp = self._redis.xreadgroup(groupname=self.GROUP,
                                          consumername=self._consumer_id,
                                          streams={self._in_channel: last_id},
                                          count=1,
                                          block=block)
            if len(resp) == 0:
                return None
            logging.log(
                logging.DEBUG,
                f"receive from channel: {self._in_channel} id: {last_id} resp: {resp}"
            )
            key, messages = resp[0]
            #  print('key messages', last_id, key, messages, flush=True)
            if messages:
                assert key == self._in_channel
                return messages[0]
            else:
                return None

        if not self._read_pending:
            rsp = read_msg(0, 1000)
            if rsp:
                logging.log(logging.INFO, rsp)
                return rsp
            else:
                self._read_pending = True

        return read_msg('>', 10)

    def pendings(self, count=1):
        resp = self._redis.xpending_range(name=self._in_channel,
                                          groupname=self.GROUP,
                                          min='-',
                                          max='+',
                                          count=count)
        #if len(resp) > 0:
        #    logging.log(logging.DEBUG, f"Message pendings {resp}")
        return resp

    def ack(self, id) -> None:
        logging.log(logging.DEBUG, f"ack {id}")
        self._redis.xack(self._in_channel, self.GROUP, id)

    def close(self):
        self._redis.close()


def receive_message(channel, read_pending=False):
    client = MessageClient(in_channel=channel,
                           consumer_id=channel,
                           read_pending=read_pending)
    while True:
        messages = client.receive()
        if not messages:
            break
        yield messages
