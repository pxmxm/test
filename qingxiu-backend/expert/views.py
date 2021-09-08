import datetime

# Create your views here.
from django.core.cache import cache
from django.db.models import Q
from django.db.models.functions import Substr
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from blacklist.models import ProjectLeader, ExpertsBlacklist
from expert.models import AvoidanceUnit, ExpertEducation, ExpertWork, ExpertDuty, ExpertAgency, Enclosure, \
    ExpertRecordEdit, ExpertRecordExit
from expert.serializers import ExpertsSerializers, ExpertProjectTypeSerializers, ExpertTitleSerializers, \
    ExpertFieldTreeSerializers, ExpertFieldSerializers, ExpertEducationSerializers, ExpertWorkSerializers, \
    ExpertDutySerializers, ExpertAgencySerializers, AvoidanceUnitSerializers, EnclosureSerializers, \
    ExpertRecordEditSerializers, ExpertRecordExitSerializers, EnterpriseSerializers
from subject.models import Subject, SubjectPersonnelInfo, SubjectExpertsOpinionSheet, SubjectUnitInfo
from utils.birthday import GetInformation
import re
from django.contrib.auth.hashers import make_password
from django.db import DatabaseError, transaction
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from expert.models import Expert, ExpertTitle, ExpertField, ExpertProjectType
from expert.serializers import ExpertSerializers

from utils.oss import OSS

from users.models import User, Enterprise


