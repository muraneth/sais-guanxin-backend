import os.path
import datetime
from datetime import timedelta

from minio import Minio
from minio.datatypes import PostPolicy

from util.logger import service_logger
from service.config.config import service_config

# 过期时间设置为 3 年
expire_time = timedelta(hours=1)

class MinioClient():
    def __init__(self, endpoint, access_key, access_secret, bucket, target_path, secure):
        # self.endpoint 返回给前端的 host 地址
        self.endpoint = endpoint
        # 移除 endpoint 中的 http:// 前缀
        if endpoint.startswith('http://'):
            endpoint = endpoint[7:]
        elif endpoint.startswith('https://'):
            endpoint = endpoint[8:]
            
        #print(f"endpoint: {endpoint}, access_key: {access_key}, access_secret: {access_secret}, bucket: {bucket}, target_path: {target_path}")
        self.minio_client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=access_secret,
            secure=secure
        )
        self.target_path = target_path
        self.bucket = bucket
        
    def get_file_url(self, file_oss_key, external=False):
        """获取文件的下载URL"""
        try:
            url = self.minio_client.presigned_get_object(
                self.bucket,
                file_oss_key,
                expires=expire_time
            )
            if external and self.endpoint.startswith("https://") and url.startswith("http://"):
                url = url.replace("http://", "https://")
            return url
        except Exception as e:
            service_logger.error(f"Failed to get file URL: {str(e)}")
            raise

    def get_policy(self):
        """获取上传策略信息"""
        try:
            # 创建 PostPolicy 对象
            policy = PostPolicy(
                self.bucket,
                datetime.datetime.now() + datetime.timedelta(seconds=3600)
            )

            # 设置 key 的前缀
            policy.add_starts_with_condition("key", self.target_path)
            # 设置文件大小范围（0-20MB）
            policy.add_content_length_range_condition(0, 20 * 1024 * 1024)

            # 生成 policy 和签名字段
            form_data = self.minio_client.presigned_post_policy(policy)
            form_data['host'] = self.endpoint
            form_data['bucket'] = self.bucket
            form_data['dir'] = self.target_path
            form_data['storage_type'] = 'minio'
            return form_data
        except Exception as e:
            service_logger.error(f"Failed to get policy: {str(e)}")
            raise


def get_iso_8601(expire):
    """获取 ISO 8601 格式的时间"""
    gmt = datetime.datetime.utcfromtimestamp(expire).isoformat()
    gmt += 'Z'
    return gmt

# 创建全局 MinIO 客户端实例
minio_client = MinioClient(
    endpoint=service_config.minio.endpoint, 
    access_key=service_config.minio.access_key, 
    access_secret=service_config.minio.access_secret,
    bucket=service_config.minio.bucket, 
    target_path=service_config.minio.target_path,
    secure=service_config.minio.secure
)

if __name__ == '__main__':
    #print(minio_client.get_policy())
    print(minio_client.get_file_url("storage/1749801280857-20250228-165642.jpeg"))
