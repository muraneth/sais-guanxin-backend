

import requests
import json
from util.logger import service_logger
import traceback

import time
from util.timer import Timer

# Updated URL to match your curl command
electronic_report_fixer_url = "http://10.12.34.32:5000/cardiomind-patcher"

def fix_electronic_report(electronic_report_old: dict, timeout_seconds: int = 120):
    """
    Fix electronic report using the cardiomind-patcher service
    
    Args:
        electronic_report_old (dict): The original electronic report with Chinese medical fields
        timeout_seconds (int): Request timeout in seconds (default: 120 seconds)
        
    Returns:
        dict: The fixed electronic report
    """
    timer = Timer()
    start_time = time.time()
    
    try:
        # Prepare the request data - send the report directly as the body
        headers = {
            "Content-Type": "application/json"
        }
        
        # Log the request with timeout info
        service_logger.info(f"Sending request to {electronic_report_fixer_url} with timeout: {timeout_seconds}s")
        service_logger.info(f"Request data: {electronic_report_old}")
        
        # Make the POST request with extended timeout
        response = requests.post(
            url=electronic_report_fixer_url,
            headers=headers,
            json=electronic_report_old,  # Send the report directly as JSON
            timeout=timeout_seconds
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        elapsed_time = timer.duration()
        service_logger.info(f"Successfully received response from cardiomind-patcher in {elapsed_time:.2f}s")
        
        # Log warning if it took longer than expected
        if elapsed_time > 60:
            service_logger.warning(f"Request took {elapsed_time:.2f}s (>60s) - consider optimizing the service")
        
        return result
        
    except requests.exceptions.Timeout as e:
        elapsed_time = time.time() - start_time
        service_logger.error(f"Request timed out after {elapsed_time:.2f}s (timeout: {timeout_seconds}s)")
        service_logger.error(f"Timeout error: {str(e)}")
        service_logger.error(traceback.format_exc())
        raise
    except requests.exceptions.RequestException as e:
        elapsed_time = time.time() - start_time
        service_logger.error(f"Request failed after {elapsed_time:.2f}s: {str(e)}")
        service_logger.error(traceback.format_exc())
        raise
    except json.JSONDecodeError as e:
        elapsed_time = time.time() - start_time
        service_logger.error(f"Failed to parse JSON response after {elapsed_time:.2f}s: {str(e)}")
        service_logger.error(traceback.format_exc())
        raise
    except Exception as e:
        elapsed_time = time.time() - start_time
        service_logger.error(f"Unexpected error after {elapsed_time:.2f}s: {str(e)}")
        service_logger.error(traceback.format_exc())
        raise


# Example usage and test function
def test_electronic_report_fix():
    """
    Test function to demonstrate how to use the fix_electronic_report function
    """
    sample_report = {
        "主诉": "心前区生气时疼痛，持续4-5分钟。",
        "现病史": "患者心前区生气时出现刺痛，持续4-5分钟，可自行缓解，伴有后背反射痛。平时服用阿司匹林和冠心苏合丸，阿司匹林隔一个月服用一个月，每晚100mg，冠心苏合丸服用2月，剂量不详。患者自行调整阿司匹林服用方式，担心副作用，但未出现胃痛或黑便等不适症状。建议持续服用阿司匹林并定期复查。",
        "既往史": "未提及",
        "个人史": "未提及",
        "家族史": "未提及",
        "婚育史": "未提及",
        "辅助检查": "未提及",
        "体格检查": "未提及",
        "诊断": "冠状动脉粥样硬化性心脏病（不稳定性心绞痛可能）",
        "处置": "增强型体外反搏（EECP）、心理疏导、阿司匹林、冠心苏合丸；心电图、心肌酶谱、心理评估、胃镜检查、24小时食管pH监测、运动负荷试验"
    }
    
    try:
        result = fix_electronic_report(sample_report)
        print("Fixed report result:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return None


if __name__ == "__main__":
    # Run the test
    test_electronic_report_fix()





