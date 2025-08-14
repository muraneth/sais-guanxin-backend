from datetime import datetime

DUMMY_IDEM_ID = "1"
SYSTEM_OPERATOR = "Knowledge-Assistant-Service"


def generate_idem_id(key: str) -> str:
    return key + "-" + str(int(datetime.utcnow().timestamp() * 1000))
