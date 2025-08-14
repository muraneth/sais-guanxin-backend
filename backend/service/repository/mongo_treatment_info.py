# 病人诊疗信息管理，使用 mongo 存储病人诊疗信息
# treatment_id 就诊ID 是唯一键，包含病人信息、历史病例总结、历史病例报告、诊断信息
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
dialog_id,对话ID,string
patient_info,病人信息,dict
history_summary,大模型总结历史病例得到的总结,string
history_reports,历史病例报告,list
medical_diagnosis,诊断信息,dict
created_at,创建时间,string
updated_at,更新时间,string
"""

TREATMENT_INFO_COLLECTION_NAME = "treatment_info"

class MongoTreatmentInfoManager:
    def __init__(self, mongo_client, db):
        self.db = mongo_client[db]
        self.collection = self.db[TREATMENT_INFO_COLLECTION_NAME]
    

    def get_all_treatments(self):
        """
        获取所有病人诊疗信息
        :return: 病人诊疗信息列表
        """
        try:
            # 获取 collection 的所有记录
            records = self.collection.find()
            # 将游标转换为列表，否则在函数返回后游标可能已关闭
            result = []
            for record in records:
                record["_id"] = str(record["_id"])
                result.append(record)
            return result
        except Exception as e:
            service_logger.error(f"Failed to get all treatments: {traceback.format_exc()}")
            return []
    

    def get_by_treatment_id(self, treatment_id):
        """
        根据就诊ID获取病人诊疗信息
        :param treatment_id: 就诊ID字符串
        :return: 病人诊疗信息详情字典，包含所有字段
        """
        try:
            record = self.collection.find_one({"treatment_id": treatment_id})
            if record:
                record["_id"] = str(record["_id"])
                return record
            return None
        except Exception as e:
            service_logger.error(f"Failed to get treatment info: {traceback.format_exc()}")
            return None
    

    def get_by_dialog_id(self, dialog_id):
        """
        根据对话ID获取病人诊疗信息
        :param dialog_id: 对话ID字符串
        :return: 病人诊疗信息详情字典，包含所有字段
        """
        try:
            record = self.collection.find_one({"dialog_id": dialog_id})
            if record:
                record["_id"] = str(record["_id"])
                return record
            return None
        except Exception as e:
            service_logger.error(f"Failed to get treatment info: {traceback.format_exc()}")
            return None


    def insert_treatment_info(self, treatment_data):
        """
        插入新的病人诊疗信息
        :param treatment_data: 病人诊疗信息数据字典
        :return: 插入的病人诊疗信息ID
        """
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            treatment_data["created_at"] = now
            treatment_data["updated_at"] = now
            
            result = self.collection.insert_one(treatment_data)
            return str(result.inserted_id)
        except Exception as e:
            service_logger.error(f"Failed to insert treatment info: {traceback.format_exc()}")
            return None
        

    def insert_check_recommendation(self, treatment_id, check_recommendation_id, check_recommendation_list):
        """
        插入检查推荐
        :param treatment_id: 就诊ID字符串
        :param check_recommendation_id: 检查推荐ID字符串
        :param check_recommendation_data: 检查推荐信息字典
        """
        check_recommendation_data = {
            "check_recommendation_id": check_recommendation_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "details": check_recommendation_list,
        }
        try:
            self.collection.update_one(
                {"treatment_id": treatment_id},
                {"$set": {f"check_recommendation.{check_recommendation_id}": check_recommendation_data}}
            )
        except Exception as e:
            service_logger.error(f"Failed to insert check recommendation: {traceback.format_exc()}")
            return None
        
    def get_latest_check_recommendation(self, treatment_id):
        """
        获取最新检查推荐
        :param treatment_id: 就诊ID字符串
        :return: 最新检查推荐字典
        """
        try:
            record = self.collection.find_one({"treatment_id": treatment_id})
            if record:
                if "check_recommendation" in record and len(record["check_recommendation"]) > 0:
                    # 根据 created_at 排序，获取最新的检查推荐
                    check_recommendation = sorted(record["check_recommendation"].values(), key=lambda x: x["created_at"], reverse=True)
                    return check_recommendation[0]
            return {} 
        except Exception as e:
            service_logger.error(f"Failed to get treatment info: {traceback.format_exc()}")
            return None
        

    def insert_medical_diagnosis(self, treatment_id, diagnose_id, diagnose_data):
        """
        插入诊断信息
        :param treatment_id: 就诊ID字符串
        :param diagnose_id: 诊断ID字符串
        :param diagnose_data: 诊断信息字典
        """
        diagnose_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        diagnose_data["diagnose_id"] = diagnose_id
        try:    
            self.collection.update_one(
                {"treatment_id": treatment_id},
                {"$set": {f"medical_diagnosis.{diagnose_id}": diagnose_data}}
            )
        except Exception as e:
            service_logger.error(f"Failed to insert medical diagnosis: {traceback.format_exc()}")
            return None
        
    def get_latest_medical_diagnosis(self, treatment_id):
        """
        获取最新诊断信息
        :param treatment_id: 就诊ID字符串
        :return: 最新诊断信息字典
        """
        try:
            record = self.collection.find_one({"treatment_id": treatment_id})
            if record:
                if "medical_diagnosis" in record and len(record["medical_diagnosis"]) > 0:
                    # 根据 created_at 排序，获取最新的诊断信息
                    medical_diagnosis = sorted(record["medical_diagnosis"].values(), key=lambda x: x["created_at"], reverse=True)
                    return medical_diagnosis[0]
            return {}
        except Exception as e:
            service_logger.error(f"Failed to get treatment info: {traceback.format_exc()}")
            return None

    def insert_treatment_plan(self, treatment_id, treatment_plan_id, treatment_plan_list):
        """
        插入治疗方案
        :param treatment_id: 就诊ID字符串
        :param treatment_plan_id: 治疗方案ID字符串
        :param treatment_plan_data: 治疗方案信息字典
        """ 
        treatment_plan_data = {}
        treatment_plan_data["plans"] = treatment_plan_list
        treatment_plan_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        treatment_plan_data["treatment_plan_id"] = treatment_plan_id
        try:
            self.collection.update_one(
                {"treatment_id": treatment_id},
                {"$set": {f"treatment_plan.{treatment_plan_id}": treatment_plan_data}}
            )
        except Exception as e:
            service_logger.error(f"Failed to insert treatment plan: {traceback.format_exc()}")  
            return None


    def insert_examine_result(self, treatment_id: str, examine_result_id: str, examine_result_data: dict) -> bool:
        """
        插入检查结果
        :param treatment_id: 就诊ID字符串
        :param examine_result_id: 检查结果ID字符串
        :param examine_result_data: 检查结果数据字典
        :return: 插入或追加成功返回 True，无需操作（空数据）也返回 True，失败返回 False
        """
        # 如果没有数据，直接返回成功
        if not examine_result_data:
            return True

        try:
            result = self.collection.update_one(
                {"treatment_id": treatment_id},
                {
                    "$set": {
                        f"examine_result.{examine_result_id}": examine_result_data,
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
            )
            # 可根据 modified_count 判断是否实际写入，或者仅凭没有抛异常即视为成功
            return True
        except Exception:
            service_logger.error(f"Failed to insert examine result: {traceback.format_exc()}")
            return False
        

    def update_examine_result(self, treatment_id, examine_result_id, key, value):
        """
        更新检查结果
        :param treatment_id: 就诊ID字符串
        :param examine_result_id: 检查结果ID字符串
        :param key: 需要更新的字段名
        :param value: 需要更新的字段值
        """
        try:
            self.collection.update_one(
                {"treatment_id": treatment_id},
                {"$set": {f"examine_result.{examine_result_id}.{key}": value}}
            )
        except Exception as e:
            service_logger.error(f"Failed to update examine result: {traceback.format_exc()}")
            return False


    def get_latest_treatment_plan(self, treatment_id):
        """
        获取最新治疗方案
        :param treatment_id: 就诊ID字符串
        :return: 最新治疗方案字典
        """
        try:
            record = self.collection.find_one({"treatment_id": treatment_id})
            if record:
                if "treatment_plan" in record and len(record["treatment_plan"]) > 0:
                    # 根据 created_at 排序，获取最新的治疗方案
                    treatment_plan = sorted(record["treatment_plan"].values(), key=lambda x: x["created_at"], reverse=True)
                    return treatment_plan[0]
            return {}
        except Exception as e:
            service_logger.error(f"Failed to get treatment info: {traceback.format_exc()}")
            return None

    def update_by_treatment_id(self, treatment_id: str, update_data: dict) -> tuple[bool, str]:
        """
        根据就诊ID更新病人信息
        :param treatment_id: 就诊ID字符串
        :param update_data: 需要更新的字段字典
        :return: 是否更新成功
        """
        try:
            # 先检查记录是否存在
            existing_record = self.collection.find_one({"treatment_id": treatment_id})
            if not existing_record:
                return False, "病人信息不存在"
            
            # 更新时间
            update_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 更新记录
            result = self.collection.update_one(
                {"treatment_id": treatment_id},
                {"$set": update_data}
            )
            
            return True, str(existing_record["_id"])
        except Exception as e:
            service_logger.error(f"Failed to update treatment info by treatment ID: {traceback.format_exc()}")
            return False, f"Failed to update treatment info: {str(e)}"
    
        
treatment_info_manager = MongoTreatmentInfoManager(
    mongo_client=MongoClient(service_config.storage.mongo_url),
    db=service_config.storage.mongo_db
)