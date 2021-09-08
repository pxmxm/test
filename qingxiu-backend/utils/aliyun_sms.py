import json

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from backend.settings import ALIYUN_ACCESS_KEY, ALIYUN_ACCESS_SECRET, ALIYUN_SIGNNAME, ALIYUN_TEMPLATECODE


def send_sms_verification_code(mobile, sms_verification_code):
    """
    发送短信验证码
    :param sms_verification_code: 短信验证码
    :param mobile: 手机号
    :return:
    """
    send_code = {
        "code": sms_verification_code
    }
    client = AcsClient(ALIYUN_ACCESS_KEY, ALIYUN_ACCESS_SECRET, 'cn-hangzhou')

    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('https')  # https | http
    request.set_version('2017-05-25')
    request.set_action_name('SendSms')

    request.add_query_param('RegionId', "cn-hangzhou")
    request.add_query_param('PhoneNumbers', mobile)
    request.add_query_param('SignName', ALIYUN_SIGNNAME)
    request.add_query_param('TemplateCode', ALIYUN_TEMPLATECODE)
    request.add_query_param('TemplateParam', json.dumps(send_code))

    response = client.do_action(request)
    print(response)
    response = json.loads(response)
    print(response)
    if response['Code'] == 'OK':
        # logger.info('/api/sms/ %s' % response)
        return True
    else:
        # logger.error('/api/sms/ %s' % response)
        return False


if __name__ == "__main__":
    print(send_sms_verification_code(15022704425, '8888'))
