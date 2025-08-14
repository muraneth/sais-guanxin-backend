import traceback
from enum import Enum
from bson.objectid import ObjectId
from pymongo import MongoClient, ReturnDocument
from datetime import datetime, timedelta

from util.model_types import TaskCollectionModel
from util.logger import service_logger
from service.config.config import service_config
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAIL = "fail"
    CANCEL = "cancel"


class MongoTaskManager():
    def __init__(self, mongo_client, db, collection_name):
        self.db = mongo_client[db]
        self.collection = self.db[collection_name]
        service_logger.info(f"MongoTaskManager initialized, task queue name: {collection_name}")


    def get_by_task_id(self, task_id):
        """
        根据任务ID获取任务详情
        :param task_id: 任务ID字符串
        :return: 任务详情字典，包含所有字段
        """
        try:
            # 将字符串ID转换为ObjectId
            task_object_id = ObjectId(task_id)
            # 查询数据库
            task = self.collection.find_one({"_id": task_object_id})
            if task:
                # 将ObjectId转换为字符串
                task["_id"] = str(task["_id"])
                return task
            return None
        except Exception as e:
            # 处理无效的task_id格式
            return None
        

    def update_task_status(self, task_id: str, task_status: TaskStatus):
        try:    
            self.collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"status": task_status.value}}
            )
        except Exception as e:
            service_logger.error(traceback.format_exc())
            return False
        return True
    
    
    def update_task(self, task_id: str, task_result: dict):
        try:
            self.collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"result": task_result}}
            )
        except Exception as e:
            service_logger.error(traceback.format_exc())
            return False
        return True

    
    def add_task(self, task_type, params, delay=0):
        # 获取当前时间
        now = datetime.now()
        now_time_string = now.strftime("%Y-%m-%d %H:%M:%S")
        # 计算检查时间
        if delay > 0:
            check_time = now + timedelta(seconds=delay)
        else:
            check_time = now
        # 格式化检查时间
        check_time_string = check_time.strftime("%Y-%m-%d %H:%M:%S")
        # 构造任务行
        row = {
            TaskCollectionModel.task_type: task_type,
            TaskCollectionModel.status: TaskStatus.PENDING.name.lower(),
            TaskCollectionModel.params: params,
            TaskCollectionModel.check_time: check_time_string,
            TaskCollectionModel.created_at: now_time_string,
            TaskCollectionModel.updated_at: now_time_string,
        }
        result = self.collection.insert_one(row)
        return str(result.inserted_id)
    
    def find_task_by_treatment_id(self, treatment_id):
        # 查询 params 中字段 treatment_id 的值为 treatment_id 的文档
        try:
            query = {
                f"{TaskCollectionModel.params}.treatment_id": treatment_id
            }
            cursor = self.collection.find(query).limit(100).skip(0).sort([(TaskCollectionModel.created_at, -1)])
            documents = []
            for each in cursor:
                each["_id"] = str(each["_id"])
                documents.append(each)
            return documents
        except Exception as e:
            service_logger.error(f"查询任务失败: {str(e)}")
            service_logger.error(traceback.format_exc())
            return []

    def find_pending_tasks(self):
        query = {
            TaskCollectionModel.status: TaskStatus.PENDING.name.lower(),
            TaskCollectionModel.check_time: {"$lte": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        }
        cursor = self.collection.find(query).limit(10).skip(0).sort("time", -1)
        documents = []
        for each in cursor:
            each["task_id"] = str(each["_id"])
            documents.append(each)
        return documents


    def acquire_lock(self, task_id: str, worker_id: str) -> bool:
        """
        尝试获取任务锁
        """
        result = self.collection.find_one_and_update(
            filter={"_id": ObjectId(task_id), "status": TaskStatus.PENDING.value},
            update={"$set": {"status": TaskStatus.PROCESSING.value, "worker_id": worker_id}},
            return_document=ReturnDocument.AFTER
        )
        return result is not None


    def release_lock(self, task_id: str, worker_id: str, task_status: TaskStatus, time_cost: float = 0) -> bool:
        """
        释放任务锁
        """
        if task_status is TaskStatus.PROCESSING:
            return False
        
        result = self.collection.find_one_and_update(
            filter={"_id": ObjectId(task_id), "worker_id": worker_id, "status": TaskStatus.PROCESSING.value},
            update={
                "$set": {
                    "status": task_status.value,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "time_cost": time_cost
                }
            },
            return_document=ReturnDocument.AFTER
        )
        return result is not None


task_manager = MongoTaskManager(
    mongo_client=MongoClient(service_config.storage.mongo_url),
    db=service_config.storage.mongo_db,
    collection_name=service_config.task_queue_name
)