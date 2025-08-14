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
chief_complaint，主诉，string
present_illness_history,现病史,string
past_medical_history,既往史,string
family_history,家族史,string
marital_and_reproductive_history,婚育史,string
personal_history,个人史,string
physical_examination,体格检查,string
auxiliary_examinations,辅助检查,string
diagnosis,诊断,string
treatment_plan,处置计划,string
created_at,创建时间,string
updated_at,更新时间,string
"""

MEDICAL_RECORD_COLLECTION_NAME = "medical_records"

class MongoMedicalRecordManager:
    
    def __init__(self, mongo_client, db):
        self.db = mongo_client[db]
        self.collection = self.db[MEDICAL_RECORD_COLLECTION_NAME]
    
    def get_by_treatment_id(self, treatment_id):
        """
        根据就诊ID获取电子病历
        :param treatment_id: 就诊ID字符串
        :return: 电子病历详情字典列表，每个字典包含所有字段
        """
        try:
            records = self.collection.find({"treatment_id": treatment_id}).sort("created_at", -1)
            result = []
            for record in records:
                record["_id"] = str(record["_id"])
                result.append(record)
            return result
        except Exception as e:
            service_logger.error(f"failed to get medical records: {traceback.format_exc()}")
            return []
    
    def get_latest_record_id(self, treatment_id):
        """
        获取最新的一条电子病历ID
        :param treatment_id: 就诊ID字符串
        :return: 电子病历ID字符串
        """
        try:
            record = self.collection.find_one({"treatment_id": treatment_id}, sort=[("created_at", -1)])
            if record:
                return str(record["_id"])
            return None
        except Exception as e:
            service_logger.error(f"failed to get latest medical record id: {traceback.format_exc()}")
            return None
        
    def update_last_record(self, treatment_id, field, value):
        """
        更新最后一条电子病历
        :param treatment_id: 就诊ID字符串
        :param field: 需要更新的字段
        :param value: 需要更新的字段值
        :return: 是否更新成功
        """
        try:
            while True:
                # 获取最新的一条电子病历ID
                record_id = self.get_latest_record_id(treatment_id)
                if not record_id:
                    return False, "can not get latest medical record id"
                # 更新电子病历
                success, msg = self.update_medical_record(record_id, field, value)
                if not success:
                    return False, msg
                service_logger.info(f"success to update medical record, treatment_id: {treatment_id}, field: {field}, value: {value}, record_id: {record_id}")
                # 再次获取最新的一条电子病历ID，确认是否更新成功
                ensure_report_id = self.get_latest_record_id(treatment_id)
                if ensure_report_id == record_id:
                    break
            return True, "success"
        except Exception as e:
            service_logger.error(f"failed to update last medical record: {traceback.format_exc()}")
            return False, f"failed to update last medical record: {str(e)}"

    def insert_medical_record(self, record_data):
        """
        插入新的电子病历
        :param record_data: 电子病历数据字典
        :return: 插入的电子病历ID
        """
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record_data["created_at"] = now
            record_data["updated_at"] = now
            
            result = self.collection.insert_one(record_data)
            return str(result.inserted_id)
        except Exception as e:
            service_logger.error(f"failed to insert medical record: {traceback.format_exc()}")
            return None
    
    def update_medical_record(self, record_id, field, value):
        """
        更新已有电子病历
        :param record_id: 电子病历ID字符串
        :param field: 需要更新的字段
        :param value: 需要更新的字段值
        :return: 是否更新成功
        """
        try:
            # 先检查记录是否存在
            existing_record = self.collection.find_one({"_id": ObjectId(record_id)})
            if not existing_record:
                return False, "电子病历不存在"
            
            # 更新记录
            result = self.collection.update_one(
                {"_id": ObjectId(record_id)},
                {
                    "$set": {
                        f"electronic_report.{field}": value,
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            )
            
            return True, str(existing_record["_id"])
        except Exception as e:
            service_logger.error(f"failed to update medical record: {traceback.format_exc()}")
            return False, f"failed to update medical record: {str(e)}"

    def delete_medical_record(self, record_id):
        """
        删除电子病历
        :param record_id: 电子病历ID字符串
        :return: 是否删除成功
        """
        try:
            result = self.collection.delete_one({"_id": ObjectId(record_id)})
            return result.deleted_count > 0
        except Exception as e:
            service_logger.error(f"failed to delete medical record: {traceback.format_exc()}")
            return False
        

medical_record_manager = MongoMedicalRecordManager(
    mongo_client=MongoClient(service_config.storage.mongo_url),
    db=service_config.storage.mongo_db
)   