class PagingNumber(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = 'size'
    max_page_size = 100


def check_id_data(n):
    if len(n) != 18:
        return False
    var = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    var_id = ['1', '0', 'x', '9', '8', '7', '6', '5', '4', '3', '2']
    n = str(n)
    sum_data = 0
    for i in range(0, 17):
        sum_data += int(n[i]) * var[i]
    if (var_id[sum_data % 11]) == str(n[17]):
        return True
    return False


class ExpertProjectTypeView(APIView):
    def get(self, request):
        types = ExpertProjectType.objects.all()
        res = ExpertProjectTypeSerializers(instance=types, many=True).data
        return Response({'code': 0, 'msg': '专家参与过的项目类别查询成功', 'data': res})


class ExpertTitleView(APIView):
    def get(self, request):
        types = ExpertTitle.objects.all()
        res = ExpertTitleSerializers(instance=types, many=True).data
        return Response({'code': 0, 'msg': '职称查询成功', 'data': res})


class ExpertFieldView(APIView):
    def get(self, request, field_id=None):
        tree = request.query_params.get('tree', '1')
        parent = request.query_params.get('parent')

        if tree == '1':
            ser = ExpertFieldTreeSerializers
        else:
            ser = ExpertFieldSerializers

        if field_id:
            field = ExpertField.objects.filter(pk=field_id).first()
            res = ser(instance=field, many=False).data
            return Response({'code': 0, 'msg': '专家领域查询成功', 'data': res})
        fields = ExpertField.objects.filter(parent=parent)
        res = ser(instance=fields, many=True).data
        return Response({'code': 0, 'msg': '专家领域查询成功', 'data': res})


class ExpertRegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        mobile = request.query_params.get('mobile')
        id_card_no = request.query_params.get('id_card_no')
        if not mobile and not id_card_no:
            return Response({'code': 4001, 'msg': '请输入手机号或身份证号', 'data': None})
        if mobile and Expert.objects.filter(mobile=mobile).exists():
            return Response({'code': 0, 'msg': '专家存在', 'data': None})
        if id_card_no:
            expert = User.objects.filter(username=id_card_no).first()
            if expert:
                return Response({'code': 0, 'msg': '专家存在', 'data': {
                    'id_card_no': expert.username,
                    'mobile': expert.expert.mobile,
                }})
        return Response({'code': 4002, 'msg': '专家不存在', 'data': None})

    @transaction.atomic
    def post(self, request):
        expert = Expert()

        id_card_no = request.data.get('id_card_no')
        # if not check_id_data(id_card_no):
        #     return Response({"code": 4001, "msg": "身份证号格式错误", "data": None})
        expert.id_card_no = id_card_no

        if datetime.datetime.now().year - int(id_card_no[6:10]) > 65:
            return Response({"code": 4002, "msg": "已满 65 周岁", "data": None})

        name = request.data.get('name')
        if not name:
            return Response({"code": 4003, "msg": "姓名不能为空", "data": None})
        expert.name = name

        mobile = request.data.get('mobile')
        if not mobile:
            return Response({"code": 4004, "msg": "手机号不能为空", "data": None})
        expert.mobile = mobile

        if not re.search("^(13\d|14[5|7]|15\d|166|17[3|6|7]|18\d)\d{8}$", mobile):
            return Response({"code": 4005, "msg": "手机号格式错误", "data": None})

        if User.objects.filter(username=id_card_no).exists():
            return Response({"code": 4006, "msg": "身份证号已注册", "data": None})

        # if Expert.objects.filter(mobile=mobile).exists():
        #     return Response({"code": 4007, "msg": "手机号已注册", "data": None})

        if cache.get('sms_%s' % mobile, None) is not None:
            if cache.get('sms_%s' % mobile)['sms_code'] != request.data.get('sms_code'):
                return Response({"code": 4007, "msg": "验证码错误", "data": None})
        else:
            return Response({"code": 4008, "msg": "验证码无效", "data": None})

        password = request.data.get('password')
        if len(password) < 8:
            return Response({"code": 4010, "msg": "密码不符合要求", "data": None})

        if request.data.get('password') and request.data.get('confirm_password') and request.data.get(
                'password') != request.data.get('confirm_password'):
            return Response({"code": 4011, "msg": "两次密码不一致", "data": None})

        try:
            expert.save()

            user = User(expert=expert, type='专家')

            password = make_password(password)
            user.password = password

            user.username = id_card_no

            user.save()
        except DatabaseError:
            return Response({"code": 4000, "msg": "注册失败", "data": None})
        return Response({"code": 0, "msg": "注册成功", "data": None})

    def put(self, request):

        mobile = request.data.get('mobile')
        if cache.get('sms_%s' % mobile, None) is not None:
            if cache.get('sms_%s' % mobile)['sms_code'] != request.data.get('sms_code'):
                return Response({"code": 4007, "msg": "验证码错误", "data": None})
        else:
            return Response({"code": 4008, "msg": "验证码无效", "data": None})

        id_card_no = request.data.get('id_card_no')
        user = User.objects.filter(username=id_card_no).first()
        if not user:
            return Response({"code": 4002, "msg": "用户不存在", "data": None})
        password = request.data.get('password')
        if len(password) < 8:
            return Response({"code": 4003, "msg": "密码不符合要求", "data": None})
        if request.data.get('password') and request.data.get('confirm_password') and request.data.get(
                'password') != request.data.get('confirm_password'):
            return Response({"code": 4004, "msg": "两次密码不一致", "data": None})
        password = make_password(password)
        user.password = password
        user.save()
        return Response({"code": 0, "msg": "密码修改成功", "data": None})


class TimeView(APIView):
    def get(self, request):
        return Response({
            'code': 0,
            'msg': '申请入库时间查询成功',
            'data': {
                'start': '2021-01-01',
                'stop': '2021-12-31'
            }
        })


class UnitView(APIView):
    def get(self, request):
        es = User.objects.filter(type='企业', name__contains=request.query_params.get('q'))
        return Response({
            'code': 0,
            'msg': '企业信息查询成功',
            'data': EnterpriseSerializers(instance=es, many=True).data
        })


class ExpertEducationView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, education_id=None):
        expert_id = request.query_params.get('expert_id')
        ees = ExpertEducation.objects.filter(expert_id=expert_id)
        res = ExpertEducationSerializers(instance=ees, many=True).data
        return Response({
            'code': 0,
            'msg': '专家教育简历查询成功',
            'data': res
        })

    def post(self, request, education_id=None):
        ed = ExpertRecordEdit(module=3)
        ed.old = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
            expert=request.user.expert), many=True).data

        ee = ExpertEducation()
        ee.school = request.data.get('school')
        ee.major = request.data.get('major')
        ee.education = request.data.get('education')
        ee.date_start = request.data.get('date_start')
        ee.date_stop = request.data.get('date_stop')
        ee.expert = request.user.expert
        ee.save()

        ed.new = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        res = ExpertEducationSerializers(instance=ee, many=False).data
        return Response({
            'code': 0,
            'msg': '专家教育简历添加成功',
            'data': res
        })

    def put(self, request, education_id=None):
        ed = ExpertRecordEdit(module=3)
        ed.old = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
            expert=request.user.expert), many=True).data

        ee = ExpertEducation.objects.filter(pk=education_id).first()
        ee.school = request.data.get('school')
        ee.major = request.data.get('major')
        ee.education = request.data.get('education')
        ee.date_start = request.data.get('date_start')
        ee.date_stop = request.data.get('date_stop')
        ee.expert = request.user.expert
        ee.save()

        ed.new = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        res = ExpertEducationSerializers(instance=ee, many=False).data
        return Response({
            'code': 0,
            'msg': '专家教育简历更改成功',
            'data': res
        })

    def delete(self, request, education_id=None):
        ed = ExpertRecordEdit(module=3)
        ed.old = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
            expert=request.user.expert), many=True).data

        expert_id = request.query_params.get('expert_id')
        ee = ExpertEducation.objects.filter(
            pk=education_id, expert_id=expert_id)
        if not ee:
            return Response({'code': 4001, 'msg': '简历不存在', 'data': None})
        ee.delete()

        ed.new = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        return Response({'code': 0, 'msg': '简历已删除', 'data': None})


