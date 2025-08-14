import json
from enum import Enum

from util.decorators.class_builder import builder


@builder
class StreamSearchData:
    __PREFIX = "data: "
    __SUFFIX = "\n\n"

    class SearchEvent(Enum):
        Init = 0
        Received = 1
        Query_Understood = 2
        Recalled = 3
        Answering = 4
        Debug = 5
        Finished = 6
        Error = 7
        Drawing = 8
        Drawn = 9
        Trace = 10
        Question_Recommend = 11
        Doc_Reranked = 12
        Answer = 13
        Refine_Answer = 14
        Diagnose_Finished = 15 # 预问诊状态标志
        Electronic_Report = 16 # 电子病历
        Department = 17 # 科室推荐
        Primary_Diagnose = 18 # 主诊断
        Physical_Examine = 19 # 体格检查
        Auxiliary_Examine = 20 # 辅助检查
        Auxiliary_Items = 21 # 辅助检查项目
        Update_Electronic_Report = 22 # 更新电子病历
        Final_Electronic_Report = 23 # 最终电子病历
        Index_Router = 24 # 索引路由
        Extracted = 25 # 提取信息
        Filter = 26 # 过滤信息
        Definitive_Diagnose = 27 # 确诊诊断
        Gather_Additional_Info = 28 # 收集附加信息
        Answer_Thinking = 29 # 回答思考
        Answer_Content = 30 # 回答内容
        
        def __str__(self):
            return str(self.name).lower()
        
        @classmethod
        def from_str(cls, value: str):
            """
            根据小写字符串返回对应的枚举成员。
            如果找不到匹配的成员，则抛出 ValueError 异常。
            """
            for member in cls:
                if str(member) == value:
                    return member
            raise ValueError(f"'{value}' 不是有效的 {cls.__name__}")


    def is_answer_event(self):
        return self.event in [self.SearchEvent.Answering, self.SearchEvent.Answer_Thinking, self.SearchEvent.Answer_Content]

    def __init__(self):
        self.event = None
        self.query = None
        self.answer = None
        self.debug = None
        self.dialog_id = None
        self.message_id = None
        self.reference = None
        self.trace = None
        self.prompt = None
        self.meta = None
        self.question_recommend = None
        self.info = None
    
    def answer_length(self):
        if self.answer is not None:
            return len(self.answer)
        else:
            return 0

    def to_packet(self):
        packet_dict = self.dict()
        return (self.__PREFIX + json.dumps(packet_dict, ensure_ascii=False) + self.__SUFFIX).encode('utf-8')

    def dict(self):
        packet_dict = {}
        for field_name, field_value in vars(self).items():
            if field_value is not None:
                if isinstance(field_value, StreamSearchData.SearchEvent):
                    packet_dict.update({field_name: field_value.name.lower()})
                else:
                    packet_dict.update({field_name: field_value})
        return packet_dict


    @staticmethod
    def build_from_error(dialog_id: str, meta: dict):
        return (StreamSearchData
                .Builder()
                .event(StreamSearchData.SearchEvent.Error)
                .dialog_id(dialog_id)
                .meta(meta)
                .build())

    @staticmethod
    def get_non_answering_data(event: SearchEvent, meta: dict):
        return (StreamSearchData.Builder()
                .event(event)
                .meta(meta)
                .build())
