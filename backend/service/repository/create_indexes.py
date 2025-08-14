from pymongo import MongoClient, ASCENDING, DESCENDING

from service.config.config import service_config

"""
此脚本根据仓库中各 MongoDB Manager 的查询 / 更新方式，
一次性地为各 collection 创建推荐索引。

运行方式（需在有网络访问 MongoDB 的环境下）::

    python -m backend.service.repository.create_indexes

多次运行不会重复创建相同索引，因为 create_index 默认幂等。
"""

# ------------------------
# 连接数据库
# ------------------------
client = MongoClient(service_config.storage.mongo_url)
db = client[service_config.storage.mongo_db]

# ------------------------
# treatment_info collection
# ------------------------
print("Creating indexes for collection: treatment_info")

db["treatment_info"].create_index(
    [("treatment_id", ASCENDING)],
    name="uk_treatment_id",
    unique=True,
    background=True,
)

db["treatment_info"].create_index(
    [("dialog_id", ASCENDING)],
    name="idx_dialog_id",
    background=True,
)

# ------------------------
# dialog collection
# ------------------------
print("Creating indexes for collection: dialog")

db["dialog"].create_index(
    [("user", ASCENDING), ("deleted", ASCENDING), ("time", DESCENDING)],
    name="idx_user_deleted_time",
    background=True,
)

db["dialog"].create_index(
    [("treatment_id", ASCENDING)],
    name="idx_treatment_id",
    background=True,
)

# ------------------------
# message collection
# ------------------------
print("Creating indexes for collection: message")

db["message"].create_index(
    [("domain", ASCENDING), ("dialog_id", ASCENDING)],
    name="idx_domain_dialog",
    background=True,
)

# ------------------------
# request collection
# ------------------------
print("Creating indexes for collection: request")

db["request"].create_index(
    [("user_id", ASCENDING)],
    name="uk_user_id",
    unique=True,
    background=True,
)

db["request"].create_index(
    [("user_id", ASCENDING), ("tag", ASCENDING)],
    name="idx_user_tag",
    background=True,
)

# ------------------------
# feedback collection
# ------------------------
print("Creating indexes for collection: feedback")

db["feedback"].create_index(
    [("treatment_id", ASCENDING), ("created_at", ASCENDING)],
    name="idx_treatment_created",
    background=True,
)

# ------------------------
# medical_records collection
# ------------------------
print("Creating indexes for collection: medical_records")

db["medical_records"].create_index(
    [("treatment_id", ASCENDING), ("created_at", DESCENDING)],
    name="idx_treatment_created_desc",
    background=True,
)

# ------------------------
# task queue collection (名称取自配置)
# ------------------------
TASK_COLLECTION = service_config.task_queue_name
print(f"Creating indexes for collection: {TASK_COLLECTION}")

db[TASK_COLLECTION].create_index(
    [("params.treatment_id", ASCENDING)],
    name="idx_params_treatment_id",
    background=True,
)

db[TASK_COLLECTION].create_index(
    [("status", ASCENDING), ("check_time", ASCENDING)],
    name="idx_status_check_time",
    background=True,
)

print("All indexes created successfully.") 