class ExpertWorkView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, work_id=None):
        expert_id = request.query_params.get('expert_id')
        ews = ExpertWork.objects.filter(expert_id=expert_id)
        res = ExpertWorkSerializers(instance=ews, many=True).data
        return Response({
            'code': 0,
            'msg': '专家工作简历查询成功',
            'data': res
        })

    def post(self, request, work_id=None):
        ed = ExpertRecordEdit(module=4)
        ed.old = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
            expert=request.user.expert), many=True).data

        ew = ExpertWork()
        ew.company = request.data.get('company')
        ew.duty = request.data.get('duty')
        ew.content = request.data.get('content')
        ew.date_start = request.data.get('date_start')
        ew.date_stop = request.data.get('date_stop')
        ew.expert = request.user.expert
        ew.save()

        ed.new = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        res = ExpertWorkSerializers(instance=ew, many=False).data
        return Response({
            'code': 0,
            'msg': '专家工作简历更改成功',
            'data': res
        })

    def put(self, request, work_id=None):
        ed = ExpertRecordEdit(module=4)
        ed.old = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
            expert=request.user.expert), many=True).data

        ew = ExpertWork.objects.filter(pk=work_id).first()
        ew.company = request.data.get('company')
        ew.duty = request.data.get('duty')
        ew.content = request.data.get('content', '')
        ew.date_start = request.data.get('date_start')
        ew.date_stop = request.data.get('date_stop')
        ew.save()

        ed.new = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        res = ExpertWorkSerializers(instance=ew, many=False).data
        return Response({
            'code': 0,
            'msg': '专家工作简历修改成功',
            'data': res
        })

    def delete(self, request, work_id=None):
        ed = ExpertRecordEdit(module=4)
        ed.old = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
            expert=request.user.expert), many=True).data

        expert_id = request.query_params.get('expert_id')
        ew = ExpertWork.objects.filter(pk=work_id, expert_id=expert_id)
        if not ew:
            return Response({'code': 4001, 'msg': '简历不存在', 'data': None})
        ew.delete()

        ed.new = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        return Response({'code': 0, 'msg': '简历已删除', 'data': None})


