from enum import Enum


class MetricType(Enum):
    Histogram = 1
    Counter = 2
    Gauge = 3


class Metrics:
    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, name: str, metric_type: MetricType):
        self.name = name
        self.metric_type = metric_type


REQUEST_LATENCY = Metrics("request_latency", MetricType.Histogram)
AUTH_LATENCY = Metrics("auth_latency", MetricType.Histogram)
SEARCH_ALGO_LATENCY = Metrics("search_algo_latency", MetricType.Histogram)

REQUEST_COUNT = Metrics("request_count", MetricType.Counter)
REQUEST_ERROR_COUNT = Metrics("request_error_count", MetricType.Counter)
SEARCH_ERROR_COUNT = Metrics("search_error_count", MetricType.Counter)
BING_SEARCH_ERROR_COUNT = Metrics("bing_search_error_count", MetricType.Counter)
BING_PAGE_FETCH_ERROR_COUNT = Metrics("bing_page_fetch_error_count", MetricType.Counter)
EMPTY_ANSWER_COUNT = Metrics("empty_answer_count", MetricType.Counter)
COMPACTION_RATE = Metrics("compaction_rate", MetricType.Gauge)

# RAG
QUERY_UNDERSTAND_LATENCY = Metrics("query_understand_latency", MetricType.Histogram)
CHUNK_RETRIEVE_LATENCY = Metrics("chunk_retrieve_latency", MetricType.Histogram)
RE_RANK_LATENCY = Metrics("re_rank_latency", MetricType.Histogram)
FIRST_TOKEN_LATENCY_FROM_LLM = Metrics("first_token_latency_from_llm", MetricType.Histogram)
FIRST_TOKEN_LATENCY_FROM_BEGINNING = Metrics("first_token_latency_from_beginning", MetricType.Histogram)
ANSWER_FUSION_TOTAL_LATENCY = Metrics("answer_fusion_total_duration", MetricType.Histogram)
ANSWER_FUSION_FIRST_TOKEN_LATENCY = Metrics("answer_fusion_first_token_duration", MetricType.Histogram)
EXTRACT_INFO_LATENCY = Metrics("extract_info_duration", MetricType.Histogram)