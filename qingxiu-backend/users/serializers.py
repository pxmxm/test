import re

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db.models import Q
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from backend.exceptions import CustomValidationError
from subject.models import Subject
from users.models import User, Enterprise, KExperts, PExperts, Agency, Permissions


# 用户登录
class CustomJSONWebTokenSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False, label='账号')
    password = serializers.CharField(required=True, allow_blank=False, label='密码')
    type = serializers.CharField(required=True, allow_blank=False, label='账户类型')
    validated = serializers.CharField(required=True, allow_blank=False, label='验证码标识')
    verificationCode = serializers.CharField(required=True, allow_blank=False, label='验证码')

    def increase_login_try_attempts(self, username):
        """
        增加密码登陆尝试次数
        :param username:
        :return:
        """
        login_try = cache.get('login_try_%s' % username, None)
        print(login_try)
        if login_try is None:
            cache.set('login_try_%s' % username, 0, 60 * 15)
            return True
        elif int(login_try) < 5:
            cache.set('login_try_%s' % username, int(login_try) + 1, 60 * 15)
            return True
        else:
            return False

    def clean_login_try_attempts(self, username):
        """
        清空登陆尝试次数
        :param username:
        :return:
        """
        login_try = cache.get('login_try_%s' % username, None)
        if login_try is None:
            pass
        else:
            cache.delete('login_try_%s' % username)

    # 密码校验
    def password_login(self, attrs):
        if attrs['type'] == '评估机构':
            if attrs['username']:
                credentials = {
                    'username': attrs['username']+'3',
                    'password': attrs['password']
                }
                user = authenticate(**credentials)
                if user is None or user.isDelete is True:
                    raise CustomValidationError(detail={"code": 1, 'message': '账号密码错误'})
                if user.type != '企业' and user.isActivation == '禁用':
                    raise CustomValidationError(detail={"code": 2, 'message': '该账号已被禁用，请联系管理员启用后再登录'})
                else:
                    self.clean_login_try_attempts(attrs['username']+'3')
                    return attrs
        else:
            if attrs['username']:
                credentials = {
                    'username': attrs['username'],
                    'password': attrs['password']
                }
                user = authenticate(**credentials)
                if user is None or user.isDelete is True:
                    raise CustomValidationError(detail={"code": 1, 'message': '账号密码错误'})
                if user.type != '企业' and user.isActivation == '禁用':
                    raise CustomValidationError(detail={"code": 2, 'message': '该账号已被禁用，请联系管理员启用后再登录'})
                else:
                    self.clean_login_try_attempts(attrs['username'])
                    return attrs

    def validate(self, attrs):
        self.password_login(attrs)
        if cache.get('v_%s' % attrs['validated'], None) is None:
            raise CustomValidationError(detail={"code": 6, 'message': '验证码过期，请刷新验证码后重新输入'})
        if cache.get('v_%s' % attrs['validated'])['verification_code'] != attrs['verificationCode']:
            raise CustomValidationError(detail={"code": 7, 'message': '验证码错误'})
        if attrs['type'] == '评估机构':
            if self.increase_login_try_attempts(attrs['username']+'3'):
                return attrs
            else:
                raise CustomValidationError(detail={'error_code': '登陆尝试次数过多,请稍后再试！'})
        else:
            if self.increase_login_try_attempts(attrs['username']):
                users = User.objects.get(username=attrs['username'])
                if users.type == '分管员' or users.type == '管理员':
                    if attrs.get('type') != '科技局':
                        raise CustomValidationError(detail={"code": 5, 'message': '请登录自己的系统'})
                else:
                    if attrs.get('type') != users.type:
                        raise CustomValidationError(detail={"code": 5, 'message': '请登录自己的系统'})
                return attrs
            else:
                raise CustomValidationError(detail={'error_code': '登陆尝试次数过多,请稍后再试！'})

