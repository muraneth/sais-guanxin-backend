import sys
import os

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
from util.stream.stream_search_model import StreamSearchData

class TestSearchEvent(unittest.TestCase):
    
    def test_from_str(self):
        # 测试正常请求
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("answering"), StreamSearchData.SearchEvent.Answering)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("refine_answer"), StreamSearchData.SearchEvent.Refine_Answer)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("answer"), StreamSearchData.SearchEvent.Answer)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("debug"), StreamSearchData.SearchEvent.Debug)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("diagnose_finished"), StreamSearchData.SearchEvent.Diagnose_Finished)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("electronic_report"), StreamSearchData.SearchEvent.Electronic_Report)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("department"), StreamSearchData.SearchEvent.Department)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("primary_diagnose"), StreamSearchData.SearchEvent.Primary_Diagnose)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("physical_examine"), StreamSearchData.SearchEvent.Physical_Examine)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("auxiliary_examine"), StreamSearchData.SearchEvent.Auxiliary_Examine)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("auxiliary_items"), StreamSearchData.SearchEvent.Auxiliary_Items)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("update_electronic_report"), StreamSearchData.SearchEvent.Update_Electronic_Report)
        self.assertEqual(StreamSearchData.SearchEvent.Answering.from_str("final_electronic_report"), StreamSearchData.SearchEvent.Final_Electronic_Report)


if __name__ == '__main__':
    unittest.main()