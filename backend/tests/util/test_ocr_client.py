import sys
import os

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from util.ocr_client import ocr_client, zuoyi_client
from util.oss import oss_client
import unittest

class TestOcrClient(unittest.TestCase):
    
    def setUp(self):
        self.file_oss_key = "home/health/app/user_reports/knowledge_assistant/7bd2263b8a6bcdaf8a3209482dc3328b.png"
        #self.file_url = oss_client.get_file_url(self.file_oss_key)
        self.file_url = os.path.join(os.path.dirname(__file__), 'test_data', 'test_blood.png')
        self.file_url = "http://inf-alpha.oss-cn-wulanchabu.aliyuncs.com/home/health/app/user_reports/knowledge_assistant/b038d2df22dd8b199d83a06f1c27e556.jpeg?OSSAccessKeyId=LTAI5tLkvznVfvAQbJHwkYBK&Expires=1836202532&Signature=5Uvv1vTgI%2FvQV0Lj3P0hjrm6mwA%3D"
        self.client = ocr_client
        #self.client = zuoyi_client
    
    def test_send_request(self):
        print(f"file_url: {self.file_url}")
        # 测试正常请求
        result = self.client.process_image(self.file_url)
        self.assertIsNotNone(result)
        print(f"process_image result: {result}")


if __name__ == '__main__':
    unittest.main()