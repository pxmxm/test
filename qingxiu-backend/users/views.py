import datetime
import re
import time
from ast import literal_eval

import requests
import xlrd
from django.contrib.auth import authenticate
from django.core.cache import cache
# Create your views here.
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.serializers import jwt_payload_handler, jwt_encode_handler
from rest_framework_jwt.views import JSONWebTokenAPIView

from article.tasks import expert_register, expert_editor
from blacklist.models import AgenciesBlacklist
from concluding.models import SubjectConcluding
from subject.models import Subject, SubjectExpertsOpinionSheet, SubjectKExperts, AttachmentList
from termination.models import SubjectTermination
from upload.models import LoginLog
from users.models import User, KExperts, PExperts, Enterprise, Agency, Permissions
from users.serializers import CustomJSONWebTokenSerializer, ForgotPasswordSerializers, SmsCodeSerializers, \
    UserSerializers, KExpertsSerializers, PExpertsSerializers, \
    RegisteredSerializers, EnterpriseSerializers, ResetPasswordSerializers, AgencySerializers, PermissionsSerializers
from users.utils import jwt_response_payload_handler, generate_numb_code, getPinyin
from utils.code import UnifiedSocialCreditIdentifier

from utils.letter import SMS

from utils.oss import OSS

from utils.scanning import client, get_file_png, get_base64_png

# 登陆
from utils.sendemail import SendEmailProcess


class ObtainJSONWebToken(JSONWebTokenAPIView):
    """
    API View that receives a POST with a user's username and password.
    Returns a JSON Web Token that can be used for authenticated requests.
    """
    serializer_class = CustomJSONWebTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.data['type'] == '评估机构':
            instance = User.objects.get(username=serializer.validated_data['username'] + '3')
            payload = jwt_payload_handler(instance)
            response_data = jwt_response_payload_handler(token=jwt_encode_handler(payload), user=instance,
                                                         request=request)
            cache.set('%s' % jwt_encode_handler(payload), {'token': jwt_encode_handler(payload)}, 60 * 60)
            cache.delete('v_%s' % request.data['validated'])
            ip = request.META.get('HTTP_X_FORWARDED_FOR')
            url = 'http://ip.ws.126.net/ipquery?ip=%s' % ip

            rsp = requests.get(url)
            content = rsp.content.decode('gbk')
            a = re.sub(r'\n|\r|\"|var|\;', '', content)
            b = a.split('=')[-1].split(",")[0].split(":")[-1]
            LoginLog.objects.create(ip=ip, user_id=instance.id, address=b)
            return Response({"code": 0, "message": "登录成功", "detail": response_data}, status=status.HTTP_200_OK)

        instance = User.objects.get(username=serializer.validated_data['username'])
        payload = jwt_payload_handler(instance)
        response_data = jwt_response_payload_handler(token=jwt_encode_handler(payload), user=instance,
                                                     request=request)
        cache.set('%s' % jwt_encode_handler(payload), {'token': jwt_encode_handler(payload)}, 60 * 60)
        cache.delete('v_%s' % request.data['validated'])
        if request.data['type'] == '科技局':
            cache.set('%s' % serializer.validated_data['username'],
                      {'token': jwt_encode_handler(payload), 'time': datetime.datetime.now()})
        # proxy_ip = request.META.get("REMOTE_ADDR")
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        url = 'http://ip.ws.126.net/ipquery?ip=%s' % ip

        rsp = requests.get(url)
        content = rsp.content.decode('gbk')
        a = re.sub(r'\n|\r|\"|var|\;', '', content)
        b = a.split('=')[-1].split(",")[0].split(":")[-1]
        LoginLog.objects.create(ip=ip, user_id=instance.id, address=b)
        return Response({"code": 0, "message": "登录成功", "detail": response_data}, status=status.HTTP_200_OK)


# 移动端登录
class AccountObtainJSONWebToken(JSONWebTokenAPIView):

    def post(self, request, *args, **kwargs):
        username = request.data['username']
        password = request.data['password']
        types = request.data['types']
        if User.objects.filter(username=username, isDelete=False).exists():
            credentials = {
                'username': username,
                'password': password
            }
            user = authenticate(**credentials)
            if user:
                if user.isActivation == '禁用':
                    return Response({"code": 3, 'message': '该账号已被禁用，请联系管理员启用后再登录'}, status=status.HTTP_200_OK)
                if user.type == '分管员' or user.type == '管理员':
                    if types != '科技局':
                        return Response({"code": 4, 'message': '请登录自己的系统'}, status=status.HTTP_200_OK)
                else:
                    if types != user.type:
                        return Response({"code": 4, 'message': '请登录自己的系统'}, status=status.HTTP_200_OK)
                payload = jwt_payload_handler(user)
                response_data = jwt_response_payload_handler(token=jwt_encode_handler(payload), user=user,
                                                             request=request)
                cache.set('%s' % jwt_encode_handler(payload), {'token': jwt_encode_handler(payload)}, 60 * 60)
                return Response({"code": 0, "message": "登录成功", "detail": response_data}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 2, 'message': '账号密码错误'}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, 'message': '该账号未注册，请完成注册'}, status=status.HTTP_200_OK)


# 单位注册
class RegisteredViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisteredSerializers

    @action(detail=False, methods=['post'], url_path='registered')
    def registered(self, request):
        if len(request.data['username']) != 18 or request.data['username'][2:8] != '450103':
            return Response({"code": 1, "message": "贵单位非青秀区注册单位，不支持注册申报"}, status.HTTP_200_OK)
        if not UnifiedSocialCreditIdentifier().check_social_credit_code(code=request.data['username']) is True:
            return Response({"code": 2, "message": "请输入正确的统一社会代码"}, status.HTTP_200_OK)
        if User.objects.filter(username=request.data['username'], type='企业').exists():
            return Response({"code": 1, "message": "该单位已经通过注册审核，请前往首页登录"}, status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "继续吧"}, status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if User.objects.filter(username=request.data['username']).exists():
            return Response({"code": 1, 'message': '该单位已经通过注册审核，请前往首页登录'}, status=status.HTTP_200_OK)
        if not UnifiedSocialCreditIdentifier().check_social_credit_code(code=request.data['username']) is True:
            return Response({"code": 7, "message": "请输入正确的统一社会代码"}, status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            if request.data['username'][2:8] != '450103':
                return Response({"code": 6, "message": "贵单位非青秀区注册单位，不支持注册申报"}, status=status.HTTP_200_OK)
            else:
                queryset = self.queryset.create(username=serializer.validated_data['username'],
                                                name=serializer.validated_data['name'],
                                                mobile=serializer.validated_data['mobile'],
                                                contact=serializer.validated_data['contact'],
                                                email=serializer.validated_data['email'],
                                                )
                queryset.businessLicense = request.data['businessLicense']
                queryset.set_password(request.data['password'])
                queryset.save()
                queryset.is_activation = '启用'
                queryset.save()
                # registered_address = business_license['words_result']['地址']['words']
                # queryset.registeredAddress = registered_address
                # queryset.save()
                payload = jwt_payload_handler(queryset)
                response_data = jwt_response_payload_handler(token=jwt_encode_handler(payload), user=queryset,
                                                             request=request)
                cache.set('%s' % jwt_encode_handler(payload), {'token': jwt_encode_handler(payload)}, 60 * 60)
                return Response({"code": 0, "message": "注册成功",
                                 "detail": {"user": response_data}}, status=status.HTTP_201_CREATED)

    #  上传营业执照（单位系统）
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        file = request.data['file']
        file_name = request.data['fileName']
        path = OSS().put_by_backend(path=file_name, data=file.read())
        return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)

    # 删除营业执照（单位系统）
    @action(detail=False, methods=['post'], url_path='upload_delete')
    def upload_delete(self, request):
        path = request.data['input']
        file_name = path.split("/")[-1]
        OSS().delete(bucket_name='file', file_name=file_name)
        return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)

    # 退出登录
    @action(detail=False, methods=['post'], url_path='loginOut')
    def login_out(self, request):
        if request.query_params.dict().get('token', None) is not None:
            # 尝试从url中获取token
            token = request.query_params.dict()['token']
        elif request.data.get('token', None) is not None:
            # 尝试从request.data中获取token
            token = request.data.get('token')
        elif request._request.META.get('HTTP_AUTHORIZATION', None) is not None:
            # 尝试从请求头中获取token
            token = request._request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
            cache.delete('%s' % token)
        else:
            token = None
        return Response(True)