class PermissionsSerializers(serializers.ModelSerializer):
    class Meta:
        model = Permissions
        fields = '__all__'


# 企业信息
class EnterpriseSerializers(serializers.ModelSerializer):
    highTechEnterprise = serializers.BooleanField()
    smallMediumTechnologyEnterprises = serializers.BooleanField()

    class Meta:
        model = Enterprise
        fields = '__all__'


# 注册
class RegisteredSerializers(serializers.ModelSerializer):
    smsCode = serializers.CharField(required=True, allow_blank=False, write_only=True, min_length=4, max_length=4,
                                    help_text='短信验证码', error_messages={'blank': '请输入验证码',
                                                                       'required': '请输入验证码',
                                                                       'min_length': '验证码格式错误',
                                                                       'max_length': '验证码格式错误',
                                                                       })
    password2 = serializers.CharField(label='校验密码', allow_null=False, allow_blank=False, write_only=True, )
    password = serializers.CharField(required=True, allow_blank=False, write_only=True, min_length=12, max_length=24,
                                     error_messages={
                                         'min_length': '仅允许12个字符的密码',
                                         'max_length': '仅允许24个字符的密码',
                                     })
    businessLicense = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = '__all__'

    # 校验短信密码
    def validate_smsCode(self, smsCode):
        if not re.match(r'1[3456789]\d{9}', self.initial_data['mobile']):
            raise CustomValidationError(detail={'code': 2, "message": '请输入正确的联系电话'})
        if cache.get('sms_%s' % self.initial_data['mobile'], None) is None:
            raise CustomValidationError(detail={'code': 3, 'message': '验证码失效，请重新获取验证码'})
        if cache.get('sms_%s' % self.initial_data['mobile'])['sms_code'] != smsCode:
            raise CustomValidationError(detail={'code': 4, 'message': '验证码错误'})

    def validate(self, attrs):
        if not re.match(r'^(?=.*\d)(?=.*[a-zA-Z]).{12,24}$', self.initial_data["password"]):
            raise CustomValidationError(detail={'code': 5, 'message': '密码必须包含字母和数字'})
        if self.initial_data["password"] != attrs['password2']:
            raise CustomValidationError(detail={'code': 6, 'message': '两次密码输入不一致'})
        del attrs['password2'], attrs['smsCode'],
        return attrs


# 验证码序列化
class SmsCodeSerializers(serializers.Serializer):
    mobile = serializers.CharField(required=True)

    def validate_mobile(self, mobile):
        if not re.match(r'^1[3456789]\d{9}$', mobile):
            raise CustomValidationError(detail={'code': 1, 'message': '手机格式不正确'})
            # raise serializers.ValidationError({'message': '手机格式不正确'})
        if cache.get('sms_flag_%s' % mobile):
            raise CustomValidationError(detail={'code': 2, 'message': '获取频率超出预期'})
            # raise serializers.ValidationError({'message': '获取频率超出预期'})


