import sys
import os

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
from unittest.mock import patch, MagicMock
from worker.process_task import process_pending_tasks
from service.repository.mongo_task_manager import TaskStatus

class TestProcessPendingTasks(unittest.TestCase):

    @patch('worker.process_task.task_manager')
    def test_no_pending_tasks(self, mock_task_manager):
        # 模拟没有待处理任务的情况
        mock_task_manager.find_pending_tasks.return_value = []
        
        process_pending_tasks()
        
        # 验证没有尝试获取锁
        mock_task_manager.acquire_lock.assert_not_called()

    @patch('worker.process_task.task_manager')
    def test_task_already_processed(self, mock_task_manager):
        # 模拟任务已经被处理的情况
        mock_task = {
            'status': TaskStatus.COMPLETED.value,
            'task_id': 'test_task_id'
        }
        mock_task_manager.find_pending_tasks.return_value = [mock_task]
        
        process_pending_tasks()
        
        # 验证没有尝试获取锁
        mock_task_manager.acquire_lock.assert_not_called()

    @patch('worker.process_task.task_manager')
    def test_failed_to_acquire_lock(self, mock_task_manager):
        # 模拟获取锁失败的情况
        mock_task = {
            'status': TaskStatus.PENDING.value,
            'task_id': 'test_task_id',
            'task_type': 'upload_report'
        }
        mock_task_manager.find_pending_tasks.return_value = [mock_task]
        mock_task_manager.acquire_lock.return_value = False
        
        process_pending_tasks()
        
        # 验证尝试获取锁但失败
        mock_task_manager.acquire_lock.assert_called_once()
        # 验证没有尝试处理任务
        mock_task_manager.release_lock.assert_not_called()

    @patch('worker.process_task.task_manager')
    @patch('worker.process_task.process_upload_report')
    def test_successful_task_processing(self, mock_process_report, mock_task_manager):
        # 模拟成功处理任务的情况
        mock_task = {
            'status': TaskStatus.PENDING.value,
            'task_id': 'test_task_id',
            'task_type': 'upload_report',
            'params': {'file_oss_key': 'test_key'}
        }
        mock_task_manager.find_pending_tasks.return_value = [mock_task]
        mock_task_manager.acquire_lock.return_value = True
        mock_process_report.return_value = TaskStatus.COMPLETED
        
        process_pending_tasks()
        
        # 验证完整流程
        mock_task_manager.acquire_lock.assert_called_once()
        mock_process_report.assert_called_once()
        mock_task_manager.release_lock.assert_called_once()

    @patch('worker.process_task.task_manager')
    @patch('worker.process_task.process_upload_report')
    def test_failed_task_processing(self, mock_process_report, mock_task_manager):
        # 模拟任务处理失败的情况
        mock_task = {
            'status': TaskStatus.PENDING.value,
            'task_id': 'test_task_id',
            'task_type': 'upload_report',
            'params': {'file_oss_key': 'test_key'}
        }
        mock_task_manager.find_pending_tasks.return_value = [mock_task]
        mock_task_manager.acquire_lock.return_value = True
        mock_process_report.return_value = TaskStatus.FAIL
        
        process_pending_tasks()
        
        # 验证失败处理流程
        mock_task_manager.acquire_lock.assert_called_once()
        mock_process_report.assert_called_once()
        mock_task_manager.release_lock.assert_called_once_with(
            'test_task_id', 
            unittest.mock.ANY,  # worker_id
            TaskStatus.FAIL
        )

    @patch('worker.process_task.task_manager')
    def test_unknown_task_type(self, mock_task_manager):
        # 模拟未知任务类型的情况
        mock_task = {
            'status': TaskStatus.PENDING.value,
            'task_id': 'test_task_id',
            'task_type': 'unknown_type'
        }
        mock_task_manager.find_pending_tasks.return_value = [mock_task]
        mock_task_manager.acquire_lock.return_value = True
        
        process_pending_tasks()
        
        # 验证处理未知任务类型
        mock_task_manager.acquire_lock.assert_called_once()
        mock_task_manager.release_lock.assert_called_once_with(
            'test_task_id',
            unittest.mock.ANY,  # worker_id
            TaskStatus.FAIL
        )

if __name__ == '__main__':
    unittest.main()