# 评估注册
class AgencyRegisteredViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisteredSerializers

    def list(self, request, *args, **kwargs):
        username = request.query_params.dict().get('username')
        if User.objects.filter(username=username + "3", type='评估机构').exists():
            return Response({"code": 1, "message": "该单位已注册，请直接登录系统"}, status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "继续吧"}, status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if User.objects.filter(username=request.data['username']).exists():
            return Response({"code": 1, 'message': '该单位已注册，请直接登录系统'}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            agency = Agency.objects.create(name=request.data['name'], creditCode=request.data['username'],
                                           contact=request.data['contact'], mobile=request.data['mobile'],
                                           qualification=request.data['qualification'],
                                           businessLicense=request.data['businessLicense'])
            queryset = self.queryset.create(username=serializer.validated_data['username'] + '3', type='评估机构',
                                            name=request.data['name'], agency=agency)
            queryset.set_password(request.data['password'])
            queryset.save()
            payload = jwt_payload_handler(queryset)
            response_data = jwt_response_payload_handler(token=jwt_encode_handler(payload), user=queryset,
                                                         request=request)
            cache.set('%s' % jwt_encode_handler(payload), {'token': jwt_encode_handler(payload)}, 60 * 60)
            return Response({"code": 0, "message": "注册成功", "detail": {"user": response_data}},
                            status=status.HTTP_201_CREATED)

    #  上传营业执照（单位系统）
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        file = request.data['file']
        file_name = request.data['fileName']
        path = OSS().put_by_backend(path=file_name, data=file.read())
        data = [{"name": file_name, "path": path}]
        return Response({"code": 0, "message": "上传成功", "detail": data}, status=status.HTTP_200_OK)

    # 删除营业执照（单位系统）
    @action(detail=False, methods=['delete'], url_path='delete')
    def upload_delete(self, request):
        path = request.data['path']
        file_name = path.split("/")[-1]
        OSS().delete(bucket_name='file', file_name=file_name)
        return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)


class PermissionsViewSet(viewsets.ModelViewSet):
    queryset = Permissions.objects.all()
    serializer_class = PermissionsSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)


# 企业完善信息
class EnterpriseViewSet(viewsets.ModelViewSet):
    queryset = Enterprise.objects.all()
    serializer_class = EnterpriseSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 初始数据
    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request):
        user = request.user
        name = str(user.businessLicense).split('.')[-1]
        data = {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "registeredAddress": user.registeredAddress,
            "mobile": user.mobile,
            "businessLicenseName": user.name + "营业执照." + name,
            "businessLicense": user.businessLicense,
        }
        return Response({'code': 0, 'message': '请求成功', 'detail': data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        user.enterprise_id = serializer.data['id']
        user.mobile = request.data['mobile']
        user.save()
        return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        user = request.user
        partial = kwargs.pop('partial', False)
        instance = self.queryset.get(id=user.enterprise_id)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        user.mobile = request.data['mobile']
        if user.businessLicense != request.data['businessLicense']:
            if Subject.objects.filter(Q(subjectState='待提交') | Q(subjectState='形式审查未通过'), enterprise=user).exists():
                for i in Subject.objects.filter(Q(subjectState='待提交') | Q(subjectState='形式审查未通过'), enterprise=user):
                    AttachmentList.objects.filter(attachmentName='申报单位营业执照/统一社会信用代码证书（复印件）',
                                                  attachmentShows='申报单位营业执照/统一社会信用代码证书',
                                                  subjectId=i.id).\
                        update(attachmentContent=[{"name": "营业执照", "path": request.data['businessLicense']}])

        user.businessLicense = request.data['businessLicense']
        user.save()
        return Response({'code': 0, "message": "保存成功"}, status=status.HTTP_200_OK)


class ResetPasswordViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = ResetPasswordSerializers

    def list(self, request, *args, **kwargs):
        username = request.query_params.dict().get('username')
        queryset = self.queryset.filter(username=username + '3').first()
        return Response({"code": 0, "message": "请求成功", "detail": queryset.agency.mobile})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'code': 0, 'message': '修改成功'}, status=status.HTTP_200_OK)


# 忘记密码
class ForgotPasswordViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = ForgotPasswordSerializers

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'code': 0, 'message': '修改成功'}, status=status.HTTP_200_OK)