# 忘记密码
class ForgotPasswordSerializers(serializers.Serializer):
    username = serializers.CharField(label='信用代码', allow_null=False, allow_blank=False, write_only=True, )
    password2 = serializers.CharField(label='校验密码', allow_null=False, allow_blank=False, write_only=True, )
    mobile = serializers.CharField(label='手机号', allow_null=False, allow_blank=False, write_only=True, )
    contact = serializers.CharField(label='联系人', allow_null=False, allow_blank=False, write_only=True, )
    name = serializers.CharField(label='单位名称', allow_null=False, allow_blank=False, write_only=True, )
    password = serializers.CharField(label='首次密码', allow_null=False, allow_blank=False, write_only=True, )
    smsCode = serializers.CharField(label='短信验证码', allow_null=False, allow_blank=False, write_only=True, )
    email = serializers.CharField(label='电子邮箱', allow_null=False, allow_blank=False, write_only=True)

    # 校验短信密码
    def validate_smsCode(self, smsCode):
        if cache.get('sms_%s' % self.initial_data['mobile'], None) is not None:
            if cache.get('sms_%s' % self.initial_data['mobile'])['sms_code'] != smsCode:
                raise CustomValidationError(detail={'code': 1, 'message': '短信-验证码错误'})
        else:
            raise CustomValidationError(detail={'code': 2, 'message': '短信-验证码无效'})

    def validate(self, attrs):
        if not User.objects.filter(username=self.initial_data['username'], name=self.initial_data['name']).exists():
            raise CustomValidationError(detail={'code': 3, 'message': '该单位未通过注册，请前往注册'})
        user = User.objects.get(username=self.initial_data['username'])
        if user.contact != self.initial_data['contact']:
            raise CustomValidationError(detail={'code': 4, 'message': '提交的信息与注册时填写的信息不一致，请重新输入'})
        if user.mobile != str(self.initial_data['mobile']):
            raise CustomValidationError(detail={'code': 4, 'message': '提交的信息与注册时填写的信息不一致，请重新输入'})
        if user.email != self.initial_data['email']:
            raise CustomValidationError(detail={'code': 4, 'message': '提交的信息与注册时填写的信息不一致，请重新输入'})
        if self.initial_data["password"] != attrs['password2']:
            raise CustomValidationError(detail={'code': 5, 'message': '两次密码输入不一致'})
        user.set_password(self.initial_data['password'])
        user.save()
        return attrs


# 重置密码
class ResetPasswordSerializers(serializers.Serializer):
    name = serializers.CharField(label='单位名称', allow_null=False, allow_blank=False, write_only=True, )
    username = serializers.CharField(label='信用代码', allow_null=False, allow_blank=False, write_only=True, )
    mobile = serializers.CharField(label='手机号', allow_null=False, allow_blank=False, write_only=True, )
    smsCode = serializers.CharField(label='短信验证码', allow_null=False, allow_blank=False, write_only=True, )
    password = serializers.CharField(label='首次密码', allow_null=False, allow_blank=False, write_only=True, )
    password2 = serializers.CharField(label='校验密码', allow_null=False, allow_blank=False, write_only=True, )

    # 校验短信密码
    def validate_smsCode(self, smsCode):
        if not re.match(r'^1[3456789]\d{9}$', self.initial_data['mobile']):
            raise CustomValidationError(detail={'code': 1, 'message': '请填写11位联系电话'})
        if cache.get('sms_%s' % self.initial_data['mobile'], None) is not None:
            if cache.get('sms_%s' % self.initial_data['mobile'])['sms_code'] != smsCode:
                raise CustomValidationError(detail={'code': 2, 'message': '验证码错误'})
        else:
            raise CustomValidationError(detail={'code': 3, 'message': '验证码失效，请重新获取验证码'})

    def validate(self, attrs):
        if self.initial_data["password"] != attrs['password2']:
            raise CustomValidationError(detail={'code': 5, 'message': '两次密码输入不一致'})
        if not User.objects.filter(username=self.initial_data['username']+'3',
                                   agency__name=self.initial_data['name']).exists():
            raise CustomValidationError(detail={'code': 3, 'message': '与注册时提交的信息不一致，请确认后重新填写'})
        user = User.objects.filter(username=self.initial_data['username']+'3',
                                   agency__name=self.initial_data['name']).first()
        user.set_password(self.initial_data['password'])
        user.save()
        return attrs


