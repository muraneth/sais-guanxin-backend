import copy
import json
import requests
import traceback
from datetime import datetime
from util.logger import service_logger

def send_request(url, method="POST", headers=None, body=None, streamOn=False, timeout_sec=300):

    if not url:
        service_logger.error(f"empty url, headers={headers}, body={body}")
        return
    
    default_headers = {}
    default_headers["Content-Type"] = "application/json"
    merged_headers = {**default_headers, **(headers if headers else {})}

    if not isinstance(body, str):
        body_json_str = json.dumps(body)
        
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=merged_headers,
            data=body_json_str,
            stream=streamOn,
            timeout=timeout_sec
        )
        
        try:
            response_body = response.json()
        except json.JSONDecodeError:
            response_body = response.text
        status_code = response.status_code
        resp_headers = response.headers
        
    except Exception as ex:
        service_logger.error(traceback.format_exc())
        response_body = {"message" : ex.__str__}
        status_code = 500
        resp_headers = {}
        
    #service_logger.info(f'send request url={url}, body={body}, response_body: {response_body}')
    return {"status_code": status_code, "headers": resp_headers, "body": response_body}