# 短信验证码
class SMSCodeViewSet(viewsets.GenericViewSet):
    """
    获取短信验证码
    思路为：
    redis 判断该用户是否频繁获取
    生成短信验证码
    redis增加记录
    存入redis 键 值 过期时间
    设置：cache.set(键, 值, 有效时间)
    获取：cache.get(键)
    删除：cache.delete(键)
    清空：cache.clear()
    发送短信
    返回响应
    """
    serializer_class = SmsCodeSerializers

    # # 短信验证码 云片
    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     mobile = request.data['mobile']
    #     # 调用函数generate_numb_code
    #     sms_code = generate_numb_code(4)
    #     cache.set('sms_%s' % mobile, {'sms_code': sms_code}, 5 * 60, )
    #     cache.set('sms_flag_%s' % mobile, {'mobile': mobile}, 60)
    #     yp = YunPian(APIKEY)
    #     yp.send_sms(code=sms_code, mobile=mobile)
    #     return Response({'code': 0, 'message': '发送成功'})

    # 短信验证码 一信通平台
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = request.data['mobile']
        # 调用函数generate_numb_code
        sms_code = generate_numb_code(4)
        cache.set('sms_%s' % mobile, {'sms_code': sms_code}, 10 * 60, )
        cache.set('sms_flag_%s' % mobile, {'mobile': mobile}, 60)
        # yp = YunPian(APIKEY)
        # yp.send_sms(code=sms_code, mobile=mobile)
        if request.data['action'] == '注册':
            content = "您的注册验证码是{code},验证码10分钟内有效,如非本人操作，请忽略本短信".format(code=sms_code).encode('gbk')
            SMS().send_sms(mobile, content)
            return Response({'code': 0, 'message': '发送成功'})
        elif request.data['action'] == '密码':
            content = "您正在找回密码，验证码是{code},验证码10分钟内有效,如非本人操作，请忽略本短信".format(code=sms_code).encode('gbk')
            SMS().send_sms(mobile, content)
            return Response({'code': 0, 'message': '发送成功'})
        elif request.data['action'] == '编辑':
            content = "您当前正在修改手机号，验证码是{code},验证码10分钟内有效,如非本人操作，请忽略本短信".format(code=sms_code).encode('gbk')
            SMS().send_sms(mobile, content)
            return Response({'code': 0, 'message': '发送成功'})
        else:
            return Response({'code': 1, 'message': 'ben'})

    # 数字验证码
    @action(detail=False, methods=['post'], url_path='verification')
    def verification(self, request, *args, **kwargs):
        validated = request.data['validated']
        # 调用函数generate_numb_code
        verification_code = generate_numb_code(4)
        # datetime.timedelta 时间差值1
        resend_time_obj = datetime.datetime.now() + datetime.timedelta(seconds=5 * 60)
        resend_time = resend_time_obj.strftime('%Y-%m-%d %H:%M:%S')
        # 存入redis 键 值 过期时间
        cache.set('v_%s' % validated,
                  {'verification_code': verification_code, 'resend_time': resend_time}, 5 * 60)
        return Response({"code": 0, "message": "ok", "detail": {'verificationCode': verification_code}},
                        status=status.HTTP_200_OK)

    # 邮箱验证码
    @action(detail=False, methods=['post'], url_path='email_code')
    def email_code(self, request, *args, **kwargs):
        email = request.data['email']
        action = request.data['action']
        if not re.match(r'^[A-Za-z0-9]+([_\.][A-Za-z0-9]+)*@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,6}$', email):
            return Response({"code": 1, "message": "邮箱格式错误"}, status=status.HTTP_200_OK)
        if cache.get('email_flag_%s' % email, None) is not None:
            return Response({'code': 2, 'message': '邮箱-请求过于频繁'})
        # 调用函数generate_numb_code
        email_code = generate_numb_code(4)
        cache.set('email_%s' % email, {'email_code': email_code}, 10 * 60, )
        cache.set('email_flag_%s' % email, {'email': email}, 60)
        if action == '注册':
            contents = '''
               <body>
                   <div  style="width: 500px; height: 380px; box-shadow: 0px 0px 7px -3px #999999; margin: 100px auto;overflow: hidden;">
                       <div style="width: 90%; height: 90%; border-top: 1px solid #6969694a; margin: 30px auto;">
                           <div style="margin: 20px auto 40px auto; width: 100%; height: auto; font-size: 16px; font-weight: 500;">
                               <p>感谢您使用青秀区科技计划项目管理平台</p >
                               <p>您的电子邮箱:
                                   <span>{}&nbsp;</span>
                               </p >
                           </div>
                           <div style=" width: 100%; height: 100px; background: #0064000d;overflow: hidden;">
                               <div style="width: 90%; height: auto; font-size: 14px; font-weight: 500; margin: 20px auto;">
                                   <p>验证码:
                                       <span>{}&nbsp;（10分钟内有效）</span>
                                   </p >
                                   <p>请妥善保存</p >
                               </div>
                           </div>
                           <div style="margin-top: 20px; font-size: 14px; color: #999999;">
                               <p>(此邮件为注册账号操作，如不是您本人操作，请忽略！)</p >
                               <p>此邮件由系统自动发出，请勿直接回复</p >
                           </div>
                       </div>
                   </div>
               </body>
               '''.format(email, email_code)
            SendEmailProcess(email, '青秀区科技计划项目管理平台', contents).start()
            return Response({'code': 0, 'message': '发送成功'})
        else:
            contents = '''
               <body>
                   <div  style="width: 500px; height: 380px; box-shadow: 0px 0px 7px -3px #999999; margin: 100px auto;overflow: hidden;">
                       <div style="width: 90%; height: 90%; border-top: 1px solid #6969694a; margin: 30px auto;">
                           <div style="margin: 20px auto 40px auto; width: 100%; height: auto; font-size: 16px; font-weight: 500;">
                               <p>感谢您使用青秀区科技计划项目管理平台</p >
                               <p>您的电子邮箱:
                                   <span>{}&nbsp;</span>
                               </p >
                           </div>
                           <div style=" width: 100%; height: 100px; background: #0064000d;overflow: hidden;">
                               <div style="width: 90%; height: auto; font-size: 14px; font-weight: 500; margin: 20px auto;">
                                   <p>验证码:
                                       <span>{}&nbsp;（10分钟内有效）</span>
                                   </p >
                                   <p>请妥善保存</p >
                               </div>
                           </div>
                           <div style="margin-top: 20px; font-size: 14px; color: #999999;">
                               <p>(此邮件为密码找回操作，如不是您本人操作，请及时修改密码！)</p >
                               <p>此邮件由系统自动发出，请勿直接回复</p >
                           </div>
                       </div>
                   </div>
               </body>
               '''.format(email, email_code)
            SendEmailProcess(email, '青秀区科技计划项目管理平台', contents).start()
            return Response({'code': 0, 'message': '发送成功'})

