from decimal import Decimal

from django.db.models import Q

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_mongoengine import viewsets as mongodb_viewsets

from contract.models import ContractContent, Contract
from funding.models import GrantSubject, AllocatedSingle
from funding.serializers import GrantSubjectSerializers, AllocatedSingleSerializers
from subject.models import Subject
from utils.oss import OSS


class GrantSubjectViewSet(viewsets.ModelViewSet):
    queryset = GrantSubject.objects.all()
    serializer_class = GrantSubjectSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 经费管理 申请拨款/分管人员
    @action(detail=False, methods=['get'], url_path='detection_type')
    def detection_type(self, request):
        charge = request.user
        subject_id = request.query_params.dict().get('subjectId')
        if Subject.objects.filter(id=subject_id, subjectState='验收通过').exists() and self.queryset.filter(
                Q(state='待提交') | Q(state='待审核') | Q(state='退回'), subject_id=subject_id,
                subject__project__charge=charge).count() == 2:
            return Response({"code": 1, "message": "不可以操作尾款"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "OK"}, status=status.HTTP_200_OK)

    # 经费管理 申请拨款/分管人员
    # @action(detail=False, methods=['get'], url_path='charge_user_funding_show')
    # def charge_user_funding_show(self, request):
    #     charge = request.user
    #     queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
    #                                       '-subject__contract_subject__contractNo').filter(
    #         Q(state='待提交') | Q(state='待审核') | Q(state='退回'), subject__charge=charge)
    #     serializers = self.get_serializer(queryset, many=True)
    #     return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 经费管理 申请拨款/分管人员
    @action(detail=False, methods=['get'], url_path='charge_user_funding_show')
    def charge_user_funding_show(self, request):
        charge = request.user
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').exclude(
            Q(subject__subjectState="验收不通过") | Q(subject__subjectState="项目终止") | Q(subject__subjectState="逾期未结题")).filter(
            Q(state='待提交') | Q(state='待审核') | Q(state='退回'), subject__project__charge=charge)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 申请拨款查询/分管人员
    @action(detail=False, methods=['post'], url_path='charge_user_funding_query')
    def charge_user_funding_query(self, request):
        charge = request.user
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').exclude(
            Q(subject__subjectState="验收不通过") | Q(subject__subjectState="项目终止") | Q(subject__subjectState="逾期未结题")).filter(
            Q(state='待提交') | Q(state='待审核') | Q(state='退回'), subject__project__charge=charge)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
            "grantType": "grantType",
            "state": "state",
            "head": "subject__head__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request, *args, **kwargs):
        file = request.data['file']
        file_name = request.data['fileName']
        grant_type = request.data['grantType']
        grant_subject = GrantSubject.objects.get(subject=request.data['subjectId'], grantType=grant_type)
        if AllocatedSingle.objects.filter(grantSubject=grant_subject.id, storage=False):
            return Response({"code": 1, "message": "请核对申请拨款单是否全部填写完毕"}, status=status.HTTP_201_CREATED)
        for i in AllocatedSingle.objects.filter(grantSubject=grant_subject.id):
            grant_subject.money += i.money
        grant_subject.attachmentName = request.data['attachmentName'],
        grant_subject.attachment = OSS().put_by_backend(path=file_name, data=file.read())
        grant_subject.state = '待审核'
        grant_subject.save()
        return Response({"code": 0, "message": "上传成功"}, status=status.HTTP_201_CREATED)

    # 经费统计展示/分管人员
    @action(detail=False, methods=['get'], url_path='change_user_funding_statistical_show')
    def change_user_funding_statistical_show(self, request):
        lists = []
        charge = request.user
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(subject__project__charge=charge,
                                                                                           state='通过')
        for i in queryset:
            unit = []
            data = {
                "annualPlan": i.subject.project.category.batch.annualPlan,
                "projectBatch": i.subject.project.category.batch.projectBatch,
                "planCategory": i.subject.project.category.planCategory,
                "projectName": i.subject.project.projectName,
                "contractNo": i.subject.contract_subject.values('contractNo'),
                "subjectName": i.subject.subjectName,
                "head": i.subject.head,
                "mobile": i.subject.mobile,
                "scienceFunding": i.subject.contract_subject.values('approvalMoney'),
                "money": i.money,
                "grantType": i.grantType,
            }
            # 拨款申请单
            allocated_single = AllocatedSingle.objects.filter(grantSubject=i.id)
            for j in allocated_single:
                unit.append({"unitName": j.unitName, "money": j.money})
            data["unit"] = unit
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 经费统计查询 / 分管人员
    @action(detail=False, methods=['post'], url_path='change_user_funding_statistical_query')
    def change_user_funding_statistical_query(self, request):
        lists = []
        list2 = []
        charge = request.user
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(subject__project__charge=charge,
                                                                                           state='通过')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
            "subjectName": "subject__subjectName__contains",
            "head": 'subject__head__contains',
            "grantType": "grantType",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        for i in instance:
            unit = []
            data = {
                "annualPlan": i.subject.project.category.batch.annualPlan,
                "projectBatch": i.subject.project.category.batch.projectBatch,
                "planCategory": i.subject.project.category.planCategory,
                "projectName": i.subject.project.projectName,
                "contractNo": i.subject.contract_subject.values('contractNo'),
                "subjectName": i.subject.subjectName,
                "head": i.subject.head,
                "mobile": i.subject.mobile,
                "scienceFunding": i.subject.contract_subject.values('approvalMoney'),
                "money": i.money,
                "grantType": i.grantType,
            }
            # 拨款申请单
            allocated_single = AllocatedSingle.objects.filter(grantSubject=i.id)
            for j in allocated_single:
                unit.append({"unitName": j.unitName, "money": j.money})
            data["unit"] = unit
            lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 未拨付项目经费统计展示/管理员
    @action(detail=False, methods=['get'], url_path='change_user_funding_no_show')
    def change_user_funding_no_show(self, request):
        lists = []
        charge = request.user
        subject = Subject.objects.order_by('-project__category__batch__annualPlan',
                                           '-contract_subject__contractNo').exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题')).filter(project__charge=charge)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            if queryset.exists():
                contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
                if queryset.filter(state='通过').count() == 2:
                    pass
                elif queryset.count() == 2:
                    for i in queryset.filter(Q(state='通过') | Q(state='待提交') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }

                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '通过':
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
                else:
                    for i in queryset.filter(Q(state='待提交') | Q(state='通过') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '待提交' or i.state == '待审核' or i.state == '退回':
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 未拨付项目经费统计查询/管理员
    @action(detail=False, methods=['post'], url_path='change_user_funding_no_query')
    def change_user_funding_no_query(self, request):
        lists = []
        list2 = []
        charge = request.user
        subject_obj = Subject.objects.order_by('-project__category__batch__annualPlan',
                                               '-contract_subject__contractNo').exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题')).filter(project__charge=charge)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "head": "head__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject = subject_obj.filter(**data)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            if queryset.exists():
                contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
                if queryset.filter(state='通过').count() == 2:
                    pass
                elif queryset.count() == 2:
                    for i in queryset.filter(Q(state='通过') | Q(state='待提交') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '通过':
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
                else:
                    for i in queryset.filter(Q(state='待提交') | Q(state='通过') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '待提交' or i.state == '待审核' or i.state == '退回':
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 失信项目经费统计展示/管理员
    @action(detail=False, methods=['get'], url_path='change_user_funding_blacklist_show')
    def change_user_funding_blacklist_show(self, request):
        lists = []
        charge = request.user
        subject = Subject.objects.order_by('-project__category__batch__annualPlan',
                                           '-contract_subject__contractNo').filter(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'),
            project__charge=charge)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
            for i in queryset:
                unit = []
                data = {
                    "annualPlan": i.subject.project.category.batch.annualPlan,
                    "projectBatch": i.subject.project.category.batch.projectBatch,
                    "planCategory": i.subject.project.category.planCategory,
                    "projectName": i.subject.project.projectName,
                    "contractNo": i.subject.contract_subject.values('contractNo'),
                    "subjectName": i.subject.subjectName,
                    "subjectState": i.subject.subjectState,
                    "head": i.subject.head,
                    "mobile": i.subject.mobile,
                    "scienceFunding": contract_content.scienceFunding,
                    "money": i.money
                }
                for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                    for funding in contract_content.unitFunding:
                        if funding['unit'] == ut.unitName:
                            if i.state == '通过':
                                money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})
                            else:
                                money = Decimal(funding['first']) + Decimal(funding['last'])
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})

                data["unit"] = unit
                if len(unit) == 0:
                    pass
                else:
                    lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 失信项目经费统计查询/
    @action(detail=False, methods=['post'], url_path='change_user_blacklist_query')
    def change_user_blacklist_query(self, request):
        lists = []
        list2 = []
        charge = request.user
        subject_obj = Subject.objects.order_by('-project__category__batch__annualPlan',
                                               '-contract_subject__contractNo').filter(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'),
            project__charge=charge)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            # "unit_name": "subject__unit_name__contains",
            "head": "head__contains",
            "subjectState": "subjectState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject = subject_obj.filter(**data)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
            for i in queryset:
                unit = []
                data = {
                    "annualPlan": i.subject.project.category.batch.annualPlan,
                    "projectBatch": i.subject.project.category.batch.projectBatch,
                    "planCategory": i.subject.project.category.planCategory,
                    "projectName": i.subject.project.projectName,
                    "contractNo": i.subject.contract_subject.values('contractNo'),
                    "subjectName": i.subject.subjectName,
                    "subjectState": i.subject.subjectState,
                    "head": i.subject.head,
                    "mobile": i.subject.mobile,
                    "scienceFunding": contract_content.scienceFunding,
                    "money": i.money
                }
                for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                    for funding in contract_content.unitFunding:
                        if funding['unit'] == ut.unitName:
                            if i.state == '通过':
                                money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})

                            else:
                                money = Decimal(funding['first']) + Decimal(funding['last'])
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})
                data["unit"] = unit
                if len(unit) == 0:
                    pass
                else:
                    lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 小程序
    @action(detail=False, methods=['get'], url_path='change_user_funding_show')
    def change_user_funding_show(self, request):
        charge = request.user
        annual_plan = request.query_params.dict().get('annualPlan')

        # 已拨付
        has_allocated = sum([i.money for i in self.queryset.filter(state='通过',
                                                                   subject__project__charge=charge,
                                                                   subject__project__category__batch__annualPlan=annual_plan)])
        # 失信经费
        subject = Subject.objects.filter(Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'),
                                         project__category__batch__annualPlan=annual_plan, project__charge=charge,).values(
            'contract_subject__contractContent', 'id')
        dishonest_money = 0
        for j in subject:
            funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
            money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
            dishonest_money += funding - money
        # 待拨付
        subject = Subject.objects.exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题')).filter(
            project__category__batch__annualPlan=annual_plan, project__charge=charge,)
        not_allocated = 0
        for j in subject:
            if self.queryset.filter(subject=j).exists():
                contract_content = j.contract_subject.values('contractContent')
                funding = ContractContent.objects.get(id=contract_content[0]['contractContent']).scienceFunding
                money = sum([i.money for i in GrantSubject.objects.filter(subject=j) if i.state == '通过'])
                not_allocated += (funding - money)
        data = {
            "hasAllocated": has_allocated,
            "dishonestMoney": dishonest_money,
            "notAllocated": not_allocated,

        }
        return Response({'code': 0, 'message': '请求成功', 'detail': data}, status=status.HTTP_200_OK)

    """
    管理员
    """

    # 项目经费审批查询/管理员
    @action(detail=False, methods=['post'], url_path='admin_funding_examination_query_wx')
    def admin_funding_examination_query_wx(self, request):
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(state='待审核')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan__in",
            "planCategory": "subject__project__category__planCategory__in",
            "subjectName": "subject__subjectName__contains",
            "grantType": "grantType__in",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目经费审批展示/管理员
    @action(detail=False, methods=['get'], url_path='admin_funding_examination_show')
    def admin_funding_examination_show(self, request):
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(state='待审核')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目经费审批查询/管理员
    @action(detail=False, methods=['post'], url_path='admin_funding_examination_query')
    def admin_funding_examination_query(self, request):
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(state='待审核')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
            "grantType": "grantType",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目经费审批/管理员
    @action(detail=False, methods=['post'], url_path='admin_funding_examination')
    def admin_funding_statistical(self, request):
        grant_subject_id = request.data['grantSubjectId']
        state = request.data['state']
        queryset = self.queryset.get(id=grant_subject_id)
        if state == '通过':
            queryset.state = state
            queryset.save()
        else:
            queryset.state = '退回'
            queryset.money = 0
            queryset.save()
        return Response({"code": 0, "message": "完成审核"}, status=status.HTTP_200_OK)

    # 经费统计展示/分管人员
    @action(detail=False, methods=['get'], url_path='admin_funding_statistical_show')
    def admin_funding_statistical_show(self, request):
        lists = []
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(state='通过')
        for i in queryset:
            unit = []
            data = {
                "annualPlan": i.subject.project.category.batch.annualPlan,
                "projectBatch": i.subject.project.category.batch.projectBatch,
                "planCategory": i.subject.project.category.planCategory,
                "projectName": i.subject.project.projectName,
                "contractNo": i.subject.contract_subject.values('contractNo'),
                "subjectName": i.subject.subjectName,
                "head": i.subject.head,
                "mobile": i.subject.mobile,
                "scienceFunding": i.subject.contract_subject.values('approvalMoney'),
                "money": i.money,
                "grantType": i.grantType,
            }
            # 拨款申请单
            allocated_single = AllocatedSingle.objects.filter(grantSubject=i.id)
            for j in allocated_single:
                unit.append({"unitName": j.unitName, "money": j.money})
            data["unit"] = unit
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 经费统计查询 / 分管人员
    @action(detail=False, methods=['post'], url_path='admin_funding_statistical_query')
    def admin_funding_statistical_query(self, request):
        lists = []
        list2 = []
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(state='通过')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
            "subjectName": "subject__subjectName__contains",
            "head": 'subject__head__contains',
            "grantType": "grantType",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        for i in instance:
            unit = []
            data = {
                "annualPlan": i.subject.project.category.batch.annualPlan,
                "projectBatch": i.subject.project.category.batch.projectBatch,
                "planCategory": i.subject.project.category.planCategory,
                "projectName": i.subject.project.projectName,
                "contractNo": i.subject.contract_subject.values('contractNo'),
                "subjectName": i.subject.subjectName,
                "head": i.subject.head,
                "mobile": i.subject.mobile,
                "scienceFunding": i.subject.contract_subject.values('approvalMoney'),
                "money": i.money,
                "grantType": i.grantType,
            }
            # 拨款申请单
            allocated_single = AllocatedSingle.objects.filter(grantSubject=i.id)
            for j in allocated_single:
                unit.append({"unitName": j.unitName, "money": j.money})
            data["unit"] = unit
            lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 未拨付项目经费统计展示/管理员
    @action(detail=False, methods=['get'], url_path='admin_funding_no_show')
    def admin_funding_no_show(self, request):
        lists = []
        subject = Subject.objects.order_by('-project__category__batch__annualPlan',
                                           '-contract_subject__contractNo').exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'))
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            if queryset.exists():
                contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
                if queryset.filter(state='通过').count() == 2:
                    pass
                elif queryset.count() == 2:
                    for i in queryset.filter(Q(state='通过') | Q(state='待提交') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '通过':
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
                else:
                    for i in queryset.filter(Q(state='待提交') | Q(state='通过') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '待提交' or i.state == '待审核' or i.state == '退回':
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal('0.00'):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal('0.00'):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 未拨付项目经费统计查询/管理员
    @action(detail=False, methods=['post'], url_path='admin_funding_no_query')
    def admin_funding_no_query(self, request):
        lists = []
        list2 = []
        subject_obj = Subject.objects.order_by('-project__category__batch__annualPlan',
                                               '-contract_subject__contractNo').exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'))
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "head": "head__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject = subject_obj.filter(**data)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            if queryset.exists():
                contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
                # if queryset.count() == 2:
                if queryset.filter(state='通过').count() == 2:
                    pass
                elif queryset.count() == 2:
                    for i in queryset.filter(Q(state='通过') | Q(state='待提交') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '通过':
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
                else:
                    for i in queryset.filter(Q(state='待提交') | Q(state='通过') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '待提交' or i.state == '待审核' or i.state == '退回':
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 失信项目经费统计展示/管理员
    @action(detail=False, methods=['get'], url_path='admin_funding_blacklist_show')
    def admin_funding_blacklist_show(self, request):
        lists = []
        subject = Subject.objects.order_by('-project__category__batch__annualPlan',
                                           '-contract_subject__contractNo').filter(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'))
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
            for i in queryset:
                unit = []
                data = {
                    "annualPlan": i.subject.project.category.batch.annualPlan,
                    "projectBatch": i.subject.project.category.batch.projectBatch,
                    "planCategory": i.subject.project.category.planCategory,
                    "projectName": i.subject.project.projectName,
                    "contractNo": i.subject.contract_subject.values('contractNo'),
                    "subjectName": i.subject.subjectName,
                    "subjectState": i.subject.subjectState,
                    "head": i.subject.head,
                    "mobile": i.subject.mobile,
                    "scienceFunding": contract_content.scienceFunding,
                    "money": i.money
                }
                for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                    for funding in contract_content.unitFunding:
                        if funding['unit'] == ut.unitName:
                            if i.state == '通过':
                                money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})
                            else:
                                money = Decimal(funding['first']) + Decimal(funding['last'])
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})
                data["unit"] = unit
                if len(unit) == 0:
                    pass
                else:
                    lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 失信项目经费统计查询/
    @action(detail=False, methods=['post'], url_path='admin_blacklist_query')
    def admin_blacklist_query(self, request):
        lists = []
        list2 = []
        subject_obj = Subject.objects.order_by('-project__category__batch__annualPlan',
                                               '-contract_subject__contractNo').filter(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'))
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "head": "head__contains",
            "subjectState": "subjectState",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject = subject_obj.filter(**data)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
            for i in queryset:
                unit = []
                data = {
                    "annualPlan": i.subject.project.category.batch.annualPlan,
                    "projectBatch": i.subject.project.category.batch.projectBatch,
                    "planCategory": i.subject.project.category.planCategory,
                    "projectName": i.subject.project.projectName,
                    "contractNo": i.subject.contract_subject.values('contractNo'),
                    "subjectName": i.subject.subjectName,
                    "subjectState": i.subject.subjectState,
                    "head": i.subject.head,
                    "mobile": i.subject.mobile,
                    "scienceFunding": contract_content.scienceFunding,
                    "money": i.money
                }
                for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                    for funding in contract_content.unitFunding:
                        if funding['unit'] == ut.unitName:
                            if i.state == '通过':
                                money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})
                            else:
                                money = Decimal(funding['first']) + Decimal(funding['last'])
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})

                data["unit"] = unit
                if len(unit) == 0:
                    pass
                else:
                    lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 小程序
    @action(detail=False, methods=['get'], url_path='admin_funding_show')
    def admin_funding_show(self, request):
        annual_plan = request.query_params.dict().get('annualPlan')
        # 已拨付
        has_allocated = sum([i.money for i in self.queryset.filter(state='通过',
                                                                   subject__project__category__batch__annualPlan=annual_plan)])
        # 失信经费
        subject = Subject.objects.filter(Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'),
                                         project__category__batch__annualPlan=annual_plan).values(
                                         'contract_subject__contractContent', 'id')
        dishonest_money = 0
        for j in subject:
            funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
            money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
            dishonest_money += funding - money
        # 待拨付
        subject = Subject.objects.exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题')).filter(
            project__category__batch__annualPlan=annual_plan)
        not_allocated = 0
        for j in subject:
            if self.queryset.filter(subject=j).exists():
                contract_content = j.contract_subject.values('contractContent')
                funding = ContractContent.objects.get(id=contract_content[0]['contractContent']).scienceFunding
                money = sum([i.money for i in GrantSubject.objects.filter(subject=j) if i.state == '通过'])
                not_allocated += (funding - money)
        data = {
            "hasAllocated": has_allocated,
            "dishonestMoney": dishonest_money,
            "notAllocated": not_allocated,

        }
        return Response({'code': 0, 'message': '请求成功', 'detail': data}, status=status.HTTP_200_OK)


    ###单位
    # 经费统计展示/分管人员
    @action(detail=False, methods=['get'], url_path='enterprise_funding_statistical_show')
    def enterprise_funding_statistical_show(self, request):
        lists = []
        enterprise = request.user
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(
            subject__enterprise=enterprise, state='通过')
        for i in queryset:
            unit = []
            data = {
                "annualPlan": i.subject.project.category.batch.annualPlan,
                "projectBatch": i.subject.project.category.batch.projectBatch,
                "planCategory": i.subject.project.category.planCategory,
                "projectName": i.subject.project.projectName,
                "contractNo": i.subject.contract_subject.values('contractNo'),
                "subjectName": i.subject.subjectName,
                "head": i.subject.head,
                "mobile": i.subject.mobile,
                "scienceFunding": i.subject.contract_subject.values('approvalMoney'),
                "money": i.money,
                "grantType": i.grantType,
            }
            # 拨款申请单
            allocated_single = AllocatedSingle.objects.filter(grantSubject=i.id)
            for j in allocated_single:
                unit.append({"unitName": j.unitName, "money": j.money})
            data["unit"] = unit
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 经费统计查询 / 分管人员
    @action(detail=False, methods=['post'], url_path='enterprise_funding_statistical_query')
    def enterprise_funding_statistical_query(self, request):
        lists = []
        list2 = []
        enterprise = request.user
        queryset = self.queryset.order_by('-subject__project__category__batch__annualPlan',
                                          '-subject__contract_subject__contractNo').filter(
            subject__enterprise=enterprise, state='通过')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
            "subjectName": "subject__subjectName__contains",
            "head": 'subject__head__contains',
            "grantType": "grantType",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        for i in instance:
            unit = []
            data = {
                "annualPlan": i.subject.project.category.batch.annualPlan,
                "projectBatch": i.subject.project.category.batch.projectBatch,
                "planCategory": i.subject.project.category.planCategory,
                "projectName": i.subject.project.projectName,
                "contractNo": i.subject.contract_subject.values('contractNo'),
                "subjectName": i.subject.subjectName,
                "head": i.subject.head,
                "mobile": i.subject.mobile,
                "scienceFunding": i.subject.contract_subject.values('approvalMoney'),
                "money": i.money,
                "grantType": i.grantType,
            }
            # 拨款申请单
            allocated_single = AllocatedSingle.objects.filter(grantSubject=i.id)
            for j in allocated_single:
                unit.append({"unitName": j.unitName, "money": j.money})
            data["unit"] = unit
            lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 未拨付项目经费统计展示/管理员
    @action(detail=False, methods=['get'], url_path='enterprise_funding_no_show')
    def enterprise_funding_no_show(self, request):
        lists = []
        enterprise = request.user
        subject = Subject.objects.order_by('-project__category__batch__annualPlan',
                                           '-contract_subject__contractNo').exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题')).filter(enterprise=enterprise)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            if queryset.exists():
                contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
                if queryset.filter(state='通过').count() == 2:
                    pass
                elif queryset.count() == 2:
                    for i in queryset.filter(Q(state='通过') | Q(state='待提交') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '通过':
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
                else:
                    for i in queryset.filter(Q(state='待提交') | Q(state='通过') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '待提交' or i.state == '待审核' or i.state == '退回':
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal('0.00'):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal('0.00'):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 未拨付项目经费统计查询/管理员
    @action(detail=False, methods=['post'], url_path='enterprise_funding_no_query')
    def enterprise_funding_no_query(self, request):
        lists = []
        list2 = []
        enterprise = request.user
        subject_obj = Subject.objects.order_by('-project__category__batch__annualPlan',
                                               '-contract_subject__contractNo').exclude(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题')).filter(enterprise=enterprise)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "head": "head__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject = subject_obj.filter(**data)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            if queryset.exists():
                contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
                if queryset.filter(state='通过').count() == 2:
                    pass
                elif queryset.count() == 2:
                    for i in queryset.filter(Q(state='通过') | Q(state='待提交') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '通过':
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal("0.00"):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
                        break
                else:
                    for i in queryset.filter(Q(state='待提交') | Q(state='通过') | Q(state='待审核') | Q(state='退回')):
                        unit = []
                        data = {
                            "annualPlan": i.subject.project.category.batch.annualPlan,
                            "projectBatch": i.subject.project.category.batch.projectBatch,
                            "planCategory": i.subject.project.category.planCategory,
                            "projectName": i.subject.project.projectName,
                            "contractNo": i.subject.contract_subject.values('contractNo'),
                            "subjectName": i.subject.subjectName,
                            "head": i.subject.head,
                            "mobile": i.subject.mobile,
                            "scienceFunding": contract_content.scienceFunding,
                            "money": i.money
                        }
                        for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                            for funding in contract_content.unitFunding:
                                if funding['unit'] == ut.unitName:
                                    if i.state == '待提交' or i.state == '待审核' or i.state == '退回':
                                        money = Decimal(funding['first']) + Decimal(funding['last'])
                                        if money == Decimal('0.00'):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                                    else:
                                        money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                        if money == Decimal('0.00'):
                                            pass
                                        else:
                                            unit.append({'unitName': ut.unitName, 'money': money})
                        data["unit"] = unit
                        if len(unit) == 0:
                            pass
                        else:
                            lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 失信项目经费统计展示/管理员
    @action(detail=False, methods=['get'], url_path='enterprise_funding_blacklist_show')
    def enterprise_funding_blacklist_show(self, request):
        lists = []
        enterprise = request.user
        subject = Subject.objects.order_by('-project__category__batch__annualPlan',
                                           '-contract_subject__contractNo').filter(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'),
            enterprise=enterprise)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
            for i in queryset:
                unit = []
                data = {
                    "annualPlan": i.subject.project.category.batch.annualPlan,
                    "projectBatch": i.subject.project.category.batch.projectBatch,
                    "planCategory": i.subject.project.category.planCategory,
                    "projectName": i.subject.project.projectName,
                    "contractNo": i.subject.contract_subject.values('contractNo'),
                    "subjectName": i.subject.subjectName,
                    "subjectState": i.subject.subjectState,
                    "head": i.subject.head,
                    "mobile": i.subject.mobile,
                    "scienceFunding": contract_content.scienceFunding,
                    "money": i.money
                }
                for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                    for funding in contract_content.unitFunding:
                        if funding['unit'] == ut.unitName:
                            if i.state == '通过':
                                money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})
                            else:
                                money = Decimal(funding['first']) + Decimal(funding['last'])
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})

                data["unit"] = unit
                if len(unit) == 0:
                    pass
                else:
                    lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 失信项目经费统计查询/
    @action(detail=False, methods=['post'], url_path='enterprise_blacklist_query')
    def enterprise_blacklist_query(self, request):
        lists = []
        list2 = []
        enterprise = request.user
        subject_obj = Subject.objects.order_by('-project__category__batch__annualPlan',
                                               '-contract_subject__contractNo').filter(
            Q(subjectState='验收不通过') | Q(subjectState='项目终止') | Q(subjectState='逾期未结题'),
            enterprise=enterprise)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "head": "head__contains",
            "subjectState": "subjectState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject = subject_obj.filter(**data)
        for s in subject:
            queryset = self.queryset.filter(subject=s)
            contract_content = ContractContent.objects.get(id=Contract.objects.get(subject=s).contractContent)
            for i in queryset:
                unit = []
                data = {
                    "annualPlan": i.subject.project.category.batch.annualPlan,
                    "projectBatch": i.subject.project.category.batch.projectBatch,
                    "planCategory": i.subject.project.category.planCategory,
                    "projectName": i.subject.project.projectName,
                    "contractNo": i.subject.contract_subject.values('contractNo'),
                    "subjectName": i.subject.subjectName,
                    "subjectState": i.subject.subjectState,
                    "head": i.subject.head,
                    "mobile": i.subject.mobile,
                    "scienceFunding": contract_content.scienceFunding,
                    "money": i.money
                }
                for ut in AllocatedSingle.objects.filter(grantSubject=i.id):
                    for funding in contract_content.unitFunding:
                        if funding['unit'] == ut.unitName:
                            if i.state == '通过':
                                money = Decimal(funding['first']) + Decimal(funding['last']) - ut.money
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})
                            else:
                                money = Decimal(funding['first']) + Decimal(funding['last'])
                                if money == Decimal("0.00"):
                                    pass
                                else:
                                    unit.append({'unitName': ut.unitName, 'money': money})

                data["unit"] = unit
                if len(unit) == 0:
                    pass
                else:
                    lists.append(data)
        unit_name = request.data['unitName']
        if unit_name:
            for unit in lists:
                for name in unit['unit']:
                    if unit_name in name['unitName']:
                        list2.append(unit)
            return Response({"code": 0, "message": "请求成功", "detail": list2}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)


