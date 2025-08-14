import sys
import os

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from worker.process_upload_report import process_upload_report
import unittest

class TestProcessUploadReport(unittest.TestCase):
    
    def test_send_request(self):
        task_id = "67ce97c7c12bcbe7cc2837cc"
        task_params = {
            "dialog_id": "67ce9663127d61d3742c216a",
            "file_name": "wenzhen-2.png",
            "file_type": "image/png",
            "file_oss_key": "home/health/app/user_reports/knowledge_assistant/3dc7c0a4bb1fe0432e015f211cc26de6.png"
        }
        # 测试正常请求
        result = process_upload_report(task_id, task_params)
        print(f"result: {result}")
        self.assertIsNotNone(result)
        self.assertEqual(result, 'completed')


if __name__ == '__main__':
    unittest.main()