class ExpertDutyView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, duty_id=None):
        expert_id = request.query_params.get('expert_id')
        ews = ExpertDuty.objects.filter(expert_id=expert_id)
        res = ExpertDutySerializers(instance=ews, many=True).data
        return Response({
            'code': 0,
            'msg': '专家担任社会职务经历查询成功',
            'data': res
        })

    def post(self, request, duty_id=None):
        eed = ExpertRecordEdit(module=5)
        eed.old = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
            expert=request.user.expert), many=True).data

        ed = ExpertDuty()
        ed.organization = request.data.get('organization')
        ed.duty = request.data.get('duty')
        ed.remarks = request.data.get('remarks', '')
        ed.date_start = request.data.get('date_start')
        ed.date_stop = request.data.get('date_stop')
        ed.expert = request.user.expert
        ed.save()

        eed.new = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
            expert=request.user.expert), many=True).data
        eed.expert = request.user.expert
        if eed.expert.state == 3:
            ed.save()

        res = ExpertDutySerializers(instance=ed, many=False).data
        return Response({
            'code': 0,
            'msg': '专家担任社会职务经历添加成功',
            'data': res
        })

    def put(self, request, duty_id=None):
        eed = ExpertRecordEdit(module=5)
        eed.old = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
            expert=request.user.expert), many=True).data

        ed = ExpertDuty.objects.filter(pk=duty_id).first()
        ed.organization = request.data.get('organization')
        ed.duty = request.data.get('duty')
        ed.remarks = request.data.get('remarks')
        ed.date_start = request.data.get('date_start')
        ed.date_stop = request.data.get('date_stop')
        ed.expert = request.user.expert
        ed.save()

        eed.new = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
            expert=request.user.expert), many=True).data
        eed.expert = request.user.expert
        if eed.expert.state == 3:
            ed.save()

        res = ExpertDutySerializers(instance=ed, many=False).data
        return Response({
            'code': 0,
            'msg': '专家担任社会职务经历更改成功',
            'data': res
        })

    def delete(self, request, duty_id=None):
        eed = ExpertRecordEdit(module=5)
        eed.old = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
            expert=request.user.expert), many=True).data

        expert_id = request.query_params.get('expert_id')
        ed = ExpertDuty.objects.filter(pk=duty_id, expert_id=expert_id)
        if not ed:
            return Response({'code': 4001, 'msg': '经历不存在', 'data': None})
        ed.delete()

        eed.new = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
            expert=request.user.expert), many=True).data
        eed.expert = request.user.expert
        if eed.expert.state == 3:
            eed.save()

        return Response({'code': 0, 'msg': '经历已删除', 'data': None})


class ExpertAgencyView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, agency_id=None):
        expert_id = request.query_params.get('expert_id')
        ews = ExpertAgency.objects.filter(expert_id=expert_id)
        res = ExpertAgencySerializers(instance=ews, many=True).data
        return Response({
            'code': 0,
            'msg': '专家担任其他评审专家机构情况查询成功',
            'data': res
        })

    def post(self, request, agency_id=None):
        ed = ExpertRecordEdit(module=6)
        ed.old = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
            expert=request.user.expert), many=True).data

        ea = ExpertAgency()
        ea.agency = request.data.get('agency')
        ea.duty = request.data.get('duty')
        ea.remarks = request.data.get('remarks', '')
        ea.date_start = request.data.get('date_start')
        ea.date_stop = request.data.get('date_stop')
        ea.expert = request.user.expert
        ea.save()

        ed.new = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        res = ExpertAgencySerializers(instance=ea, many=False).data
        return Response({
            'code': 0,
            'msg': '专家担任其他评审专家机构情况添加成功',
            'data': res
        })

    def put(self, request, agency_id=None):
        ed = ExpertRecordEdit(module=6)
        ed.old = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
            expert=request.user.expert), many=True).data

        ea = ExpertAgency.objects.filter(pk=agency_id).first()
        ea.agency = request.data.get('agency')
        ea.duty = request.data.get('duty')
        ea.remarks = request.data.get('remarks')
        ea.date_start = request.data.get('date_start')
        ea.date_stop = request.data.get('date_stop')
        ea.expert = request.user.expert
        ea.save()

        ed.new = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        res = ExpertAgencySerializers(instance=ea, many=False).data
        return Response({
            'code': 0,
            'msg': '专家担任其他评审专家机构情况更改成功',
            'data': res
        })

    def delete(self, request, agency_id=None):
        ed = ExpertRecordEdit(module=6)
        ed.old = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
            expert=request.user.expert), many=True).data

        expert_id = request.query_params.get('expert_id')
        ea = ExpertAgency.objects.filter(pk=agency_id, expert_id=expert_id)
        if not ea:
            return Response({'code': 4001, 'msg': '情况不存在', 'data': None})
        ea.delete()

        ed.new = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        return Response({'code': 0, 'msg': '情况已删除', 'data': None})


