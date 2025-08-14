import random
# import sys, os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util.logger import service_logger


def init_question_set(file_path: str):
    new_set = []
    f = open(file_path, "r")
    lines = f.readlines()
    for line in lines:
        new_set.append(line.strip())
    if len(new_set) == 0:
        service_logger.error(f"init question set failed")
    return new_set

question_set = []
question_drug_set = []
def get_random_questions(n: int) -> list[str]:
    global question_set
    global question_drug_set

    if len(question_set) == 0:
        question_set = init_question_set("conf/questions.txt")
    if len(question_drug_set) == 0:
        question_drug_set = init_question_set("conf/questions_drug.txt")

    # 随机数
    rand_index = {}

    while len(rand_index) < 1:
        index = random.randint(0, len(question_drug_set)-1)
        rand_index[index] = question_drug_set[index]

    while len(rand_index) < n:
        index = random.randint(0, len(question_set)-1)
        rand_index[index] = question_set[index]

    # 生成 []
    result = []
    for k, v in rand_index.items():
        result.append(v)
    return result

if __name__ == "__main__":
    print(get_random_questions(5))