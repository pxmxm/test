import hashlib
from random import choice

import pinyin
import pypinyin


def jwt_response_payload_handler(token, user=None, request=None):
    """为返回的结果添加用户相关信息"""
    if user.type == "专家":
        return {
            'token': 'JWT ' + token,
            'userId': user.id,
            'name': user.expert.name,
            'username': user.username,
            'type': user.type,
        }
    return {
        'token': 'JWT ' + token,
        'userId': user.id,
        'name': user.name,
        'username': user.username,
        'type': user.type,
    }


def generate_numb_code(number):
    """
    生成number位数验证码
    :return: number位字符数字验证码
    """
    seeds = '1234567890'
    random_str = []
    for i in range(number):
        random_str.append(choice(seeds))

    return "".join(random_str)


# Python 获取中文的首字母 和 全部拼音首字母
def getStrAllAplha(str):
    return pinyin.get_initial(str, delimiter="")


# Python 获取中文的 和 全部拼音
def getPinyin(word):
    string = ''
    for i in pypinyin.pinyin(word, style=pypinyin.NORMAL):
        string += ''.join(i)
    return string.replace(' ', '')


def generate_letter_code(number):
    """
        生成number位大写验证码
        :return: number位字符大写验证码
        """
    seeds = 'ANCDEFGHIJKLMNOPQRST'
    random_str = []
    for i in range(number):
        random_str.append(choice(seeds))

    return "".join(random_str)


def make_md5(str):
    hl = hashlib.md5()
    # Tips
    # 此处必须声明encode
    # 若写法为hl.update(str)  报错为： Unicode-objects must be encoded before hashing
    hl.update(str.encode(encoding='utf-8'))
    return hl.hexdigest()


if __name__ == "__main__":
    st = 'lsa 是'
    print(len(st))
    print(getPinyin(st))
    print(len(getPinyin(st)))
    print(getPinyin('yf111'))
