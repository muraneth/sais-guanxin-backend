import sys
import os
import time

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
from bson.objectid import ObjectId
from mongomock import MongoClient
from service.repository.mongo_task_manager import (
    MongoTaskManager,
    TaskStatus
)

class TestMongoTaskManager(unittest.TestCase):
    def setUp(self):
        """在每个测试用例执行前初始化测试环境
        1. 创建模拟的MongoDB客户端
        2. 初始化MongoTaskManager实例
        """
        self.mock_client = MongoClient()
        self.task_manager = MongoTaskManager(
            mongo_client=self.mock_client,
            db="test_db",
            collection_name="test_tasks"
        )

    def test_add_task(self):
        """测试添加任务功能
        验证：
        1. 任务能够成功添加
        2. 返回的任务ID不为空
        """
        task_id = self.task_manager.add_task("test_type", {"param": "value"})
        self.assertIsNotNone(task_id)

        task = self.task_manager.get_by_task_id(task_id=task_id)
        self.assertEqual(task["status"], TaskStatus.PENDING.value)
        self.assertEqual(task["task_type"], "test_type")
        self.assertEqual(task["params"], {"param": "value"})

    def test_update_task_status(self):
        """测试更新任务状态功能
        步骤：
        1. 添加任务
        2. 更新任务状态
        验证：
        1. 任务状态更新为指定状态
        """
        task_id = self.task_manager.add_task("test_type", {"param": "value"})
        self.task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
        task = self.task_manager.get_by_task_id(task_id=task_id)
        self.assertEqual(task["status"], TaskStatus.COMPLETED.value)
        self.task_manager.update_task_status(task_id, TaskStatus.CANCEL)
        task = self.task_manager.get_by_task_id(task_id=task_id)
        self.assertEqual(task["status"], TaskStatus.CANCEL.value)

    def test_find_pending_tasks(self):
        """测试查找待处理任务功能
        步骤：
        1. 添加多个任务
        2. 查找所有待处理任务
        验证：
        1. 返回的任务数量正确
        2. 任务状态为PENDING
        """
        self.task_manager.add_task("type1", {"param": "value1"})
        self.task_manager.add_task("type2", {"param": "value2"})
        
        tasks = self.task_manager.find_pending_tasks()
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0]["status"], TaskStatus.PENDING.value)
        self.assertEqual(tasks[1]["status"], TaskStatus.PENDING.value)

    def test_acquire_lock_success(self):
        """测试成功获取任务锁
        步骤：
        1. 添加任务
        2. 获取任务锁
        验证：
        1. 任务ID格式正确
        2. 获取锁成功
        3. 任务状态更新为PROCESSING
        4. worker_id正确设置
        """
        task_id = self.task_manager.add_task("test_type", {"param": "value"})
        self.assertIsInstance(task_id, str)
        
        result = self.task_manager.acquire_lock(task_id, "worker1")
        self.assertTrue(result)
        
        task = self.task_manager.collection.find_one({"_id": ObjectId(task_id)})
        self.assertEqual(task["status"], TaskStatus.PROCESSING.value)
        self.assertEqual(task["worker_id"], "worker1")

    def test_acquire_lock_fail(self):
        """测试获取任务锁失败场景
        步骤：
        1. 添加任务
        2. 第一次获取锁成功
        3. 尝试第二次获取锁
        验证：
        1. 第二次获取锁失败
        """
        task_id = self.task_manager.add_task("test_type", {"param": "value"})
        self.task_manager.acquire_lock(task_id, "worker1")
        result = self.task_manager.acquire_lock(task_id, "worker2")
        self.assertFalse(result)

    def test_release_lock_success(self):
        """测试成功释放任务锁
        步骤：
        1. 添加任务
        2. 获取任务锁
        3. 释放任务锁
        验证：
        1. 释放锁成功
        2. 任务状态更新为COMPLETED
        """
        task_id = self.task_manager.add_task("test_type", {"param": "value"})
        self.task_manager.acquire_lock(task_id, "worker1")
        result = self.task_manager.release_lock(task_id, "worker1", TaskStatus.COMPLETED)
        self.assertTrue(result)
        task = self.task_manager.collection.find_one({"_id": ObjectId(task_id)})
        self.assertEqual(task["status"], TaskStatus.COMPLETED.value)
        self.assertEqual(task["task_type"], "test_type")
        self.assertEqual(task["params"], {"param": "value"})

    def test_release_lock_fail(self):
        """测试释放任务锁失败场景
        步骤：
        1. 添加任务
        2. 尝试释放未获取锁的任务
        验证：
        1. 释放锁失败
        """
        task_id = self.task_manager.add_task("test_type", {"param": "value"})

        result = self.task_manager.release_lock(task_id, "worker1", TaskStatus.COMPLETED)
        self.assertFalse(result)

        result = self.task_manager.acquire_lock(task_id=task_id, worker_id="worker1" )
        self.assertTrue(result)

        result = self.task_manager.release_lock(task_id, "worker2", TaskStatus.COMPLETED)
        self.assertFalse(result)

        result = self.task_manager.release_lock(task_id, "worker1", TaskStatus.COMPLETED)
        self.assertTrue(result)

        result = self.task_manager.release_lock(task_id, "worker1", TaskStatus.FAIL)
        self.assertFalse(result)

    def test_add_task_with_delay(self):
        """测试添加延迟任务功能
        步骤：
        1. 添加一个延迟3秒的任务
        2. 立即查询待处理任务，预期为空
        3. 等待4秒后再次查询，预期可以获取到任务
        验证：
        1. 延迟任务在指定时间后才可被获取
        """
        # 添加延迟3秒的任务
        task_id = self.task_manager.add_task("test_type", {"param": "value"}, delay=3)
        self.assertIsNotNone(task_id)

        # 立即查询，应该没有待处理任务
        tasks = self.task_manager.find_pending_tasks()
        self.assertEqual(len(tasks), 0)

        # 等待4秒
        time.sleep(4)

        # 再次查询，应该能获取到任务
        tasks = self.task_manager.find_pending_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(str(tasks[0]["_id"]), task_id)
        self.assertEqual(tasks[0]["status"], TaskStatus.PENDING.value)

if __name__ == '__main__':
    unittest.main()