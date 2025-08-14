import os.path
from typing import Tuple
import oss2
import time
import datetime
import json
import base64
import hmac
from hashlib import sha1 as sha

from util.logger import service_logger
from service.config.config import service_config

MAX_FILE_SIZE = service_config.oss.max_file_size if service_config.oss.max_file_size else 50 * 1024 * 1024
endpoint=service_config.oss.endpoint
access_key=service_config.oss.access_key
access_secret=service_config.oss.access_secret
bucket = service_config.oss.bucket
target_path = service_config.oss.target_path
cdn_host = service_config.oss.cdn_host

host = '{}.{}'.format(bucket, endpoint)
expire_time = 60 * 60 * 24 * 365 * 3

# 指定Header。
headers = dict()
# 填写Object的versionId。
headers["versionId"] = "CAEQARiBgID8rumR2hYiIGUyOTAyZGY2MzU5MjQ5ZjlhYzQzZjNlYTAyZDE3****"


class Oss():

    def __init__(self, target_path):
        self.oss_auth = oss2.Auth(access_key, access_secret)
        self.oss_bucket = oss2.Bucket(self.oss_auth, endpoint, bucket)
        self.target_path = target_path
    
    def get_file_url(self, file_oss_key):
        url = self.oss_bucket.sign_url(
            'GET',
            file_oss_key,
            expires=expire_time,
            slash_safe=True,
            headers=headers
        )
        return url
    
    def get_oss_policy(self):
        now = int(time.time())
        expire_syncpoint = now + expire_time
        expire = get_iso_8601(expire_syncpoint)
        upload_dir = target_path

        policy_dict = {}
        policy_dict['expiration'] = expire
        condition_array = []
        array_item = []
        array_item.append('starts-with')
        array_item.append('$key')
        array_item.append(upload_dir)
        condition_array.append(array_item)
        policy_dict['conditions'] = condition_array
        policy = json.dumps(policy_dict).strip()
        policy_encode = base64.b64encode(policy.encode())
        h = hmac.new(access_secret.encode(), policy_encode, sha)
        sign_result = base64.encodebytes(h.digest()).strip()

        token_dict = {}
        token_dict['storage_type'] = 'oss'
        token_dict['accessid'] = access_key
        token_dict['host'] = 'https://' + host
        token_dict['policy'] = policy_encode.decode()
        token_dict['signature'] = sign_result.decode()
        token_dict['expire'] = expire_syncpoint
        token_dict['dir'] = upload_dir
        return token_dict


def get_iso_8601(expire):
    gmt = datetime.datetime.utcfromtimestamp(expire).isoformat()
    gmt += 'Z'
    return gmt

oss_client = Oss(target_path=target_path)