class AvoidanceUnitView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, avoidance_id=None):
        expert_id = request.query_params.get('expert_id')
        aus = AvoidanceUnit.objects.filter(expert_id=expert_id)
        res = AvoidanceUnitSerializers(instance=aus, many=True).data
        return Response({
            'code': 0,
            'msg': '专家回避单位查询成功',
            'data': res
        })

    def post(self, request, avoidance_id=None):
        credit_code = request.data.get('credit_code')
        if AvoidanceUnit.objects.filter(credit_code=credit_code, expert=request.user.expert).exists():
            return Response({
                'code': 4001,
                'msg': '专家回避单位重复',
                'data': None
            })
        au = AvoidanceUnit()
        au.name = request.data.get('name')
        au.credit_code = credit_code
        au.expert = request.user.expert
        au.save()
        res = AvoidanceUnitSerializers(instance=au, many=False).data
        return Response({
            'code': 0,
            'msg': '专家回避单位添加成功',
            'data': res
        })

    def delete(self, request, avoidance_id=None):
        expert_id = request.query_params.get('expert_id')
        au = AvoidanceUnit.objects.filter(pk=avoidance_id, expert_id=expert_id)
        if not au:
            return Response({'code': 4001, 'msg': '回避单位不存在', 'data': None})
        au.delete()
        return Response({'code': 0, 'msg': '回避单位已删除', 'data': None})


class EnclosureView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, enclosure_id=None):
        expert_id = request.query_params.get('expert_id')
        aus = Enclosure.objects.filter(expert_id=expert_id)
        res = EnclosureSerializers(instance=aus, many=True).data
        return Response({
            'code': 0,
            'msg': '专家附件查询成功',
            'data': res
        })

    def post(self, request, enclosure_id=None):
        enclosure = request.FILES.get('file')
        file_name = enclosure.name
        path = OSS().put_by_backend(path=file_name, data=enclosure.read())
        return Response({
            'code': 0,
            'msg': '专家附件上传成功',
            'data': {
                "file_name": file_name,
                "path": path
            }
        })
        # ed = ExpertRecordEdit(module=7)
        # ed.old = EnclosureSerializers(instance=Enclosure.objects.filter(
        #     expert=request.user.expert), many=True).data
        #
        # en = Enclosure()
        # en.type = request.data.get('type')
        # enclosure = request.FILES.get('file')
        # file_name = enclosure.name
        # path = OSS().put_by_backend(path=file_name, data=enclosure.read())
        # en.url = path
        # en.name = file_name
        # en.expert = request.user.expert
        # en.save()
        #
        # ed.new = EnclosureSerializers(instance=Enclosure.objects.filter(
        #     expert=request.user.expert), many=True).data
        # ed.expert = request.user.expert
        # if ed.expert.state == 3:
        #     ed.save()
        #
        # res = EnclosureSerializers(instance=en, many=False).data
        # return Response({
        #     'code': 0,
        #     'msg': '专家附件添加成功',
        #     'data': res
        # })

    def delete(self, request, enclosure_id=None):
        ed = ExpertRecordEdit(module=7)
        ed.old = EnclosureSerializers(instance=Enclosure.objects.filter(
            expert=request.user.expert), many=True).data

        expert_id = request.query_params.get('expert_id')
        ew = Enclosure.objects.filter(pk=enclosure_id, expert_id=expert_id)
        if not ew:
            return Response({'code': 4001, 'msg': '附件不存在', 'data': None})
        ew.delete()

        ed.new = EnclosureSerializers(instance=Enclosure.objects.filter(
            expert=request.user.expert), many=True).data
        ed.expert = request.user.expert
        if ed.expert.state == 3:
            ed.save()

        return Response({'code': 0, 'msg': '附件已删除', 'data': None})


class ExpertRecordEditView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        expert_id = request.query_params.get('expert_id')
        aus = ExpertRecordEdit.objects.filter(expert_id=expert_id).order_by('-date')
        res = ExpertRecordEditSerializers(instance=aus, many=True).data
        return Response({
            'code': 0,
            'msg': '专家信息修改记录查询成功',
            'data': res
        })


class ExpertRecordExitView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        expert_id = request.query_params.get('expert_id')
        aus = ExpertRecordExit.objects.filter(expert_id=expert_id)
        res = ExpertRecordExitSerializers(instance=aus, many=True).data
        return Response({
            'code': 0,
            'msg': '专家退库申请记录查询成功',
            'data': res
        })