# 内部账号设置
class AccountSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializers
    queryset = User.objects.all()

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 小程序
    @action(detail=False, methods=['get'], url_path='small_program_list')
    def small_program_list(self, request, *args, **kwargs):
        lists = []
        queryset = self.queryset.order_by('-created').filter(Q(type='分管员') | Q(type='管理员'), isDelete=False)
        for i in queryset:
            if i.type == "管理员":
                data = {
                    "id": i.id,
                    "name": i.name,
                    "type": i.type,
                    "isActivation": i.isActivation,
                    "number": Subject.objects.exclude(subjectState='待提交').count()

                }
                lists.append(data)
            elif i.type == "分管员":
                data = {
                    "id": i.id,
                    "name": i.name,
                    "type": i.type,
                    "isActivation": i.isActivation,
                    "number": Subject.objects.exclude(subjectState='待提交').filter(project__charge=i).count()

                }
                lists.append(data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)


    """
    管理员
    """

    @action(detail=False, methods=['get'], url_path='detection_unit')
    def detection_unit(self, request, *args, **kwargs):
        instance = self.queryset.filter(id=request.query_params.dict().get("pk")).first()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # 查看账号是否存在
    @action(detail=False, methods=['post'], url_path='detection_username')
    def detection_username(self, request, *args, **kwargs):
        if self.queryset.filter(username=request.data['username']).exists():
            return Response({"code": 1, "message": "该账号已存在，请勿重复添加"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)

    # 科技局
    # 系统设置 用户信息展示
    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-created').filter(Q(type='分管员') | Q(type='管理员'), isDelete=False)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 系统设置 用户信息条件查询
    @action(detail=False, methods=['post'], url_path='conditions')
    def get_user_by_conditions(self, request):
        queryset = self.queryset.filter(Q(type='分管员') | Q(type='管理员'), isDelete=False)
        json_data = request.data
        keys = {
            "name": "name__contains",
            "type": "type",
            "isActivation": "isActivation",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.order_by('-created').filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 系统设置 user启用用户
    @action(detail=False, methods=['post'], url_path='enable')
    def enable(self, request):
        self.queryset.filter(id=request.data['userId']).update(isActivation='启用')
        return Response({'code': 0, 'message': '启用成功 已启用该用户'})

    # 系统设置 user禁用用户
    @action(detail=False, methods=['post'], url_path='disable')
    def disable(self, request):
        queryset = self.queryset.get(id=request.data['userId'])
        if queryset.type == '分管员':
            if queryset.charge_user.count() == 0:
                queryset.isActivation = '禁用'
                queryset.save()
                return Response({'code': 0, 'message': '禁用成功 已禁用该用户'}, status=status.HTTP_200_OK)
            else:
                project_id = queryset.charge_user.values('id')
                for i in project_id:
                    if not Subject.objects.filter(project_id=i['id']).exclude(project__charge=queryset.id).exists():
                        return Response({"code": 1, "message": "有正在执行的项目仅被该用户管理，请添加分管人员"}, status=status.HTTP_200_OK)
                queryset.isActivation = '禁用'
                queryset.save()
                return Response({'code': 0, 'message': '禁用成功 已禁用该用户', }, status=status.HTTP_200_OK)
                # subject_id = queryset.charge_user.values('id')
                # for i in subject_id:
                #     if not Subject.objects.get(id=i['id']).charge.exclude(id=request.data['userId']).exists():
                #         return Response({"code": 1, "message": "有正在执行的项目仅被该用户管理，请添加分管人员"}, status=status.HTTP_200_OK)
                # queryset.isActivation = '禁用'
                # queryset.save()
                # return Response({'code': 0, 'message': '禁用成功 已禁用该用户', }, status=status.HTTP_200_OK)
        elif queryset.type == '管理员':
            if self.queryset.exclude(id=request.data['userId']).filter(type='管理员', isActivation='启用').exists():
                queryset.isActivation = '禁用'
                queryset.save()
                return Response({'code': 0, 'message': '禁用成功 已禁用该用户'}, status=status.HTTP_200_OK)
            else:
                return Response({'code': 2, "message": "当前角色仅有一个有效账号，请在角色下新增有效账号后再禁用"}, status=status.HTTP_200_OK)

    # 删除用户
    def destroy(self, request, *args, **kwargs):
        queryset = self.get_object()
        if queryset.type == '分管员':
            if queryset.charge_user.count() == 0:
                queryset.isDelete = True
                queryset.username = queryset.username + '-' + str(queryset.id)
                queryset.save()
                return Response({'code': 0, 'message': '删除成功 已删除该用户'}, status=status.HTTP_200_OK)
            else:
                project_id = queryset.charge_user.values('id')
                for i in project_id:
                    if not Subject.objects.filter(project_id=i['id']).exclude(project__charge=queryset.id).exists():
                        return Response({"code": 1, "message": "该用户有正在执行的项目，请将项目移交管理"}, status=status.HTTP_200_OK)
                queryset.isDelete = True
                queryset.username = queryset.username + '-' + str(queryset.id)
                queryset.save()
                return Response({'code': 0, 'message': '删除成功 已删除该用户'}, status=status.HTTP_200_OK)
                # subject_id = queryset.charge_user.values('id')
                # for i in subject_id:
                #     if not Subject.objects.get(id=i['id']).charge.exclude(id=queryset.id).exists():
                #         return Response({"code": 1, "message": "该用户有正在执行的项目，请将项目移交管理"}, status=status.HTTP_200_OK)
                # queryset.isDelete = True
                # queryset.username = queryset.username + '-' + str(queryset.id)
                # queryset.save()
                # return Response({'code': 0, 'message': '删除成功 已删除该用户'}, status=status.HTTP_200_OK)
        elif queryset.type == '管理员':
            if self.queryset.exclude(id=queryset.id).filter(type='管理员', isActivation='启用').exists():
                queryset.isDelete = True
                queryset.username = queryset.username + '-' + str(queryset.id)
                queryset.save()
                return Response({'code': 0, 'message': '删除成功 已删除该用户'}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 2, "message": "当前角色仅有一个有效账号，请在角色下新增有效账号后再删除"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='detection')
    def detection(self, request, *args, **kwargs):
        if self.queryset.filter(CreditCode=request.data['CreditCode']).exists():
            return Response({"code": 1, "message": "该单位已存在，请勿重复添加"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)

    # 管理服务机构
    # 新增管理服务机构
    @action(detail=False, methods=['post'], url_path='agencies_create')
    def agencies_create(self, request, *args, **kwargs):
        logo_list = sorted([i['logo'] for i in
                            self.queryset.exclude(Q(type='管理员') | Q(type='分管员') | Q(type='企业') | Q(type='专家')).values(
                                'logo')])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        queryset = self.queryset.get(id=serializer.data['id'])
        self.queryset.exclude(Q(type='管理员') | Q(type='分管员') | Q(type='企业')).values('logo')
        if logo_list:
            logo = str(int(logo_list[-1]) + 1)
            if len(logo) < 2:
                queryset.logo = '0' + logo
                queryset.save()
            else:
                queryset.logo = logo
                queryset.save()
        else:
            queryset.logo = '01'
            queryset.save()
        return Response({"code": 0, "message": "新增成功"}, status=status.HTTP_201_CREATED, headers=headers)

    # 管理服务机构
    @action(detail=False, methods=['get'], url_path='agencies_show')
    def agencies_show(self, request, *args, **kwargs):
        queryset = self.queryset.order_by('-created').exclude(
            Q(type='管理员') | Q(type='分管员') | Q(type='企业') | Q(type='专家'))
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 禁用管理服务机构
    @action(detail=False, methods=['post'], url_path='agencies_disable')
    def agencies_disable(self, request):
        queryset = self.queryset.get(id=request.data['userId'])
        if queryset.agencies_user.filter(handOverState=False).exists():
            return Response({'code': 1, "message": "有正在执行的项目仅被该评估机构管理"}, status=status.HTTP_200_OK)
        else:
            queryset.isActivation = '禁用'
            queryset.save()
            return Response({'code': 0, 'message': '禁用成功 已禁用该用户'}, status=status.HTTP_200_OK)

    # 启用管理服务机构
    @action(detail=False, methods=['post'], url_path='agencies_enable')
    def agencies_enable(self, request):
        self.queryset.filter(id=request.data['userId']).update(isActivation='启用')
        return Response({'code': 0, 'message': '启用成功 已禁用该用户'}, status=status.HTTP_200_OK)

    # 查询管理服务机构
    @action(detail=False, methods=['post'], url_path='agencies_query')
    def agencies_query(self, request):
        queryset = self.queryset.exclude(Q(type='管理员') | Q(type='分管员') | Q(type='企业') | Q(type='专家'))
        json_data = request.data
        keys = {
            "name": "name__contains",
            "type": "type",
            "isActivation": "isActivation",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.order_by('-created').filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # no
    # 注册单位信息
    @action(detail=False, methods=['get'], url_path='enterprise')
    def get_enterprise(self, request):
        queryset = self.queryset.order_by('-created').filter(type='企业', isActivation='启用')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # no
    # 注册单位查询
    @action(detail=False, methods=['post'], url_path='enterprise_query')
    def enterprise_query(self, request):
        queryset = self.queryset.order_by('-created').filter(type='企业', isActivation='启用')
        json_data = request.data
        keys = {
            "name": "name__contains",
            "username": "username__contains",
            "industry": "enterprise__industry",
            "highTechEnterprise": "enterprise__highTechEnterprise",
            "smallMediumTechnologyEnterprises": "enterprise__smallMediumTechnologyEnterprises",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 分管员信息
    @action(detail=False, methods=['get'], url_path='charge_details')
    def get_charge_user_by_id(self, request):
        queryset = self.queryset.order_by('-created').filter(type='分管员', isDelete=False, isActivation='启用')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 评估机构信息
    @action(detail=False, methods=['get'], url_path='institutions_user_details')
    def get_institutions_user_by_id(self, request):
        queryset = self.queryset.order_by('-created').exclude(
            Q(type='管理员') | Q(type='分管员') | Q(type='专家') | Q(type='企业')).filter(
            isDelete=False, isActivation='启用')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # # 根据name 企业查看用户信息
    # @action(detail=False, methods=['post'], url_path='search')
    # def search_unit_name(self, request):
    #     unit = User.objects.filter(name=request.data['name'], isActivation='启用')
    #     if unit:
    #         serializer = self.get_serializer(unit, many=True)
    #         return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
    #     else:
    #         return Response({'code': 1, 'message': '不存在'}, status=status.HTTP_200_OK)

    # 评估机构专家\企业 ----修改密码
    @action(detail=False, methods=['post'], url_path='change_password')
    def change_password(self, request):
        user = request.user
        credentials = {
            'username': user.username,
            'password': request.data['oldPassword']
        }
        users = authenticate(**credentials)
        if users:
            if re.match(r'^(?=.*\d)(?=.*[a-zA-Z]).{12,24}$', request.data['newPassword']):
                if request.data['newPassword'] == request.data['confirmPassword']:
                    user.set_password(request.data['newPassword'])
                    user.save()
                    return Response({"code": 0, "message": "修改密码成功"}, status=status.HTTP_200_OK)
                else:
                    return Response({"code": 3, "message": "两次密码输入不一致"}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 2, "message": "密码必须包含字母和数字"}, status=status.HTTP_200_OK)

        else:
            return Response({"code": 1, "message": "原密码错误"}, status=status.HTTP_200_OK)


# 评估机构专家
class PExpertsViewSet(viewsets.ModelViewSet):
    serializer_class = PExpertsSerializers
    queryset = PExperts.objects.all()

    # # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        birthday = str(serializer.validated_data['birthday']).split('-')
        name = getPinyin(serializer.validated_data['name'])
        password = name + birthday[0] + birthday[1] + birthday[2]
        username = user.logo + serializer.validated_data['mobile']
        if User.objects.filter(username=username, isDelete=False).exists():
            return Response({'code': 1, 'message': '专家已存在'}, status=status.HTTP_200_OK)
        else:
            self.perform_create(serializer)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.ratingAgencies = user.id
            queryset.save()
            user = User.objects.create(username=username,
                                       name=serializer.validated_data['name'], isActivation='启用', type='专家',
                                       mobile=serializer.validated_data['mobile'],
                                       experts=queryset
                                       )
            user.set_password(password)
            user.save()
            a = expert_register(email=request.data['email'], username=username, password=password)
            return Response({'code': 0, 'message': '新增成功'}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        username = request.user.logo + request.data['mobile']
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if instance.mobile != request.data['mobile'] and User.objects.filter(username=username).exists():
            return Response({"code": 1, "message": "专家已存在"}, status.HTTP_200_OK, )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        user = User.objects.get(experts_id=serializer.data['id'])
        if user.username == username and user.password == request.data['password']:
            instance.user_set.update(name=request.data['name'])
            return Response({"code": 0, "message": "保存成功"}, status.HTTP_200_OK)
        elif user.username != username and user.password == request.data['password']:
            instance.user_set.update(username=username, mobile=request.data['mobile'], name=request.data['name'])
            expert_editor(email=request.data['email'], username=username, password='为原密码')
            return Response({"code": 0, "message": "保存成功，账号和密码已发送给专家"}, status.HTTP_200_OK, )
        elif user.username == username and user.password != request.data['password']:
            instance.user_set.update(username=username, mobile=request.data['mobile'], name=request.data['name'])
            user.set_password(request.data['password'])
            user.save()
            expert_editor(email=request.data['email'], username=username, password=request.data['password'])
            return Response({"code": 0, "message": "保存成功，账号和密码已发送给专家"}, status.HTTP_200_OK, )
        elif user.username != username and user.password != request.data['password']:
            instance.user_set.update(username=username, mobile=request.data['mobile'], name=request.data['name'])
            user.set_password(request.data['password'])
            user.save()
            expert_editor(email=request.data['email'], username=username, password=request.data['password'])
            return Response({"code": 0, "message": "保存成功，账号和密码已发送给专家"}, status.HTTP_200_OK, )
        return Response(True)

    # 专家库专家列表信息展示/评估机构
    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        agencies = request.user
        queryset = self.queryset.order_by('-created').filter(ratingAgencies=agencies.id, isDelete=False)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 专家库列表查询/评估机构
    @action(detail=False, methods=['post'], url_path='p_experts_query')
    def p_experts_query(self, request):
        agencies = request.user
        p_experts = self.queryset.filter(ratingAgencies=agencies.id, isDelete=False)
        json_data = request.data
        keys = {
            "gender": "gender",
            "title": "title__contains",
            "name": "name__contains",
            "mobile": "mobile__contains",
            "unit": "unit__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = p_experts.order_by('-created').filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评估机构专家信息导入/评估机构
    @action(detail=False, methods=['post'], url_path='import_p_experts')
    def import_p_experts(self, request):
        agencies = request.user
        file_excel = request.data['fileExcel']
        # 开始解析上传的excel表格
        wb = xlrd.open_workbook(filename=None, file_contents=file_excel.read())
        # 获取工作表
        table = wb.sheets()[0]
        # 总行数  nrows = table.nrows
        # 总列数  ncols = table.ncols
        n = 1
        repeat = []
        m_format = []
        no_data = []
        # nrows = table.nrows #行数 ncols = table.ncols #列数 print sh.row_values(rownum)
        for line in range(n, table.nrows):
            row = table.row_values(line)
            # 查看行值是否为空
            if row and len(row) == 10:
                if row[1] == ' ':
                    continue
                if type(row[3]) == float or type(row[3]) == str:
                    row[3] = int(row[3])
                    if not re.match(r'1[3456789]\d{9}', str(row[3])):
                        m_format.append(row)
                        continue
                    if not re.match(r'^[A-Za-z0-9]+([_\.][A-Za-z0-9]+)*@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,6}$',
                                    str(row[4])):
                        m_format.append(row)
                        continue
                    if not '-' in str(row[2]):
                        m_format.append(row)
                        continue
                    try:
                        time.strptime(row[2], "%Y-%m-%d")
                    except Exception as e:
                        m_format.append(row)
                        continue
                    # 判断该行值是否在数据库中重复
                    username = agencies.logo + str(int(row[3]))
                    if User.objects.filter(username=username, isDelete=False).exists():
                        # 重复值计数
                        repeat.append(row)
                        continue
                    else:
                        paword = str(row[2]).split('-')
                        name = getPinyin(row[0])
                        password = name + paword[0] + paword[1] + paword[2]
                        p_experts = PExperts.objects.create(name=row[0], gender=row[1], birthday=row[2],
                                                            email=row[4],
                                                            mobile=row[3],
                                                            unit=row[5], title=row[6], position=row[7],
                                                            learnProfessional=row[8],
                                                            engagedProfessional=row[9],
                                                            ratingAgencies=agencies.id)
                        user = User.objects.create(username=username, name=row[0], isActivation='启用', type='专家',
                                                   mobile=row[3])
                        user.experts = p_experts
                        user.set_password(password)
                        user.save()
                        a = expert_register(email=row[4], username=username, password=password)
            else:
                no_data.append(row)
        data = {
            'repeat': repeat,
            'no_data': no_data,
            'm_format': m_format,
        }
        if repeat or no_data or m_format:
            return Response({"code": 1, "message": "专家信息部分导入成功", "detail": data}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "专家信息全部导入成功"}, status=status.HTTP_200_OK)

    # 待指派项目
    # 选择专家列表查询（评估机构系统）
    @action(detail=False, methods=['post'], url_path='choose_p_experts_query')
    def choose_p_experts_query(self, request):
        lists = []
        p_experts_id = request.data['expertsId']
        # p_experts_id = literal_eval(p_experts_id)
        agencies = request.user
        experts = PExperts.objects.filter(ratingAgencies=agencies.id, isDelete=False)
        json_data = request.data
        keys = {
            "name": "name__contains",
            "unit": "unit__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != ''}
        queryset = experts.exclude(id__in=p_experts_id).filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        # lists.extend(serializers.data)
        # for i in p_experts_id:
        #     for j in lists:
        #         if i == j['id']:
        #             lists.remove(j)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理 已选择专家
    @action(detail=False, methods=['get'], url_path='group_p_experts_show')
    def group_p_experts_show(self, request):
        lists = []
        list2 = []
        agencies = request.user
        agencies_subject = Subject.objects.filter(state='未评审', agencies=agencies,
                                                  subjectState='专家评审', assignWay='按组指派')
        json_data = request.query_params.dict()
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject_obj = agencies_subject.filter(**data)
        for subject in subject_obj:
            subject_experts_opinion_sheet = SubjectExpertsOpinionSheet.objects.filter(subject=subject)
            for j in subject_experts_opinion_sheet:
                lists.append(j.pExperts_id)
        lists = list(set(lists))
        for pExperts_id in lists:
            p_experts_user = User.objects.get(id=pExperts_id)
            queryset = self.queryset.filter(id=p_experts_user.experts_id)
            serializers = self.get_serializer(queryset, many=True)
            list2.extend(serializers.data)
        return Response({"code": 0, "message": "ok", "detail": list2}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理 选择专家列表查询
    @action(detail=False, methods=['post'], url_path='group_choose_pg_experts_query')
    def group_choose_pg_experts_query(self, request):
        p_experts_id = request.data['expertsId']
        agencies = request.user
        json_data = request.data
        key = {
            "name": "name__contains",
            "unit": "unit__contains",
        }
        data = {key[k]: v for k, v in json_data.items() if k in key and json_data[k] != '全部' and json_data[k] != ''}
        queryset = self.queryset.exclude(id__in=p_experts_id).filter(**data, ratingAgencies=agencies.id, isDelete=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 评审管理
    # 单项指派-评审管理 已指派专家展示
    @action(detail=False, methods=['post'], url_path='single_p_experts_show')
    def single_p_experts_show(self, request):
        lists = []
        subject_id = request.data['subjectId']
        subject_experts_opinion_sheet = SubjectExpertsOpinionSheet.objects.filter(subject_id=subject_id)
        for i in subject_experts_opinion_sheet:
            p_experts = self.queryset.get(id=i.pExperts.experts.id)
            serializer = self.get_serializer(p_experts)
            lists.append(serializer.data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 评审管理
    # 单项指派-评审管理 选择专家列表查询/展示
    @action(detail=False, methods=['post'], url_path='single_choose_p_experts_query')
    def single_choose_p_experts_query(self, request):
        agencies = request.user
        p_experts_id = request.data['expertsId']
        json_data = request.data
        keys = {
            "name": "name__contains",
            "unit": "unit__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        p_experts = self.queryset.exclude(id__in=p_experts_id).filter(**data, ratingAgencies=agencies.id,
                                                                      isDelete=False)
        serializer = self.get_serializer(p_experts, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 管理员
    # 建祖指派指派详情展示-专家
    @action(detail=False, methods=['get'], url_path='expert_review_group_details_show')
    def expert_review_group_details_show(self, request):
        lists = []
        list2 = []
        subject_obj = Subject.objects.filter(projectTeamLogo=request.query_params.dict().get('projectTeamLogo'))
        for subject in subject_obj:
            subject_experts_opinion_sheet = SubjectExpertsOpinionSheet.objects.filter(subject=subject)
            for j in subject_experts_opinion_sheet:
                lists.append(j.pExperts_id)
        lists = list(set(lists))
        for pExperts_id in lists:
            p_experts_user = User.objects.get(id=pExperts_id)
            queryset = self.queryset.filter(id=p_experts_user.experts_id)
            serializers = self.get_serializer(queryset, many=True)
            list2.extend(serializers.data)
        return Response({"code": 0, "message": "ok", "detail": list2}, status=status.HTTP_200_OK)

    # 管理员
    # 建祖指派指派详情查询-专家
    @action(detail=False, methods=['post'], url_path='expert_review_group_details_query')
    def expert_review_group_details_query(self, request):
        lists = []
        list2 = []
        json_data = request.data
        keys = {
            "name": "name",
            "unit": "unit",
            "title": "title",
            "position": "position",
            "learnProfessional": "learnProfessional",
            "engagedProfessional": "engagedProfessional",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject_obj = Subject.objects.filter(projectTeamLogo=request.data['projectTeamLogo'])
        for subject in subject_obj:
            subject_experts_opinion_sheet = SubjectExpertsOpinionSheet.objects.filter(subject=subject)
            for j in subject_experts_opinion_sheet:
                lists.append(j.pExperts_id)
        lists = list(set(lists))
        for pExperts_id in lists:
            p_experts_user = User.objects.get(id=pExperts_id)
            queryset = self.queryset.filter(**data, id=p_experts_user.experts_id)
            serializers = self.get_serializer(queryset, many=True)
            list2.extend(serializers.data)
        return Response({"code": 0, "message": "ok", "detail": list2}, status=status.HTTP_200_OK)


# 科技局专家
class KExpertsViewSet(viewsets.ModelViewSet):
    serializer_class = KExpertsSerializers
    queryset = KExperts.objects.all()

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    """
    管理员
    """

    # 系统设置 科技局专家信息导入/管理员
    @action(detail=False, methods=['post'], url_path='import_k_experts')
    def import_k_experts(self, request):
        file_excel = request.data['fileExcel']
        # 开始解析上传的excel表格
        wb = xlrd.open_workbook(filename=None, file_contents=file_excel.read())
        # 获取工作表
        table = wb.sheets()[0]
        # 总行数  nrows = table.nrows
        # 总列数  ncols = table.ncols
        n = 1
        # 错误数据
        wrong_data = []
        # nrows = table.nrows #行数 ncols = table.ncols #列数 print sh.row_values(rownum)
        for line in range(n, table.nrows):
            row = table.row_values(line)

            # 查看行值是否为空
            if row and len(row) == 10:
                if row[1] == ' ':
                    continue
                if type(row[3]) == float or type(row[3]) == str:
                    row[3] = int(row[3])
                    if not re.match(r'1[3456789]\d{9}', str(row[3])):
                        wrong_data.append(row)
                        continue
                    if not '@' in row[4]:
                        wrong_data.append(row)
                        continue
                    # 判断该行值是否在数据库中重复
                    if KExperts.objects.filter(mobile=row[3], isDelete=False).exists():
                        # 重复值计数
                        wrong_data.append(row)
                        continue
                    if row[0] and row[1] and row[2] and row[3] and row[4] and row[5] and row[6] and row[7] and row[
                        8] and row[9]:

                        KExperts.objects.create(name=row[0], gender=row[1], birthday=row[2], email=row[4],
                                                mobile=row[3], unit=row[5], title=row[6], position=row[7],
                                                learnProfessional=row[8], engagedProfessional=row[9])
                        # WorkList.append(KExperts(name=row[0], gender=row[1], birthday=row[2], email=row[4],
                        #                          mobile=row[3], unit=row[5], title=row[6], position=row[7],
                        #                          learnProfessional=row[8], engagedProfessional=row[9]))
                    else:
                        wrong_data.append(row)
            else:
                wrong_data.append(row)
        # KExperts.objects.bulk_create(WorkList)
        if wrong_data:
            return Response(wrong_data)
        else:
            return Response({"code": 0, "message": "导入成功"}, status=status.HTTP_200_OK)

    # 系统设置 科技局专家信息展示/管理员
    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(isDelete=False)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 系统设置 删除科技局专家/管理员
    @action(detail=False, methods=['delete'], url_path='k_experts_delete')
    def k_experts_delete(self, request, *args, **kwargs):
        lists = []
        k_experts_id = request.data['expertsId']
        for i in k_experts_id:
            queryset = self.queryset.get(id=i)
            if SubjectKExperts.objects.filter(kExperts_id=i).exclude(
                    Q(subject__subjectState='验收通过') | Q(subject__subjectState='验收不通过') | Q(
                        subject__subjectState='项目终止') | Q(
                        subject__subjectState='项目退回')).exists():
                lists.append(queryset.name)
            else:
                queryset.isDelete = True
                queryset.save()
        if len(lists) == 0:
            return Response({'code': 0, 'message': '删除成功'}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, "message": "项目评审完成后方可删除该专家", "detail": lists}, status=status.HTTP_200_OK)

    # 科技局专家条件查询/管理员
    @action(detail=False, methods=['post'], url_path='query')
    def query_k_experts(self, request):
        queryset = self.queryset.filter(isDelete=False)
        json_data = request.data
        keys = {
            "name": "name__contains",
            "gender": "gender",
            "mobile": "mobile__contains",
            "unit": "unit__contains",
            "title": "title__contains",
            "engaged_professional": "engaged_professional__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    """
    分管人员
    """

    # 结题验收 指派专家条件查询/分管员
    @action(detail=False, methods=['post'], url_path='chang_user_query')
    def chang_user_query(self, request):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(isDelete=False)
        json_data = request.data
        keys = {
            "name": "name__contains",
            "unit": "unit__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.exclude(id__in=request.data['kExpertsId']).filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 结题验收 调整指派专家查询/分管员
    @action(detail=False, methods=['post'], url_path='chang_user_assigned_query')
    def chang_user_assigned_query(self, request):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(isDelete=False)
        json_data = request.data
        keys = {
            "name": "name__contains",
            "unit": "unit__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        k_experts_obj = queryset.exclude(id__in=request.data['kExpertsId']).filter(**data)
        page = self.paginate_queryset(k_experts_obj)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(k_experts_obj, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)


# 管理服务机构
class AgencyViewSet(viewsets.ModelViewSet):
    queryset = Agency.objects.all()
    serializer_class = AgencySerializers

    # # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        json_data = request.query_params
        keys = {
            "name": "name__contains",
            "creditCode": "creditCode__contains",
            "permissions": "permissions"

        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != '' and json_data[k] != '空'}
        if request.query_params.dict().get("permissions") == "空":
            queryset = self.queryset.order_by("-created").exclude(permissions__in=[1, 2]).filter(**data)
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return Response({"code": 0, "message": "ok", "detail": serializer.data})

            serializer = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            queryset = self.queryset.order_by("-created").filter(**data)
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return Response({"code": 0, "message": "ok", "detail": serializer.data})

            serializer = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # def update(self, request, *args, **kwargs):
    #     # permissions_list = literal_eval(request.data['permissions'])
    #     permissions_list = request.data['permissions']
    #     instance = self.get_object()
    #     if instance.permissions.count() != 0:
    #         instance.permissions.clear()
    #     for i in permissions_list:
    #         permissions = Permissions.objects.filter(id=i).first()
    #         instance.permissions.add(permissions)
    #     return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        # permissions_list = set(literal_eval(request.data['permissions']))
        permissions_list = set(request.data['permissions'])
        instance = self.get_object()
        if instance.permissions.count() == 0 or len(permissions_list) == 2:
            for i in permissions_list:
                permissions = Permissions.objects.filter(id=i).first()
                instance.permissions.add(permissions)
            return Response({"code": 0, "message": "ok1"}, status=status.HTTP_200_OK)
        else:
            m = 0
            n = 0
            user = User.objects.filter(agency=instance).first()
            if len(permissions_list) == 0:
                if user.agencies_user.filter(subjectState="专家评审").count() == 0:
                    m += 1
                    permissions = Permissions.objects.filter(id=1).first()
                    instance.permissions.remove(permissions)
                if SubjectConcluding.objects.exclude(
                        Q(concludingState="结题复核") | Q(concludingState="验收不通过") | Q(concludingState="验收通过")). \
                        filter(agency=user).count() == 0 and SubjectTermination.objects. \
                        exclude(Q(terminationState="终止不通过") | Q(terminationState="项目终止")).filter(agency=user). \
                        count() == 0:
                    n += 1
                    permissions = Permissions.objects.filter(id=2).first()
                    instance.permissions.remove(permissions)
                if m == 0 and n == 0:
                    return Response({"code": 3, "message": "该机构有未完成的立项评估和结题终止项目，无法撤销权限"}, status=status.HTTP_200_OK)
                elif m == 0 and n == 1:
                    return Response({"code": 2, "message": "该机构有未完成的立项评估项目，无法撤销其立项评估管理权限"}, status=status.HTTP_200_OK)
                elif m == 1 and n == 1:
                    return Response({"code": 0, "message": "okx"}, status=status.HTTP_200_OK)
                elif m == 1 and n == 0:
                    return Response({"code": 1, "message": "该机构有未完成的结题终止项目，无法撤销其结题终止管理权限"}, status=status.HTTP_200_OK)
            else:
                permissions_set = set([i.id for i in instance.permissions.all()])
                permissions = permissions_set - permissions_list
                if len(list(permissions)) != 0:
                    for j in list(permissions):
                        if j == 1:
                            if user.agencies_user.filter(subjectState="专家评审").count() != 0:
                                return Response({"code": 1, "message": "该机构有未完成的立项评估项目，无法撤销其立项评估管理权限"}, status=status.HTTP_200_OK)
                            else:
                                permissions = Permissions.objects.filter(id=j).first()
                                instance.permissions.remove(permissions)
                                return Response({"code": 0, "message": "ok2"}, status=status.HTTP_200_OK)
                        else:
                            if SubjectConcluding.objects.exclude(
                                    Q(concludingState="结题复核") | Q(concludingState="验收不通过") | Q(concludingState="验收通过")). \
                                    filter(agency=user).count() != 0 or SubjectTermination.objects. \
                                    exclude(Q(terminationState="终止不通过") | Q(terminationState="项目终止")).filter(agency=user). \
                                    count() != 0:
                                return Response({"code": 2, "message": "该机构有未完成的结题终止项目，无法撤销其结题终止管理权限"}, status=status.HTTP_200_OK)
                            else:
                                permissions = Permissions.objects.filter(id=j).first()
                                instance.permissions.remove(permissions)
                                return Response({"code": 0, "message": "ok3"}, status=status.HTTP_200_OK)
                return Response({"code": 0, "message": "ok4"}, status=status.HTTP_200_OK)

    # 评估机构信息
    @action(detail=False, methods=['get'], url_path='agency_show')
    def agency_show(self, request):
        lists = []
        permissions = request.query_params.dict().get('permissions')
        new_time = datetime.date.today()
        if permissions == "1":
            queryset = self.queryset.filter(permissions=1)
            for i in queryset:
                if AgenciesBlacklist.objects.filter(creditCode=i.creditCode, isArchives=False,
                                                    disciplinaryTime__gt=new_time).exists():
                    pass
                else:
                    serializer = self.get_serializer(i)
                    lists.append(serializer.data)
            return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)
        elif permissions == "2":
            queryset = self.queryset.filter(permissions=2)
            for i in queryset:
                if AgenciesBlacklist.objects.filter(creditCode=i.creditCode, isArchives=False,
                                                    disciplinaryTime__gt=new_time).exists():
                    pass
                else:
                    serializer = self.get_serializer(i)
                    lists.append(serializer.data)

            return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok", "detail": {}}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='initial_data')
    def initial_data(self, request, *args, **kwargs):
        user = request.user
        data = {
            "id": user.agency.id,
            "name": user.agency.name,
            "creditCode": user.agency.creditCode,
            "contact": user.agency.contact,
            "mobile": user.agency.mobile,
            "qualification": user.agency.qualification,
            "businessLicense": user.agency.businessLicense,
        }
        return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put'], url_path='modify')
    def modify(self, request, *args, **kwargs):
        instance = self.queryset.filter(id=request.data['id']).first()
        if request.data['mobile'] == instance.mobile:
            instance.contact = request.data['contact']
            instance.qualification = request.data['qualification']
            instance.save()
            return Response({"code": 0, "message": "修改成功"}, status=status.HTTP_200_OK)
        else:
            if not re.match(r'1[3456789]\d{9}', request.data['mobile']):
                return Response({'code': 0, "message": '请输入正确的联系电话'}, status=status.HTTP_200_OK)
            if request.data["smsCode"] == '':
                return Response({'code': 0, "message": '请输入手机验证码'}, status=status.HTTP_200_OK)
            if cache.get('sms_%s' % request.data['mobile'], None) is None:
                return Response({'code': 0, "message": '验证码失效，请重新获取验证码'}, status=status.HTTP_200_OK)
            if cache.get('sms_%s' % request.data['mobile'])['sms_code'] != request.data["smsCode"]:
                return Response({'code': 0, "message": '验证码错误'}, status=status.HTTP_200_OK)
            instance.contact = request.data['contact']
            instance.qualification = request.data['qualification']
            instance.mobile = request.data['mobile']
            instance.save()
            return Response({"code": 0, "message": "修改成功"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put'], url_path='reset_password')
    def reset_password(self, request, *args, **kwargs):
        user = request.user
        if user.check_password(request.data['password']):
            if request.data['newPassword'] != '' or request.data['confirmPassword'] != '':
                if request.data['newPassword'] == request.data['confirmPassword']:
                    user.set_password(request.data['newPassword'])
                    user.save()
                    return Response({"code": 0, "message": "重置密码成功"}, status=status.HTTP_200_OK)
                else:
                    return Response({"code": 3, "message": "两次密码输入不一致"}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 2, "message": "信息填写不完整"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, "message": "原密码不正确"}, status=status.HTTP_200_OK)
