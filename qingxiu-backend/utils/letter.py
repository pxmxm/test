import json
import re
from datetime import datetime
import requests


class SMS:
    def __init__(self):
        self.single_send_url = "https://api.ums86.com:9600/sms/Api/Send.do"

        # self.single_send_url = "http://gx.ums86.com/sms/Api/Send.do"
        self.SerialNumber = re.sub(r'-', '', datetime.now().__str__().split(' ')[0])+re.sub(r':|\.', '', datetime.now().__str__().split(' ')[1])

    def send_sms(self, mobile, content):

        parameter = {
            "SpCode": "240912",
            "LoginName": "nn_qxzf",
            # "Password": "qwe12345",
            "Password": "qxqdxpt888",
            # "MessageContent": ("您的验证码是{code}。本人操作，请忽略本短信".format(code=code)).encode('gbk'),
            "MessageContent": content,
            "UserNumber": mobile,
            "templateId": '',
            "SerialNumber": self.SerialNumber,
            "ScheduleTime": '',
            "f": 1,
        }
        response = requests.post(self.single_send_url, data=parameter)
        return response

    def receipt_sms(self):
        single_send_url = 'https://api.ums86.com:9600/sms/Api/report.do'
        parameter = {
            "SpCode": "240912",
            "LoginName": "nn_qxzf",
            # "Password": "qwe12345",
            "Password": "qxqdxpt888",
        }
        response = requests.post(single_send_url, data=parameter)
        return response




if __name__ == "__main__":
    SMS().send_sms("2097", "15022704425")
    # a = re.sub(r'-', '', datetime.now().__str__().split(' ')[0])+re.sub(r':|\.', '', datetime.now().__str__().split(' ')[1])
    # print(len(a))
    # print(a)

