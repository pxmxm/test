from django.core.cache import cache
from django.db.models import Q
from django.db.models.functions import Substr
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from expert.models import ExpertRecordEdit, ExpertRecordExit, ExpertEducation, ExpertWork, ExpertDuty, ExpertAgency, \
    Enclosure
from expert.serializers import ExpertProjectTypeSerializers, ExpertTitleSerializers, ExpertFieldSerializers, \
    ExpertEducationSerializers, ExpertWorkSerializers, ExpertDutySerializers, ExpertAgencySerializers, \
    EnclosureSerializers
from subject.models import Subject, SubjectExpertsOpinionSheet, SubjectKExperts
import re
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.views import APIView
from expert.models import Expert, ExpertTitle, ExpertField, ExpertProjectType
from expert.serializers import ExpertSerializers
from users.models import User
from utils.letter import SMS


class PagingNumber(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = 'size'
    max_page_size = 100




class ExpertView(APIView):
    authentication_classes = [JSONWebTokenAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, expert_id=None):
        if expert_id:
            user = request.query_params.get('user', 'false')
            if user == 'true':
                u = User.objects.filter(pk=expert_id).first()
                expert = u.expert
            else:
                expert = Expert.objects.filter(pk=expert_id).first()
            if expert:
                res = ExpertSerializers(instance=expert, many=False).data
                return Response({
                    'code': 0,
                    'msg': '查询专家信息成功',
                    'data': res
                })
            return Response({'code': 1, 'msg': '专家不存在', 'data': None})

        experts = Expert.objects.all()

        sex = request.query_params.get('sex')
        if sex is not None:
            if sex == '0':
                experts = Expert.objects.annotate(sex=Substr('id_card_no', 17, 1)).filter(
                    sex__in=['1', '3', '5', '7', '9'])
            else:
                experts = Expert.objects.annotate(sex=Substr('id_card_no', 17, 1)).filter(
                    sex__in=['2', '4', '6', '8', '0'])

        sort_by = request.query_params.get('sort_by', '-id')
        sorts = sort_by.split(',')
        experts = experts.order_by(*sorts)

        state = request.query_params.get('state')
        if state:
            states = state.split(',')
            if len(states) < 2:
                experts = experts.filter(state=int(states[0]))
            else:
                experts = experts.filter(
                    Q(state=int(states[1])) | Q(state=int(states[0])))

        name = request.query_params.get('name')
        if name:
            experts = experts.filter(name__contains=name)

        id_card_no = request.query_params.get('id_card_no')
        if id_card_no:
            experts = experts.filter(id_card_no__contains=id_card_no)

        company = request.query_params.get('company')
        if company:
            experts = experts.filter(company__contains=company)

        degree = request.query_params.get('degree')
        if degree:
            experts = experts.filter(degree=degree)

        title = request.query_params.get('title')
        if title:
            experts = experts.filter(title_id=title)

        field = request.query_params.get('field')
        print(experts)
        if field:
            experts = experts.filter(Q(field__parent_id=field)
                                     | Q(field__parent__parent_id=field)
                                     | Q(field__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent__parent__parent_id=field)
                                     | Q(field__parent__parent__parent__parent__parent__parent__parent__parent_id=field)
                                     ).distinct()
            print(experts)

        paging = PagingNumber()
        page = paging.paginate_queryset(experts, request, self)
        data = ExpertSerializers(instance=page, many=True).data
        res = paging.get_paginated_response(data).data

        return Response({
            'code': 0,
            'msg': '查询专家信息成功',
            'data': res
        })

    def put(self, request, expert_id=None):
        if 'mobile' in request.data:
            mobile = request.data.get('mobile')
            if cache.get('sms_%s' % mobile, None) is not None:
                if cache.get('sms_%s' % mobile)['sms_code'] != request.data.get('sms_code'):
                    return Response({"code": 4001, "msg": "验证码错误", "data": None})
            else:
                return Response({"code": 4003, "msg": "验证码无效", "data": None})

            if not re.search("^(13\d|14[5|7]|15\d|166|17[3|6|7]|18\d|19\d)\d{8}$", mobile):
                return Response({"code": 4002, "msg": "手机号格式错误", "data": None})
            # if Expert.objects.filter(mobile=mobile).exclude(pk=expert_id).exists():
            #     return Response({"code": 4003, "msg": "手机号已注册", "data": None})
            old_mobile = request.data.get('old_mobile')
            expert = Expert.objects.filter(
                pk=expert_id, mobile=old_mobile).first()
            if not expert:
                return Response({"code": 4004, "msg": "用户不存在", "data": None})

            ed = ExpertRecordEdit()
            ed.old = str(expert.mobile)
            expert.mobile = mobile
            expert.save()
            ed.new = str(expert.mobile)
            ed.expert = expert
            ed.module = 8
            ed.save()
            return Response({"code": 0, "msg": "专家信息更改成功", "data": None})

        if 'password' in request.data:
            password = request.data.get('password')
            if not authenticate(username=request.user.username, password=password):
                return Response({"code": 4001, "msg": "原密码错误", "data": None})
            new_password = request.data.get('new_password')
            confirm_password = request.data.get('confirm_password')
            if len(new_password) < 8:
                return Response({"code": 4002, "msg": "密码不符合要求", "data": None})
            if new_password and confirm_password and new_password != confirm_password:
                return Response({"code": 4003, "msg": "两次密码不一致", "data": None})
            password = make_password(new_password)
            user = User.objects.filter(username=request.user.username).first()
            user.password = password
            user.save()
            return Response({"code": 0, "msg": "专家信息更改成功", "data": None})

        if 'ids' in request.data:
            if request.user.type == '管理员':
                experts = Expert.objects.filter(pk__in=request.data.get('ids'))
                f = list()
                s = list()
                date = timezone.now()
                for i in experts:
                    h1 = SubjectExpertsOpinionSheet.objects.filter(pExperts=User.objects.filter(expert=i).first(),
                                                                   state='待评审',
                                                                   subject__project__category__batch__state='同意')
                    h2 = SubjectKExperts.objects.filter(
                        subject__subjectState='验收审核', expert=i)
                    h3 = SubjectKExperts.objects.filter(
                        subject__subjectState='终止审核', expert=i)

                    if h1 or h2 or h3:
                        f.append(
                            {'name': i.name, 'msg': f'{i.name}专家当前有未完成评审的项目，无法移出'})
                    else:
                        s.append(i)

                if len(f) == 0:
                    for ex in s:
                        ed = ExpertRecordEdit()
                        ed.old = ex.state
                        ed.new = 4
                        ed.expert = ex
                        ed.module = 10
                        ed.save()

                        ex.state = 4
                        ex.reason = request.data.get('reason', '')
                        ex.date = date
                        ex.save()
                        sex = '女士' if int(
                            ex.id_card_no[-2:-1]) % 2 == 0 else '先生'
                        content = f"尊敬的{ex.name}{sex}，您已被青秀区科技管理部门移出专家库，如有疑问请联系青秀区科技局。".encode(
                            'gbk')
                        SMS().send_sms(ex.mobile, content)
                else:
                    return Response({'code': 4000, 'msg': '专家当前有未完成评审的项目，无法移出', 'data': f})
                return Response({'code': 0, 'msg': '批量移出专家成功', 'data': None})
            return Response({'code': 1, 'msg': '没有权限', 'data': None})

        expert = Expert.objects.filter(pk=expert_id).first()
        if not expert:
            return Response({'code': 4001, 'msg': '专家不存在', 'data': None})
        if 'state' in request.data:
            state = request.data.get('state')
            ed = ExpertRecordEdit()
            ed.old = expert.state
            ed.new = state
            ed.expert = expert
            ed.module = 10
            if state == 1 and (expert.state == 0 or expert.state == 2 or expert.state == 4 or expert.state == 6):
                expert.state = 1
                expert.save()
                ed.save()
                return Response({'code': 0, 'msg': '入库申请提交成功', 'data': None})
            elif state == 3:
                ed.save()
                if expert.state == 1:
                    expert.state = 3
                    expert.save()
                    sex = '女士' if int(
                        expert.id_card_no[-2:-1]) % 2 == 0 else '先生'
                    content = f"尊敬的{expert.name}{sex}，您向青秀区科技专家管理平台提交的入库申请已通过审批。".encode(
                        'gbk')
                    SMS().send_sms(expert.mobile, content)
                    ExpertRecordExit.objects.filter(expert=expert).delete()
                    return Response({'code': 0, 'msg': '入库申请审核通过', 'data': None})
                elif expert.state == 5:
                    ee = ExpertRecordExit(reason=request.data.get(
                        'reason', ''), user=request.user.username)
                    ee.expert = expert
                    ee.save()
                    expert.state = 3
                    expert.save()
                    sex = '女士' if int(
                        expert.id_card_no[-2:-1]) % 2 == 0 else '先生'
                    content = f"尊敬的{expert.name}{sex}，感谢您对青秀区科技管理工作的支持，您向青秀区科技专家管理平台提交的出库申请未通过。".encode(
                        'gbk')
                    SMS().send_sms(expert.mobile, content)
                    return Response({'code': 0, 'msg': '退库申请未通过', 'data': None})
            elif state == 2 and expert.state == 1:
                ed.save()
                expert.state = 2
                expert.reason = request.data.get('reason', '')
                expert.save()
                sex = '女士' if int(expert.id_card_no[-2:-1]) % 2 == 0 else '先生'
                content = f"尊敬的{expert.name}{sex}，您向青秀区科技专家管理平台提交的入库申请未通过审批，请登录系统根据退回原因修改信息后重新提交申请。".encode(
                    'gbk')
                SMS().send_sms(expert.mobile, content)
                return Response({'code': 0, 'msg': '入库申请审核未通过', 'data': None})
            elif state == 4 and expert.state == 3:
                h1 = SubjectExpertsOpinionSheet.objects.filter(pExperts=User.objects.filter(expert=expert).first(),
                                                               state='待评审',
                                                               subject__project__category__batch__state='同意')
                h2 = SubjectKExperts.objects.filter(
                    subject__subjectState='验收审核', expert=expert)
                h3 = SubjectKExperts.objects.filter(
                    subject__subjectState='终止审核', expert=expert)
                if h1 or h2 or h3:
                    return Response({'code': 4000, 'msg': f'{expert.name}专家当前有未完成评审的项目，无法移出', 'data': None})
                expert.state = 4
                expert.reason = request.data.get('reason', '')
                expert.save()
                ExpertRecordEdit.objects.filter(
                    expert=expert).exclude(module=10).delete()
                sex = '女士' if int(expert.id_card_no[-2:-1]) % 2 == 0 else '先生'
                content = f"尊敬的{expert.name}{sex}，您已被青秀区科技管理部门移出专家库，如有疑问请联系青秀区科技局。".encode(
                    'gbk')
                SMS().send_sms(expert.mobile, content)
                ed.save()
                return Response({'code': 0, 'msg': '已被移出专家库', 'data': None})
            elif state == 5 and expert.state == 3:
                ed.save()
                ss = SubjectExpertsOpinionSheet.objects.filter(pExperts__expert=expert, state='待评审',
                                                               subject__project__category__batch__state='同意')
                if ss:
                    return Response({'code': 4000, 'msg': f'{expert.name}专家当前有未完成评审的项目，无法移出', 'data': None})
                ee = ExpertRecordExit(reason=request.data.get('reason', ''))
                ee.expert = expert
                ee.save()
                expert.state = 5
                expert.save()
                return Response({'code': 0, 'msg': '申请退库审核中', 'data': None})
            elif state == 6 and expert.state == 5:
                ed.save()
                expert.state = 6
                expert.save()
                ExpertRecordEdit.objects.filter(
                    expert=expert).exclude(module=10).delete()
                sex = '女士' if int(expert.id_card_no[-2:-1]) % 2 == 0 else '先生'
                content = f"尊敬的{expert.name}{sex}，感谢您对青秀区科技管理工作的支持，您向青秀区科技专家管理平台提交的出库申请已通过。".encode(
                    'gbk')
                SMS().send_sms(expert.mobile, content)
                ee = ExpertRecordExit(user=request.user.username, reason='')
                ee.expert = expert
                ee.save()
                return Response({'code': 0, 'msg': '专家已退库', 'data': None})
            elif state == 7 and expert.state == 5:
                expert.state = 3
                expert.save()
                ExpertRecordExit.objects.filter(expert=expert).last().delete()
                return Response({'code': 0, 'msg': '退库申请已撤销', 'data': None})
            return Response({'code': 4002, 'msg': '状态不可改变', 'data': None})
        fields = [
            ['name', 0],
            ['password', 0],
            ['id_card_no', 0],
            ['mobile', 0],
            ['email', 0],
            ['education', 0],
            ['degree', 0],
            ['title', 0],
            ['title_no', 0],
            ['company', 0],
            ['duty', 0],
            ['academician', 0],
            ['supervisor', 0],
            ['overseas', 0],
            ['laboratory', 0],
            ['participate', 0],
            ['field', 0],
            ['tags', 0],
            ['bank', 0],
            ['bank_branch', 0],
            ['bank_account', 0],
        ]

        old = dict()
        new = dict()
        ed = ExpertRecordEdit(expert=expert)
        for i in fields:
            if i[0] in request.data:
                ed.module = i[1]
                data = request.data.get(i[0])
                if i[0] == 'title':
                    old[i[0]] = ExpertTitleSerializers(
                        instance=expert.title, many=False).data

                    title = ExpertTitle.objects.filter(pk=data).first()
                    expert.title = title

                    new[i[0]] = ExpertTitleSerializers(
                        instance=expert.title, many=False).data
                elif i[0] == 'participate':
                    old[i[0]] = ExpertProjectTypeSerializers(
                        instance=expert.participate, many=True).data

                    types = ExpertProjectType.objects.filter(pk__in=data)
                    expert.participate.clear()
                    expert.participate.add(*types)

                    new[i[0]] = ExpertProjectTypeSerializers(
                        instance=expert.participate, many=True).data
                elif i[0] == 'field':
                    old[i[0]] = ExpertFieldSerializers(
                        instance=expert.field, many=True).data

                    fields = ExpertField.objects.filter(pk__in=data)
                    expert.field.clear()
                    expert.field.add(*fields)

                    new[i[0]] = ExpertFieldSerializers(
                        instance=expert.field, many=True).data
                else:
                    if getattr(expert, i[0]) != data:
                        old[i[0]] = getattr(expert, i[0])
                        new[i[0]] = data
                    setattr(expert, i[0], data)
        expert.save()
        ed.old = old
        ed.new = new
        if old and new and expert.state == 3:
            ed.save()

        if 'expert_experience_education' in request.data:
            ed = ExpertRecordEdit(expert=expert, module=3)
            ed.old = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
                expert=expert), many=True).data

            ExpertEducation.objects.filter(expert=expert).delete()
            for i in request.data.get('expert_experience_education', []):
                e = ExpertEducation(expert=expert)
                e.school = i.get('school')
                e.major = i.get('major')
                e.education = i.get('education')
                e.date_start = i.get('date_start')
                e.date_stop = i.get('date_stop')
                e.save()

            ed.new = ExpertEducationSerializers(instance=ExpertEducation.objects.filter(
                expert=expert), many=True).data
            if ed.expert.state == 3:
                ed.save()

        if 'expert_experience_work' in request.data:
            ed = ExpertRecordEdit(expert=expert, module=4)
            ed.old = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
                expert=expert), many=True).data

            ExpertWork.objects.filter(expert=expert).delete()
            for i in request.data.get('expert_experience_work', []):
                e = ExpertWork(expert=expert)
                e.company = i.get('company')
                e.duty = i.get('duty')
                e.content = i.get('content')
                e.date_start = i.get('date_start')
                e.date_stop = i.get('date_stop')
                e.save()

            ed.new = ExpertWorkSerializers(instance=ExpertWork.objects.filter(
                expert=expert), many=True).data
            if ed.expert.state == 3:
                ed.save()

        if 'expert_history_duty' in request.data:
            eed = ExpertRecordEdit(expert=expert, module=5)
            eed.old = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
                expert=expert), many=True).data

            ExpertDuty.objects.filter(expert=expert).delete()
            for i in request.data.get('expert_history_duty', []):
                ed = ExpertDuty(expert=expert)
                ed.organization = i.get('organization')
                ed.duty = i.get('duty')
                ed.remarks = i.get('remarks', '')
                ed.date_start = i.get('date_start')
                ed.date_stop = i.get('date_stop')
                ed.save()

            eed.new = ExpertDutySerializers(instance=ExpertDuty.objects.filter(
                expert=expert), many=True).data
            if eed.expert.state == 3:
                eed.save()

        if 'expert_history_agency' in request.data:
            eed = ExpertRecordEdit(expert=expert, module=6)
            eed.old = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
                expert=expert), many=True).data

            ExpertAgency.objects.filter(expert=expert).delete()
            for i in request.data.get('expert_history_agency', []):
                ed = ExpertAgency(expert=expert)
                ed.agency = i.get('agency')
                ed.duty = i.get('duty')
                ed.remarks = i.get('remarks', '')
                ed.date_start = i.get('date_start')
                ed.date_stop = i.get('date_stop')
                ed.save()

            eed.new = ExpertAgencySerializers(instance=ExpertAgency.objects.filter(
                expert=expert), many=True).data
            if eed.expert.state == 3:
                eed.save()

        if 'expert_enclosure' in request.data:
            ed = ExpertRecordEdit(expert=expert, module=7)
            ed.old = EnclosureSerializers(instance=Enclosure.objects.filter(
                expert=expert), many=True).data

            Enclosure.objects.filter(expert=expert).delete()
            for i in request.data.get('expert_enclosure', []):
                en = Enclosure(expert=expert)
                en.type = i.get('type')
                en.url = i.get('path')
                en.name = i.get('file_name')
                en.save()

            ed.new = EnclosureSerializers(instance=Enclosure.objects.filter(
                expert=expert), many=True).data
            if ed.expert.state == 3:
                ed.save()

        res = ExpertSerializers(instance=expert, many=False).data
        return Response({
            'code': 0,
            'msg': '更新专家信息成功',
            'data': res
        })
