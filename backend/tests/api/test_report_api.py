import sys
import os

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from service.repository.mongo_task_manager import task_manager
from service.repository.mongo_dialog_manager import dialog_manager
from util.model_types import StatusCode

client = TestClient(app)

class TestReportAPI(unittest.TestCase):
    def setUp(self):
        # 重置mock
        task_manager.add_task = MagicMock()
        dialog_manager.upsert_message = MagicMock()
        task_manager.get_by_task_id = MagicMock()

    def test_submit_report_success(self):
        # 测试正常提交报告
        test_data = {
            "dialog_id": "test_dialog",
            "file_name": "report.pdf",
            "file_type": "pdf",
            "file_oss_key": "oss_key_123",
            "mode": "search"
        }
        
        # Mock task_manager返回task_id
        task_manager.add_task.return_value = "task_123"
        
        response = client.post("/api/submit_report", json=test_data)
        
        print(f"response: {response.json()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], StatusCode.Success)
        self.assertEqual(response.json()["message_id"], "task_123")
        
        # 验证task_manager被正确调用
        task_manager.add_task.assert_called_once_with(
            task_type="upload_report",
            params={
                "dialog_id": "test_dialog",
                "file_name": "report.pdf",
                "file_type": "pdf",
                "file_oss_key": "oss_key_123"
            }
        )

    def test_submit_report_missing_fields(self):
        # 测试缺少必要字段
        test_data = {
            "file_name": "report.pdf",
            "file_type": "pdf"
        }
        
        response = client.post("/api/submit_report", json=test_data)
        print(f"response: {response.json()}")
        self.assertEqual(response.status_code, 200)  # FastAPI 参数验证错误
        self.assertEqual(response.json()["code"], StatusCode.BadRequest)
        self.assertEqual(response.json()["msg"], "missing required fields")

    def test_submit_report_task_failed(self):
        # 测试任务创建失败
        test_data = {
            "dialog_id": "test_dialog",
            "file_name": "report.pdf",
            "file_type": "pdf",
            "file_oss_key": "oss_key_123"
        }
        
        # Mock task_manager返回None
        task_manager.add_task.return_value = None
        
        response = client.post("/api/submit_report", json=test_data)
        print(f"response: {response.json()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], StatusCode.InternalError)
        self.assertEqual(response.json()["msg"], "submit report fail")

    def test_check_report_process_success(self):
        # 测试正常查询报告进度
        test_task = {
            "status": "processing",
            "params": {
                "file_name": "report.pdf",
                "file_type": "pdf",
                "file_oss_key": "oss_key_123"
            }
        }
        
        # Mock task_manager返回任务
        task_manager.get_by_task_id.return_value = test_task
        
        response = client.get("/api/check_report_process?report_id=task_123")
        print(f"response: {response.json()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], StatusCode.Success)
        self.assertEqual(response.json()["data"]["status"], "processing")
        self.assertEqual(response.json()["data"]["params"]["file_name"], "report.pdf")

    def test_check_report_process_not_found(self):
        # 测试查询不存在的任务
        task_manager.get_by_task_id.return_value = None
        
        response = client.get("/api/check_report_process?report_id=invalid_id")
        print(f"response: {response.json()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], StatusCode.InternalError)
        self.assertEqual(response.json()["msg"], "task not found")

    def test_check_report_process_missing_id(self):
        # 测试缺少report_id参数
        response = client.get("/api/check_report_process")
        print(f"response: {response.json()}")
        self.assertEqual(response.status_code, 200)  # FastAPI 参数验证错误
        self.assertEqual(response.json()["code"], StatusCode.BadRequest)
        self.assertEqual(response.json()["msg"], "missing required fields")

if __name__ == '__main__':
    unittest.main()