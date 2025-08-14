import pytest
from datetime import datetime
from bson.objectid import ObjectId
from unittest.mock import MagicMock, patch
from service.repository.mongo_medical_record_manager import MongoMedicalRecordManager

@pytest.fixture
def mock_mongo_client():
    # 创建一个模拟的 MongoDB 客户端
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    return mock_client, mock_collection

@pytest.fixture
def medical_record_manager(mock_mongo_client):
    mock_client, _ = mock_mongo_client
    return MongoMedicalRecordManager(mock_client, "test_db")

@pytest.fixture
def sample_medical_record():
    return {
        "treatment_id": "test_treatment_001",
        "chief_complaint": "头痛、发热",
        "present_illness_history": "患者3天前开始出现头痛、发热症状",
        "past_medical_history": "无特殊病史",
        "family_history": "无家族遗传病史",
        "marital_and_reproductive_history": "已婚，育有1子",
        "personal_history": "吸烟20年，每天1包",
        "physical_examination": "体温38.5℃，血压120/80mmHg",
        "auxiliary_examinations": "血常规：WBC 12.5×10^9/L",
        "diagnosis": "上呼吸道感染",
        "treatment_plan": "建议口服布洛芬，多休息"
    }

def test_get_by_treatment_id(medical_record_manager, mock_mongo_client):
    # 准备测试数据
    mock_client, mock_collection = mock_mongo_client
    test_records = [
        {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "treatment_id": "test_treatment_001",
            "chief_complaint": "头痛"
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "treatment_id": "test_treatment_001",
            "chief_complaint": "发热"
        }
    ]
    mock_collection.find.return_value = test_records

    # 执行测试
    result = medical_record_manager.get_by_treatment_id("test_treatment_001")

    # 验证结果
    assert len(result) == 2
    assert result[0]["_id"] == "507f1f77bcf86cd799439011"
    assert result[1]["_id"] == "507f1f77bcf86cd799439012"
    mock_collection.find.assert_called_once_with({"treatment_id": "test_treatment_001"})

def test_get_by_treatment_id_error(medical_record_manager, mock_mongo_client):
    # 模拟数据库异常
    mock_client, mock_collection = mock_mongo_client
    mock_collection.find.side_effect = Exception("Database error")

    # 执行测试
    result = medical_record_manager.get_by_treatment_id("test_treatment_001")

    # 验证结果
    assert result == []

def test_insert_medical_record(medical_record_manager, mock_mongo_client, sample_medical_record):
    # 准备测试数据
    mock_client, mock_collection = mock_mongo_client
    mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId("507f1f77bcf86cd799439011"))

    # 执行测试
    result = medical_record_manager.insert_medical_record(sample_medical_record)

    # 验证结果
    assert result == "507f1f77bcf86cd799439011"
    mock_collection.insert_one.assert_called_once()
    inserted_data = mock_collection.insert_one.call_args[0][0]
    assert inserted_data["treatment_id"] == sample_medical_record["treatment_id"]
    assert "created_at" in inserted_data
    assert "updated_at" in inserted_data

def test_insert_medical_record_error(medical_record_manager, mock_mongo_client, sample_medical_record):
    # 模拟数据库异常
    mock_client, mock_collection = mock_mongo_client
    mock_collection.insert_one.side_effect = Exception("Database error")

    # 执行测试
    result = medical_record_manager.insert_medical_record(sample_medical_record)

    # 验证结果
    assert result is None

def test_update_medical_record(medical_record_manager, mock_mongo_client):
    # 准备测试数据
    mock_client, mock_collection = mock_mongo_client
    record_id = "507f1f77bcf86cd799439011"
    existing_record = {
        "_id": ObjectId(record_id),
        "treatment_id": "test_treatment_001",
        "chief_complaint": "头痛"
    }
    update_data = {
        "chief_complaint": "头痛、发热"
    }
    mock_collection.find_one.return_value = existing_record
    mock_collection.update_one.return_value = MagicMock(modified_count=1)

    # 执行测试
    success, result = medical_record_manager.update_medical_record(record_id, update_data)

    # 验证结果
    assert success is True
    assert result == record_id
    mock_collection.find_one.assert_called_once_with({"_id": ObjectId(record_id)})
    mock_collection.update_one.assert_called_once()
    update_call = mock_collection.update_one.call_args[0]
    assert update_call[0] == {"_id": ObjectId(record_id)}
    assert "updated_at" in update_call[1]["$set"]

def test_update_medical_record_not_found(medical_record_manager, mock_mongo_client):
    # 准备测试数据
    mock_client, mock_collection = mock_mongo_client
    record_id = "507f1f77bcf86cd799439011"
    mock_collection.find_one.return_value = None

    # 执行测试
    success, result = medical_record_manager.update_medical_record(record_id, {})

    # 验证结果
    assert success is False
    assert result == "电子病历不存在"

def test_update_medical_record_error(medical_record_manager, mock_mongo_client):
    # 准备测试数据
    mock_client, mock_collection = mock_mongo_client
    record_id = "507f1f77bcf86cd799439011"
    mock_collection.find_one.side_effect = Exception("Database error")

    # 执行测试
    success, result = medical_record_manager.update_medical_record(record_id, {})

    # 验证结果
    assert success is False
    assert "failed to update medical record" in result

def test_delete_medical_record(medical_record_manager, mock_mongo_client):
    # 准备测试数据
    mock_client, mock_collection = mock_mongo_client
    record_id = "507f1f77bcf86cd799439011"
    mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

    # 执行测试
    result = medical_record_manager.delete_medical_record(record_id)

    # 验证结果
    assert result is True
    mock_collection.delete_one.assert_called_once_with({"_id": ObjectId(record_id)})

def test_delete_medical_record_error(medical_record_manager, mock_mongo_client):
    # 准备测试数据
    mock_client, mock_collection = mock_mongo_client
    record_id = "507f1f77bcf86cd799439011"
    mock_collection.delete_one.side_effect = Exception("Database error")

    # 执行测试
    result = medical_record_manager.delete_medical_record(record_id)

    # 验证结果
    assert result is False 