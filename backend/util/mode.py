MODE_INQUIRY = "medical_inquiry"
MODE_INQUIRY_MINI = "medical_inquiry_mini"

DOMAIN_SEARCH = "search"
DOMAIN_INQUIRY = "inquiry"
DOMAIN_INQUIRY_MINI = "inquiry_mini"
DOMAIN_AI_DOCTOR = "ai_doctor"

def get_domain_from_mode(mode: str) -> str:
    if mode == MODE_INQUIRY:
        return DOMAIN_INQUIRY
    elif mode == MODE_INQUIRY_MINI:
        return DOMAIN_INQUIRY_MINI
    return DOMAIN_SEARCH