# 科技局专家
class KExpertsSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    # mobile = serializers.CharField(required=True, allow_blank=False,
    #                                validators=[UniqueValidator(queryset=KExperts.objects.all(), message='专家已存在')])

    class Meta:
        model = KExperts
        fields = (
            'id', 'name', 'gender', 'birthday', 'email', 'mobile', 'unit', 'title', 'position', 'learnProfessional',
            'engagedProfessional', 'created', 'updated')

    def create(self, validated_data):
        if KExperts.objects.filter(mobile=validated_data['mobile'], isDelete=False).exists():
            raise CustomValidationError(detail={'code': 6, 'message': '专家已存在'})
        instance = super(KExpertsSerializers, self).create(validated_data)
        return instance

    def update(self, instance, validated_data):
        if KExperts.objects.exclude(id=instance.id).filter(mobile=validated_data['mobile'], isDelete=False).exists():
            raise CustomValidationError(detail={'code': 6, 'message': '专家已存在'})
        instance = super(KExpertsSerializers, self).update(instance, validated_data)
        return instance


# 评估机构
class PExpertsSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    userExpert = serializers.SerializerMethodField(read_only=True)
    ratingAgencies = serializers.CharField(read_only=True)

    class Meta:
        model = PExperts
        fields = (
            'id', 'name', 'gender', 'birthday', 'mobile', 'email', 'unit', 'title', 'position', 'learnProfessional',
            'engagedProfessional', 'ratingAgencies', 'created', 'updated', 'userExpert')

    def get_userExpert(self, obj):
        try:
            return obj.user_set.values('id', 'username', 'password')
        except Exception as e:
            return None


# 管理服务机构
class AgencySerializers(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Agency
        fields = '__all__'

    def get_permissions(self, obj):
        try:
            return obj.permissions.values("name")
        except Exception as e:
            return None

    def get_user(self, obj):
        try:
            return obj.user_set.values("id")
        except Exception as e:
            return None


# 用户序列化
class UserSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M", required=False, read_only=True)
    # 企业
    enterprise = EnterpriseSerializers(read_only=True)
    # 评估机构专家
    experts = PExpertsSerializers(read_only=True)
    username = serializers.CharField(required=True, allow_blank=False,
                                     validators=[UniqueValidator(queryset=User.objects.all(), message='用户已经存在')])
    # password = serializers.CharField(required=True, allow_blank=False, min_length=12, max_length=24,
    #                                  error_messages={
    #                                      'min_length': '仅允许12个字符的密码',
    #                                      'max_length': '仅允许24个字符的密码',
    #                                  })
    businessLicense = serializers.URLField(read_only=True)
    businessLicenseName = serializers.SerializerMethodField(read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'name', 'CreditCode', 'mobile', 'phone', 'contact', 'QQ', 'email', 'type', 'password',
            'isActivation',
            'enterprise', 'experts', 'businessLicense', 'businessLicenseName', 'subject', 'created')

    def create(self, validated_data):
        if not re.match(r'^(?=.*\d)(?=.*[a-zA-Z]).{12,24}$', validated_data['password']):
            raise CustomValidationError(detail={'code': 5, 'message': '密码必须包含字母和数字'})
        instance = super(UserSerializers, self).create(validated_data)
        instance.set_password(validated_data['password'])
        instance.is_activation = '启用'
        instance.save()
        return instance

    def update(self, instance, validated_data):
        # if not re.match(r'^(?=.*\d)(?=.*[a-zA-Z]).{12,24}$', validated_data['password']):
        #     raise CustomValidationError(detail={'code': 5, 'message': '密码必须包含字母和数字'})
        old_password = instance.password
        instance = super(UserSerializers, self).update(instance, validated_data)
        if old_password != validated_data['password']:
            instance.set_password(validated_data['password'])
            instance.save()
        return instance

    def get_subject(self, obj):
        try:
            declare = Subject.objects.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查不通过')).filter(
                enterprise=obj).count()
            research = Subject.objects.exclude(
                Q(subjectState='待提交') | Q(subjectState='形式审查不通过') | Q(subjectState='项目退回') | Q(
                    subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='验收通过')).filter(
                enterprise=obj).count()
            return {"declare": declare, "research": research}
        except Exception as e:
            return None

    def get_businessLicenseName(self, obj):
        try:
            return obj.name + '营业执照.' + str(obj.businessLicense).split('.')[-1]
        except Exception as e:
            return None
