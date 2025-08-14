import datetime
from bson import ObjectId
from pymongo import MongoClient
from service.config.config import service_config
from util.model_types import MessageCollectionModel, DialogCollectionModel, DialogMgrCollectionType, RequestCollectionModel
from util.mode import DOMAIN_SEARCH, DOMAIN_AI_DOCTOR
from util.oss import oss_client
from util.minio_client import minio_client

class MongoDialogManager():
    def __init__(self, mongo_client, db):
        self.db = mongo_client[db]

    def upsert_message(self, content, dialog_id, message_id, sources, cost, domain = DOMAIN_SEARCH, enable_think = None):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        data = {
            MessageCollectionModel.content: content,
            MessageCollectionModel.dialog_id: dialog_id,
            MessageCollectionModel.cost: cost,
            MessageCollectionModel.domain: domain,
            MessageCollectionModel.sources: sources,
        }
        if enable_think is not None:
            data[MessageCollectionModel.enable_think] = enable_think
        now = datetime.datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        row = {
            **data,
            MessageCollectionModel.like: False,
            MessageCollectionModel.dislike: False,
            MessageCollectionModel.time: dt_string
        }
        if message_id:
            match = {
                "_id": ObjectId(message_id)
            }
            self.db[collection_name].update_one(match, {"$set": row}, upsert=True)
            return message_id
        else:
            result = self.db[collection_name].insert_one(row)
            return str(result.inserted_id)

    def delete_message(self, message_id):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        match = {
            "_id": ObjectId(message_id)
        }
        return self.db[collection_name].delete_one(match)

    def get_dialog_message(self, message_id):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        match = {
            "_id": ObjectId(message_id)
        }
        document = self.db[collection_name].find_one(match)
        document["_id"] = str(document["_id"])
        return document 

    def activate_dialog(self, dialog_id):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        match = {"_id": ObjectId(dialog_id)}
        new_row = {"$set": {
            DialogCollectionModel.activated: True
        }}
        return self.db[collection_name].update_one(match, new_row)

    def get_dialog_messages(self, domain, dialog_id):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        query = {
            MessageCollectionModel.domain: domain,
            MessageCollectionModel.dialog_id: dialog_id
        }
        cursor = self.db[collection_name].find(query).limit(1000).skip(0)
        documents = []
        for each in cursor:
            each["_id"] = str(each["_id"])
            # handle like and dislike
            if MessageCollectionModel.like in each:
                if each[MessageCollectionModel.like]:
                    each[MessageCollectionModel.dislike] = False  # like the answer
                elif MessageCollectionModel.dislike not in each:
                    each[MessageCollectionModel.dislike] = False  # neutrality
            if MessageCollectionModel.unlike in each:
                del each[MessageCollectionModel.unlike]
            documents.append(each)
        return documents

    def get_dialog_messages_context(self, domain, dialog_id):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        query = {
            MessageCollectionModel.domain: domain,
            MessageCollectionModel.dialog_id: dialog_id
        }
        # only trace back 100 Q&A pairs for speeding up
        cursor = self.db[collection_name].find(query, sort=[("_id", 1)]).limit(100).skip(0)
        history = []
        for each in cursor:
            each["_id"] = str(each["_id"])
            # filter Q&A in content
            if MessageCollectionModel.content in each:
                content = each[MessageCollectionModel.content]
                if content:
                    history.append(content)
        return history

    def update_conversation(self, data):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        conversation_id = data[MessageCollectionModel.conversation_id]
        row = {}
        if MessageCollectionModel.like in data:
            is_like = data[MessageCollectionModel.like]
            row[MessageCollectionModel.like] = is_like
            if is_like:
                row[MessageCollectionModel.dislike] = False
        elif MessageCollectionModel.dislike in data:
            is_dislike = data[MessageCollectionModel.dislike]
            row[MessageCollectionModel.dislike] = is_dislike
            if is_dislike:
                row[MessageCollectionModel.like] = False

        match = {"_id": ObjectId(conversation_id)}
        new_row = {"$set": row}
        return self.db[collection_name].update_one(match, new_row)

    def clear_stop_generating(self, message_id):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        match = {"_id": ObjectId(message_id)}
        unset = {"$unset": {
            MessageCollectionModel.stop_generating: False,
            MessageCollectionModel.stop_generating_reason: ""
        }}
        return self.db[collection_name].update_one(match, unset)
    
    def stop_generating(self, message_id, stop_generating_reason):
        collection_name = DialogMgrCollectionType.MESSAGE.name.lower()
        row = {
            MessageCollectionModel.stop_generating: True,
            MessageCollectionModel.stop_generating_reason: stop_generating_reason
        }
        match = {"_id": ObjectId(message_id)}
        set = {"$set": row}
        return self.db[collection_name].update_one(match, set)

    def get_dialog(self, keyword, user_id):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        query = {
            DialogCollectionModel.user: user_id,
            DialogCollectionModel.deleted: False,
        }
        if keyword and keyword != "":
            query[DialogCollectionModel.name] = {"$regex": keyword}

        cursor = self.db[collection_name].find(query).limit(200).skip(0).sort("time", -1)
        documents = []
        for each in cursor:
            each["_id"] = str(each["_id"])
            documents.append(each)
        return documents

    def update_dialog(self, dialog_id, sources: list):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        match = {"_id": ObjectId(dialog_id)}
        new_row = {"$set": {
            DialogCollectionModel.sources: sources
        }}
        return self.db[collection_name].update_one(match, new_row)

    def delete_dialog(self, dialog_id):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        match = {
            "_id": ObjectId(dialog_id)
        }
        row = {
            DialogCollectionModel.deleted: True
        }
        new_row = {"$set": row}
        return self.db[collection_name].update_one(match, new_row)

    def new_ai_doctor_dialog(self, treatment_id):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        now = datetime.datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "treatment_id": treatment_id,           # 治疗 ID，TODO:需要加索引
            DialogCollectionModel.time: dt_string,
        }
        return self.db[collection_name].insert_one(row)
    
    def get_dialog_by_treatment_id(self, treatment_id):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        query = {
            "treatment_id": treatment_id
        }
        return self.db[collection_name].find_one(query)

    def add_dialog(self, user_id, user_name, company, name, sources, domain):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        now = datetime.datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        row = {
            DialogCollectionModel.user: user_id,
            DialogCollectionModel.user_name: user_name,
            DialogCollectionModel.company: company,
            DialogCollectionModel.name: name,
            DialogCollectionModel.domain: domain,
            DialogCollectionModel.deleted: False,
            DialogCollectionModel.sources: sources,
            DialogCollectionModel.time: dt_string,
            DialogCollectionModel.activated: False
        }
        return self.db[collection_name].insert_one(row)

    def edit_dialog_name(self, dialog_id, dialog_name):
        collection_name = DialogMgrCollectionType.DIALOG.name.lower()
        match = {
            "_id": ObjectId(dialog_id)
        }
        row = {
            DialogCollectionModel.name: dialog_name
        }
        new_row = {"$set": row}
        return self.db[collection_name].update_one(match, new_row)

    def update_session_requester(self, user_id, task_state, tag, msg_id, sources, dialog_id=None):
        collection_name = DialogMgrCollectionType.REQUEST.name.lower()
        match = {
            RequestCollectionModel.user_id: user_id
        }
        row = {
            RequestCollectionModel.task_state: task_state,
            RequestCollectionModel.tag: tag,
            RequestCollectionModel.message_id: msg_id,
            RequestCollectionModel.sources: sources
        }
        if dialog_id:
            row[RequestCollectionModel.dialog_id] = dialog_id
        new_row = {"$set": row}
        return self.db[collection_name].update_one(match, new_row, upsert=True)

    def get_session_requester(self, user_id):
        collection_name = DialogMgrCollectionType.REQUEST.name.lower()
        row = {
            RequestCollectionModel.user_id: user_id
        }
        return self.db[collection_name].find_one(row)

    def delete_session_requester(self, user_id, tag):
        collection_name = DialogMgrCollectionType.REQUEST.name.lower()
        row = {
            RequestCollectionModel.user_id: user_id,
            RequestCollectionModel.tag: tag
        }
        return self.db[collection_name].delete_one(row)


