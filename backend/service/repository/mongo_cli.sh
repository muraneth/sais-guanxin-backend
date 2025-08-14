// 选库
use health_knowledge_assistant_test

// -----------------------------------------------------------------------------
// treatment_info
// -----------------------------------------------------------------------------
db.treatment_info.createIndex(
    { treatment_id: 1 },
    { name: "uk_treatment_id", unique: true }
)
db.treatment_info.createIndex(
    { dialog_id: 1 },
    { name: "idx_dialog_id" }
)

// -----------------------------------------------------------------------------
// dialog
// -----------------------------------------------------------------------------
db.dialog.createIndex(
    { user: 1, deleted: 1, time: -1 },
    { name: "idx_user_deleted_time" }
)
db.dialog.createIndex(
    { treatment_id: 1 },
    { name: "idx_treatment_id" }
)

// -----------------------------------------------------------------------------
// message
// -----------------------------------------------------------------------------
db.message.createIndex(
    { domain: 1, dialog_id: 1 },
    { name: "idx_domain_dialog" }
)

// -----------------------------------------------------------------------------
// request
// -----------------------------------------------------------------------------
db.request.createIndex(
    { user_id: 1 },
    { name: "uk_user_id", unique: true }
)
db.request.createIndex(
    { user_id: 1, tag: 1 },
    { name: "idx_user_tag" }
)

// -----------------------------------------------------------------------------
// feedback
// -----------------------------------------------------------------------------
db.feedback.createIndex(
    { treatment_id: 1, created_at: 1 },
    { name: "idx_treatment_created" }
)

// -----------------------------------------------------------------------------
// medical_records
// -----------------------------------------------------------------------------
db.medical_records.createIndex(
    { treatment_id: 1, created_at: -1 },
    { name: "idx_treatment_created_desc" }
)

// -----------------------------------------------------------------------------
// 任务队列（配置项 service_config.task_queue_name，默认 tasks_dev）
// -----------------------------------------------------------------------------
db.tasks_dev.createIndex(
    { "params.treatment_id": 1 },
    { name: "idx_params_treatment_id" }
)
db.tasks_dev.createIndex(
    { status: 1, check_time: 1 },
    { name: "idx_status_check_time" }
)