class ExpertsViewSet(viewsets.ModelViewSet):
    queryset = Expert.objects.all()
    serializer_class = ExpertsSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 专家修改记录展示
    @action(detail=False, methods=['get'], url_path='detection')
    def detection(self, request, *args, **kwargs):
        lists = []
        queryset = self.queryset.filter(state=3)
        json_data = request.query_params
        keys = {
            "name": "name__contains",
            "idCardNo": "id_card_no__contains",
            "company": "company__contains",
            "education": "education",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        sex = request.query_params.get('sex')
        if sex is not None:
            if sex == '0':
                queryset = queryset.annotate(sex=Substr('id_card_no', 17, 1)).filter(
                    sex__in=['1', '3', '5', '7', '9'])
            else:
                queryset = queryset.annotate(sex=Substr('id_card_no', 17, 1)).filter(
                    sex__in=['2', '4', '6', '8', '0'])
        field = request.query_params.get('field')
        if field:
            queryset = queryset.filter(Q(field__parent_id=field)
                                     | Q(field__parent__parent_id=field)
                                     | Q(field__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent__parent__parent__parent_id=field)
                                     ).distinct()
        for i in queryset:
            # print(i.expertrecordedit_set.exists())
            # print(i.expertrecordedit_set.filter().count())
            if i.expertrecordedit_set.exists():
            # if i.expertrecordedit_set.all():
                serializer = self.get_serializer(i)
                lists.append(serializer.data)
        if len(lists) == 0:
            return Response({'code': 1, 'message': '提示：当前暂无专家修改信息'})
        return Response({'code': 0, 'message': lists})






    # @action(detail=False, methods=['post'], url_path='expert_query')
    # def expert_query(self, request, *args, **kwargs):
    #     queryset = self.queryset.filter(state=3)
    #     json_data = request.data
    #     keys = {
    #         "name": "name__contains",
    #         "idCardNo": "id_card_no__contains",
    #         "company": "company__contains",
    #         "title": "title__name__contains",
    #         "education": "education"
    #     }
    #     data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
    #     queryset = queryset.filter(**data)
    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #     return self.get_paginated_response(serializer.data)
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='expert_query')
    def expert_query(self, request, *args, **kwargs):
        queryset = self.queryset.filter(state=3)
        json_data = request.data
        keys = {
            "name": "name__contains",
            "idCardNo": "id_card_no__contains",
            "company": "company__contains",
            "title": "title__name__contains",
            "education": "education",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        if request.data['gender'] == "全部" or request.data['gender'] == '':
            # page = self.paginate_queryset(queryset)
            # if page is not None:
            #     serializer = self.get_serializer(page, many=True)
            #     return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        else:
            lists = [self.get_serializer(i).data for i in queryset if
                     GetInformation(i.id_card_no).get_sex() == request.data['gender']]
            return Response(lists)

    # 立项
    @action(detail=False, methods=['post'], url_path='choose_experts_first')
    def choose_experts_first(self, request, *args, **kwargs):
        lists = []
        annual_plan = request.data['annualPlan']
        project_batch = request.data['projectBatch']
        new_time = datetime.date.today()

        experts = self.queryset.filter(state=3)
        for i in experts:
            if ProjectLeader.objects.filter(isArchives=False, idNumber=i.id_card_no).exists():
                disciplinary_time = ProjectLeader.objects.filter(isArchives=False,
                                                                 idNumber=i.id_card_no).get().disciplinaryTime
                if new_time < disciplinary_time:
                    lists.append(i.id)
            if ExpertsBlacklist.objects.filter(isArchives=False, idNumber=i.id_card_no).exists():
                disciplinary_time = ExpertsBlacklist.objects.filter(isArchives=False,
                                                                    idNumber=i.id_card_no).get().disciplinaryTime
                if new_time < disciplinary_time:
                    lists.append(i.id)
            for j in Subject.objects.filter(project__category__batch__annualPlan=annual_plan,
                                            project__category__batch__projectBatch=project_batch, subjectState='专家评审'):
                personnel_info = SubjectPersonnelInfo.objects.get(subjectId=j.id)
                if personnel_info.idNumber == i.id_card_no:
                    lists.append(i.id)
                same = [
                    i.id for x in personnel_info.researchDevelopmentPersonnel if x['idNumber'] == i.id_card_no]
                lists = lists + same
            if GetInformation(i.id_card_no).get_age() > 65:
                lists.append(i.id)
        experts_id = request.data['expertsId']
        # experts_id = literal_eval(request.data['expertsId'])
        json_data = request.data
        keys = {
            "name": "name__contains",
            "unit": "company__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != ''}
        queryset = experts.exclude(id__in=experts_id + lists).filter(**data)
        if request.data['field'] == '全部' or request.data['field'] == '':
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            queryset = queryset.filter(Q(field__parent_id=request.data['field']) | Q(field__parent__parent_id=request.data['field'])
                            | Q(field__parent__parent__parent_id=request.data['field']))
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 验收终止
    @action(detail=False, methods=['post'], url_path='choose_experts_last')
    def choose_experts_last(self, request, *args, **kwargs):
        lists = []
        limit = request.query_params.dict().get('limit', None)
        subject_id = request.data["subjectId"]
        review_time = request.data['reviewTime']
        new_time = datetime.date.today()
        experts = self.queryset.filter(state=3)
        for i in experts:
            if ProjectLeader.objects.filter(isArchives=False, idNumber=i.id_card_no).exists():
                disciplinary_time = ProjectLeader.objects.filter(isArchives=False,
                                                                 idNumber=i.id_card_no).get().disciplinaryTime
                if new_time < disciplinary_time:
                    lists.append(i.id)
            if ExpertsBlacklist.objects.filter(isArchives=False, idNumber=i.id_card_no).exists():
                disciplinary_time = ExpertsBlacklist.objects.filter(isArchives=False,
                                                                    idNumber=i.id_card_no).get().disciplinaryTime
                if new_time < disciplinary_time:
                    lists.append(i.id)
            subject = Subject.objects.filter(id=subject_id).first()
            personnel_info = SubjectPersonnelInfo.objects.get(subjectId=subject.id)
            if personnel_info.idNumber == i.id_card_no:
                lists.append(i.id)
            same = [
                i.id for x in personnel_info.researchDevelopmentPersonnel if x['idNumber'] == i.id_card_no]
            lists = lists + same
            if GetInformation(i.id_card_no).get_age() > 65:
                lists.append(i.id)
            for y in AvoidanceUnit.objects.filter(expert=i):
                if y.credit_code == subject.enterprise.username:
                    lists.append(i.id)
                subject_info = SubjectUnitInfo.objects.get(subjectId=subject_id)
                if y.credit_code == subject_info.unitInfo[0]['creditCode']:
                    lists.append(i.id)
                unit = [i.id for x in subject_info.jointUnitInfo if x['creditCode'] == y.credit_code]
                lists = lists + unit
        experts_id = request.data['expertsId']
        json_data = request.data
        keys = {
            "name": "name__contains",
            "unit": "company__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != ''}

        queryset = experts.exclude(id__in=experts_id + lists).filter(**data)
        if request.data['field'] == '全部' or request.data['field'] == '':
            page = self.paginate_queryset(queryset)
            if page is not None and limit is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            queryset = queryset.filter(
                Q(field__parent_id=request.data['field']) | Q(field__parent__parent_id=request.data['field'])
                | Q(field__parent__parent__parent_id=request.data['field']))
            page = self.paginate_queryset(queryset)
            if page is not None and limit is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理 已选择专家
    @action(detail=False, methods=['get'], url_path='group_experts_show')
    def group_experts_show(self, request):
        lists = []
        list2 = []
        agencies = request.user
        agencies_subject = Subject.objects.filter(
            state='未评审', agencies=agencies, subjectState='专家评审', assignWay='按组指派')
        json_data = request.query_params
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject_obj = agencies_subject.filter(**data)
        for subject in subject_obj:
            subject_experts_opinion_sheet = SubjectExpertsOpinionSheet.objects.filter(
                subject=subject)
            for j in subject_experts_opinion_sheet:
                lists.append(j.pExperts_id)
        lists = list(set(lists))
        for pExperts_id in lists:
            p_experts_user = User.objects.get(id=pExperts_id)
            queryset = self.queryset.filter(id=p_experts_user.expert_id)
            serializers = self.get_serializer(queryset, many=True)
            list2.extend(serializers.data)
        return Response({"code": 0, "message": "ok", "detail": list2}, status=status.HTTP_200_OK)

    # 评审管理
    # 单项指派-评审管理 已指派专家展示
    @action(detail=False, methods=['get'], url_path='single_experts_show')
    def single_experts_show(self, request):
        lists = []
        subject_id = request.query_params.dict().get('subjectId')
        subject_experts_opinion_sheet = SubjectExpertsOpinionSheet.objects.filter(
            subject_id=subject_id)
        for i in subject_experts_opinion_sheet:
            p_experts = self.queryset.get(id=i.pExperts.expert.id)
            serializer = self.get_serializer(p_experts)
            lists.append(serializer.data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)