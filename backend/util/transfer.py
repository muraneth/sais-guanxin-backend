def get_chinese_patient_info(patient_info: dict):
    chinese_patient_info = {}
    for key, value in patient_info.items():
        if key == "name":
            chinese_patient_info["姓名"] = value
        elif key == "gender":
            chinese_patient_info["性别"] = value
        elif key == "age":
            chinese_patient_info["年龄"] = value
        elif key == "occupation":
            chinese_patient_info["职业"] = value
        elif key == "marital_status":
            chinese_patient_info["婚姻状况"] = value
        elif key == "phone":
            chinese_patient_info["电话"] = value
        elif key == "address":
            chinese_patient_info["地址"] = value
        elif key == "email":
            chinese_patient_info["邮箱"] = value
        else:
            chinese_patient_info[key] = value
    
    return chinese_patient_info
