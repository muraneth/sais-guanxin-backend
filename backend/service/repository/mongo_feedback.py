# 电子病历管理，使用 mongo 存储电子病历
from bson.objectid import ObjectId
from datetime import datetime
import traceback
from util.logger import service_logger
from pymongo import MongoClient
from service.config.config import service_config

"""
字段,含义,字段类型
_id,唯一键ID,string
treatment_id,就诊ID,string
feedback_type,反馈类型,string
origin_content,原始内容,dict
created_at,创建时间,string
updated_at,更新时间,string
"""

FEEDBACK_COLLECTION_NAME = "feedback"

class MongoFeedbackManager:
    def __init__(self, mongo_client, db):
        self.db = mongo_client[db]
        self.collection = self.db[FEEDBACK_COLLECTION_NAME]
    
    
    def get_by_treatment_id(self, treatment_id):
        """
        根据就诊ID获取反馈
        :param treatment_id: 就诊ID字符串
        :return: 反馈详情字典列表，每个字典包含所有字段
        """
        try:
            records = self.collection.find({"treatment_id": treatment_id}).sort("created_at", 1)
            result = []
            for record in records:
                record["_id"] = str(record["_id"])
                result.append(record)
            return result
        except Exception as e:
            service_logger.error(f"failed to get feedback: {traceback.format_exc()}")
            return []
    

    def insert_feedback(self, treatment_id, feedback_type, origin_content):
        """
        插入新的反馈
        :param treatment_id: 就诊ID字符串
        :param feedback_type: 反馈类型
        :param origin_content: 原始内容
        :return: 插入的反馈ID
        """
        try:
            record_data = {
                "treatment_id": treatment_id,
                "feedback_type": feedback_type,
                "origin_content": origin_content,
            }
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record_data["created_at"] = now
            record_data["updated_at"] = now
            
            result = self.collection.insert_one(record_data)
            return str(result.inserted_id)
        except Exception as e:
            service_logger.error(f"failed to insert feedback: {traceback.format_exc()}")
            return None

        
mongo_feedback_manager = MongoFeedbackManager(
    mongo_client=MongoClient(service_config.storage.mongo_url),
    db=service_config.storage.mongo_db
)   