#
class AllocatedSingleViewSet(mongodb_viewsets.ModelViewSet):
    queryset = AllocatedSingle.objects.all()
    serializer_class = AllocatedSingleSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        print(request.data)
        if self.queryset.filter(grantSubject=request.data['grantSubject'], unitName=request.data['unitName']):
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(grantSubject=request.data['grantSubject'], unitName=request.data['unitName'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            self.queryset.filter(id=serializer.data['id']).update(storage=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            self.queryset.filter(id=serializer.data['id']).update(storage=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 当前项目下所有申请拨款单的展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        lists = []
        subject_id = request.query_params.dict().get('subjectId')
        grant_subject = GrantSubject.objects.filter(subject_id=subject_id, state='通过')
        for grant in grant_subject:
            queryset = self.queryset.filter(grantSubject=grant.id)
            serializers = self.get_serializer(queryset, many=True)
            lists.extend(serializers.data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 初始数据展示
    @action(detail=False, methods=['get'], url_path='change_user_init')
    def change_user_init(self, request):
        lists = []
        subject_id = request.query_params.dict().get("subjectId")
        grant_type = request.query_params.dict().get("grantType")
        grant_subject = GrantSubject.objects.filter(subject_id=subject_id, grantType=grant_type)
        for grant in grant_subject:
            queryset = self.queryset.filter(grantSubject=grant.id)
            serializers = self.get_serializer(queryset, many=True)
            lists.extend(serializers.data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 当前项目下所有申请拨款单附件的展示
    @action(detail=False, methods=['get'], url_path='attachment_show')
    def attachment_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        try:
            grant_subject = GrantSubject.objects.filter(subject_id=subject_id, state='通过').values('attachment')
            return Response({"code": 0, "message": "请求成功", "detail": {"attachment": grant_subject}},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response(False)
