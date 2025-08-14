from threading import Thread
from service.config.config import algo_config
from util.logger import algo_logger
from util.sync_http_request import send_request

question_recommend_service_url = algo_config.medical_algo_service_http_url + "/assistant/batch-question-recommend"
question_filter_service_url = algo_config.medical_algo_service_http_url + "/assistant/question-filter"

def batch_question_recommend(chat_history: list, reference: list[dict], top_k=None, query_rewrite=None):
    body = {
        "chat_history": chat_history,
        "reference": reference,
    }

    if top_k and top_k > 0:
        body["top_k"] = top_k

    if query_rewrite and len(query_rewrite) > 0:
        body["query_rewrite"] = query_rewrite

    gen_questions = {}
    try:
        resp = send_request(url=question_recommend_service_url, body=body)
        #algo_logger.info(f"batch question recommend request:{body} response: {resp}")
        gen_questions = resp["body"]["data"]
    except Exception as e:
        algo_logger.error(f"request question recommend error: {e}")

    return gen_questions
    
    
def question_filter(gen_questions: dict, ref_info: list[dict], current_answer=None):
    body = {
        "gen_questions": gen_questions,
        "ref_info": ref_info
    }

    if current_answer:
        body["cur_answer"] = current_answer

    filtered_questions = {}
    try:
        resp = send_request(url=question_filter_service_url, body=body)
        filtered_questions = resp["body"]["data"]
        #algo_logger.info(f"question filter request body: {body}, response: {resp}")
    except Exception as e:
        algo_logger.error(f"request question recommend error: {e}")

    return filtered_questions


class ThreadGetQuestionRecommend(Thread):
    def __init__(self, chat_history: list, reference: list[dict], top_k=None, query_rewrite=None):
        Thread.__init__(self)
        self.chat_history = chat_history
        self.reference = reference
        self.top_k = top_k
        self.query_rewrite = query_rewrite
        self.result = {}
        self.started = False

    def set(self, chat_history: list, reference: list[dict], top_k=None, query_rewrite=None):
        self.chat_history = chat_history
        self.reference = reference
        self.top_k = top_k
        self.query_rewrite = query_rewrite

    def has_started(self):
        return self.started
    
    def start_working(self):
        if self.started:
            return
        self.started = True
        self.start()

    def run(self):
        self.result = batch_question_recommend(
            chat_history=self.chat_history, 
            reference=self.reference, 
            top_k=self.top_k, 
            query_rewrite=self.query_rewrite)

    def wait_result(self):
        self.join()
        return self.result