dialog_manager = MongoDialogManager(
    mongo_client=MongoClient(service_config.storage.mongo_url),
    db=service_config.storage.mongo_db
)

# 获取对话历史
def get_ai_doctor_chat_history(dialog_id: str = None, show_appendix: bool = False, domain: str = DOMAIN_AI_DOCTOR):
    chat_history_raw = dialog_manager.get_dialog_messages_context(domain=domain, dialog_id=dialog_id)
    messages_context = []
    diagnose_finished = False
    for content in chat_history_raw:
        query = content.get("query")
        if query is not None and query != "":
            messages_context.append({
                "role": "user",
                "content": query
            })
        answer = content.get("answer")
        if answer is not None and answer != "":
            messages_context.append({
                "role": "assistant",
                "content": answer
            })
        if show_appendix:
            # 如果 content 是 report 类型，并且有 file_oss_key，则添加一个下载链接给 content
            content_type = content.get("type")
            file_oss_key = content.get("file_oss_key")
            storage_type = content.get("storage_type")
            if content_type is not None and content_type == "report" and file_oss_key is not None and file_oss_key != "":
                # 添加一个下载链接给 content
                if storage_type == "oss":
                    content["file_url"] = oss_client.get_file_url(file_oss_key=file_oss_key)
                elif storage_type == "minio":
                    content["file_url"] = minio_client.get_file_url(file_oss_key=file_oss_key, external=True)
                messages_context.append({
                    "role": "user",
                    "content": content,
                    "appendix": True,
                })
        # 有预问诊结束的标志
        if content.get("diagnose_finished"):
            diagnose_finished = True
    
    return messages_context, diagnose_finished
