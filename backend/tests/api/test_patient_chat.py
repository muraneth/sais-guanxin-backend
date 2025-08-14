import unittest
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import jwt
from service.config.config import service_config


class TestPatientChat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 初始化 FastAPI 测试客户端
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)
    
    def setUp(self):
        # 生成测试用的 token
        self.token = jwt.encode(
            {
                'dialog_id': "test_dialog",
                'treatment_id': "test_treatment",
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)
            },
            service_config.jwt.secret_key,
            algorithm='HS256'
        )
        
        self.dialog_manager_patcher = patch('service.api.ai_doctor.patient_chat.dialog_manager')
        self.mock_dialog_manager = self.dialog_manager_patcher.start()
        # 配置 dialog_manager 的方法
        self.mock_dialog_manager.get_dialog_messages_context = AsyncMock(return_value=[
            {"query": "测试问题", "answer": "测试回答"},
            {"type": "report", "file_oss_key": "test_key"}
        ])
        self.mock_dialog_manager.new_ai_doctor_dialog = AsyncMock(return_value="new_test_dialog")
        self.mock_dialog_manager.upsert_message = AsyncMock(return_value="new_message_id")
        self.mock_dialog_manager.delete_message = AsyncMock()
        
        self.task_manager_patcher = patch('service.api.ai_doctor.patient_chat.task_manager')
        self.mock_task_manager = self.task_manager_patcher.start()
        self.mock_task_manager.add_task = MagicMock(return_value="test_task_id")
        self.mock_task_manager.update_task_status = AsyncMock()

        self.oss_client_patcher = patch('service.api.ai_doctor.patient_chat.oss_client')
        self.mock_oss_client = self.oss_client_patcher.start()
        self.mock_oss_client.get_oss_policy.return_value = {"policy": "dummy_policy"}
        self.mock_oss_client.get_file_url = MagicMock(return_value="https://dummy.download.url")
        

    def tearDown(self):
        self.dialog_manager_patcher.stop()
        self.task_manager_patcher.stop()
        self.oss_client_patcher.stop()


    def test_new_treatment_chat_without_dialog_id(self):
        # 没有传入 dialog_id 时，应生成新的 dialog_id 且返回空对话历史
        response = self.client.post("/api/doctor/new_treatment_chat", json={
            "treatment_id": "test_treatment"
        }, headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("dialog_id", data)
        self.assertEqual(data["dialog_id"], "new_test_dialog")
        self.assertEqual(data["chat_history"], [])


    def test_new_treatment_chat_with_dialog_id(self):
        # 传入 dialog_id 时，应返回对应的对话历史
        response = self.client.post("/api/doctor/new_treatment_chat", json={
            "treatment_id": "test_treatment",
            "dialog_id": "test_dialog"
        }, headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("chat_history", data)
        # 根据模拟数据，chat_history 长度应大于 0
        self.assertTrue(len(data["chat_history"]) > 0)



if __name__ == '__main__':
    unittest.main()