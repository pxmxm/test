# Create your views here.
import datetime
import uuid
from ast import literal_eval
from decimal import Decimal
from io import BytesIO

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.http import StreamingHttpResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_mongoengine import viewsets as mongodb_viewsets

from article.tasks import add_declare, Reduction_declare, pdf
from blacklist.models import UnitBlacklist, ProjectLeader, ExpertsBlacklist
from change.models import ChangeSubject
from concluding.models import Acceptance, KOpinionSheet, Output, ExpenditureStatement, SubjectConcluding
from contract.models import Contract, ContractContent
from expert.models import Expert
from funding.models import GrantSubject, AllocatedSingle
from project.models import Project, Batch, Category
from research.models import Proposal
from sms.models import TextTemplate
from subject.models import Subject, SubjectExpertsOpinionSheet, OpinionSheet, ExpertOpinionSheet, \
    SubjectKExperts, ExpectedResults, FundingBudget, IntellectualProperty, SubjectUnitInfo, \
    SubjectPersonnelInfo, SubjectOtherInfo, AttachmentList, UnitCommitment, SubjectInfo, Process, Attachment
from subject.serializers import SubjectSerializers, SubjectUnitSerializers, \
    SubjectAdminSerializers, SubjectChargeSerializers, SubjectOrganSerializers, OpinionSheetSerializers, \
    PGExpertsSystemSerializers, \
    PGOpinionSheetSerializers, PGExpertsSubjectOpinionSheetSerializers, \
    ExpectedResultsSerializers, FundingBudgetSerializers, IntellectualPropertySerializers, SubjectUnitInfoSerializers, \
    SubjectPersonnelInfoSerializers, SubjectOtherInfoSerializers, AttachmentListSerializers, UnitCommitmentSerializers, \
    SubjectInfoSerializers, ProcessSerializers, AttachmentSerializers, SubjectKExpertsSerializers
from termination.models import Termination, TKOpinionSheet, SubjectTermination, ChargeTermination, TOutput, \
    TExpenditureStatement
from tpl.views_download import generate_declare_pdf, generate_experts_review_single_pdf, generate_review_single_pdf, \
    read_file
from users.models import User, KExperts, Agency, Enterprise
from utils.excel import Excel_data
from utils.letter import SMS
from utils.oss import OSS
from utils.sms_template import send_template


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)


    # 新增项目申报项目/单位
    @action(detail=False, methods=['post'], url_path='new_subject')
    def new_subject(self, request, *args, **kwargs):
        user = request.user
        new_time = datetime.date.today()
        if Batch.objects.exclude(isActivation='禁用').filter().count() == 0:
            return Response({"code": 1, "message": "当前无可申报项目"}, status=status.HTTP_200_OK)
        if not UnitBlacklist.objects.filter(creditCode=user.username, isArchives=False,
                                            disciplinaryTime__gt=new_time).exists():
            if user.enterprise.industry == '企业':
                if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 2:
                    return Response({"code": 3, "message": "贵单位逾期未结题项目超过2项，无法申请立项"}, status=status.HTTP_200_OK)
                else:
                    return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)
            else:
                if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 5:
                    return Response({"code": 4, "message": "贵单位逾期未结题项目超过5项，无法申请立项"},
                                    status=status.HTTP_200_OK)
                else:
                    return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 2, "message": "贵单位已被列为失信人，无法申报项目，详情请联系青秀区科技局"}, status=status.HTTP_200_OK)

    # 课题名称检索 /单位
    # 是否可编辑 / 单位
    @action(detail=False, methods=['get'], url_path='editor_subject')
    def editor_subject(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        if self.queryset.get(id=subject_id).project.category.batch.isActivation == '启用' or Batch.objects.filter(isActivation='启用').exists():
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, "message": "当前没有可申报的批次"}, status=status.HTTP_200_OK)

    # 课题名称检索 /单位
    @action(detail=False, methods=['post'], url_path='subject_name_retrieval')
    def subject_name_retrieval(self, request, *args, **kwargs):
        if self.queryset.filter(subjectName=request.data['subjectName'], enterprise=request.user).exists():
            return Response({"code": 1, "message": "课题名称已存在"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)

    # 填写项目申报书首页/单位
    def create(self, request, *args, **kwargs):
        user = request.user
        # | Q(subjectState='项目退回', state='立项复核') == subjectState='立项复核未通过'
        queryset = self.queryset.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='立项复核未通过')).filter(
            enterprise=user,
            project__category__batch__annualPlan=request.data['annualPlan'],
            project__category__batch__isActivation='启用')
        if user.enterprise.industry == '企业':
            if queryset.count() >= 3:
                return Response({"code": 1, "message": "同一批次下最多可申请立项3个项目"}, status=status.HTTP_200_OK)
        else:
            if queryset.count() >= 10:
                return Response({"code": 1, "message": "同一批次下最多可申请立项10个项目"}, status=status.HTTP_200_OK)
        json_data = request.data
        keys = {
            "annualPlan": "category__batch__annualPlan",
            "planCategory": "category__planCategory",
            "projectName": "projectName",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys}
        try:
            project = Project.objects.get(**data, category__batch__isActivation="启用")
            if project.category.batch.isActivation == '启用':
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                queryset = self.queryset.get(id=serializer.data['id'])
                queryset.enterprise_id = user.id
                queryset.project = project
                queryset.save()
                return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 1, "message": "该项目类别、名称被禁用，请选择其他项目类别、名称"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"code": 2, "message": "该项目类别、名称被禁用，请选择其他项目类别、名称"}, status=status.HTTP_200_OK)

    # 编辑项目申报书首页/单位
    def update(self, request, *args, **kwargs):
        user = request.user
        queryset = self.queryset.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='立项复核未通过')).filter(
            enterprise=user,
            project__category__batch__annualPlan=request.data['annualPlan'],
            project__category__batch__isActivation='启用')
        if user.enterprise.industry == '企业':
            if queryset.count() >= 3:
                return Response({"code": 1, "message": "同一批次下最多可申请立项3个项目"}, status=status.HTTP_200_OK)
        else:
            if queryset.count() >= 10:
                return Response({"code": 1, "message": "同一批次下最多可申请立项10个项目"}, status=status.HTTP_200_OK)
        json_data = request.data
        keys = {
            "annualPlan": "category__batch__annualPlan",
            "planCategory": "category__planCategory",
            "projectName": "projectName",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys}
        try:
            project = Project.objects.get(**data, category__batch__isActivation="启用")
            if project.category.batch.isActivation == '启用':
                partial = kwargs.pop('partial', False)
                instance = self.get_object()
                serializers = self.get_serializer(instance, data=request.data, partial=partial)
                serializers.is_valid(raise_exception=True)
                self.perform_update(serializers)
                instance.project = project
                instance.save()
                return Response({"code": 0, "message": "更新成功"}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 1, "message": "该项目类别、名称被禁用，请选择其他项目类别、名称"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"code": 2, "message": "该项目类别、名称被禁用，请选择其他项目类别、名称"}, status=status.HTTP_200_OK)
            # return Response({"code": 2, "message": "同一项目名称有两个哦"}, status=status.HTTP_200_OK)

    # 课题提交/单位
    @action(detail=False, methods=['post'], url_path='submit')
    def subject_submit(self, request):
        user = request.user
        queryset = self.queryset.get(id=request.data['subjectId'])
        new_time = datetime.date.today()
        if not AttachmentList.objects.filter(attachmentName='可行性报告', subjectId=request.data['subjectId']) and \
                not AttachmentList.objects.filter(attachmentName='项目负责人居民身份证复印件', subjectId=request.data['subjectId']):
            return Response({"code": 7, "message": "请上传可行性报告以及项目负责人居民身份证复印件"}, status=status.HTTP_200_OK)
        elif not AttachmentList.objects.filter(attachmentName='可行性报告', subjectId=request.data['subjectId']):
            return Response({"code": 8, "message": "请上传可行性报告"}, status=status.HTTP_200_OK)
        elif not AttachmentList.objects.filter(attachmentName='项目负责人居民身份证复印件',
                                               subjectId=request.data['subjectId']):
            return Response({"code": 9, "message": "请上传项目负责人居民身份证复印件"}, status=status.HTTP_200_OK)
        if UnitBlacklist.objects.filter(creditCode=user.username, isArchives=False,
                                        disciplinaryTime__gt=new_time).exists():
            return Response({"code": 6, "message": "贵单位已被列为失信人，无法申报项目，详情请联系青秀区科技局"}, status=status.HTTP_200_OK)
        if queryset.project.category.batch.isActivation == '启用':
            if queryset.subjectState == '待提交' or queryset.subjectState == '形式审查未通过' or queryset.subjectState == '立项复核未通过':
                instance = self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过') |
                                                 Q(subjectState='立项复核未通过')).filter(
                    enterprise=user,
                    project__category__batch__annualPlan=queryset.project.category.batch.annualPlan,
                    project__category__batch__projectBatch=queryset.project.category.batch.projectBatch)
                if user.enterprise.industry == '企业':
                    if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 2:
                        return Response({"code": 3, "message": "贵单位逾期未结题项目超过2项，无法申请立项"}, status=status.HTTP_200_OK)
                    if instance.count() >= 3:
                        return Response({"code": 1, "message": "同一批次下最多可申请立项3个项目"}, status=status.HTTP_200_OK)
                    else:
                        queryset.state = '提交成功'
                        # queryset.subjectState = '提交成功'
                        queryset.subjectState = '形式审查'
                        queryset.returnReason = None
                        queryset.declareTime = datetime.date.today()
                        pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
                        queryset.attachmentPDF = pdf_url
                        queryset.save()
                        Process.objects.create(state='形式审查', subject=queryset)
                        abc = add_declare(annualPlan=queryset.project.category.batch.annualPlan,
                                          projectBatch=queryset.project.category.batch.projectBatch,
                                          planCategory=queryset.project.category.planCategory,
                                          projectName=queryset.project.projectName)
                        # print(abc.state)
                        return Response({'code': 0, 'message': '提交成功'}, status=status.HTTP_200_OK)
                else:
                    if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 5:
                        return Response({"code": 4, "message": "贵单位逾期未结题项目超过5项，无法申请立项"}, status=status.HTTP_200_OK)
                    if instance.count() >= 10:
                        return Response({"code": 1, "message": "同一批次下最多可申请立项10个项目"}, status=status.HTTP_200_OK)
                    else:
                        queryset.subjectState = '形式审查'
                        queryset.state = '提交成功'
                        # queryset.subjectState = '提交成功'
                        queryset.returnReason = None
                        queryset.declareTime = datetime.date.today()
                        pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
                        queryset.attachmentPDF = pdf_url
                        queryset.save()
                        Process.objects.create(state='形式审查', subject=queryset)
                        abc = add_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
                                                projectBatch=queryset.project.category.batch.projectBatch,
                                                planCategory=queryset.project.category.planCategory,
                                                projectName=queryset.project.projectName)
                        # print(abc.state)
                        return Response({'code': 0, 'message': '提交成功'}, status=status.HTTP_200_OK)
            else:
                return Response({"code": "4", "message": "已经重复提交"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": "3", "message": "该项目类别、名称被禁用，请选择其他项目类别、名称"}, status=status.HTTP_200_OK)

    # # 课题提交/单位（待提交/形式审查未通过）
    # @action(detail=False, methods=['post'], url_path='submit')
    # def subject_submit(self, request):
    #     user = request.user
    #     queryset = self.queryset.get(id=request.data['subjectId'])
    #     new_time = datetime.date.today()
    #     if not AttachmentList.objects.filter(attachmentName='可行性报告', subjectId=request.data['subjectId']) and \
    #             not AttachmentList.objects.filter(attachmentName='项目负责人居民身份证复印件', subjectId=request.data['subjectId']):
    #         return Response({"code": 7, "message": "项目负责人居民身份证复印件"}, status=status.HTTP_200_OK)
    #     elif not AttachmentList.objects.filter(attachmentName='可行性报告', subjectId=request.data['subjectId']):
    #         return Response({"code": 8, "message": "请上传可行性报告"}, status=status.HTTP_200_OK)
    #     elif not AttachmentList.objects.filter(attachmentName='项目负责人居民身份证复印件',
    #                                            subjectId=request.data['subjectId']):
    #         return Response({"code": 9, "message": "请上传项目负责人居民身份证复印件"}, status=status.HTTP_200_OK)
    #     if UnitBlacklist.objects.filter(creditCode=user.username, isArchives=False, disciplinaryTime__gt=new_time).exists():
    #         return Response({"code": 6, "message": "贵单位已被列为失信人，无法申报项目，详情请联系青秀区科技局"}, status=status.HTTP_200_OK)
    #     if queryset.project.category.batch.isActivation == '启用':
    #         if queryset.subjectState == '待提交':
    #             if user.enterprise.industry == '企业':
    #                 if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 2:
    #                     return Response({"code": 3, "message": "贵单位逾期未结题项目超过2项，无法申请立项"}, status=status.HTTP_200_OK)
    #                 if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='项目退回',
    #                                                                                                state='立项复核')).filter(
    #                     enterprise=user,
    #                     project__category__batch__annualPlan=queryset.project.category.batch.annualPlan,
    #                     project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() >= 3:
    #                     return Response({"code": 1, "message": "同一批次下最多可申请立项3个项目"}, status=status.HTTP_200_OK)
    #                 else:
    #                     queryset.state = '提交成功'
    #                     # queryset.subjectState = '提交成功'
    #                     queryset.subjectState = '形式审查'
    #                     queryset.declareTime = datetime.date.today()
    #                     pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
    #                     queryset.attachmentPDF = pdf_url
    #                     queryset.save()
    #                     Process.objects.create(state='提交成功', subject=queryset)
    #                     abc = add_declare(annualPlan=queryset.project.category.batch.annualPlan,
    #                                       projectBatch=queryset.project.category.batch.projectBatch,
    #                                       planCategory=queryset.project.category.planCategory,
    #                                       projectName=queryset.project.projectName)
    #                     # print(abc.state)
    #                     return Response({'code': 0, 'message': '提交成功'}, status=status.HTTP_200_OK)
    #             else:
    #                 if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 5:
    #                     return Response({"code": 4, "message": "贵单位逾期未结题项目超过5项，无法申请立项"}, status=status.HTTP_200_OK)
    #                 if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='项目退回',
    #                                                                                                state='立项复核')).filter(
    #                     enterprise=user,
    #                     project__category__batch__annualPlan=queryset.project.category.batch.annualPlan,
    #                     project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() >= 10:
    #                     return Response({"code": 1, "message": "同一批次下最多可申请立项10个项目"}, status=status.HTTP_200_OK)
    #                 else:
    #                     queryset.subjectState = '形式审查'
    #                     queryset.state = '提交成功'
    #                     # queryset.subjectState = '提交成功'
    #                     queryset.declareTime = datetime.date.today()
    #                     pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
    #                     queryset.attachmentPDF = pdf_url
    #                     queryset.save()
    #                     Process.objects.create(state='提交成功', subject=queryset)
    #                     abc = add_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
    #                                             projectBatch=queryset.project.category.batch.projectBatch,
    #                                             planCategory=queryset.project.category.planCategory,
    #                                             projectName=queryset.project.projectName)
    #                     # print(abc.state)
    #                     return Response({'code': 0, 'message': '提交成功'}, status=status.HTTP_200_OK)
    #         else:
    #             if queryset.subjectState == '形式审查未通过':
    #                 if user.enterprise.industry == '企业':
    #                     if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 2:
    #                         return Response({"code": 3, "message": "贵单位逾期未结题项目超过2项，无法申请立项"}, status=status.HTTP_200_OK)
    #                     if self.queryset.exclude(
    #                             Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='项目退回',
    #                                                                                   state='立项复核')).filter(
    #                         enterprise=user,
    #                         project__category__batch__annualPlan=queryset.project.category.batch.annualPlan,
    #                         project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() >= 3:
    #                         return Response({"code": 1, "message": "同一批次下最多可申请立项3个项目"}, status=status.HTTP_200_OK)
    #                     else:
    #                         queryset.subjectState = '形式审查'
    #                         queryset.state = '提交成功'
    #                         queryset.returnReason = None
    #                         queryset.declareTime = datetime.date.today()
    #                         pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
    #                         queryset.attachmentPDF = pdf_url
    #                         queryset.save()
    #                         Process.objects.create(state='提交成功', subject=queryset)
    #                         abc = add_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
    #                                                 projectBatch=queryset.project.category.batch.projectBatch,
    #                                                 planCategory=queryset.project.category.planCategory,
    #                                                 projectName=queryset.project.projectName)
    #                         # print(abc.state)
    #                         return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_200_OK)
    #                 else:
    #                     if self.queryset.filter(enterprise=user, subjectState='逾期未结题').count() > 5:
    #                         return Response({"code": 4, "message": "贵单位逾期未结题项目超过5项，无法申请立项"}, status=status.HTTP_200_OK)
    #                     if self.queryset.exclude(
    #                             Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='项目退回',
    #                                                                                   state='立项复核')).filter(
    #                         enterprise=user,
    #                         project__category__batch__annualPlan=queryset.project.category.batch.annualPlan,
    #                         project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() >= 10:
    #                         return Response({"code": 2, "message": "同一批次下最多可申请立项10个项目"}, status=status.HTTP_200_OK)
    #                     else:
    #                         queryset.subjectState = '形式审查'
    #                         queryset.state = '提交成功'
    #                         queryset.returnReason = None
    #                         queryset.declareTime = datetime.date.today()
    #                         pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
    #                         queryset.attachmentPDF = pdf_url
    #                         queryset.save()
    #                         Process.objects.create(state='提交成功', subject=queryset)
    #                         abc = add_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
    #                                                 projectBatch=queryset.project.category.batch.projectBatch,
    #                                                 planCategory=queryset.project.category.planCategory,
    #                                                 projectName=queryset.project.projectName)
    #                         # print(abc.state)
    #                         return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_200_OK)
    #         return Response({"code": "4", "message": "已经重复提交"}, status=status.HTTP_200_OK)
    #     else:
    #         return Response({"code": "3", "message": "该项目类别、名称被禁用，请选择其他项目类别、名称"}, status=status.HTTP_200_OK)

    # # 课题提交/单位
    # @action(detail=False, methods=['post'], url_path='submit')
    # def subject_submit(self, request):
    #     user = request.user
    #     queryset = self.queryset.get(id=request.data['subjectId'])
    #     if queryset.project.category.batch.isActivation == '启用':
    #         if queryset.subjectState == '待提交':
    #             if user.enterprise.industry == '企业':
    #                 if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
    #                         enterprise=user,
    #                         project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() > 3:
    #                     return Response({"code": 1, "message": "同一批次下最多可申请立项3个项目"}, status=status.HTTP_200_OK)
    #                 else:
    #                     queryset.state = '提交成功'
    #                     queryset.subjectState = '提交成功'
    #                     queryset.declareTime = datetime.date.today()
    #                     # pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
    #                     # queryset.attachmentPDF = pdf_url
    #                     a = pdf(subject_id=queryset.id)
    #                     print(a)
    #                     # print(a.state)
    #                     queryset.save()
    #                     Process.objects.create(state='提交成功', subject=queryset)
    #                     abc = add_declare(annualPlan=queryset.project.category.batch.annualPlan,
    #                                       projectBatch=queryset.project.category.batch.projectBatch,
    #                                       planCategory=queryset.project.category.planCategory,
    #                                       projectName=queryset.project.projectName)
    #                     # print(abc.state)
    #                     return Response({'code': 0, 'message': '提交成功'}, status=status.HTTP_200_OK)
    #             else:
    #                 if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
    #                         enterprise=user,
    #                         project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() > 10:
    #                     return Response({"code": 1, "message": "同一批次下最多可申请立项10个项目"}, status=status.HTTP_200_OK)
    #                 else:
    #                     queryset.state = '提交成功'
    #                     queryset.subjectState = '提交成功'
    #                     queryset.declareTime = datetime.date.today()
    #                     pdf_url = generate_declare_pdf(subject_id=request.data['subjectId'])
    #                     queryset.attachmentPDF = pdf_url
    #                     queryset.save()
    #                     Process.objects.create(state='提交成功', subject=queryset)
    #                     abc = add_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
    #                                             projectBatch=queryset.project.category.batch.projectBatch,
    #                                             planCategory=queryset.project.category.planCategory,
    #                                             projectName=queryset.project.projectName)
    #                     # print(abc.state)
    #                     return Response({'code': 0, 'message': '提交成功'}, status=status.HTTP_200_OK)
    #         else:
    #             if queryset.subjectState == '形式审查未通过':
    #                 if user.enterprise.industry == '企业':
    #                     if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
    #                             enterprise=user,
    #                             project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() > 3:
    #                         return Response({"code": 1, "message": "同一批次下最多可申请立项3个项目"}, status=status.HTTP_200_OK)
    #                     else:
    #                         queryset.subjectState = '形式审查'
    #                         queryset.state = '提交成功'
    #                         queryset.returnReason = None
    #                         queryset.declareTime = datetime.date.today()
    #                         queryset.save()
    #                         Process.objects.create(state='提交成功', subject=queryset)
    #                         abc = add_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
    #                                                 projectBatch=queryset.project.category.batch.projectBatch,
    #                                                 planCategory=queryset.project.category.planCategory,
    #                                                 projectName=queryset.project.projectName)
    #                         # print(abc.state)
    #                         return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_200_OK)
    #                 else:
    #                     if self.queryset.filter(enterprise=user,
    #                                             project__category__batch__projectBatch=queryset.project.category.batch.projectBatch).count() > 10:
    #                         return Response({"code": 2, "message": "同一批次下最多可申请立项10个项目"}, status=status.HTTP_200_OK)
    #                     else:
    #                         queryset.subjectState = '形式审查'
    #                         queryset.state = '提交成功'
    #                         queryset.returnReason = None
    #                         queryset.declareTime = datetime.date.today()
    #                         queryset.save()
    #                         Process.objects.create(state='提交成功', subject=queryset)
    #                         abc = add_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
    #                                                 projectBatch=queryset.project.category.batch.projectBatch,
    #                                                 planCategory=queryset.project.category.planCategory,
    #                                                 projectName=queryset.project.projectName)
    #                         # print(abc.state)
    #                         return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_200_OK)
    #     else:
    #         return Response({"message": "该项目类别、名称被禁用，请选择其他项目类别、名称"}, status=status.HTTP_200_OK)

    # 课题删除 / 单位
    @action(detail=False, methods=['delete'], url_path='delete_subject')
    def delete_subject(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        instance = self.queryset.get(id=subject_id)
        SubjectInfo.objects.filter(subjectId=subject_id).delete()
        SubjectUnitInfo.objects.filter(subjectId=subject_id).delete()
        ExpectedResults.objects.filter(subjectId=subject_id).delete()
        FundingBudget.objects.filter(subjectId=subject_id).delete()
        IntellectualProperty.objects.filter(subjectId=subject_id).delete()
        SubjectPersonnelInfo.objects.filter(subjectId=subject_id).delete()
        SubjectOtherInfo.objects.filter(subjectId=subject_id).delete()
        UnitCommitment.objects.filter(subjectId=subject_id).delete()
        AttachmentList.objects.filter(subjectId=subject_id).delete()
        self.perform_destroy(instance)
        return Response({'code': 0, 'message': '已删除 '}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show/(?P<subject_id>\d+)')
    def show(self, request, subject_id):
        queryset = self.queryset.filter(id=subject_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({'code': 0, 'message': 'ok ', "detail": serializer.data}, status=status.HTTP_200_OK)

    # 实地调研展示
    @action(detail=False, methods=['get'], url_path='research_show')
    def research_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.get(id=subject_id)
        if queryset.fieldResearch:
            data = {
                "times": queryset.fieldResearch.times,
                "place": queryset.fieldResearch.place,
                "personnel": queryset.fieldResearch.personnel,
                "opinion": queryset.fieldResearch.opinion,
                "attachmentPDF": queryset.fieldResearch.attachmentPDF
            }
            return Response({'code': 0, 'message': '请求成功 ', "detail": data}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 1, 'message': '数据不存在'}, status=status.HTTP_200_OK)

    # 项目资料导入
    @action(detail=False, methods=['post'], url_path='import_subject')
    def import_subject(self, request):
        json_data = request.data
        keys = {
            "annualPlan": "category__batch__annualPlan",
            "projectBatch": "category__batch__projectBatch",
            "planCategory": "category__planCategory",
            "projectName": "projectName",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys}
        project = Project.objects.get(**data)
        queryset = self.queryset.create(project=project,
                                        subjectName=request.data['subjectName'],
                                        unitName=request.data['unitName'],
                                        head=request.data['head'],
                                        phone=request.data['phone'],
                                        subjectState=request.data['subjectState'],
                                        warning=request.data['warning'],
                                        )
        charge_user = User.objects.get(id=request.data['charge'])
        queryset.charge.add(charge_user)
        queryset.save()
        return Response({'code': 0, 'message': '保存成功', 'detail': queryset.id}, status=status.HTTP_200_OK)

    # 项目申报PDF展示
    @action(detail=False, methods=['get'], url_path='show_pdf')
    def show_pdf(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        types = request.query_params.dict().get('types')
        queryset = self.queryset.get(id=subject_id)
        if queryset.attachmentPDF:
            return Response({'code': 0, 'message': 'ok ', "detail": queryset.attachmentPDF}, status=status.HTTP_200_OK)
        else:
            try:
                attachment = Attachment.objects.get(subject=subject_id, types=types)
                return Response({'code': 0, 'message': 'ok ', "detail": attachment.attachmentPath[0]['path']},
                                status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'code': 1, 'message': '没有数据'}, status=status.HTTP_200_OK)


# 项目流程
class ProcessViewSet(viewsets.ModelViewSet):
    queryset = Process.objects.all()
    serializer_class = ProcessSerializers
    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request, *args, **kwargs):
        queryset = self.queryset.order_by('-time').filter(subject_id=request.query_params.dict().get('subjectId'),
                                                          dynamic=False).exclude(state='项目下达')
        serializer = self.get_serializer(queryset, many=True)
        return Response({'code': 0, 'message': '请求成功', 'detail': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='dynamic_show')
    def dynamic_show(self, request, *args, **kwargs):
        enterprise = request.user
        queryset = self.queryset.order_by('-time').filter(subject__enterprise=enterprise, dynamic=True)

        serializer = self.get_serializer(queryset, many=True)

        return Response({'code': 0, 'message': '请求成功', 'detail': serializer.data}, status=status.HTTP_200_OK)


# 课题附件
class AttachmentViewSet(mongodb_viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    #  上传
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        file = request.data['file']
        file_name = request.data['fileName']
        types = request.data['types']
        subject_id = request.data['subjectId']
        path = OSS().put_by_backend(path=file_name, data=file.read())
        if self.queryset.filter(subject=subject_id, types=types):
            attachment = self.queryset.get(subject=subject_id, types=types)
            attachment.attachmentPath.append({"name": file_name, "path": path})
            attachment.save()
            return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)
        else:
            self.queryset.create(types=types, subject=subject_id, attachmentPath=[{"name": file_name, "path": path}])
            return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)

    # 删除
    @action(detail=False, methods=['delete'], url_path='upload_delete')
    def upload_delete(self, request):
        types = request.data['types']
        subject_id = request.data['subjectId']
        attachment_path = request.data['attachmentPath']
        if attachment_path:
            queryset = self.queryset.get(subject=subject_id, types=types)
            for j in attachment_path:
                for i in queryset.attachmentPath:
                    if i['name'] == j['name'] and i['path'] == j['path']:
                        queryset.attachmentPath.remove(i)
                        queryset.save()
                        file_name = j['path'].split("/")[-1]
                        OSS().delete(bucket_name='file', file_name=file_name)
            return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)
        return Response({"code": 0, "message": "蹦跶"}, status=status.HTTP_200_OK)

    # 展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subject=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 是否导入
    @action(detail=False, methods=['post'], url_path='is_import')
    def is_import(self, request):
        state = request.data['state']
        subject_id = request.data['subjectId']
        if state == '导入':
            return Response({"code": 0, "message": "导入成功"}, status=status.HTTP_200_OK)
        else:
            if state == '取消':
                queryset = self.queryset.filter(subject=subject_id)
                for i in queryset:
                    for j in i.attachmentPath:
                        file_name = j['path'].split("/")[-1]
                        OSS().delete(bucket_name='file', file_name=file_name)
                Subject.objects.filter(id=subject_id).delete()
                return Response({"code": 0, "message": "取消成功"}, status=status.HTTP_200_OK)
        return Response({"code": 0, "message": "蹦跶"}, status=status.HTTP_200_OK)


# 课题基本信息
class SubjectInfoViewSet(mongodb_viewsets.ModelViewSet):
    queryset = SubjectInfo.objects.all()
    serializer_class = SubjectInfoSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 创建课题基本信息/编辑课题基本信息
    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 课题基本信息展示
    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_info(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)


class SubjectUnitInfoViewSet(mongodb_viewsets.ModelViewSet):
    queryset = SubjectUnitInfo.objects.all()
    serializer_class = SubjectUnitInfoSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            if len(queryset.jointUnitInfo) == 0:
                Subject.objects.filter(id=request.data['subjectId']).update(unitName=queryset.unitInfo[0]['unitName'])
            else:
                join_unit = [i['unitName'] for i in queryset.jointUnitInfo]
                unit_name = '、'.join(join_unit)
                Subject.objects.filter(id=request.data['subjectId']).update(
                    unitName=queryset.unitInfo[0]['unitName'] + '、' + unit_name)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            if len(queryset.jointUnitInfo) == 0:
                Subject.objects.filter(id=request.data['subjectId']).update(unitName=queryset.unitInfo[0]['unitName'])
            else:
                join_unit = [i['unitName'] for i in queryset.jointUnitInfo]
                unit_name = '、'.join(join_unit)
                Subject.objects.filter(id=request.data['subjectId']).update(
                    unitName=queryset.unitInfo[0]['unitName'] + '、' + unit_name)
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_information(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 删除联合申报单位
    @action(detail=False, methods=['delete'], url_path='delete')
    def delete(self, request, *args, **kwargs):
        credit_code_number = request.data['creditCode']
        queryset = self.queryset.get(subjectId=request.data['subjectId'])
        for unit_list in queryset.jointUnitInfo:
            for k, v in unit_list.items():
                if k == 'creditCode' and v == credit_code_number:
                    queryset.jointUnitInfo.remove(unit_list)
                    queryset.save()
                    return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)

    # 检测课题负责人是否是失信人
    @action(detail=False, methods=['post'], url_path='blacklist_query')
    def blacklist_query(self, request, *args, **kwargs):
        credit_code = request.data['creditCode']
        if UnitBlacklist.objects.filter(creditCode=credit_code, isArchives=False).exists():
            project_leader = UnitBlacklist.objects.filter(creditCode=credit_code, isArchives=False).values(
                'disciplinaryTime')
            new_time = datetime.date.today()
            for i in project_leader:
                if new_time < i['disciplinaryTime']:
                    return Response({"code": 1, "message": "该单位已被列为失信单位，无法申报项目，请更换单位"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)


# 预期成果及经济效益
class ExpectedResultsViewSet(mongodb_viewsets.ModelViewSet):
    queryset = ExpectedResults.objects.all()
    serializer_class = ExpectedResultsSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 创建预期成果及经济效益/编辑预期成果及经济效益
    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 预期成果及经济效益展示
    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_information(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)


# 经费预算
class FundingBudgetViewSet(mongodb_viewsets.ModelViewSet):
    queryset = FundingBudget.objects.all()
    serializer_class = FundingBudgetSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 预期成果及经济效益展示
    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_information(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)


# 知识产权
class IntellectualPropertyViewSet(viewsets.ModelViewSet):
    queryset = IntellectualProperty.objects.all()
    serializer_class = IntellectualPropertySerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_information(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)


class SubjectPersonnelInfoViewSet(mongodb_viewsets.ModelViewSet):
    queryset = SubjectPersonnelInfo.objects.all()
    serializer_class = SubjectPersonnelInfoSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            subject = Subject.objects.get(id=request.data['subjectId'])
            subject.idNumber = queryset.idNumber
            subject.save()
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            subject = Subject.objects.get(id=request.data['subjectId'])
            subject.idNumber = queryset.idNumber
            subject.save()
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_information(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 删除主要研究开发人员
    @action(detail=False, methods=['delete'], url_path='delete')
    def delete(self, request, *args, **kwargs):
        id_number = request.data['idNumber']
        queryset = self.queryset.get(subjectId=request.data['subjectId'])
        for development in queryset.researchDevelopmentPersonnel:
            for k, v in development.items():
                if k == 'idNumber' and v == id_number:
                    queryset.researchDevelopmentPersonnel.remove(development)
                    queryset.save()
                    return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)

    # 检测课题负责人是否是失信人
    @action(detail=False, methods=['post'], url_path='blacklist_query')
    def blacklist_query(self, request, *args, **kwargs):
        id_number = request.data['idNumber']
        if ProjectLeader.objects.filter(idNumber=id_number, isArchives=False).exists():
            project_leader = ProjectLeader.objects.filter(idNumber=id_number, isArchives=False).values(
                'disciplinaryTime')
            new_time = datetime.date.today()
            for i in project_leader:
                if new_time < i['disciplinaryTime']:
                    return Response({"code": 1, "message": "项目负责人已被列为失信人，无法申报项目，请更换项目负责人"}, status=status.HTTP_200_OK)
        if ExpertsBlacklist.objects.filter(idNumber=id_number, isArchives=False).exists():
            experts_blacklist = ExpertsBlacklist.objects.filter(idNumber=id_number, isArchives=False).values(
                'disciplinaryTime')
            new_time = datetime.date.today()
            for i in experts_blacklist:
                if new_time < i['disciplinaryTime']:
                    return Response({"code": 1, "message": "项目负责人已被列为失信人，无法申报项目，请更换项目负责人"}, status=status.HTTP_200_OK)
        if Subject.objects.filter(idNumber=id_number, stateLabel=True).exclude():
            return Response({"code": 2, "message": "该项目负责人有逾期未结题，无法申报项目，请更换负责人"}, status=status.HTTP_200_OK)
        if Subject.objects.filter(
                Q(subjectState='验收审核') | Q(subjectState='终止审核') | Q(
                    subjectState='签订合同') | Q(subjectState='项目执行'), idNumber=id_number).count() == 2:
            return Response({"code": 3, "message": "该项目负责人已有两项青秀区科技局在研项目，无法申报项目，请更换项目负责人"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)


class SubjectOtherInfoViewSet(mongodb_viewsets.ModelViewSet):
    queryset = SubjectOtherInfo.objects.all()
    serializer_class = SubjectOtherInfoSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_information(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 删除课题负责人近五年内承担各级科技计划项目
    @action(detail=False, methods=['delete'], url_path='del_other_matters')
    def del_other_matters(self, request, *args, **kwargs):
        contract_no = request.data['contractNo']
        queryset = self.queryset.get(subjectId=request.data['subjectId'])
        for other_list in queryset.otherMatters:
            for k, v in other_list.items():
                if k == 'contractNo' and v == contract_no:
                    queryset.otherMatters.remove(other_list)
                    queryset.save()
                    return Response({"code": 0, "message": "删除成功"})


class UnitCommitmentViewSet(mongodb_viewsets.ModelViewSet):
    queryset = UnitCommitment.objects.all()
    serializer_class = UnitCommitmentSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if self.queryset.filter(subjectId=request.data['subjectId']):
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(subjectId=request.data['subjectId'])
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)


class AttachmentListViewSet(mongodb_viewsets.ModelViewSet):
    queryset = AttachmentList.objects.all()
    serializer_class = AttachmentListSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = request.data['file']
        file_name = request.data['fileName']
        path = OSS().put_by_backend(path=file_name, data=file.read())
        if self.queryset.filter(subjectId=request.data['subjectId'],
                                attachmentName=request.data['attachmentName'],
                                attachmentShows=request.data['attachmentShows']):
            queryset = self.queryset.get(subjectId=request.data['subjectId'],
                                         attachmentName=request.data['attachmentName'],
                                         attachmentShows=request.data['attachmentShows'])
            queryset.attachmentContent.append({"name": file_name, "path": path})
            queryset.save()
            return Response({"code": 0, "message": "上传成功"}, status=status.HTTP_200_OK)
        else:
            self.queryset.create(subjectId=request.data['subjectId'],
                                 attachmentName=request.data['attachmentName'],
                                 attachmentShows=request.data['attachmentShows'],
                                 attachmentContent=[{"name": file_name, "path": path}],
                                 )
            return Response({"code": 0, "message": "上传成功"}, status=status.HTTP_200_OK, )

    @action(detail=False, methods=['get'], url_path='show')
    def show_subject_information(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subjectId=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 删除附件
    @action(detail=False, methods=['delete'], url_path='delete')
    def delete(self, request):
        subject_id = request.data['subjectId']
        attachment_content = request.data['attachmentContent']
        if attachment_content:
            queryset = self.queryset.get(subjectId=subject_id, attachmentName=request.data['attachmentName'],
                                         attachmentShows=request.data['attachmentShows'], )
            for j in attachment_content:
                for i in queryset.attachmentContent:
                    if i['name'] == j['name'] and i['path'] == j['path']:
                        queryset.attachmentContent.remove(i)
                        queryset.save()
                        if len(queryset.attachmentContent) == 0:
                            queryset.delete()
                        file_name = j['path'].split("/")[-1]
                        OSS().delete(bucket_name='file', file_name=file_name)
            return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)
        return Response({"code": 0, "message": "蹦跶啥"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request, *args, **kwargs):
        user = request.user
        data = {
            "attachmentName": "申报单位营业执照/统一社会信用代码证书（复印件）",
            "attachmentShows": "申报单位营业执照/统一社会信用代码证书",
            "attachmentContent": [{"name": "营业执照", "path": user.businessLicense}],
        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='storage')
    def storage(self, request, *args, **kwargs):
        data = request.data['data']
        if self.queryset.filter(subjectId=data['subjectId'], attachmentName=data['attachmentName'],
                                attachmentShows=data['attachmentShows']):
            return Response(False)
        else:
            self.queryset.create(attachmentName=data['attachmentName'], attachmentShows=data['attachmentShows'],
                                 attachmentContent=data['attachmentContent'], subjectId=data['subjectId'])
            return Response({"code": 0, "message": "保存成功"}, status=status.HTTP_200_OK)


# 单位系统
class SubjectUnitViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectUnitSerializers
    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 移动端 申报项目列表条件查询
    @action(detail=False, methods=['post'], url_path='app_query_subject')
    def app_query_subject(self, request):
        enterprise = request.user
        queryset = self.queryset.filter(enterprise=enterprise)
        subject_name = request.data['subjectName']
        if subject_name:
            queryset = queryset.filter(subjectName__contains=subject_name)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请填写项目名称"}, status=status.HTTP_200_OK)

    """
    申报单位系统
    """

    # 首页 草拟电子合同
    @action(detail=False, methods=['get'], url_path='home_page')
    def home_page(self, request):
        enterprise = request.user
        contract_fill = self.queryset.filter(Q(contract_subject__state='待提交') | Q(contract_subject__state='未通过'),
                                             enterprise=enterprise, subjectState='签订合同').count()
        contract_upload = self.queryset.filter(contract_subject__contractState='待上传', enterprise=enterprise,
                                               subjectState='签订合同').count()
        report_fill = self.queryset.filter(progress_report_subject__state='待提交', enterprise=enterprise).count()
        data = {
            "contractFill": contract_fill,
            "contractUpload": contract_upload,
            "reportFill": report_fill
        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 首页2
    # 快捷通道
    @action(detail=False, methods=['get'], url_path='fast_passage')
    def fast_passage(self, request):
        enterprise = request.user
        contract_fill = self.queryset.filter(Q(contract_subject__state='待提交') | Q(contract_subject__state='未通过'),
                                             enterprise=enterprise, subjectState='签订合同').count()
        # 上传合同
        contract_upload = self.queryset.filter(contract_subject__contractState='待上传', enterprise=enterprise,
                                               subjectState='签订合同').count()
        report_fill = self.queryset.filter(progress_report_subject__state='待提交', enterprise=enterprise).count()
        # 项目变更
        change_count = self.queryset.filter(enterprise=enterprise, subjectState="项目执行").count()
        # 验收
        acceptance_count = len([i for i in self.queryset.filter(Q(subjectState='项目执行') | Q(subjectState='结题复核'),
                                                                enterprise=enterprise)
                                if SubjectConcluding.objects.filter(subject=i, concludingState='结题复核').count() == 1
                                and SubjectConcluding.objects.filter(subject=i).count() == 1
                                or SubjectConcluding.objects.filter(subject=i).count() == 0])
        # 终止
        termination_count = len([i for i in self.queryset.exclude(terminationState='分管员发起').filter(
            Q(subjectState='项目执行') | Q(subjectState='逾期未结题') | Q(subjectState='结题复核'), enterprise=enterprise)
                                 if SubjectTermination.objects.filter(
                subject=i).count() == 0 or SubjectTermination.objects.exclude(
                Q(terminationState='终止不通过') | Q(terminationState='项目终止')).filter(subject=i).count() == 0])
        data = {
            "contractFill": contract_fill,
            "contractUpload": contract_upload,
            "reportFill": report_fill,
            "changeCount": change_count,
            "acceptanceCount": acceptance_count,
            "terminationCount": termination_count,
        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 快捷通道 申报项目
    @action(detail=False, methods=['get'], url_path='declare_project')
    def declare_project(self, request):
        enterprise = request.user
        lists = []
        subject = Subject.objects.exclude(subjectState='待提交').filter(enterprise=enterprise)
        annual_plan = list(set([i.project.category.batch.annualPlan for i in subject]))
        for k in annual_plan:
            subject_count = subject.filter(project__category__batch__annualPlan=k).count()
            data = {
                "annualPlan": k,
                "subjectCount": subject_count,
            }
            lists.append(data)
        lists.sort(key=lambda an: an['annualPlan'])
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 申报项目列表展示
    @action(detail=False, methods=['get'], url_path='show_subject')
    def show_subject(self, request):
        limit = request.query_params.dict().get('limit', None)
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan', '-updated').filter(
            enterprise=enterprise)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "请求成功", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_201_CREATED)

    # 申报项目列表条件查询
    @action(detail=False, methods=['post'], url_path='query_subject')
    def query_subject(self, request):
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan', '-updated').filter(
            enterprise=enterprise)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            # "subjectState": "subjectState",
            "charge": "project__charge__name__contains"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        if request.data['charge'] != '全部':
            queryset = queryset.exclude(subjectState='待提交')
        if request.data['subjectState'] != '全部' and request.data['subjectState'] == '立项调研':
            queryset = queryset.filter(subjectState__in=['立项调研', '项目下达'])
        if request.data['subjectState'] != '全部' and request.data['subjectState'] != '立项调研':
            queryset = queryset.filter(subjectState=request.data['subjectState'])
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 合同书列表
    @action(detail=False, methods=['get'], url_path='contract_list')
    def contract_list(self, request):
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan',
                                          '-contract_subject__contractNo').filter(enterprise=enterprise,
                                                                                  subjectState='签订合同',
                                                                                  contract_subject__contractState='-')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 合同书列表条件查询
    @action(detail=False, methods=['post'], url_path='contract_list_query')
    def contract_list_query(self, request):
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan',
                                          '-contract_subject__contractNo').filter(enterprise=enterprise,
                                                                                  subjectState='签订合同',
                                                                                  contract_subject__contractState='-')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "head": "head____contains",
            "contractState": "contract_subject__state",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 合同书附件列表
    @action(detail=False, methods=['get'], url_path='contract_file_show')
    def contract_file_show(self, request):
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan',
                                          '-contract_subject__contractNo').exclude(
            contract_subject__contractState='-').filter(enterprise=enterprise,
                                                        subjectState='签订合同')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 合同书附件列表条件查询
    @action(detail=False, methods=['post'], url_path='contract_file_query')
    def contract_file_query(self, request):
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan',
                                          '-contract_subject__contractNo').exclude(
            contract_subject__contractState='-').filter(enterprise=enterprise,
                                                        subjectState='签订合同')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "head": "head__contains",
            "contractState": "contract_subject__contractState",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 合同书展示
    @action(detail=False, methods=['get'], url_path='contract_show')
    def contract_show(self, request):
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan',
                                          '-contract_subject__contractNo').filter(enterprise=enterprise,
                                                                                  contract_subject__contractState='通过')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 合同书查询条件查询
    @action(detail=False, methods=['post'], url_path='contract_show_query')
    def contract_show_query(self, request):
        enterprise = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan',
                                          '-contract_subject__contractNo').filter(enterprise=enterprise,
                                                                                  contract_subject__contractState='通过')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 查看合同附件
    @action(detail=False, methods=['get'], url_path='contract_attachment_show')
    def contract_attachment_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.get(id=subject_id)
        attachment = queryset.contract_subject.values('attachment')
        return Response({"code": 0, "message": "ok", "detail": attachment}, status.HTTP_200_OK)


# 管理员系统
class SubjectAdminViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectAdminSerializers

    # 判断用户登录态
    # permission_classes = [IsAuthenticated, ]
    # authentication_classes = (JSONWebTokenAuthentication,)

    # 移动端 申报项目列表条件查询
    @action(detail=False, methods=['post'], url_path='app_admin_subject_query')
    def app_query_subject(self, request):
        queryset = self.queryset.exclude(subjectState='待提交')
        subject_name = request.data['subjectName']
        if subject_name:
            queryset = queryset.filter(subjectName__contains=subject_name)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请填写项目名称"}, status=status.HTTP_200_OK)

    """
    管理员系统
    """

    # 首页1
    @action(detail=False, methods=['get'], url_path='home_page')
    def home_page(self, request):
        # assigned = self.queryset.filter(subjectState='提交成功').count()
        contract_audit = self.queryset.filter(state='局长审核', subjectState='签订合同').count()
        funding = GrantSubject.objects.filter(state='待审核').count()
        concluding = self.queryset.filter(subjectState='验收审核', state='局长审核').count()
        termination = self.queryset.filter(Q(subjectState='终止审核') | Q(subjectState='项目执行'), state='局长审核').count()
        expert_review = Batch.objects.filter(state='待审核').count()
        data = {
            # "assigned": assigned,
            "contractAudit": contract_audit,
            "funding": funding,
            "concluding": concluding,
            "termination": termination,
            "expertReview": expert_review,
        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 首页2
    # 快捷通道
    @action(detail=False, methods=['get'], url_path='fast_passage')
    def fast_passage(self, request):
        # assigned = self.queryset.filter(subjectState='提交成功').count()
        contract_audit = self.queryset.filter(state='局长审核', subjectState='签订合同').count()
        funding = GrantSubject.objects.filter(state='待审核').count()
        concluding = self.queryset.filter(subjectState='验收审核', state='局长审核').count()
        termination = self.queryset.filter(Q(subjectState='终止审核') | Q(subjectState='项目执行'), state='局长审核').count()
        expert_out = Expert.objects.filter(state=5).count()
        expert_info = Expert.objects.filter(state=1).count()

        # 小程序
        # project_review = Batch.objects.exclude(opinionState="3").filter(isActivation='禁用', handOverState=True).count()
        project_review = Batch.objects.filter(Q(opinionState='2') | Q(state='待审核'), isActivation='禁用',
                                              handOverState=True).count()

        data = {
            "projectReview": project_review,
            # "assigned": assigned,
            "contractAudit": contract_audit,
            "funding": funding,
            "concluding": concluding,
            "termination": termination,
            "expertInfo": expert_info,
            "expertOut": expert_out,
        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 快捷通道 单位注册类型
    @action(detail=False, methods=['get'], url_path='registered_unit')
    def registered_unit(self, request):
        administrative_organ = User.objects.filter(enterprise__industry="行政机关").count()
        administrative_institutions = User.objects.filter(enterprise__industry="行政类事业单位").count()
        public_institution = User.objects.filter(enterprise__industry="公益类事业单位").count()
        enterprise = User.objects.filter(enterprise__industry="企业").count()
        social_groups = User.objects.filter(enterprise__industry="社会团体").count()
        other_units = User.objects.filter(enterprise__industry="其他单位").count()

        # other_units = User.objects.filter(Q(enterprise__industry="其他单位") | Q(type="企业", enterprise_id=None)).count()

        data = {
            "administrativeOrgan": administrative_organ,
            "administrativeInstitutions": administrative_institutions,
            "publicInstitution": public_institution,
            "enterprise": enterprise,
            "socialGroups": social_groups,
            "otherUnits": other_units,

        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 快捷通道 申报项目
    @action(detail=False, methods=['get'], url_path='declare_project')
    def declare_project(self, request):
        annual_plan = request.query_params.dict().get("annualPlan")
        project_batch = request.query_params.dict().get("projectBatch")
        lists = []
        subject = Subject.objects.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(
                subjectState='立项复核') | Q(subjectState='立项复核未通过')).filter(
            project__category__batch__annualPlan=annual_plan, project__category__batch__projectBatch=project_batch)
        category_obj = Category.objects.filter(batch__annualPlan=annual_plan, batch__projectBatch=project_batch)
        for j in category_obj:
            subject_count = subject.filter(project__category=j).count()
            data = {
                "planCategory": j.planCategory,
                'subjectCount': subject_count}
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 快捷通道 签订合同
    @action(detail=False, methods=['get'], url_path='sign_contract')
    def sign_contract(self, request):
        annual_plan = request.query_params.dict().get("annualPlan")
        project_batch = request.query_params.dict().get("projectBatch")
        lists = []
        subject = Subject.objects.filter(project__category__batch__annualPlan=annual_plan,
                                         project__category__batch__projectBatch=project_batch, signedState=True)
        category_obj = Category.objects.filter(batch__annualPlan=annual_plan, batch__projectBatch=project_batch)
        for j in category_obj:
            subject_count = subject.filter(project__category=j).count()
            data = {
                "planCategory": j.planCategory,
                'subjectCount': subject_count}
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 小程序
    @action(detail=False, methods=['post'], url_path='multi_select_subject')
    def multi_select_subject(self, request):
        lists = []
        # 立项评审
        project_review = ['提交成功', '形式审查', '形式审查未通过', '立项复核', '立项复核通过', '立项复核未通过', '专家评审', '立项调研', '项目下达']
        # 签订合同
        sign_contract = ['签订合同']
        # 项目执行
        project_perform = ['项目执行']
        # 验收评审
        acceptance_review = ['验收审核', '验收通过', '验收不通过', '结题复核']
        # 终止评审
        termination_review = ['终止审核', '项目终止']
        # 逾期未结题
        timeout = ['逾期未结题']
        # 项目退回
        project_return = ['项目退回']

        project_status = request.data['projectStatus']
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            'name': 'project__charge__name__in',
            "subjectName": 'subjectName__contains'
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and len(json_data[k]) != 0 and json_data[k] != ''}
        for i in project_status:
            if i == '立项评审':
                lists += project_review
            if i == '签订合同':
                lists += sign_contract
            if i == "项目执行":
                lists += project_perform
            if i == "验收评审":
                lists += acceptance_review
            if i == "终止评审":
                lists += termination_review
            if i == "逾期未结题":
                lists += timeout
            if i == "项目退回":
                lists += project_return
        if len(lists) == 0:
            queryset = self.queryset.exclude(subjectState='待提交').filter(**data)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_201_CREATED)
        else:
            queryset = self.queryset.exclude(subjectState='待提交').filter(**data, subjectState__in=lists)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_201_CREATED)

    # 项目查询 项目查询展示/管理员
    @action(detail=False, methods=['get'], url_path='admin_subject_show')
    def administrator_subject(self, request):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-project__category__batch__annualPlan', '-declareTime').exclude(
            subjectState='待提交')
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "保存成功", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_201_CREATED)

    # 项目查询 项目查询条件查询 /管理员
    @action(detail=False, methods=['post'], url_path='admin_subject_query')
    def administrator_subject_conditions(self, request):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.exclude(subjectState='待提交')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "subjectState": "subjectState",
            'charge': 'project__charge__name__contains',
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != '' and json_data[k] != '未指派'}
        if request.data['charge'] == '未指派':
            queryset = queryset.order_by('-project__category__batch__annualPlan', '-declareTime').filter(**data,
                                                                                                         subjectState='提交成功')
            page = self.paginate_queryset(queryset)
            if page is not None and limit is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({"code": 0, "message": "保存成功", "detail": serializer.data})
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        queryset = queryset.order_by('-project__category__batch__annualPlan', '-declareTime').filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "保存成功", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目查询 指派分管员/管理员
    @action(detail=False, methods=['post'], url_path='assigned')
    def assigned_charge_user(self, request):
        user_id = request.data['userId']
        subject_id = request.data['subjectId']
        for j in user_id:
            charge_user = User.objects.get(id=j)
            for i in subject_id:
                queryset = self.queryset.get(id=i)
                if queryset.charge.count() != 0:
                    queryset.charge.add(charge_user)
                    queryset.save()
                else:
                    queryset.subjectState = '形式审查'
                    queryset.charge.add(charge_user)
                    queryset.save()
                    Process.objects.create(state='形式审查', subject=queryset)
        return Response({'code': 0, 'message': '指派成功 '}, status=status.HTTP_200_OK)

    # 项目查询 调整指派分管员/管理员
    @action(detail=False, methods=['post'], url_path='adjust_assigned')
    def adjust_assigned(self, request):
        user_id = request.data['userId']
        subject_id = request.data['subjectId']
        user_id2 = request.data['userId2']
        if len(subject_id) != 1:
            for i in subject_id:
                queryset = self.queryset.get(id=i)
                for y in user_id:
                    queryset.charge.remove(y)
            for j in user_id2:
                charge_user = User.objects.get(id=j)
                for x in subject_id:
                    queryset = self.queryset.get(id=x)
                    if queryset.subjectState == '提交成功':
                        queryset.subjectState = '形式审查'
                        queryset.save()
                    queryset.charge.add(charge_user)
                    queryset.save()
        else:
            for i in user_id:
                queryset = self.queryset.get(id=subject_id[0])
                queryset.charge.remove(i)
            for j in user_id2:
                charge_user = User.objects.get(id=j)
                queryset = self.queryset.get(id=subject_id[0])
                if queryset.subjectState == '提交成功':
                    queryset.subjectState = '形式审查'
                    queryset.save()
                queryset.charge.add(charge_user)
                queryset.save()
        return Response({'code': 0, 'message': '指派成功 '}, status=status.HTTP_200_OK)

    # 项目管理 立项评审列表展示/ 管理员1
    @action(detail=False, methods=['get'], url_path='admin_review_subject_show')
    def admin_review_subject_show(self, request):
        lists = []
        batch = Batch.objects.filter(isActivation='禁用', handOverState=False)
        for i in batch:
            if self.queryset.exclude(subjectState='待提交').filter(
                    Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(subjectState='立项复核'),
                    project__category__batch=i).exists():
                data = {
                    "annualPlan": i.annualPlan,
                    "projectBatch": i.projectBatch,
                    "reviewState": '未完成',

                }
                lists.append(data)

            else:
                if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
                        subjectState='立项复核通过', project__category__batch=i).count() == 0:
                    pass
                else:
                    data = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '已完成',
                        "subjectCount": self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
                            subjectState='立项复核通过', project__category__batch=i).count(),
                    }
                    lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)

    # 项目管理 立项评审列表条件查询/ 管理员1
    @action(detail=False, methods=['post'], url_path='admin_review_subject_query')
    def admin_review_subject_query(self, request):
        lists = []
        json_data = request.data
        keys = {
            "annualPlan": "annualPlan",
            "projectBatch": "projectBatch",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        batch = Batch.objects.filter(**data, isActivation='禁用', handOverState=False)
        if request.data['reviewState'] == '全部':
            for i in batch:
                if self.queryset.exclude(subjectState='待提交').filter(
                        Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(subjectState='立项复核'),
                        project__category__batch=i).exists():
                    data_set = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '未完成'
                    }
                    lists.append(data_set)
                else:
                    if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
                            subjectState='立项复核通过', project__category__batch=i).count() == 0:
                        pass
                    else:
                        data_set = {
                            "annualPlan": i.annualPlan,
                            "projectBatch": i.projectBatch,
                            "reviewState": '已完成'
                        }
                        lists.append(data_set)
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)
        elif request.data['reviewState'] == '未完成':
            for i in batch:
                if self.queryset.exclude(subjectState='待提交').filter(
                        Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(subjectState='立项复核'),
                        project__category__batch=i).exists():
                    data_set = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '未完成'
                    }
                    lists.append(data_set)
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)
        elif request.data['reviewState'] == '已完成':
            for i in batch:
                if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
                        subjectState='立项复核通过', project__category__batch=i).count() == 0:
                    pass
                else:
                    if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
                            Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(subjectState='立项复核'),
                            project__category__batch=i).count() == 0:
                        data_set = {
                            "annualPlan": i.annualPlan,
                            "projectBatch": i.projectBatch,
                            "reviewState": '已完成'
                        }
                        lists.append(data_set)
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)

    # 立项评审移交评估机构/管理员1
    @action(detail=False, methods=['post'], url_path='project_review')
    def project_review(self, request):
        # 年度计划  # 项目批次
        annual_plan = request.data['annualPlan']
        project_batch = request.data['projectBatch']
        agencies = request.data['userId']
        agencies_user = User.objects.get(id=agencies)
        batch = Batch.objects.get(annualPlan=annual_plan, projectBatch=project_batch)
        # 项目批次 实例
        if self.queryset.exclude(subjectState='待提交').filter(
                Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(subjectState='立项复核'),
                project__category__batch=batch).exists():
            return Response({'code': 1, 'message': '该批次下有未完成立项复核的项目，请完成立项复核后再移交评审'}, status=status.HTTP_200_OK)
        else:
            # 项目类别
            batch.agency_id = agencies_user
            batch.save()
            subject = self.queryset.exclude(
                Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='项目退回')).filter(
                subjectState='立项复核通过', project__category__batch=batch)
            for sub in subject:
                sub.subjectState = '专家评审'
                sub.state = "待指派"
                sub.agencies.add(agencies_user)
                sub.save()
                Process.objects.create(state='专家评审', subject=sub)
            batch.handOverState = True
            batch.save()
            return Response({'code': 0, 'message': '移交成功', 'detail': {"subjectCount": subject.count()}},
                            status=status.HTTP_200_OK)

    # 项目管理 立项评审列表展示/ 管理员2
    @action(detail=False, methods=['get'], url_path='review_subject_show')
    def review_subject_show(self, request):
        lists = []
        batch = Batch.objects.exclude(opinionState="3").filter(isActivation='禁用').order_by("-annualPlan", "-created")
        for i in batch:
            if self.queryset.exclude(subjectState='待提交').filter(
                    Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(subjectState='立项复核'),
                    project__category__batch=i).exists():
                data = {
                    "annualPlan": i.annualPlan,
                    "projectBatch": i.projectBatch,
                    "reviewState": '未完成',
                    "handOverState": "-",
                    "state": "-",
                    "opinionState": "-",
                    "agency":'-'
                }
                lists.append(data)
            else:
                if self.queryset.exclude(Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
                        Q(subjectState='立项复核通过') | Q(subjectState='专家评审'), project__category__batch=i).count() == 0:
                    pass
                else:

                    data = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '已完成',
                        "handOverState": i.handOverState,
                        "state": i.state,
                        "opinionState": i.get_opinionState_display(),
                        "agency": i.agency.name if i.handOverState is True else '-',
                        "subjectCount": self.queryset.exclude(
                            Q(subjectState='待提交') | Q(subjectState='形式审查未通过')).filter(
                            subjectState='立项复核通过', project__category__batch=i).count(),
                    }
                    lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)

    # 立项评审移交评估机构/管理员2
    @action(detail=False, methods=['post'], url_path='hand_over_batch')
    def hand_over_batch(self, request):
        # 年度计划  # 项目批次
        annual_plan = request.data['annualPlan']
        project_batch = request.data['projectBatch']
        agencies = request.data['userId']
        agencies_user = User.objects.get(id=agencies)
        batch = Batch.objects.get(annualPlan=annual_plan, projectBatch=project_batch)
        # 项目批次 实例
        if self.queryset.exclude(subjectState='待提交').filter(
                Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(subjectState='立项复核'),
                project__category__batch=batch).exists():
            return Response({'code': 1, 'message': '该批次下有未完成立项复核的项目，请完成立项复核后再移交评审'}, status=status.HTTP_200_OK)
        else:
            # 项目类别
            batch.agency_id = agencies_user
            batch.save()
            subject = self.queryset.exclude(
                Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='项目退回')).filter(
                subjectState='立项复核通过', project__category__batch=batch)
            for sub in subject:
                sub.subjectState = '专家评审'
                sub.state = "待指派"
                sub.agencies.add(agencies_user)
                sub.save()
                Process.objects.create(state='专家评审', subject=sub)
            batch.handOverState = True
            batch.state = "待提交"
            batch.save()
            return Response({'code': 0, 'message': '移交成功', 'detail': {"subjectCount": subject.count()}},
                            status=status.HTTP_200_OK)

    # 评审专家审核展示/ 管理员
    @action(detail=False, methods=['get'], url_path='expert_review_show')
    def expert_review_show(self, request):
        lists = []
        batch = Batch.objects.order_by('-submitTime').filter(state='待审核')
        for i in batch:
            data = {
                "annualPlan": i.annualPlan,
                "projectBatch": i.projectBatch,
                "name": i.agency.name,
                "submitTime": i.submitTime
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 评审专家审核查询 / 管理员
    @action(detail=False, methods=['post'], url_path='expert_review_query')
    def expert_review_query(self, request):
        lists = []
        batch = Batch.objects.filter(state='待审核')
        json_data = request.data
        keys = {
            "annualPlan": "annualPlan",
            "projectBatch": "projectBatch",
            "name": "agency__name"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        for i in batch.order_by('-submitTime').filter(**data):
            data = {
                "annualPlan": i.annualPlan,
                "projectBatch": i.projectBatch,
                "name": i.agency.name,
                "submitTime": i.submitTime
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 评审专家审核按组指派展示
    @action(detail=False, methods=['get'], url_path='expert_review_group_show')
    def expert_review_group_show(self, request):
        lists = []
        annual_plan = request.query_params.dict().get('annualPlan')
        project_batch = request.query_params.dict().get('projectBatch')
        agencies_subject = self.queryset.filter(project__category__batch__annualPlan=annual_plan,
                                                project__category__batch__projectBatch=project_batch,
                                                project__category__batch__state='待审核',
                                                assignWay='按组指派')
        project_team_logo = set([i['projectTeamLogo'] for i in agencies_subject.values('projectTeamLogo')])
        for j in project_team_logo:
            subject_obj_num = agencies_subject.filter(projectTeamLogo=j)
            for subject in subject_obj_num:
                data = {
                    "projectTeamLogo": j,
                    "projectTeam": subject.projectTeam,
                    "reviewWay": subject.reviewWay,
                    "subjectNumber": subject_obj_num.count(),
                    "expertsNumber": SubjectExpertsOpinionSheet.objects.filter(
                        subject=subject).count()
                }
                lists.append(data)
                break
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 评审专家审核按组指派查询
    @action(detail=False, methods=['post'], url_path='expert_review_group_query')
    def expert_review_group_query(self, request):
        lists = []
        json_data = request.data
        keys = {
            "projectTeam": "projectTeam__contains",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        agencies_subject = self.queryset.filter(project__category__batch__annualPlan=request.data['annualPlan'],
                                                project__category__batch__projectBatch=request.data['projectBatch'],
                                                project__category__batch__state='待审核',
                                                assignWay='按组指派')
        subject_obj = agencies_subject.filter(**data)
        project_team_logo = set([i['projectTeamLogo'] for i in subject_obj.values('projectTeamLogo')])
        for j in project_team_logo:
            subject_obj_num = subject_obj.filter(projectTeamLogo=j)
            for subject in subject_obj_num:
                data = {
                    "projectTeamLogo": j,
                    "projectTeam": subject.projectTeam,
                    "reviewWay": subject.reviewWay,
                    "subjectNumber": subject_obj_num.count(),
                    "expertsNumber": SubjectExpertsOpinionSheet.objects.filter(
                        subject=subject).count()
                }
                lists.append(data)
                break
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 评审专家审核按组指派详情展示
    @action(detail=False, methods=['get'], url_path='expert_review_group_details_show')
    def expert_review_group_details_show(self, request):
        lists = []
        annual_plan = request.query_params.dict().get('annualPlan')
        project_team = request.query_params.dict().get('projectTeam')
        project_team_logo = request.query_params.dict().get('projectTeamLogo')
        agencies_subject = self.queryset.filter(project__category__batch__annualPlan=annual_plan,
                                                projectTeam=project_team,
                                                projectTeamLogo=project_team_logo,
                                                assignWay='按组指派')
        for subject in agencies_subject:
            data = {
                "annualPlan": subject.project.category.batch.annualPlan,
                "subjectName": subject.subjectName,
                "unitName": subject.unitName,
                "head": subject.head
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 评审专家审核按组指派详情chauxn
    @action(detail=False, methods=['post'], url_path='expert_review_group_details_query')
    def expert_review_group_details_query(self, request):
        lists = []
        project_team_logo = request.data['projectTeamLogo']
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        agencies_subject = self.queryset.filter(projectTeamLogo=project_team_logo, assignWay='按组指派')
        queryset = agencies_subject.filter(**data)
        for subject in queryset:
            data = {
                "annualPlan": subject.project.category.batch.annualPlan,
                "subjectName": subject.subjectName,
                "unitName": subject.unitName,
                "head": subject.head
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 评审专家审核单项指派查询
    @action(detail=False, methods=['post'], url_path='expert_review_single_query')
    def expert_review_single_query(self, request):
        limit = request.query_params.dict().get('limit', None)
        agencies_subject = self.queryset.filter(project__category__batch__annualPlan=request.data['annualPlan'],
                                                project__category__batch__projectBatch=request.data['projectBatch'],
                                                project__category__batch__state='待审核',
                                                assignWay='单项指派')
        json_data = request.data
        keys = {
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "reviewWay": "reviewWay",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 评审专家审核1
    @action(detail=False, methods=['post'], url_path='expert_review')
    def expert_review(self, request):
        if request.data['state'] == '同意':
            Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                 projectBatch=request.data['projectBatch']).update(state='同意')
        else:
            Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                 projectBatch=request.data['projectBatch']).update(state='不同意',
                                                                                   returnReason=request.data[
                                                                                       'returnReason'])
        return Response({'code': 0, 'message': '操作成功'}, status=status.HTTP_200_OK)

    # 评审专家审核2
    @action(detail=False, methods=['post'], url_path='expert_audit')
    def expert_audit(self, request):
        if request.data['state'] == '同意':
            Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                 projectBatch=request.data['projectBatch']).update(state='同意', opinionState="1")
            for i in Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                          projectBatch=request.data['projectBatch']):
                for subject in Subject.objects.filter(subjectState='专家评审', project__category__batch=i):
                    send_template(name='管理员评审专家审核-同意', subject_id=subject.id)
        else:
            Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                 projectBatch=request.data['projectBatch']).update(state='不同意',
                                                                                   returnReason=request.data[
                                                                                       'returnReason'])
        return Response({'code': 0, 'message': '操作成功'}, status=status.HTTP_200_OK)

    # 评审专家审核 按组指派 展示 查询2
    @action(detail=False, methods=['post'], url_path='expert_audit_group_to_view')
    def expert_audit_group_to_view(self, request):
        dicts = {}
        lists = []
        annual_plan = request.data['annualPlan']
        project_batch = request.data['projectBatch']
        json_data = request.data
        keys = {
            "projectTeam": "projectTeam__contains",
            "subjectName": "subjectName__contains",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        agencies_subject = self.queryset.filter(project__category__batch__annualPlan=annual_plan,
                                                project__category__batch__projectBatch=project_batch,
                                                assignWay='按组指派').filter(**data)
        for i in agencies_subject:
            dicts[i.projectTeamLogo] = i.projectTeam
        for k, v in dicts.items():
            data = {"projectTeam": v}
            expert_list = []
            subject_list = []
            for x in SubjectExpertsOpinionSheet.objects.filter(
                    subject=agencies_subject.filter(projectTeamLogo=k).first()):
                expert_list.append({"name": x.pExperts.expert.name,
                                    "title": x.pExperts.expert.title.name,
                                    "company": x.pExperts.expert.company
                                    })
            for j in agencies_subject.filter(projectTeamLogo=k):
                subject_list.append({
                    "id": j.id,
                    "subjectName": j.subjectName,
                    "planCategory": j.project.category.planCategory,
                    "reviewWay": j.reviewWay,
                })
            data["expertList"] = expert_list
            data["subjectList"] = subject_list
            lists.append(data)

        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 评审专家审核 单项指派 展示 查询2
    @action(detail=False, methods=['post'], url_path='expert_audit_single_to_view')
    def expert_audit_single_to_view(self, request):
        lists = []
        agencies_subject = self.queryset.filter(project__category__batch__annualPlan=request.data['annualPlan'],
                                                project__category__batch__projectBatch=request.data['projectBatch'],
                                                project__category__batch__state='待审核',
                                                assignWay='单项指派')
        json_data = request.data
        keys = {
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "reviewWay": "reviewWay",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        for i in queryset:
            expert_list = []
            for x in SubjectExpertsOpinionSheet.objects.filter(subject=i):
                expert_list.append({"name": x.pExperts.expert.name,
                                    "title": x.pExperts.expert.title.name,
                                    "company": x.pExperts.expert.company
                                    })
            data = {
                "planCategory": i.project.category.planCategory,
                "subjectName": i.subjectName,
                "reviewWay": i.reviewWay,
                "expertList": expert_list,
            }
            lists.append(data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 评审意见审核2
    # OPINION = (('0', '-'), ('1', '待提交'), ('2', '待审核'), ('3', '通过'), ('4', '不通过'))
    @action(detail=False, methods=['post'], url_path='opinion_audit')
    def opinion_audit(self, request):
        if request.data['state'] == '同意':
            Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                 projectBatch=request.data['projectBatch']).update(opinionState='3')
            # Subject.objects.filter(project__category__batch__annualPlan=request.data['annualPlan'],
            #                        project__category__batch__projectBatch=request.data['projectBatch']).update(
            #     subjectState="立项调研", handOverState=True)
            for i in Subject.objects.filter(project__category__batch__annualPlan=request.data['annualPlan'],
                                            project__category__batch__projectBatch=request.data['projectBatch'],
                                            subjectState="专家评审"):
                i.handOverState = True
                i.subjectState = '立项调研'
                i.save()
                Process.objects.create(state='立项调研', subject=i)
        else:
            Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                 projectBatch=request.data['projectBatch']).update(opinionState='4',
                                                                                   returnReason=request.data[
                                                                                       'returnReason'])
        return Response({'code': 0, 'message': '操作成功'}, status=status.HTTP_200_OK)

    # 评审意见审核 展示 查看
    @action(detail=False, methods=['post'], url_path='opinion_audit_to_view')
    def opinion_audit_to_view(self, request):
        limit = request.query_params.dict().get('limit', None)
        agencies_subject = self.queryset.filter(project__category__batch__annualPlan=request.data['annualPlan'],
                                                project__category__batch__projectBatch=request.data['projectBatch'],
                                                subjectState='专家评审')
        # agencies_subject = self.queryset.exclude(subjectState='待提交').filter(project__category__batch__annualPlan=request.data['annualPlan'],
        #                                         project__category__batch__projectBatch=request.data['projectBatch'],
        #                                         )
        json_data = request.data
        keys = {
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目管理 评审汇总表按组指派展示/ 管理员
    @action(detail=False, methods=['get'], url_path='admin_review_summary')
    def admin_review_summary(self, request):
        lists = []
        agencies_subject = self.queryset.filter(assignWay='按组指派', handOverState=True)
        project_team_logo = list(set([i['projectTeamLogo'] for i in agencies_subject.values('projectTeamLogo')]))
        for j in project_team_logo:
            for i in agencies_subject.filter(projectTeamLogo=j):
                date = {

                    'annualPlan': i.project.category.batch.annualPlan,
                    'projectBatch': i.project.category.batch.projectBatch,
                    'projectTeam': i.projectTeam,
                    'projectTeamLogo': j,
                    'reviewWay': i.reviewWay,
                    'subjectNumber': agencies_subject.filter(projectTeamLogo=j).count(),
                    'expertsNumber': SubjectExpertsOpinionSheet.objects.filter(subject=i).count(),
                }
                lists.append(date)
                break
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 项目管理 评审汇总表按组指派条件查询/ 管理员
    @action(detail=False, methods=['post'], url_path='admin_review_summary_query')
    def admin_review_summary_query(self, request):
        dicts = {}
        lists = []
        institutions_user_subject = self.queryset.filter(assignWay='按组指派', handOverState=True)
        json_data = request.data
        keys = {"annualPlan": "project__category__batch__annualPlan",
                "projectBatch": "project__category__batch__projectBatch",
                "projectTeam": "projectTeam__contains", }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = institutions_user_subject.filter(**data)
        project_team_logo = list(set([i['projectTeamLogo'] for i in queryset.values('projectTeamLogo')]))
        for j in project_team_logo:
            for i in queryset.filter(projectTeamLogo=j):
                date = {

                    'annualPlan': i.project.category.batch.annualPlan,
                    'projectBatch': i.project.category.batch.projectBatch,
                    'projectTeam': i.projectTeam,
                    'projectTeamLogo': j,
                    'reviewWay': i.reviewWay,
                    'subjectNumber': queryset.filter(projectTeamLogo=j).count(),
                    'expertsNumber': SubjectExpertsOpinionSheet.objects.filter(subject=i).count(),
                }
                lists.append(date)
                break
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 项目管理 评审汇总表按组指派详情展示/管理员
    @action(detail=False, methods=['post'], url_path='admin_group_assigned_obj')
    def admin_group_assigned_obj(self, request):
        institutions_user_subject = self.queryset.filter(assignWay='按组指派', handOverState=True)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "projectTeam": "projectTeam",
            "projectTeamLogo": "projectTeamLogo",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = institutions_user_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审管理项目组指派详情展示条件查询/管理员
    @action(detail=False, methods=['post'], url_path='admin_group_assigned_obj_query')
    def admin_group_assigned_obj_query(self, request):
        institutions_user_subject = self.queryset.filter(assignWay='按组指派', handOverState=True)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "projectTeam": "projectTeam",
            "projectTeamLogo": "projectTeamLogo",

            "planCategory": "project__category__planCategory",
            "proposal": "opinion_sheet_subject__proposal",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "agency": "project__category__batch__agency__name"

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = institutions_user_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目管理 评审汇总表单项指派详情展示/管理员
    @action(detail=False, methods=['get'], url_path='admin_single_assigned_obj')
    def admin_single_assigned_obj(self, request):
        institutions_user_subject = self.queryset.filter(assignWay='单项指派', handOverState=True)
        serializers = self.get_serializer(institutions_user_subject, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目管理 评审汇总表单项指派详情查询/管理员
    @action(detail=False, methods=['post'], url_path='admin_single_assigned_obj_query')
    def admin_single_assigned_obj_query(self, request):
        institutions_user_subject = self.queryset.filter(assignWay='单项指派', handOverState=True)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "agency": "project__category__batch__agency__name"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = institutions_user_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 立项审批展示 立项建议 管理员
    @action(detail=False, methods=['get'], url_path='admin_show_subject')
    def admin_show_subject(self, request):
        lists = []
        queryset = self.queryset.order_by("-project__category__batch__annualPlan",
                                          "-project__category__batch__created").exclude(
            subjectState='待提交').filter(advice=True)
        for i in queryset:
            unit = SubjectUnitInfo.objects.get(subjectId=i.id)
            subject_info = SubjectInfo.objects.get(subjectId=i.id)
            units = []
            joint_unit = []
            data = {
                "annualPlan": i.project.category.batch.annualPlan,
                "projectBatch": i.project.category.batch.projectBatch,
                "planCategory": i.project.category.planCategory,
                "projectName": i.project.projectName,
                "subjectName": i.subjectName,
                "head": i.head,
                "mobile": i.mobile,
                "charge": i.proposal.charge.name,
                "scienceFunding": i.proposal.scienceFunding,
                "scienceProposal": i.proposal.scienceProposal,
                "firstFunding": i.proposal.firstFunding,
                "assessmentIndicators": subject_info.assessmentIndicators,
            }
            if len(unit.jointUnitInfo) == 0:
                units.append({"unitName": unit.unitInfo[0]['unitName'], "scienceProposal": i.proposal.scienceFunding,
                              "firstFunding": i.proposal.firstFunding})
                data['unitName'] = units
                lists.append(data)
            else:
                if unit.unitInfo[0]['industry'] == "企业":
                    units.append({"unitName": unit.unitInfo[0]['unitName'],
                                  "scienceProposal": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                     i.proposal.scienceFunding,
                                  "firstFunding": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                  i.proposal.scienceFunding * Decimal('0.6')})
                else:
                    units.append({"unitName": unit.unitInfo[0]['unitName'],
                                  "scienceProposal": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                     i.proposal.scienceFunding,
                                  "firstFunding": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                  i.proposal.scienceFunding})
                for j in unit.jointUnitInfo:
                    if j['industry'] == "企业":
                        joint_unit.append({"unitName": j['unitName'],
                                           "scienceProposal": Decimal(j['fundsAccounted']) / 100 *
                                                              i.proposal.scienceFunding,
                                           "firstFunding": Decimal(j['fundsAccounted']) / 100 *
                                                           i.proposal.scienceFunding * Decimal('0.6')})
                    else:
                        joint_unit.append({"unitName": j['unitName'],
                                           "scienceProposal": Decimal(j['fundsAccounted']) / 100 *
                                                              i.proposal.scienceFunding,
                                           "firstFunding": Decimal(j['fundsAccounted']) / 100 *
                                                           i.proposal.scienceFunding})
                data['unitName'] = units + joint_unit
                lists.append(data)
        return Response({"code": 0, "message": "保存成功", "detail": lists}, status=status.HTTP_200_OK)

    # 立项审批条件查询 立项建议 管理员
    @action(detail=False, methods=['post'], url_path='admin_conditions')
    def admin_conditions(self, request):
        lists = []
        queryset = self.queryset.order_by("-project__category__batch__annualPlan", "-proposal__updated").exclude(
            subjectState='待提交').filter(advice='t')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "proposal": "proposal__scienceProposal",
            "unitName": "unitName__contains",
            "charge": "proposal__charge__name",
            "head": "head__contains"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        for i in instance:
            unit = SubjectUnitInfo.objects.get(subjectId=i.id)
            subject_info = SubjectInfo.objects.get(subjectId=i.id)
            funding_budget = FundingBudget.objects.get(subjectId=i.id)
            units = []
            joint_unit = []
            data = {
                "subjectId": i.id,
                "annualPlan": i.project.category.batch.annualPlan,
                "projectBatch": i.project.category.batch.projectBatch,
                "planCategory": i.project.category.planCategory,
                "projectName": i.project.projectName,
                "subjectName": i.subjectName,
                "head": i.head,
                "mobile": i.mobile,
                "charge": i.proposal.charge.name,
                "scienceFunding": i.proposal.scienceFunding,
                "scienceProposal": i.proposal.scienceProposal,
                "firstFunding": i.proposal.firstFunding,
                "assessmentIndicators": subject_info.assessmentIndicators,

                "overallGoal": subject_info.overallGoal,
                "startStopYear": i.startStopYear,
                "unitScienceFunding": funding_budget.scienceFunding,
                "unitSelfRaised": funding_budget.unitSelfRaised,
                "combined": i.proposal.scienceFunding + funding_budget.unitSelfRaised
            }
            if len(unit.jointUnitInfo) == 0:
                units.append({"unitName": unit.unitInfo[0]['unitName'], "scienceProposal": i.proposal.scienceFunding,
                              "firstFunding": i.proposal.firstFunding})
                data['unitName'] = units
                lists.append(data)
            else:
                if unit.unitInfo[0]['industry'] == "企业":
                    units.append({"unitName": unit.unitInfo[0]['unitName'],
                                  "scienceProposal": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                     i.proposal.scienceFunding,
                                  "firstFunding": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                  i.proposal.scienceFunding * Decimal('0.6')})
                else:
                    units.append({"unitName": unit.unitInfo[0]['unitName'],
                                  "scienceProposal": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                     i.proposal.scienceFunding,
                                  "firstFunding": Decimal(unit.unitInfo[0]['fundsAccounted']) / 100 *
                                                  i.proposal.scienceFunding})
                for j in unit.jointUnitInfo:
                    if j['industry'] == "企业":
                        joint_unit.append({"unitName": j['unitName'],
                                           "scienceProposal": Decimal(j['fundsAccounted']) / 100 *
                                                              i.proposal.scienceFunding,
                                           "firstFunding": Decimal(j['fundsAccounted']) / 100 *
                                                           i.proposal.scienceFunding * Decimal('0.6')})
                    else:
                        joint_unit.append({"unitName": j['unitName'],
                                           "scienceProposal": Decimal(j['fundsAccounted']) / 100 * i.proposal.scienceFunding,
                                           "firstFunding": Decimal(j['fundsAccounted']) / 100 * i.proposal.scienceFunding})
                data['unitName'] = units + joint_unit
                lists.append(data)
        return Response({"code": 0, "message": "保存成功", "detail": lists}, status=status.HTTP_200_OK)

    # 立项报批退回 立项建议 管理员
    @action(detail=False, methods=['post'], url_path='admin_suggest_return')
    def admin_suggest_return(self, request):
        m = 0
        subject_id_list = request.data['subjectIdList']
        for i in subject_id_list:
            subject = self.queryset.get(id=i)
            if subject.subjectState != '项目下达' or (subject.subjectState == '项目退回' and subject.state == '项目下达'):
                m += 1
            else:
                subject = self.queryset.get(id=i)
                subject.proposal = None
                subject.advice = False
                subject.subjectState = '立项调研'
                Proposal.objects.filter(id=subject.proposal_id).delete()
                subject.save()
        if m == 0:
            return Response({"code": 0, "message": "已退回"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, "message": "项目已过立项评审阶段，不支持退回"}, status=status.HTTP_200_OK)

    # 合同审批列表查询 / 管理员
    @action(detail=False, methods=['post'], url_path='g_audit_contract_list_query_wx')
    def g_audit_contract_list_query_wx(self, request):
        queryset = self.queryset.filter(subjectState='签订合同', state='局长审核')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 合同审批列表 / 管理员
    @action(detail=False, methods=['get'], url_path='g_audit_contract_list')
    def g_audit_contract_list(self, request):
        queryset = self.queryset.filter(subjectState='签订合同', state='局长审核')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 合同审批列表查询 / 管理员
    @action(detail=False, methods=['post'], url_path='g_audit_contract_list_query')
    def g_audit_contract_list_query(self, request):
        queryset = self.queryset.filter(subjectState='签订合同', state='局长审核')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "head": "head__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 审核合同书 / 管理员
    @action(detail=False, methods=['post'], url_path='g_audit_contract')
    def g_audit_contract(self, request):
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '通过':
            queryset.state = '待上传'
            queryset.contract_subject.update(state=state, contractState='待上传')
            queryset.save()
            # content = "您好，您在青秀区科技项目平台提交的科研项目电子合同已通过审核，请及时下载打印合同，前往科技局盖章。".encode('gbk')
            # SMS().send_sms(queryset.mobile, content)
            # SMS().send_sms('15022704425', content)
            Process.objects.create(subject=queryset, state='签订合同', note='电子合同审核通过，请上传合同书附件', dynamic=True)
            send_template(name='电子合同审核通过', subject_id=queryset.id)
            return Response({'code': 0, 'message': '通过'}, status.HTTP_200_OK)
        else:
            queryset.contract_subject.update(state='未通过')
            queryset.state = '待提交'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            Process.objects.create(subject=queryset, state='签订合同', note='电子合同退回补正,请完成电子合同补正并提交审批', dynamic=True)
            send_template(name='电子合同审核不通过', subject_id=queryset.id)
            return Response({'code': 1, 'message': '退回'}, status.HTTP_200_OK)

    # 验收审批查询 / 管理员
    @action(detail=False, methods=['post'], url_path='admin_acceptance_list_query_wx')
    def admin_acceptance_list_query_wx(self, request):
        queryset = self.queryset.filter(subjectState='验收审核', state='局长审核')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains",
            "results": "results__in",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 验收审批展示 / 管理员
    @action(detail=False, methods=['get'], url_path='admin_acceptance_list')
    def admin_acceptance_list(self, request):
        queryset = self.queryset.filter(subjectState='验收审核', state='局长审核')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 验收审批查询 / 管理员
    @action(detail=False, methods=['post'], url_path='admin_acceptance_list_query')
    def admin_acceptance_list_query(self, request):
        queryset = self.queryset.filter(subjectState='验收审核', state='局长审核')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "head": "head__contains",
            "results": "results",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 验收审批 /管理员
    @action(detail=False, methods=['post'], url_path='admin_acceptance')
    def admin_acceptance(self, request):
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '补正资料':
            queryset.state = '补正资料'
            queryset.concludingState = '补正资料'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
                concludingState='补正资料')
            return Response({'code': '0', "message": '管理员 - 补正资料'}, status=status.HTTP_200_OK)
        elif state == '确认验收通过':
            queryset.state = '验收通过'
            queryset.concludingState = '验收通过'
            queryset.subjectState = '验收通过'
            queryset.save()
            Process.objects.create(state='验收通过', subject=queryset)
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
                concludingState='验收通过')
            contract = Contract.objects.get(subject=queryset)
            subject_unit_info = SubjectUnitInfo.objects.get(subjectId=request.data['subjectId'])
            unit = subject_unit_info.unitInfo + subject_unit_info.jointUnitInfo
            grant_subject = GrantSubject.objects.create(subject_id=request.data['subjectId'], grantType='尾款')
            m = 0
            for i in ContractContent.objects.get(id=contract.contractContent).unitFunding:
                for j in unit:
                    if i['unitName'] == j['unitName']:
                        if i['last'] == '0.00':
                            m += 1
                        else:
                            AllocatedSingle.objects.create(subjectName=queryset.subjectName,
                                                           contractNo=contract.contractNo,
                                                           head=queryset.head, unitName=i['unitName'],
                                                           grantSubject=grant_subject.id,
                                                           money=Decimal(i['last']),
                                                           initial=Decimal(i['last']),
                                                           receivingUnit=i['unitName'],
                                                           bankAccount=j['bankAccount'],
                                                           bank=j['bank']
                                                           )
            if m == len(unit):
                GrantSubject.objects.filter(subject_id=request.data["subjectId"], grantType='尾款',
                                            id=grant_subject.id).delete()
            Process.objects.create(state='验收通过', subject=queryset, note='验收申请结果：验收通过', dynamic=True)
            return Response({"code": 0, "message": '管理员 - 验收通过'}, status=status.HTTP_200_OK)
        elif state == '确认验收不通过':
            queryset.state = '验收不通过'
            queryset.concludingState = '验收不通过'
            queryset.subjectState = '验收不通过'
            queryset.save()
            Process.objects.create(state='验收不通过', subject=queryset)
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
                concludingState='验收不通过')
            instance = SubjectPersonnelInfo.objects.get(subjectId=request.data['subjectId'])
            project_leader = ProjectLeader.objects.filter(idNumber=instance.idNumber, isArchives=False)
            if project_leader:
                project_leader = ProjectLeader.objects.get(idNumber=instance.idNumber, isArchives=False)
                disciplinary_time = project_leader.disciplinary_time
                ProjectLeader.objects.filter(idNumber=instance.idNumber, isArchives=False).update(isArchives='t')
                ProjectLeader.objects.create(name=instance.name,
                                             unitName=instance.workUnit,
                                             idNumber=instance.idNumber,
                                             mobile=queryset.mobile,
                                             degreeOf='一般失信',
                                             breachTime=datetime.date.today(),
                                             disciplinaryTime=disciplinary_time + relativedelta(years=1),
                                             returnReason='课题结题验收不通过',
                                             subjectName=queryset.subjectName,
                                             annualPlan=queryset.project.category.batch.annualPlan,
                                             declareTime=queryset.declareTime,
                                             contractNo=Contract.objects.get(subject=queryset).contractNo
                                             )
            else:
                ProjectLeader.objects.create(name=instance.name,
                                             unitName=instance.workUnit,
                                             idNumber=instance.idNumber,
                                             mobile=queryset.mobile,
                                             degreeOf='一般失信',
                                             breachTime=datetime.date.today(),
                                             disciplinaryTime=datetime.date.today() + relativedelta(years=2),
                                             returnReason='课题结题验收不通过',
                                             subjectName=queryset.subjectName,
                                             annualPlan=queryset.project.category.batch.annualPlan,
                                             declareTime=queryset.declareTime,
                                             contractNo=Contract.objects.get(subject=queryset).contractNo
                                             )
            Process.objects.create(state='验收不通过', subject=queryset, note='验收申请结果：验收不通过', dynamic=True)
            return Response({"code": 0, "message": '管理员 - 验收不通过'}, status=status.HTTP_200_OK)

        elif state == '确认结题复核':
            queryset.state = '结题复核'
            queryset.concludingState = '结题复核'
            queryset.subjectState = '结题复核'
            queryset.double = True
            queryset.save()
            Process.objects.create(state='结题复核', subject=queryset)
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
                concludingState='结题复核')
            SubjectKExperts.objects.filter(subject=queryset).update(reviewState=True)
            Process.objects.create(state='结题复核', subject=queryset, note='验收申请结果：重新复核', dynamic=True)
            return Response({"code": 0, "message": '管理员 - 验收不通过'}, status=status.HTTP_200_OK)

    # 项目终止审批  待终止审批项目列表查询/管理员
    @action(detail=False, methods=['post'], url_path='admin_management_query_wx')
    def admin_management_query_wx(self, request):
        queryset = self.queryset.filter(Q(subjectState='项目执行') | Q(subjectState='终止审核'), state='局长审核')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains",
            "results": "results__in",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止审批  待终止审批项目列表/管理员
    @action(detail=False, methods=['get'], url_path='admin_management_show')
    def admin_management_show(self, request):
        queryset = self.queryset.filter(Q(subjectState='项目执行') | Q(subjectState='终止审核'), state='局长审核')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止审批  待终止审批项目列表查询/管理员
    @action(detail=False, methods=['post'], url_path='admin_management_query')
    def admin_management_query(self, request):
        queryset = self.queryset.filter(Q(subjectState='项目执行') | Q(subjectState='终止审核'), state='局长审核')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "results": "results",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止  评审/管理员管员
    @action(detail=False, methods=['post'], url_path='admin_review_z')
    def admin_review_z(self, request):
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '补正资料':
            queryset.state = '补正资料'
            queryset.terminationState = '补正资料'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                terminationState='补正资料')
            return Response({"code": 0, "message": '管理员 - 补正资料'}, status=status.HTTP_200_OK)
        elif state == '确认终止通过':
            if queryset.terminationOriginator == '承担单位':
                queryset.state = '项目终止'
                queryset.terminationState = '项目终止'
                queryset.subjectState = '项目终止'
                queryset.stateLabel = False
                queryset.save()
                Process.objects.create(state='项目终止', subject=queryset)
                SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                    terminationState='项目终止')
                Process.objects.create(state='项目终止', subject=queryset, note='终止申请结果：终止通过', dynamic=True)
            else:
                queryset.state = '项目终止'
                queryset.terminationState = '项目终止'
                queryset.subjectState = '项目终止'
                queryset.stateLabel = False
                queryset.save()
                Process.objects.create(state='项目终止', subject=queryset)
                SubjectTermination.objects.create(subject_id=request.data['subjectId'], terminationState='项目终止',
                                                  declareTime=queryset.applyTime)
                ChargeTermination.objects.filter(state='待审核', subject=queryset).update(state='项目终止',
                                                                                       auditTime=datetime.date.today())
                Process.objects.create(state='项目终止', subject=queryset, note='终止申请结果：终止通过', dynamic=True)
            return Response({"code": 0, "message": '管理员 - 终止通过'}, status=status.HTTP_200_OK)
        elif state == '确认终止不通过':
            if queryset.terminationOriginator == '承担单位' and queryset.stateLabel == False:
                queryset.state = '终止不通过'
                queryset.terminationState = '终止不通过'
                queryset.subjectState = '项目执行'
                queryset.save()
                Process.objects.create(state='项目执行', subject=queryset)
                SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                    terminationState='终止不通过')
                Process.objects.create(state='项目终止', subject=queryset, note='终止申请结果：终止不通过', dynamic=True)
                return Response({"code": 0, "message": '管理员 - 终止不通过'}, status=status.HTTP_200_OK)
            elif queryset.terminationOriginator == '承担单位' and queryset.stateLabel == True:
                queryset.state = '终止不通过'
                queryset.terminationState = '终止不通过'
                queryset.subjectState = '逾期未结题'
                queryset.save()
                Process.objects.create(state='项目执行', subject=queryset)
                SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                    terminationState='终止不通过')
                Process.objects.create(state='项目终止', subject=queryset, note='终止申请结果：终止不通过', dynamic=True)
                return Response({"code": 0, "message": '管理员 - 终止不通过'}, status=status.HTTP_200_OK)
            elif queryset.stateLabel == False:
                queryset.subjectState = '项目执行'
                queryset.state = '不同意终止'
                queryset.terminationOriginator = None
                queryset.save()
                ChargeTermination.objects.filter(state='待审核', subject=queryset).update(state='终止不通过',
                                                                                       auditTime=datetime.date.today())
                return Response({"code": 0, "message": '管理员 - 终止不通过'}, status=status.HTTP_200_OK)
            elif queryset.stateLabel == True:
                queryset.subjectState = '逾期未结题'
                queryset.state = '不同意终止'
                queryset.terminationOriginator = None
                queryset.save()
                ChargeTermination.objects.filter(state='待审核', subject=queryset).update(state='终止不通过',
                                                                                       auditTime=datetime.date.today())
                return Response({"code": 0, "message": '管理员 - 终止不通过'}, status=status.HTTP_200_OK)

    # 1.3 申报项目  年度下项目统计
    @action(detail=False, methods=['get'], url_path='declare_annual_analysis')
    def declare_annual_analysis(self, request, *args, **kwargs):
        lists = []
        subject = Subject.objects.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(
                subjectState='立项复核') | Q(subjectState='立项复核未通过'))
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            subject_count = subject.filter(project__category__batch__annualPlan=i).count()
            data = {
                "annualPlan": i,
                "subjectCount": subject_count,
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 1.3 申报项目  计划类别项目统计   annualPlan
    @action(detail=False, methods=['get'], url_path='declare_category_analysis')
    def declare_category_analysis(self, request, *args, **kwargs):
        lists = []
        subject = Subject.objects.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(
                subjectState='立项复核') | Q(subjectState='立项复核未通过'))
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            category_list = []
            category_obj = Category.objects.filter(batch__annualPlan=i)
            category = set([j.planCategory for j in category_obj])
            data = {"annualPlan": i}
            for j in category:
                subject_count = subject.filter(project__category__batch__annualPlan=i,
                                               project__category__planCategory=j).count()
                category_list.append({
                    "planCategory": j,
                    'subjectCount': subject_count})
            data['categoryList'] = category_list
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    #  1.3 签订合同 计划年度合同统计
    @action(detail=False, methods=['post'], url_path='contract_annualPlan_analysis')
    def contract_annualPlan_analysis(self, request, *args, **kwargs):
        lists = []
        subject = Subject.objects.filter(signedState=True)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            subject_count = subject.filter(project__category__batch__annualPlan=i).count()
            data = {
                "annualPlan": i,
                "subjectCount": subject_count,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3 签订合同 计划类别合同统计
    @action(detail=False, methods=['get'], url_path='contract_category_analysis')
    def contract_category_analysis(self, request, *args, **kwargs):
        lists = []
        subject = Subject.objects.filter(signedState=True)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            category_list = []
            category_obj = Category.objects.filter(batch__annualPlan=i)
            category = set([j.planCategory for j in category_obj])
            data = {"annualPlan": i}
            for j in category:
                subject_count = subject.filter(project__category__batch__annualPlan=i,
                                               project__category__planCategory=j).count()
                category_list.append({
                    "planCategory": j,
                    'subjectCount': subject_count})
            data['categoryList'] = category_list
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    #  1.3 经费拨付 计划年度经费统计
    @action(detail=False, methods=['get'], url_path='annualPlan_fee_analysis')
    def annualPlan_fee_analysis(self, request, *args, **kwargs):
        lists = []
        subject_obj = Subject.objects.filter(signedState=True)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            moneys = 0
            has_allocated = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i).values(
                'contract_subject__contractContent')
            for m in subject:
                money = ContractContent.objects.get(id=m['contract_subject__contractContent']).scienceFunding

                moneys += money
                has_allocated = sum([i.money for i in
                                     GrantSubject.objects.filter(subject__project__category__batch__annualPlan=i,
                                                                 state='通过')])
            data = {
                "annualPlan": i,
                # 申请经费
                'totalMoney': moneys,
                # 已拨付经费
                'hasAllocated': has_allocated
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3  经费拨付 计划类别经费统计
    @action(detail=False, methods=['get'], url_path='category_fee_analysis')
    def allocated_analysis(self, request, *args, **kwargs):
        lists = []
        subject_obj = Subject.objects.filter(signedState=True)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:

            category_list = []
            category_obj = Category.objects.filter(batch__annualPlan=i)
            category = set([j.planCategory for j in category_obj])
            data = {"annualPlan": i}
            for j in category:
                funding_number = 0
                subject = subject_obj.filter(project__category__batch__annualPlan=i,
                                             project__category__planCategory=j).values(
                    'contract_subject__contractContent')
                for s in subject:
                    funding = ContractContent.objects.get(id=s['contract_subject__contractContent']).scienceFunding
                    funding_number += funding
                category_list.append(
                    # 类别
                    {"planCategory": j,
                     # 申请经费
                    "fundingNumber": funding_number,
                                      })
            data['categoryList'] = category_list
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3 失信项目经费统计
    @action(detail=False, methods=['get'], url_path='funding_blacklist')
    def funding_blacklist(self, request):
        lists = []
        subject_obj = Subject.objects.filter(signedState=True)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='验收不通过').values(
                'contract_subject__contractContent', 'id')
            acceptance_money = 0
            for j in subject:
                # funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
                # money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
                # acceptance_money += funding - money
                funding = ContractContent.objects.get(id=j['contract_subject__contractContent'])
                for u in funding.unitFunding:
                    acceptance_money += Decimal(u['last'])

            subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='项目终止').values(
                'contract_subject__contractContent', 'id')
            termination_money = 0
            for j in subject:
                # funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
                # money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
                # termination_money += funding - money
                funding = ContractContent.objects.get(id=j['contract_subject__contractContent'])
                for u in funding.unitFunding:
                    termination_money += Decimal(u['last'])

            subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='逾期未结题').values(
                'contract_subject__contractContent', 'id')
            not_money = 0
            for j in subject:
                # funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
                # money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
                # not_money += funding - money
                funding = ContractContent.objects.get(id=j['contract_subject__contractContent'])
                for u in funding.unitFunding:
                    not_money += Decimal(u['last'])
            data = {
                "annualPlan": i,
                "acceptanceMoney": acceptance_money,
                "terminationMoney": termination_money,
                "notMoney": not_money,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3 经费使用情况统计
    @action(detail=False, methods=['get'], url_path='funding_use')
    def funding_use(self, request):
        lists = []
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:

            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            # 设备费 材料费 测试化验加工费 燃料动力费 差旅费 会议费 国际合作与交流费 出版/文献/信息传播/知识产权事务费 劳务费 专家咨询费 其他费用 间接费用
            equipment_fee = materials_costs = test_cost = fuel_cost = travel_cost = meeting_cost = international_cost = published_cost = labor_cost = expert_cost = other_cost = indirect_cost = 0

            for j in subject:
                acceptance = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=acceptance.acceptance)
                fees = ExpenditureStatement.objects.get(acceptance=str(acceptance.id))
                equipment_fee += sum([Decimal(x['equipmentFee']['spending']) for x in fees.equipmentFee])
                materials_costs += sum([Decimal(x['materialsCosts']['spending']) for x in fees.materialsCosts])
                test_cost += sum([Decimal(x['testCost']['spending']) for x in fees.testCost])
                fuel_cost += sum([Decimal(x['fuelCost']['spending']) for x in fees.fuelCost])
                travel_cost += sum([Decimal(x['travelCost']['spending']) for x in fees.travelCost])
                meeting_cost += sum([Decimal(x['meetingCost']['spending']) for x in fees.meetingCost])
                international_cost += sum([Decimal(x['internationalCost']['spending']) for x in fees.internationalCost])
                published_cost += sum([Decimal(x['publishedCost']['spending']) for x in fees.publishedCost])
                labor_cost += sum([Decimal(x['laborCost']['spending']) for x in fees.laborCost])
                expert_cost += sum([Decimal(x['expertCost']['spending']) for x in fees.expertCost])
                other_cost += sum([Decimal(x['otherCost']['spending']) for x in fees.otherCost])
                indirect_cost += sum([Decimal(x['indirectCost']['spending']) for x in fees.indirectCost])
            data = {
                "annualPlan": i,
                "equipmentFee": equipment_fee,
                "materialsCosts": materials_costs,
                "testCost": test_cost,
                "fuelCost": fuel_cost,
                "travelCost": travel_cost,
                "meetingCost": meeting_cost,
                "internationalCost": international_cost,
                "publishedCost": published_cost,
                "laborCost": labor_cost,
                "expertCost": expert_cost,
                "otherCost": other_cost,
                "indirectCost": indirect_cost,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # app
    # 1.3 科技成果统计分析
    @action(detail=False, methods=['get'], url_path='science_analysis')
    def science_analysis(self, request, *args, **kwargs):
        lists = []
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            imported_technology = 0
            application_technology = 0
            scientific_technological_achievements_transformed = 0
            new_industrial_products = 0
            new_agricultural_variety = 0
            new_process = 0
            new_material = 0
            new_device = 0
            cs = 0
            research_platform = 0
            ts = 0
            pilot_studies = 0
            pilot_line = 0
            production_line = 0
            experimental_base = 0
            apply_patent = 0
            authorized_patents = 0
            technical_standards = 0
            thesis_research_report = 0
            postdoctoral_training = 0
            training_doctors = 0
            training_master = 0
            monographs = 0
            academic_report = 0
            training_courses = 0
            training_number = 0
            for j in subject:
                subject_concluding = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=subject_concluding.acceptance)
                imported_technology += sum(
                    [i.importedTechnology for i in Output.objects.filter(acceptance=str(acceptance.id))])

                application_technology += sum(
                    [i.applicationTechnology for i in Output.objects.filter(acceptance=str(acceptance.id))])

                scientific_technological_achievements_transformed += sum(
                    [i.scientificTechnologicalAchievementsTransformed for i in
                     Output.objects.filter(acceptance=str(acceptance.id))])

                new_industrial_products += sum(
                    [i.newIndustrialProducts for i in Output.objects.filter(acceptance=str(acceptance.id))])

                new_agricultural_variety += sum(
                    [i.newAgriculturalVariety for i in Output.objects.filter(acceptance=str(acceptance.id))])
                new_process += sum([i.newProcess for i in Output.objects.filter(acceptance=str(acceptance.id))])
                new_material += sum([i.newMaterial for i in Output.objects.filter(acceptance=str(acceptance.id))])

                new_device += sum([i.newDevice for i in Output.objects.filter(acceptance=str(acceptance.id))])
                cs += sum([i.cs for i in Output.objects.filter(acceptance=str(acceptance.id))])
                research_platform += sum(
                    [i.researchPlatform for i in Output.objects.filter(acceptance=str(acceptance.id))])
                ts += sum([i.TS for i in Output.objects.filter(acceptance=str(acceptance.id))])

                pilot_studies += sum([i.pilotStudies for i in Output.objects.filter(acceptance=str(acceptance.id))])
                pilot_line += sum([i.pilotLine for i in Output.objects.filter(acceptance=str(acceptance.id))])
                production_line += sum([i.productionLine for i in Output.objects.filter(acceptance=str(acceptance.id))])

                experimental_base += sum(
                    [i.experimentalBase for i in Output.objects.filter(acceptance=str(acceptance.id))])
                apply_patent += sum([i.applyPatent for i in Output.objects.filter(acceptance=str(acceptance.id))])
                authorized_patents += sum(
                    [i.authorizedPatents for i in Output.objects.filter(acceptance=str(acceptance.id))])
                technical_standards += sum(
                    [i.technicalStandards for i in Output.objects.filter(acceptance=str(acceptance.id))])
                thesis_research_report += sum(
                    [i.thesisResearchReport for i in Output.objects.filter(acceptance=str(acceptance.id))])
                postdoctoral_training += sum(
                    [i.postdoctoralTraining for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_doctors += sum(
                    [i.trainingDoctors for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_master += sum([i.trainingMaster for i in Output.objects.filter(acceptance=str(acceptance.id))])
                monographs += sum([i.monographs for i in Output.objects.filter(acceptance=str(acceptance.id))])
                academic_report += sum([i.academicReport for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_courses += sum(
                    [i.trainingCourses for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_number += sum([i.trainingNumber for i in Output.objects.filter(acceptance=str(acceptance.id))])
            data = {
                "annualPlan": i,
                "importedTechnology": imported_technology,
                "applicationTechnology": application_technology,
                "scientificTechnologicalAchievementsTransformed": scientific_technological_achievements_transformed,
                "newIndustrialProducts": new_industrial_products,
                "newAgriculturalVariety": new_agricultural_variety,
                "newProcess": new_process,
                "newMaterial": new_material,
                "newDevice": new_device,
                "cs": cs,
                "researchPlatform": research_platform,
                "TS": ts,
                "pilotStudies": pilot_studies,
                "pilotLine": pilot_line,
                "productionLine": production_line,
                "experimentalBase": experimental_base,
                "applyPatent": apply_patent,
                "authorizedPatents": authorized_patents,
                "technicalStandards": technical_standards,
                "thesisResearchReport": thesis_research_report,
                "postdoctoralTraining": postdoctoral_training,
                "trainingDoctors": training_doctors,
                "trainingMaster": training_master,
                "monographs": monographs,
                "academicReport": academic_report,
                "trainingCourses": training_courses,
                "trainingNumber": training_number,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # app
    # 1.3  专利成果统计分析
    @action(detail=False, methods=['get'], url_path='science_technology_analysis')
    def science_technology_analysis(self, request, *args, **kwargs):
        lists = []
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            apply_patent = authorized_patents = apply_utility_model = authorized_utility_model = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                acceptance = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=acceptance.acceptance)
                apply_patent += sum(
                    [i.applyInventionPatent for i in Output.objects.filter(acceptance=str(acceptance.id))])
                authorized_patents += sum(
                    [i.authorizedInventionPatent for i in Output.objects.filter(acceptance=str(acceptance.id))])
                apply_utility_model += sum(
                    [i.applyUtilityModel for i in Output.objects.filter(acceptance=str(acceptance.id))])
                authorized_utility_model += sum(
                    [i.authorizedUtilityModel for i in Output.objects.filter(acceptance=str(acceptance.id))])

            data = {
                "annualPlan": i,
                "applyPatent": apply_patent,
                "authorizedPatents": authorized_patents,
                "applyUtilityModel": apply_utility_model,
                "authorizedUtilityModel": authorized_utility_model,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3 参与制定技术标准
    @action(detail=False, methods=['get'], url_path='patent_analysis')
    def patent_analysis(self, request, *args, **kwargs):
        lists = []
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            enterprise_standard = local_standards = industry_standard = national_standard = international_standard = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                acceptance = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=acceptance.acceptance)
                enterprise_standard += sum(
                    [i.enterpriseStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])
                local_standards += sum(
                    [i.localStandards for i in Output.objects.filter(acceptance=str(acceptance.id))])
                industry_standard += sum(
                    [i.industryStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])
                national_standard += sum(
                    [i.nationalStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])
                international_standard += sum(
                    [i.internationalStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])

            data = {
                "annualPlan": i,
                "enterpriseStandard": enterprise_standard,
                "localStandards": local_standards,
                "nationalStandard": national_standard,
                "industryStandard": industry_standard,
                "internationalStandard": international_standard
            }
            lists.append(data)

        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 论文研究报告
    @action(detail=False, methods=['get'], url_path='academic_analysis')
    def academict_analysis(self, request, *args, **kwargs):
        lists = []
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            core_journals = high_level_journal = general_journal = 0

            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                acceptance = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=acceptance.acceptance)
                core_journals += sum(
                    [i.coreJournals for i in Output.objects.filter(acceptance=str(acceptance.id))])
                high_level_journal += sum(
                    [i.highLevelJournal for i in Output.objects.filter(acceptance=str(acceptance.id))])
                general_journal += sum(
                    [i.generalJournal for i in Output.objects.filter(acceptance=str(acceptance.id))])
            data = {
                "annual_plan": i,
                "coreJournals": core_journals,
                "highLevelJournal": high_level_journal,
                "generalJournal": general_journal,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 经济效益统计分析
    @action(detail=False, methods=['get'], url_path='economic_analysis')
    def economic_analysis(self, request, *args, **kwargs):
        lists = []
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            sales_revenue = sales_revenue2 = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                subject_concluding = SubjectConcluding.objects.get(subject=j.id, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=subject_concluding.acceptance)
                sales_revenue += sum(
                    [i.salesRevenue + i.newProduction + i.newTax + (i.export * 7) for i in
                     Output.objects.filter(acceptance=str(acceptance.id))])
                sales_revenue2 += sum(
                    [i.salesRevenue2 + i.newProduction2 + i.newTax2 + (i.export2 * 7) for i in
                     Output.objects.filter(acceptance=str(acceptance.id))])

            data = {
                "annual_plan": i,
                "salesRevenue": sales_revenue,
                "salesRevenue2": sales_revenue2,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)


class SubjectChargeViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectChargeSerializers
    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 移动端 申报项目列表条件查询
    @action(detail=False, methods=['post'], url_path='app_charge_subject_query')
    def app_query_subject(self, request):
        queryset = self.queryset.exclude(subjectState='待提交')
        subject_name = request.data['subjectName']
        if subject_name:
            queryset = queryset.filter(subjectName__contains=subject_name)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "请填写项目名称"}, status=status.HTTP_200_OK)

    # 小程序
    @action(detail=False, methods=['post'], url_path='multi_select_subject')
    def multi_select_subject(self, request):
        user = request.user
        lists = []
        # 立项评审
        project_review = ['提交成功', '形式审查', '形式审查未通过', '立项复核', '立项复核未通过', '立项复核通过', '专家评审', '立项调研', '项目下达']
        # 签订合同
        sign_contract = ['签订合同']
        # 项目执行
        project_perform = ['项目执行']
        # 验收评审
        acceptance_review = ['验收审核', '验收通过', '验收不通过', '结题复核']
        # 终止评审
        termination_review = ['终止审核', '项目终止']
        # 逾期未结题
        timeout = ['逾期未结题']
        # 项目退回
        project_return = ['项目退回']

        project_status = request.data['projectStatus']
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": 'subjectName__contains'

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and len(json_data[k]) != 0}
        for i in project_status:
            if i == '立项评审':
                lists += project_review
            if i == '签订合同':
                lists += sign_contract
            if i == "项目执行":
                lists += project_perform
            if i == "验收评审":
                lists += acceptance_review
            if i == "终止评审":
                lists += termination_review
            if i == "逾期未结题":
                lists += timeout
            if i == "项目退回":
                lists += project_return
        if len(lists) == 0:
            queryset = self.queryset.exclude(subjectState='待提交').filter(**data, project__charge=user)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_201_CREATED)
        else:
            queryset = self.queryset.exclude(subjectState='待提交').filter(**data, subjectState__in=lists,
                                                                        project__charge=user)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_201_CREATED)

    """
    分管人员系统
    """

    # 首页 草拟电子合同
    @action(detail=False, methods=['get'], url_path='home_page')
    def home_page(self, request):
        charge = request.user
        censorship = self.queryset.filter(subjectState='形式审查', project__charge=charge).count()
        review = self.queryset.filter(subjectState='立项复核', project__charge=charge).count()
        research = self.queryset.filter(subjectState='立项调研', research=False, project__charge=charge).count()
        advice = self.queryset.filter(subjectState='立项调研', advice=False, project__charge=charge).count()
        electronic_contract = self.queryset.filter(contract_subject__state='审核中', subjectState='签订合同',
                                                   state='待审核', project__charge=charge).count()
        contract = self.queryset.filter(contract_subject__contractState='审核中', subjectState='签订合同', state='待审核',
                                        project__charge=charge).count()
        funding = GrantSubject.objects.filter(state='待提交', subject__project__charge=charge).count()
        change_subject = ChangeSubject.objects.filter(state='审核中', subject__project__charge=charge).count()
        concluding = self.queryset.filter(subjectState='验收审核', state='已提交', project__charge=charge).count()
        termination = self.queryset.filter(subjectState='终止审核', state='已提交', project__charge=charge).count()

        data = {
            "censorship": censorship,
            "review": review,
            "research": research,
            "advice": advice,
            "electronicContract": electronic_contract,
            "contract": contract,
            "funding": funding,
            "change_subject": change_subject,
            "concluding": concluding,
            "termination": termination,

        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 首页2
    # 快捷通道
    @action(detail=False, methods=['get'], url_path='fast_passage')
    def fast_passage(self, request):
        charge = request.user
        censorship_count = self.queryset.filter(subjectState='形式审查', project__charge=charge, state='提交成功').count()
        review_count = self.queryset.filter(subjectState="立项复核", project__charge=charge).count()
        suggested_count = self.queryset.filter(subjectState="立项调研", advice=False, project__charge=charge).count()
        issued_count = self.queryset.filter(subjectState="项目下达", project__charge=charge).count()

        electronic_contract = self.queryset.filter(contract_subject__state='审核中', subjectState='签订合同',
                                                   state='待审核', project__charge=charge).count()
        contract = self.queryset.filter(contract_subject__contractState='审核中', subjectState='签订合同', state='待审核',
                                        project__charge=charge).count()
        change_subject = ChangeSubject.objects.filter(state='审核中', subject__project__charge=charge).count()
        # funding = GrantSubject.objects.exclude(
        #     Q(subject__subjectState="验收不通过") | Q(subject__subjectState="项目终止") | Q(subject__subjectState="逾期未结题")) \
        #     .filter(Q(state='待提交') | Q(state='退回'), subject__project__charge=charge).count()
        funding = GrantSubject.objects.filter(Q(state='待提交') | Q(state='退回'), subject__project__charge=charge).count()
        concluding = self.queryset.filter(subjectState='验收审核', state='已提交', project__charge=charge).count()
        concluding_count = self.queryset.filter(subjectState='验收审核', state='分管员审核', project__charge=charge).count()

        termination = self.queryset.filter(subjectState='终止审核', state='已提交', project__charge=charge).count()
        termination_count = self.queryset.filter(subjectState='终止审核', state='分管员审核', project__charge=charge).count()

        data = {
            "censorshipCount": censorship_count,
            "reviewCount": review_count,
            "suggestedCount": suggested_count,
            "issuedCount": issued_count,
            "electronicContract": electronic_contract,
            "contract": contract,
            "changeSubject": change_subject,
            "funding": funding,
            "concluding": concluding,
            "concludingCount": concluding_count,
            "termination": termination,
            "terminationCount": termination_count,
        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 快捷通道 申报项目
    @action(detail=False, methods=['get'], url_path='declare_project')
    def declare_project(self, request):
        change_user = request.user
        lists = []
        dicts = {}
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        subject = Subject.objects.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(
                subjectState='立项复核') | Q(subjectState='立项复核未通过')).filter(project__charge=change_user, project__category__batch__annualPlan__range=[start, end])
        for i in subject:
            dicts[i.project.category.batch.annualPlan + i.project.category.batch.projectBatch] = [
                i.project.category.batch.annualPlan, i.project.category.batch.projectBatch]
        for k, v in dicts.items():
            subject_count = subject.filter(project__category__batch__annualPlan=v[0],
                                           project__category__batch__projectBatch=v[1]).count()
            data = {
                "annualPlan": v[0] + "年度" + v[1],
                "subjectCount": subject_count,
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 快捷通道 签订合同
    @action(detail=False, methods=['get'], url_path='sign_contract')
    def sign_contract(self, request):
        lists = []
        dicts = {}
        change_user = request.user
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        subject = Subject.objects.filter(signedState=True, project__charge=change_user, project__category__batch__annualPlan__range=[start, end])

        for i in subject:
            dicts[i.project.category.batch.annualPlan + i.project.category.batch.projectBatch] = [
                i.project.category.batch.annualPlan, i.project.category.batch.projectBatch]
        for k, v in dicts.items():
            subject_count = subject.filter(project__category__batch__annualPlan=v[0],
                                           project__category__batch__projectBatch=v[1]).count()
            data = {
                "annualPlan": v[0] + "年度" + v[1],
                "subjectCount": subject_count,
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 项目列表 申报立项项目列表展示/分管人员
    @action(detail=False, methods=['get'], url_path='charge_subject_show')
    def charge_subject_show(self, request):
        limit = request.query_params.dict().get('limit', None)
        charge = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan', '-declareTime').filter(
            project__charge=charge).exclude(subjectState='待提交')
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "保存成功", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目列表 申报立项项目列表查询/分管人员
    @action(detail=False, methods=['post'], url_path='charge_subject_query')
    def charge_subject_query(self, request):
        charge = request.user
        queryset = self.queryset.order_by('-project__category__batch__annualPlan', '-declareTime').filter(
            project__charge=charge).exclude(subjectState='待提交')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "subjectState": "subjectState",
            "warning": "warning",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 形式审查 待形式审查项目列表展示/ 分管员
    @action(detail=False, methods=['get'], url_path='charge_subject_show_a')
    def charge_subject_show_a(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='形式审查', state='提交成功')
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 形式审查 待形式审查项目列表条件查询 /分管人员
    @action(detail=False, methods=['post'], url_path='charge_subject_query_a')
    def charge_subject_query_a(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='形式审查', state='提交成功')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "unitName": "unitName__contains",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 微信小程序
    # 形式审查 待形式审查项目列表条件查询 /分管人员
    @action(detail=False, methods=['post'], url_path='charge_subject_query_wx')
    def charge_subject_query_wx(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='形式审查', state='提交成功')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 形式审查 形式审查/分管员
    @action(detail=False, methods=['post'], url_path='censorship')
    def censorship_subject_state(self, request):
        subject_id = request.data['subjectId']
        state = request.data['state']
        queryset = self.queryset.get(id=subject_id)
        if state == '通过':
            queryset.state = state
            queryset.subjectState = '立项复核'
            queryset.returnReason = None
            queryset.save()
            Process.objects.create(state='立项复核', subject=queryset)
            Process.objects.create(state='立项复核', subject=queryset, note='形式审查通过，请提交纸质版申报材料', dynamic=True)
            send_template(name='立项复核', subject_id=queryset.id)
            return Response({'code': 0, 'message': '形式审查 ok'}, status=status.HTTP_200_OK)
        else:
            queryset.state = '形式审查未通过'
            queryset.subjectState = '形式审查未通过'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            Process.objects.create(state='形式审查未通过', subject=queryset, note=request.data['returnReason'])
            Process.objects.create(state='形式审查未通过', subject=queryset, note='形式审查未通过', dynamic=True)
            attachment = AttachmentList.objects.get(attachmentName='申报单位营业执照/统一社会信用代码证书（复印件）',
                                                    attachmentShows='申报单位营业执照/统一社会信用代码证书',
                                                    subjectId=queryset.id)
            if attachment.attachmentContent[0]['path'] != queryset.enterprise.businessLicense:
                attachment.attachmentContent = [{"name": "营业执照", "path": queryset.enterprise.businessLicense}]
                attachment.save()
            abc = Reduction_declare.delay(annualPlan=queryset.project.category.batch.annualPlan,
                                          projectBatch=queryset.project.category.batch.projectBatch,
                                          planCategory=queryset.project.category.planCategory,
                                          projectName=queryset.project.projectName)
            print(abc.state)
            send_template(name='形式审查未通过', subject_id=queryset.id)
            # text_template = TextTemplate.objects.filter(enable=True, name='形式审查未通过')
            # if text_template.exists():
            #     sms_template = text_template.first()
            #     if sms_template.recipient == '1':
            #         content = sms_template.template.encode('gbk')
            #         SMS().send_sms(queryset.mobile, content)
            return Response({'code': 1, 'message': '形式审查 项目退回 '}, status=status.HTTP_200_OK)

    # 立项复核 立项复核列表条件查询 /分管员
    @action(detail=False, methods=['post'], url_path='charge_subject_query_b_wx')
    def charge_subject_query_b_wx(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='立项复核', reviewState='未完成')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 立项复核 立项复核列表展示/  分管员
    @action(detail=False, methods=['get'], url_path='charge_subject_show_b')
    def charge_subject_show_b(self, request):
        limit = request.query_params.dict().get('limit', None)
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='立项复核', reviewState='未完成')
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 立项复核 立项复核列表条件查询 /分管员
    @action(detail=False, methods=['post'], url_path='charge_subject_query_b')
    def charge_subject_query_b(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='立项复核', reviewState='未完成')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "unitName": "unitName__contains",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 立项复核 立项复核/分管人员
    @action(detail=False, methods=['post'], url_path='review')
    def review(self, request):
        subject_id = request.data['subjectId']
        state = request.data['state']
        queryset = self.queryset.get(id=subject_id)
        if state == '通过':
            queryset.subjectState = '立项复核通过'
            queryset.state = '立项复核通过'
            queryset.returnReason = None
            queryset.reviewState = '已完成'
            queryset.save()
            Process.objects.create(state='立项复核通过', subject=queryset)
            Process.objects.create(state='立项复核通过', subject=queryset, note='立项复核通过', dynamic=True)
            send_template(name='立项复核通过', subject_id=queryset.id)
            return Response({'code': 0, 'message': '立项复核 '}, status=status.HTTP_200_OK)
        else:
            # queryset.state = '立项复核'
            # queryset.subjectState = '项目退回'
            # queryset.returnReason = request.data['returnReason']
            # queryset.save()
            # Process.objects.create(state='项目退回', subject=queryset, note=request.data['returnReason'])
            # Process.objects.create(state='立项复核', subject=queryset, note='项目退回', dynamic=True)
            # send_template(name='项目退回', subject_id=queryset.id)
            # return Response({'code': 1, 'message': '立项复核 项目退回 '}, status=status.HTTP_200_OK)
            queryset.state = '立项复核未通过'
            queryset.subjectState = '立项复核未通过'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            Process.objects.create(state='立项复核未通过', subject=queryset, note=request.data['returnReason'])
            Process.objects.create(state='立项复核未通过', subject=queryset, note='立项复核未通过', dynamic=True)
            send_template(name='项目退回', subject_id=queryset.id)
            return Response({'code': 1, 'message': '立项复核未通过'}, status=status.HTTP_200_OK)

    # 立项调研 立项调研列表展示/分管员
    @action(detail=False, methods=['get'], url_path='charge_subject_show_c')
    def charge_subject_show_c(self, request):
        charge = request.user
        # queryset = self.queryset.filter(charge=charge, research='f', handOverState='t')
        queryset = self.queryset.filter(project__charge=charge, subjectState='立项调研')
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 立项调研 立项调研列表条件查询/分管员
    @action(detail=False, methods=['post'], url_path='charge_subject_query_c')
    def charge_subject_query_c(self, request):
        charge = request.user
        # queryset = self.queryset.filter(charge=charge, research='f', handOverState='t')
        queryset = self.queryset.filter(project__charge=charge, subjectState='立项调研')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "unitName": "unitName__contains",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 立项建议 立项建议列表展示/分管员
    @action(detail=False, methods=['get'], url_path='charge_subject_show_d')
    def charge_subject_show_d(self, request):
        charge = request.user
        # queryset = self.queryset.filter(charge=charge, advice='f', handOverState='t')
        queryset = self.queryset.filter(project__charge=charge, subjectState='立项调研')
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 立项建议列表/立项审批条件查询  分管员
    @action(detail=False, methods=['post'], url_path='charge_subject_query_d')
    def charge_subject_query_d(self, request):
        charge = request.user
        # queryset = self.queryset.filter(charge=charge, advice='f', handOverState='t')
        queryset = self.queryset.filter(project__charge=charge, subjectState='立项调研')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "unitName": "unitName__contains",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

        # 项目下达 条件查询/分管员

    @action(detail=False, methods=['post'], url_path='charge_user_project_issued_query_wx')
    def charge_user_project_issued_query_wx(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='项目下达')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 展示/分管员
    @action(detail=False, methods=['get'], url_path='charge_user_project_issued_show')
    def charge_user_project_issued_show(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='项目下达')
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 条件查询/分管员
    @action(detail=False, methods=['post'], url_path='charge_user_project_issued_query')
    def charge_user_project_issued_query(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='项目下达')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains"

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 分管员
    @action(detail=False, methods=['post'], url_path='issued')
    def project_issued(self, request):
        charge = request.user
        subject = self.queryset.get(id=request.data['subjectId'])
        if subject.contract_subject.exists():
            return Response({"code": 2, "message": "项目已下达，请勿重复操作"}, status=status.HTTP_200_OK)
        else:
            if request.data['state'] == '立项通过':
                if Subject.objects.filter(
                        Q(subjectState='验收审核') | Q(subjectState='终止审核') | Q(
                            subjectState='签订合同') | Q(subjectState='项目执行'), idNumber=subject.idNumber).count() == 2:
                    return Response({"code": 2, "message": "项目负责人最多可承担两个科技计划项目"}, status=status.HTTP_200_OK)
                else:
                    subject.state = '待提交'
                    subject.subjectState = '签订合同'
                    subject.giveTime = datetime.date.today()
                    subject.research = True
                    subject.save()
                    Contract.objects.create(contractNo=request.data['contractNo'],
                                            approvalMoney=int(Decimal(request.data['approvalMoney'])),
                                            subject=subject,
                                            chargeUser=charge)
                    Process.objects.create(state='签订合同', subject=subject)
                    # content = "您好，您向青秀区科技局申请的科研项目已经通过立项审批，请及时在系统内提交电子合同。".encode('gbk')
                    # SMS().send_sms(subject.mobile, content)

                    send_template(name='签订合同', subject_id=subject.id)

                    return Response({"code": 0, 'message': '签订合同成功'}, status=status.HTTP_200_OK)
            else:
                subject.subjectState = '项目退回'
                subject.state = '项目下达'
                subject.save()
                # Process.objects.create(state='项目退回', subject=subject)
                Process.objects.create(state='立项不通过', subject=subject)
                Process.objects.create(state='项目下达', subject=subject, note='项目退回', dynamic=True)
                send_template(name='项目退回', subject_id=subject.id)
                return Response({'code': 1, 'message': '项目退回'}, status=status.HTTP_200_OK)

    # 项目下达 审核电子合同条件查询/分管员
    @action(detail=False, methods=['post'], url_path='charge_user_review_contract_query_wx')
    def charge_user_review_contract_query_wx(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='签订合同', state='待审核',
                                        contract_subject__contractState='-', contract_subject__state='审核中',)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, 'message': 'ok', "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 审核电子合同展示/分管员
    @action(detail=False, methods=['get'], url_path='charge_user_review_contract_show')
    def charge_user_review_contract(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='签订合同',
                                        contract_subject__contractState='-')
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, 'message': 'ok', "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 审核电子合同条件查询/分管员
    @action(detail=False, methods=['post'], url_path='charge_user_review_contract_query')
    def charge_user_review_contract_query(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='签订合同',
                                        contract_subject__contractState='-')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "head": "head__contains",
            "state": "state",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, 'message': 'ok', "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 审核电子合同 退回 /分管员
    @action(detail=False, methods=['post'], url_path='charge_user_review_contract_back')
    def charge_user_review_contract_back(self, request):
        subject_id = request.data['subjectId']
        for s_id in subject_id:
            queryset = self.queryset.get(id=s_id)
            queryset.subjectState = '项目退回'
            queryset.state = '签订合同'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            Contract.objects.filter(subject=queryset).delete()
            Process.objects.create(state='项目退回', subject=queryset, note=request.data['returnReason'])
            Process.objects.create(state='签订合同', subject=queryset, note='项目退回', dynamic=True)
            send_template(name='项目退回', subject_id=queryset.id)
        return Response({'code': 0, "message": "已退回"}, status=status.HTTP_200_OK)

    # 审核合同书 / 分管员
    @action(detail=False, methods=['post'], url_path='f_audit_contract')
    def f_audit_contract(self, request):
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '通过':
            queryset.state = '局长审核'
            queryset.save()
            return Response({'code': 0, 'message': '通过'}, status.HTTP_200_OK)
        else:
            queryset.state = '待提交'
            queryset.contract_subject.update(state='未通过')
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            Process.objects.create(state='签订合同', subject=queryset, note='电子合同退回补正,请完成电子合同补正并提交审批',
                                   dynamic=True)
            send_template(name='电子合同审核不通过', subject_id=queryset.id)

            return Response({'code': 1, 'message': '补正资料ok'}, status.HTTP_200_OK)

    # 项目下达 审核合同条件查询/分管员
    @action(detail=False, methods=['post'], url_path='charge_user_review_contract_file_query_wx')
    def charge_user_review_contract_file_query_wx(self, request):
        charge = request.user
        queryset = self.queryset.exclude(contract_subject__contractState='-').filter(project__charge=charge,
                                                                                     subjectState='签订合同')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan__in",
            "planCategory": "project__category__planCategory__in",
            "subjectName": "subjectName__contains"
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != [] and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializers = self.get_serializer(instance, many=True)
        return Response({"code": 0, 'message': 'ok', "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 审核合同展示/分管员
    @action(detail=False, methods=['get'], url_path='charge_user_review_contract_file_show')
    def charge_user_review_contract_file_show(self, request):
        charge = request.user
        queryset = self.queryset.exclude(contract_subject__contractState='-').filter(project__charge=charge,
                                                                                     subjectState='签订合同')
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, 'message': 'ok', "detail": serializers.data}, status=status.HTTP_200_OK)

    # 项目下达 审核合同条件查询/分管员
    @action(detail=False, methods=['post'], url_path='charge_user_review_contract_file_query')
    def charge_user_review_contract_file_query(self, request):
        charge = request.user
        queryset = self.queryset.exclude(contract_subject__contractState='-').filter(project__charge=charge,
                                                                                     subjectState='签订合同')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "contractNo": "contract_subject__contractNo",
            "head": "head",
            "state": "state",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializers = self.get_serializer(instance, many=True)
        return Response({"code": 0, 'message': 'ok', "detail": serializers.data}, status=status.HTTP_200_OK)

    # 审核合同书 / 分管员
    @action(detail=False, methods=['post'], url_path='charge_user_review_contract_file')
    def charge_user_review_contract_file(self, request):
        state = request.data['state']
        # return_reason = request.data['returnReason']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '通过':
            queryset.subjectState = '项目执行'
            queryset.state = '通过'
            queryset.signedState = True
            queryset.save()
            queryset.contract_subject.update(contractState='通过')
            Process.objects.create(state='项目执行', subject=queryset)
            if queryset.subject_grant_type.filter(grantType='首笔经费').exists():
                pass
            else:
                grant_subject = GrantSubject.objects.create(subject=queryset, grantType='首笔经费')
                contract = Contract.objects.get(subject=queryset)
                subject_unit_info = SubjectUnitInfo.objects.get(subjectId=request.data['subjectId'])
                unit = subject_unit_info.unitInfo + subject_unit_info.jointUnitInfo
                m = 0
                for i in ContractContent.objects.get(id=contract.contractContent).unitFunding:
                    for j in unit:
                        if i['unitName'] == j['unitName']:
                            if i['first'] == '0.00':
                                m += 1
                            else:
                                AllocatedSingle.objects.create(subjectName=queryset.subjectName,
                                                               contractNo=contract.contractNo,
                                                               head=queryset.head, unitName=i['unitName'],
                                                               grantSubject=grant_subject.id,
                                                               money=Decimal(i['first']),
                                                               initial=Decimal(i['first']),
                                                               receivingUnit=i['unitName'],
                                                               bankAccount=j['bankAccount'],
                                                               bank=j['bank']
                                                               )
                if m == len(unit):
                    GrantSubject.objects.filter(subject_id=request.data["subjectId"], grantType='首笔经费',
                                                id=grant_subject.id).delete()
            Process.objects.create(state='项目执行', subject=queryset, note='合同书审核通过', dynamic=True)
            send_template(name='合同附件审核通过', subject_id=queryset.id)
            return Response({'code': 0, 'message': '通过 ok'}, status.HTTP_200_OK)
        else:
            queryset.state = '待上传'
            queryset.contract_subject.update(contractState='待上传')
            queryset.save()
            Process.objects.create(state='项目执行', subject=queryset, note='合同书审核不通过', dynamic=True)
            send_template(name='合同附件审核不通过', subject_id=queryset.id)
            return Response({'code': 1, 'message': '退回 ok'}, status.HTTP_200_OK)

    # 项目结题验收 结题验收审核列表展示/分管人员1
    @action(detail=False, methods=['get'], url_path='change_user_concluding_show')
    def change_user_concluding_show(self, request):
        charge = request.user
        queryset = self.queryset.filter(subjectState='验收审核', project__charge=charge, state='已提交')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 结题验收审核列表条件查询/分管人员1
    @action(detail=False, methods=['post'], url_path='change_user_concluding_query')
    def change_user_concluding_query(self, request):
        charge = request.user
        queryset = self.queryset.filter(subjectState='验收审核', project__charge=charge, state='已提交')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 结题验收审核列表展示/分管人员2
    @action(detail=False, methods=['get'], url_path='acceptance_show')
    def acceptance_show(self, request):
        limit = request.query_params.dict().get('limit', None)
        charge = request.user
        queryset = self.queryset.order_by("id", "subject_concluding__declareTime").filter(subjectState='验收审核',
                                                                                          project__charge=charge,
                                                                                          state='已提交').distinct("id")
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 结题验收审核-移交 /分管人员2
    @action(detail=False, methods=['post'], url_path='acceptance_hand_over')
    def acceptance_hand_over(self, request):
        acceptance_id = request.data["acceptanceId"]
        subject_id = request.data['subjectId']
        user_id = request.data['agencyId']
        self.queryset.filter(id=subject_id).update(state="移交")
        SubjectConcluding.objects.filter(acceptance=acceptance_id, subject_id=subject_id).update(agency_id=user_id)
        return Response({"code": 0, "message": "移交成功"}, status=status.HTTP_201_CREATED)

    # 项目结题验收 上传验收资料/分管人员2
    @action(detail=False, methods=['post'], url_path='acceptance_record_show')
    def acceptance_record_show(self, request):
        limit = request.query_params.dict().get('limit', None)
        charge = request.user
        # queryset = self.queryset.order_by('updated').exclude(subjectState='验收审核', state='已提交').filter(
        #     subjectState='验收审核', charge=charge)
        queryset = self.queryset.order_by("id", "subject_concluding__declareTime",
                                          "subject_concluding__updated").exclude(subjectState='验收审核',
                                                                                 state='已提交').filter(
            subjectState='验收审核', project__charge=charge).distinct('id')
        json_data = request.data
        keys = {
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "results": "results"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 上传验收资料/分管人员2
    @action(detail=False, methods=['post'], url_path='acceptance_submit')
    def acceptance_submit(self, request):
        if request.data['state'] == '提交':
            self.queryset.filter(id=request.data['subjectId']).update(state="局长审核")
            return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_201_CREATED)
        else:
            subject_concluding = SubjectConcluding.objects.get(subject=request.data['subjectId'], concludingState='待审核')
            KOpinionSheet.objects.filter(acceptance=subject_concluding.acceptance).delete()
            return Response({"code": 0, "message": "已经取消"}, status=status.HTTP_201_CREATED)

    # 项目结题验收 结题验收审核退回/分管人员
    @action(detail=False, methods=['post'], url_path='change_user_concluding_back')
    def change_user_concluding_back(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        queryset.returnReason = request.data['returnReason']
        queryset.state = '审核退回'
        queryset.subjectState = '项目执行'
        queryset.concludingState = '审核退回'
        SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
            concludingState='审核退回')
        queryset.save()
        Process.objects.create(state='项目执行', subject=queryset)
        return Response({'code': 0, 'message': "退回成功"}, status=status.HTTP_200_OK)

    # 项目结题验收 结题验收审核同意验收/分管人员
    @action(detail=False, methods=['post'], url_path='change_user_concluding_agree')
    def change_user_concluding_agree(self, request):
        k_experts_id = request.data['kExpertsId']
        queryset = self.queryset.get(id=request.data['subjectId'])
        acceptance = SubjectConcluding.objects.filter(subject=queryset, concludingState='待审核').get().acceptance
        for k_id in k_experts_id:
            k_experts = KExperts.objects.get(id=k_id)
            SubjectKExperts.objects.create(subject=queryset, kExperts=k_experts, acceptance=acceptance)
        queryset.reviewTime = request.data['reviewTime']
        queryset.state = '组织专家评审'
        queryset.save()
        return Response({'code': 0, 'message': "指派成功"}, status=status.HTTP_200_OK)

    # 项目结题验收  验收管理列表展示/分管员
    @action(detail=False, methods=['get'], url_path='change_user_acceptance_show')
    def change_user_acceptance_show(self, request):
        charge = request.user
        queryset = self.queryset.filter(subjectState='验收审核', state='组织专家评审', project__charge=charge)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  验收管理列表条件查询/分管员
    @action(detail=False, methods=['post'], url_path='change_user_acceptance_query')
    def change_user_acceptance_query(self, request):
        charge = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(subjectState='验收审核', state='组织专家评审', project__charge=charge)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  评审管理展示/分管员
    @action(detail=False, methods=['get'], url_path='change_user_review_show')
    def change_user_review_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(id=subject_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  评审管理取消指派/分管员
    @action(detail=False, methods=['post'], url_path='change_user_cancel_assigned')
    def change_user_cancel_assigned(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        SubjectKExperts.objects.filter(subject=queryset).delete()
        queryset.state = '已提交'
        queryset.reviewTime = None
        queryset.save()
        return Response({'code': 0, "message": '取消指派OK'}, status=status.HTTP_200_OK)

    # 项目结题验收  评审管理调整指派/分管员
    @action(detail=False, methods=['post'], url_path='change_user_adjust_assigned')
    def change_user_adjust_assigned(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        k_experts = request.data['kExperts']
        k_experts2 = request.data['kExperts2']
        review_time = request.data['reviewTime']
        queryset.reviewTime = review_time
        queryset.save()
        for i in k_experts:
            SubjectKExperts.objects.filter(subject=queryset, kExperts_id=i,
                                           acceptance=request.data['acceptance']).delete()
        for k_id in k_experts2:
            SubjectKExperts.objects.create(subject=queryset, kExperts_id=k_id, acceptance=request.data['acceptance'])
        return Response({'code': 0, "message": '调整指派ok'}, status=status.HTTP_200_OK)

    # 项目结题验收  评审/分管员
    @action(detail=False, methods=['post'], url_path='change_user_review')
    def change_user_review(self, request):
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '验收通过':
            queryset.state = '局长审核'
            queryset.returnReason = None
            queryset.results = '验收通过'
            queryset.save()
            return Response({'code': 0, "message": '分管员 - 验收通过'}, status=status.HTTP_200_OK)
        elif state == '补正资料':
            queryset.state = '补正资料'
            queryset.concludingState = '待提交'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
                concludingState='补正资料')
            return Response({'code': 0, "message": '分管员 - 补正资料'}, status=status.HTTP_200_OK)
        elif state == '结题复核':
            if queryset.double == False:
                queryset.state = '局长审核'
                queryset.returnReason = None
                queryset.results = '结题复核'
                queryset.save()
                return Response({'code': 0, "message": '分管员 - 结题复核'}, status=status.HTTP_200_OK)
            else:
                return Response({'code': 1, "message": '不允许第二次结题复核'}, status=status.HTTP_200_OK)
        elif state == '验收不通过':
            queryset.state = '局长审核'
            queryset.returnReason = None
            queryset.results = '验收不通过'
            queryset.save()
            return Response({'code': 2, "message": '分管员 - 验收不通过'}, status=status.HTTP_200_OK)
        elif state == '取消':
            subject_concluding = SubjectConcluding.objects.get(subject=request.data['subjectId'], concludingState='待审核')
            acceptance = Acceptance.objects.get(id=subject_concluding.acceptance)
            KOpinionSheet.objects.filter(acceptance=str(acceptance.id)).delete()
            return Response({'code': 3, "message": '分管员 - 取消'}, status=status.HTTP_200_OK)
        else:
            subject_concluding = SubjectConcluding.objects.get(subject=request.data['subjectId'], concludingState='待审核')
            acceptance = Acceptance.objects.get(id=subject_concluding.acceptance)
            KOpinionSheet.objects.filter(acceptance=str(acceptance.id)).delete()
            return Response({'code': 4, "message": '取消'}, status=status.HTTP_200_OK)

    # 项目结题验收  补正资料列表展示/分管员
    @action(detail=False, methods=['get'], url_path='change_user_data_show')
    def change_user_data_show(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='验收审核', state='补正资料')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  补正资料列表查询/分管员
    @action(detail=False, methods=['post'], url_path='change_user_data_query')
    def change_user_data_query(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='验收审核', state='补正资料')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "concludingState": "concludingState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止 终止审核列表展示/分管人员1
    @action(detail=False, methods=['get'], url_path='change_user_termination_show')
    def change_user_termination_show(self, request):
        charge = request.user
        queryset = self.queryset.filter(subjectState='终止审核', project__charge=charge, state='已提交')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止 终止审核列表查询/分管人员1
    @action(detail=False, methods=['post'], url_path='change_user_termination_query')
    def change_user_termination_query(self, request):
        charge = request.user
        queryset = self.queryset.filter(subjectState='终止审核', project__charge=charge, state='已提交')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止 终止审核列表查询/分管人员2
    @action(detail=False, methods=['post'], url_path='termination_show')
    def termination_show(self, request):
        limit = request.query_params.dict().get('limit', None)
        charge = request.user
        queryset = self.queryset.order_by("id", "subject_concluding__declareTime").filter(subjectState='终止审核',
                                                                                          project__charge=charge,
                                                                                          state='已提交').distinct("id")
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 结题验收审核-移交 /分管人员2
    @action(detail=False, methods=['post'], url_path='termination_hand_over')
    def termination_hand_over(self, request):
        termination_id = request.data["terminationId"]
        subject_id = request.data['subjectId']
        user_id = request.data['agencyId']
        self.queryset.filter(id=subject_id).update(state="移交")
        SubjectTermination.objects.filter(termination=termination_id, subject_id=subject_id).update(agency_id=user_id)
        return Response({"code": 0, "message": "移交成功"}, status=status.HTTP_201_CREATED)

    # 项目结题验收 上传验收资料/分管人员2
    @action(detail=False, methods=['post'], url_path='termination_record_show')
    def termination_record_show(self, request):
        limit = request.query_params.dict().get('limit', None)
        charge = request.user
        queryset = self.queryset.order_by('updated').exclude(subjectState='终止审核', state='已提交').filter(
            terminationOriginator='承担单位', subjectState='终止审核', project__charge=charge)
        json_data = request.data
        keys = {
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "results": "results"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 上传验收资料/分管人员2
    @action(detail=False, methods=['post'], url_path='termination_submit')
    def termination_submit(self, request):
        if request.data['state'] == '提交':
            self.queryset.filter(id=request.data['subjectId']).update(state="局长审核")
            return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_201_CREATED)
        else:
            subject_termination = SubjectTermination.objects.get(subject=request.data['subjectId'],
                                                                 terminationState='待审核')
            TKOpinionSheet.objects.filter(termination=subject_termination.termination).delete()
            return Response({"code": 0, "message": "已经取消"}, status=status.HTTP_201_CREATED)

    # 项目终止 终止审核退回/分管人员
    @action(detail=False, methods=['post'], url_path='change_user_termination_back')
    def change_user_termination_back(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        if queryset.stateLabel == False:
            queryset.returnReason = request.data['returnReason']
            queryset.terminationState = '审核退回'
            queryset.subjectState = '项目执行'
            queryset.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                terminationState='审核退回')
        else:
            queryset.returnReason = request.data['returnReason']
            queryset.terminationState = '审核退回'
            queryset.subjectState = '逾期未结题'
            queryset.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                terminationState='审核退回')
        return Response({'code': 0, 'message': "退回成功"}, status=status.HTTP_200_OK)

    # 项目终止 终止审核同意终止/分管人员
    @action(detail=False, methods=['post'], url_path='change_user_termination_agree')
    def change_user_termination_agree(self, request):
        k_experts_id = request.data['kExpertsId']
        queryset = self.queryset.get(id=request.data['subjectId'])
        termination = SubjectTermination.objects.filter(subject=queryset, terminationState='待审核').get().termination
        for k_id in k_experts_id:
            k_experts = KExperts.objects.get(id=k_id)
            SubjectKExperts.objects.create(subject=queryset, kExperts=k_experts, termination=termination)
        queryset.reviewTime = request.data['reviewTime']
        queryset.state = '组织终止评审'
        queryset.save()
        return Response({'code': 0, 'message': "指派成功"}, status=status.HTTP_200_OK)

    # 项目终止  终止评审管理列表展示/分管员
    @action(detail=False, methods=['get'], url_path='change_user_review_show_z')
    def change_user_review_show_z(self, request):
        charge = request.user
        queryset = self.queryset.filter(subjectState='终止审核', state='组织终止评审', project__charge=charge)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止  终止评审管理列表条件查询/分管员
    @action(detail=False, methods=['post'], url_path='change_user_review_query')
    def change_user_review_query(self, request):
        charge = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(subjectState='终止审核', state='组织终止评审', project__charge=charge)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止  评审管理取消指派/分管员
    @action(detail=False, methods=['post'], url_path='change_user_cancel_assigned_z')
    def change_user_cancel_assigned_z(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        SubjectKExperts.objects.filter(subject=queryset).delete()
        queryset.state = '已提交'
        queryset.reviewTime = None
        queryset.save()
        return Response({'code': 0, "message": '取消指派OK'}, status=status.HTTP_200_OK)

    # 项目终止  评审管理调整指派/分管员
    @action(detail=False, methods=['post'], url_path='change_user_adjust_assigned_z')
    def change_user_adjust_assigned_z(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        k_experts = request.data['kExperts']
        k_experts2 = request.data['kExperts2']
        review_time = request.data['reviewTime']

        queryset.reviewTime = review_time
        queryset.save()
        for i in k_experts:
            SubjectKExperts.objects.filter(subject=queryset, kExperts_id=i,
                                           termination=request.data['termination']).delete()
        for k_id in k_experts2:
            SubjectKExperts.objects.create(subject=queryset, kExperts_id=k_id, termination=request.data['termination'])
        return Response({'code': 0, "message": '调整指派ok'}, status=status.HTTP_200_OK)

    # 项目终止  评审/分管员
    @action(detail=False, methods=['post'], url_path='change_user_review_z')
    def change_user_review_z(self, request):
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '终止通过':
            queryset.state = '局长审核'
            queryset.returnReason = None
            queryset.results = '终止通过'
            queryset.save()
            return Response({'code': 0, "message": '分管员 - 终止通过'}, status=status.HTTP_200_OK)
        elif state == '补正资料':
            queryset.state = '补正资料'
            queryset.terminationState = '待提交'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                terminationState='补正资料')
            return Response({'code': 1, "message": '分管员 - 补正资料'}, status=status.HTTP_200_OK)
        elif state == '终止不通过':
            queryset.state = '局长审核'
            queryset.results = '终止不通过'
            queryset.returnReason = None
            queryset.save()
            return Response({'code': 2, "message": '分管员 - 终止不通过'}, status=status.HTTP_200_OK)
        elif state == '取消':
            subject_termination = SubjectTermination.objects.get(subject=request.data['subjectId'],
                                                                 terminationState='待审核')
            termination = Termination.objects.get(id=subject_termination.termination)
            TKOpinionSheet.objects.filter(termination=str(termination.id)).delete()
            return Response({'code': 3, "message": '分管员 - 取消'}, status=status.HTTP_200_OK)
        else:
            subject_termination = SubjectTermination.objects.get(subject=request.data['subjectId'],
                                                                 terminationState='待审核')
            termination = Termination.objects.get(id=subject_termination.termination)
            TKOpinionSheet.objects.filter(termination=str(termination.id)).delete()
            return Response({'code': 3, "message": ' 取消'}, status=status.HTTP_200_OK)

    # 项目终止  补正资料列表展示/分管员
    @action(detail=False, methods=['get'], url_path='change_user_data_show_z')
    def change_user_data_show_z(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='终止审核', state='补正资料')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目终止  补正资料列表查询/分管员
    @action(detail=False, methods=['post'], url_path='change_user_data_query_z')
    def change_user_data_query_z(self, request):
        charge = request.user
        queryset = self.queryset.filter(project__charge=charge, subjectState='终止审核', state='补正资料')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "terminationState": "terminationState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 分管员发起 终止项目展示 /分管员
    @action(detail=False, methods=['get'], url_path='change_user_show')
    def change_user_show(self, request, *args, **kwargs):
        charge = request.user
        subject_obj = Subject.objects.exclude(state='局长审核').filter(
            Q(subjectState='项目执行') | Q(subjectState='逾期未结题') | Q(subjectState='结题复核'), project__charge=charge)
        serializer = self.get_serializer(subject_obj, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 分管员发起 终止项目查询 /分管员
    @action(detail=False, methods=['post'], url_path='change_user_query')
    def change_user_query(self, request, *args, **kwargs):
        charge = request.user
        subject_obj = Subject.objects.exclude(state='局长审核').filter(
            Q(subjectState='项目执行') | Q(subjectState='逾期未结题') | Q(subjectState='结题复核'), project__charge=charge)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = subject_obj.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 分管员发起 终止项目 /分管员
    @action(detail=False, methods=['post'], url_path='change_user_termination')
    def change_user_termination(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        queryset = self.queryset.get(id=subject_id)
        if request.data['state'] == '确认终止':
            queryset.state = '局长审核'
            queryset.subjectState = '终止审核'
            queryset.terminationState = '待审核'
            queryset.results = '-'
            queryset.terminationOriginator = request.user.name
            queryset.applyTime = datetime.date.today()
            queryset.save()
            charge_termination = ChargeTermination.objects.create(subject_id=subject_id, state='待审核',
                                                                  declareTime=datetime.date.today(),
                                                                  charge=request.user,
                                                                  returnReason=request.data['returnReason'])
            TKOpinionSheet.objects.filter(chargeTermination=subject_id).update(chargeTermination=charge_termination.id)
            return Response({'code': 0, "message": "提交成功,已提交至科技局局长审核"}, status=status.HTTP_200_OK)
        if request.data['state'] == '取消':
            TKOpinionSheet.objects.filter(chargeTermination=subject_id).delete()
            return Response({'code': 1, "message": '分管员 - 验收不通过'}, status=status.HTTP_200_OK)

    # 1.3 申报项目  年度下项目统计
    @action(detail=False, methods=['get'], url_path='declare_annual_analysis')
    def declare_annual_analysis(self, request, *args, **kwargs):
        change_user = request.user
        lists = []
        subject = Subject.objects.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(
                subjectState='立项复核') | Q(subjectState='立项复核未通过')).filter(project__charge=change_user)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            subject_count = subject.filter(project__category__batch__annualPlan=i).count()
            data = {
                "annualPlan": i,
                "subjectCount": subject_count,
            }
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 1.3 申报项目  计划类别项目统计   annualPlan
    @action(detail=False, methods=['get'], url_path='declare_category_analysis')
    def declare_category_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject = Subject.objects.exclude(
            Q(subjectState='待提交') | Q(subjectState='形式审查未通过') | Q(subjectState='提交成功') | Q(subjectState='形式审查') | Q(
                subjectState='立项复核') | Q(subjectState='立项复核未通过')).filter(project__charge=change_user)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            category_list = []
            category_obj = Category.objects.filter(batch__annualPlan=i)
            category = set([j.planCategory for j in category_obj])
            data = {"annualPlan": i}
            for j in category:
                subject_count = subject.filter(project__category__batch__annualPlan=i,
                                               project__category__planCategory=j).count()
                category_list.append({
                    "planCategory": j,
                    'subjectCount': subject_count})
            data['categoryList'] = category_list
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    #  1.3 签订合同 计划年度合同统计
    @action(detail=False, methods=['post'], url_path='contract_annualPlan_analysis')
    def contract_annualPlan_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject = Subject.objects.filter(signedState=True, project__charge=change_user)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            subject_count = subject.filter(project__category__batch__annualPlan=i).count()
            data = {
                "annualPlan": i,
                "subjectCount": subject_count,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3 签订合同 计划类别合同统计
    @action(detail=False, methods=['get'], url_path='contract_category_analysis')
    def contract_category_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject = Subject.objects.filter(signedState=True, project__charge=change_user)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            category_list = []
            category_obj = Category.objects.filter(batch__annualPlan=i)
            category = set([j.planCategory for j in category_obj])
            data = {"annualPlan": i}
            for j in category:
                subject_count = subject.filter(project__category__batch__annualPlan=i,
                                               project__category__planCategory=j).count()
                category_list.append({
                    "planCategory": j,
                    'subjectCount': subject_count})
            data['categoryList'] = category_list
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # app 项目经费统计分析
    @action(detail=False, methods=['get'], url_path='funding_analysis')
    def funding_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(signedState=True, project__charge=change_user)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            moneys = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i).values(
                'contract_subject__contractContent')
            for m in subject:
                money = ContractContent.objects.get(id=m['contract_subject__contractContent']).scienceFunding
                moneys += money
                has_allocated = sum([i.money for i in
                                     GrantSubject.objects.filter(subject__project__category__batch__annualPlan=i,
                                                                 state='通过')])
                data = {
                    "annualPlan": i,
                    'totalMoney': moneys,
                    'hasAllocated': has_allocated
                }
                lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    #  1.3 经费拨付 计划年度经费统计
    @action(detail=False, methods=['get'], url_path='annualPlan_fee_analysis')
    def annualPlan_fee_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(signedState=True, project__charge=change_user)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            moneys = 0
            has_allocated = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i).values(
                'contract_subject__contractContent')
            for m in subject:
                money = ContractContent.objects.get(id=m['contract_subject__contractContent']).scienceFunding
                moneys += money
                has_allocated = sum([i.money for i in
                                     GrantSubject.objects.filter(subject__project__category__batch__annualPlan=i,
                                                                 state='通过')])
            data = {
                "annualPlan": i,
                'totalMoney': moneys,
                'hasAllocated': has_allocated
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3  经费拨付 计划类别经费统计
    @action(detail=False, methods=['get'], url_path='category_fee_analysis')
    def allocated_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(signedState=True, project__charge=change_user)
        batch = set([i.annualPlan for i in Batch.objects.filter()])
        for i in batch:
            category_list = []
            category_obj = Category.objects.filter(batch__annualPlan=i)
            category = set([j.planCategory for j in category_obj])
            data = {"annualPlan": i}
            for j in category:
                funding_number = 0
                subject = subject_obj.filter(project__category__batch__annualPlan=i,
                                             project__category__planCategory=j).values(
                    'contract_subject__contractContent')
                for s in subject:
                    funding = ContractContent.objects.get(id=s['contract_subject__contractContent']).scienceFunding
                    funding_number += funding
                category_list.append({"planCategory": j,
                                      "fundingNumber": funding_number,
                                      })
            data['categoryList'] = category_list
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # # 1.3 失信项目经费统计（首款（待拨付）尾款合计）
    # @action(detail=False, methods=['get'], url_path='funding_blacklist')
    # def funding_blacklist(self, request):
    #     lists = []
    #     change_user = request.user
    #     subject_obj = Subject.objects.filter(signedState=True, project__charge=change_user)
    #     batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
    #     annual_plan_list = sorted(list(batch_list))
    #     for i in annual_plan_list:
    #         subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='验收不通过').values(
    #             'contract_subject__contractContent', 'id')
    #         acceptance_money = 0
    #         for j in subject:
    #             funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
    #             money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
    #             acceptance_money += funding - money
    #
    #         subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='项目终止').values(
    #             'contract_subject__contractContent', 'id')
    #         termination_money = 0
    #         for j in subject:
    #             funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
    #             money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
    #             termination_money += funding - money
    #         subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='逾期未结题').values(
    #             'contract_subject__contractContent', 'id')
    #         not_money = 0
    #         for j in subject:
    #             funding = ContractContent.objects.get(id=j['contract_subject__contractContent']).scienceFunding
    #             money = sum([i.money for i in GrantSubject.objects.filter(subject_id=j['id']) if i.state == '通过'])
    #             not_money += funding - money
    #         data = {
    #             "annualPlan": i,
    #             "acceptanceMoney": acceptance_money,
    #             "terminationMoney": termination_money,
    #             "notMoney": not_money
    #         }
    #         lists.append(data)
    #     return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3 失信项目经费统计 （只展示尾款）
    @action(detail=False, methods=['get'], url_path='funding_blacklist')
    def funding_blacklist(self, request):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(signedState=True, project__charge=change_user)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='验收不通过').values(
                'contract_subject__contractContent', 'id')
            acceptance_money = 0
            for j in subject:
                funding = ContractContent.objects.get(id=j['contract_subject__contractContent'])
                for u in funding.unitFunding:
                    acceptance_money += Decimal(u['last'])

            subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='项目终止').values(
                'contract_subject__contractContent', 'id')
            termination_money = 0
            for j in subject:
                funding = ContractContent.objects.get(id=j['contract_subject__contractContent'])
                for u in funding.unitFunding:
                    termination_money += Decimal(u['last'])

            subject = subject_obj.filter(project__category__batch__annualPlan=i, subjectState='逾期未结题').values(
                'contract_subject__contractContent', 'id')
            not_money = 0
            for j in subject:
                funding = ContractContent.objects.get(id=j['contract_subject__contractContent'])
                for u in funding.unitFunding:
                    not_money += Decimal(u['last'])
            data = {
                "annualPlan": i,
                "acceptanceMoney": acceptance_money,
                "terminationMoney": termination_money,
                "notMoney": not_money,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)


    # 1.3 经费使用情况统计
    @action(detail=False, methods=['get'], url_path='funding_use')
    def funding_use(self, request):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True, project__charge=change_user)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            subject = subject_obj.filter(project__category__batch__annualPlan=i)

            # 设备费 材料费 测试化验加工费 燃料动力费 差旅费 会议费 国际合作与交流费 出版/文献/信息传播/知识产权事务费 劳务费 专家咨询费 其他费用 间接费用
            equipment_fee = materials_costs = test_cost = fuel_cost = travel_cost = meeting_cost = international_cost = published_cost = labor_cost = expert_cost = other_cost = indirect_cost = 0
            for j in subject:
                acceptance = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=acceptance.acceptance)
                fees = ExpenditureStatement.objects.get(acceptance=str(acceptance.id))
                equipment_fee += sum([Decimal(x['equipmentFee']['spending']) for x in fees.equipmentFee])
                materials_costs += sum([Decimal(x['materialsCosts']['spending']) for x in fees.materialsCosts])
                test_cost += sum([Decimal(x['testCost']['spending']) for x in fees.testCost])
                fuel_cost += sum([Decimal(x['fuelCost']['spending']) for x in fees.fuelCost])
                travel_cost += sum([Decimal(x['travelCost']['spending']) for x in fees.travelCost])
                meeting_cost += sum([Decimal(x['meetingCost']['spending']) for x in fees.meetingCost])
                international_cost += sum([Decimal(x['internationalCost']['spending']) for x in fees.internationalCost])
                published_cost += sum([Decimal(x['publishedCost']['spending']) for x in fees.publishedCost])
                labor_cost += sum([Decimal(x['laborCost']['spending']) for x in fees.laborCost])
                expert_cost += sum([Decimal(x['expertCost']['spending']) for x in fees.expertCost])
                other_cost += sum([Decimal(x['otherCost']['spending']) for x in fees.otherCost])
                indirect_cost += sum([Decimal(x['indirectCost']['spending']) for x in fees.indirectCost])
            data = {
                "annualPlan": i,
                "equipmentFee": equipment_fee,
                "materialsCosts": materials_costs,
                "testCost": test_cost,
                "fuelCost": fuel_cost,
                "travelCost": travel_cost,
                "meetingCost": meeting_cost,
                "internationalCost": international_cost,
                "publishedCost": published_cost,
                "laborCost": labor_cost,
                "expertCost": expert_cost,
                "otherCost": other_cost,
                "indirectCost": indirect_cost,

            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # app
    # 1.3 科技成果统计分析
    @action(detail=False, methods=['get'], url_path='science_analysis')
    def science_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True, project__charge=change_user)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            imported_technology = 0
            application_technology = 0
            scientific_technological_achievements_transformed = 0
            new_industrial_products = 0
            new_agricultural_variety = 0
            new_process = 0
            new_material = 0
            new_device = 0
            cs = 0
            research_platform = 0
            ts = 0
            pilot_studies = 0
            pilot_line = 0
            production_line = 0
            experimental_base = 0
            apply_patent = 0
            authorized_patents = 0
            technical_standards = 0
            thesis_research_report = 0
            postdoctoral_training = 0
            training_doctors = 0
            training_master = 0
            monographs = 0
            academic_report = 0
            training_courses = 0
            training_number = 0
            for j in subject:
                subject_concluding = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=subject_concluding.acceptance)
                imported_technology += sum(
                    [i.importedTechnology for i in Output.objects.filter(acceptance=str(acceptance.id))])

                application_technology += sum(
                    [i.applicationTechnology for i in Output.objects.filter(acceptance=str(acceptance.id))])

                scientific_technological_achievements_transformed += sum(
                    [i.scientificTechnologicalAchievementsTransformed for i in
                     Output.objects.filter(acceptance=str(acceptance.id))])

                new_industrial_products += sum(
                    [i.newIndustrialProducts for i in Output.objects.filter(acceptance=str(acceptance.id))])

                new_agricultural_variety += sum(
                    [i.newAgriculturalVariety for i in Output.objects.filter(acceptance=str(acceptance.id))])
                new_process += sum([i.newProcess for i in Output.objects.filter(acceptance=str(acceptance.id))])
                new_material += sum([i.newMaterial for i in Output.objects.filter(acceptance=str(acceptance.id))])

                new_device += sum([i.newDevice for i in Output.objects.filter(acceptance=str(acceptance.id))])
                cs += sum([i.cs for i in Output.objects.filter(acceptance=str(acceptance.id))])
                research_platform += sum(
                    [i.researchPlatform for i in Output.objects.filter(acceptance=str(acceptance.id))])
                ts += sum([i.TS for i in Output.objects.filter(acceptance=str(acceptance.id))])

                pilot_studies += sum([i.pilotStudies for i in Output.objects.filter(acceptance=str(acceptance.id))])
                pilot_line += sum([i.pilotLine for i in Output.objects.filter(acceptance=str(acceptance.id))])
                production_line += sum([i.productionLine for i in Output.objects.filter(acceptance=str(acceptance.id))])

                experimental_base += sum(
                    [i.experimentalBase for i in Output.objects.filter(acceptance=str(acceptance.id))])
                apply_patent += sum([i.applyPatent for i in Output.objects.filter(acceptance=str(acceptance.id))])
                authorized_patents += sum(
                    [i.authorizedPatents for i in Output.objects.filter(acceptance=str(acceptance.id))])
                technical_standards += sum(
                    [i.technicalStandards for i in Output.objects.filter(acceptance=str(acceptance.id))])
                thesis_research_report += sum(
                    [i.thesisResearchReport for i in Output.objects.filter(acceptance=str(acceptance.id))])
                postdoctoral_training += sum(
                    [i.postdoctoralTraining for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_doctors += sum(
                    [i.trainingDoctors for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_master += sum([i.trainingMaster for i in Output.objects.filter(acceptance=str(acceptance.id))])
                monographs += sum([i.monographs for i in Output.objects.filter(acceptance=str(acceptance.id))])
                academic_report += sum([i.academicReport for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_courses += sum(
                    [i.trainingCourses for i in Output.objects.filter(acceptance=str(acceptance.id))])
                training_number += sum([i.trainingNumber for i in Output.objects.filter(acceptance=str(acceptance.id))])
            data = {
                "annualPlan": i,
                "importedTechnology": imported_technology,
                "applicationTechnology": application_technology,
                "scientificTechnologicalAchievementsTransformed": scientific_technological_achievements_transformed,
                "newIndustrialProducts": new_industrial_products,
                "newAgriculturalVariety": new_agricultural_variety,
                "newProcess": new_process,
                "newMaterial": new_material,
                "newDevice": new_device,
                "cs": cs,
                "researchPlatform": research_platform,
                "TS": ts,
                "pilotStudies": pilot_studies,
                "pilotLine": pilot_line,
                "productionLine": production_line,
                "experimentalBase": experimental_base,
                "applyPatent": apply_patent,
                "authorizedPatents": authorized_patents,
                "technicalStandards": technical_standards,
                "thesisResearchReport": thesis_research_report,
                "postdoctoralTraining": postdoctoral_training,
                "trainingDoctors": training_doctors,
                "trainingMaster": training_master,
                "monographs": monographs,
                "academicReport": academic_report,
                "trainingCourses": training_courses,
                "trainingNumber": training_number,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # app
    # 1.3  专利成果统计分析
    @action(detail=False, methods=['get'], url_path='science_technology_analysis')
    def science_technology_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True, project__charge=change_user)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            apply_patent = authorized_patents = apply_utility_model = authorized_utility_model = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                acceptance = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=acceptance.acceptance)
                apply_patent += sum(
                    [i.applyInventionPatent for i in Output.objects.filter(acceptance=str(acceptance.id))])
                authorized_patents += sum(
                    [i.authorizedInventionPatent for i in Output.objects.filter(acceptance=str(acceptance.id))])
                apply_utility_model += sum(
                    [i.applyUtilityModel for i in Output.objects.filter(acceptance=str(acceptance.id))])
                authorized_utility_model += sum(
                    [i.authorizedUtilityModel for i in Output.objects.filter(acceptance=str(acceptance.id))])
            data = {
                "annualPlan": i,
                "applyPatent": apply_patent,
                "authorizedPatents": authorized_patents,
                "applyUtilityModel": apply_utility_model,
                "authorizedUtilityModel": authorized_utility_model,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 1.3 参与制定技术标准
    @action(detail=False, methods=['get'], url_path='patent_analysis')
    def patent_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user

        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True, project__charge=change_user)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            enterprise_standard = local_standards = industry_standard = national_standard = international_standard = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                subject_concluding = SubjectConcluding.objects.get(subject=j.id, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=subject_concluding.acceptance)
                enterprise_standard += sum(
                    [i.enterpriseStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])
                local_standards += sum(
                    [i.localStandards for i in Output.objects.filter(acceptance=str(acceptance.id))])
                industry_standard += sum(
                    [i.industryStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])
                national_standard += sum(
                    [i.nationalStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])
                international_standard += sum(
                    [i.internationalStandard for i in Output.objects.filter(acceptance=str(acceptance.id))])

            data = {
                "annualPlan": i,
                "enterpriseStandard": enterprise_standard,
                "localStandards": local_standards,
                "nationalStandard": national_standard,
                "industryStandard": industry_standard,
                "internationalStandard": international_standard
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 论文研究报告
    @action(detail=False, methods=['get'], url_path='academic_analysis')
    def academict_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True, project__charge=change_user)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            core_journals = high_level_journal = general_journal = 0

            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                acceptance = SubjectConcluding.objects.get(subject=j, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=acceptance.acceptance)
                core_journals += sum(
                    [i.coreJournals for i in Output.objects.filter(acceptance=str(acceptance.id))])
                high_level_journal += sum(
                    [i.highLevelJournal for i in Output.objects.filter(acceptance=str(acceptance.id))])
                general_journal += sum(
                    [i.generalJournal for i in Output.objects.filter(acceptance=str(acceptance.id))])
            data = {
                "annual_plan": i,
                "coreJournals": core_journals,
                "highLevelJournal": high_level_journal,
                "generalJournal": general_journal,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)

    # 经济效益统计分析
    @action(detail=False, methods=['get'], url_path='economic_analysis')
    def economic_analysis(self, request, *args, **kwargs):
        lists = []
        change_user = request.user
        subject_obj = Subject.objects.filter(subjectState='验收通过', signedState=True, project__charge=change_user)
        batch_list = set([i['annualPlan'] for i in Batch.objects.filter().values('annualPlan')])
        annual_plan_list = sorted(list(batch_list))
        for i in annual_plan_list:
            sales_revenue = sales_revenue2 = 0
            subject = subject_obj.filter(project__category__batch__annualPlan=i)
            for j in subject:
                subject_concluding = SubjectConcluding.objects.get(subject=j.id, concludingState='验收通过')
                acceptance = Acceptance.objects.get(id=subject_concluding.acceptance)
                sales_revenue += sum(
                    [i.salesRevenue + i.newProduction + i.newTax + (i.export * 7) for i in
                     Output.objects.filter(acceptance=str(acceptance.id))])
                sales_revenue2 += sum(
                    [i.salesRevenue2 + i.newProduction2 + i.newTax2 + (i.export2 * 7) for i in
                     Output.objects.filter(acceptance=str(acceptance.id))])

            data = {
                "annual_plan": i,
                "salesRevenue": sales_revenue,
                "salesRevenue2": sales_revenue2,
            }
            lists.append(data)
        return Response({'code': 0, 'message': '请求成功', 'detail': lists}, status=status.HTTP_200_OK)


# 评估机构
class SubjectOrganViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectOrganSerializers
    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 首页 草拟电子合同
    @action(detail=False, methods=['get'], url_path='home_page')
    def home_page(self, request):
        lists = []
        agencies = request.user
        assigned = self.queryset.filter(agencies=agencies, subjectState='专家评审', state='待指派').count()
        rate_count = self.queryset.filter(agencies=agencies, subjectState='专家评审', reviewWay='会评', state='未评审').count()
        network_count = self.queryset.filter(agencies=agencies, subjectState='专家评审', reviewWay='网评')
        for i in network_count:
            if SubjectExpertsOpinionSheet.objects.filter(subject=i, isReview=False).exists():
                pass
            else:
                if i.state == '未评审':
                    lists.append(i)
        results = rate_count + len(lists)
        undo = SubjectExpertsOpinionSheet.objects.filter(subject__agencies=agencies, agenciesState='待审核',
                                                         subject__subjectState='专家评审').count()
        data = {
            "assigned": assigned,
            "results": results,
            "undo": undo,
        }
        return Response({"code": 0, "message": "请求成功", "detail": data}, status=status.HTTP_201_CREATED)

    # 评估机构权限判断
    @action(detail=False, methods=['post'], url_path='permissions_judge')
    def permissions_judge(self, request):
        data = request.data['data']
        user = request.user
        if data == "1":
            if Agency.objects.filter(id=user.agency.id, permissions=data).exists():
                return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)
            if not Agency.objects.filter(id=user.agency.id,
                                         permissions=data).exists() and user.agencies_user.count() != 0:
                return Response({"code": 1, "message": "ok"}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 2, "message": "您暂无立项评审管理权限"}, status=status.HTTP_200_OK)
        else:
            if data == "2":
                if Agency.objects.filter(id=user.agency.id, permissions=data).exists():
                    return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)
                if SubjectConcluding.objects.filter(agency=user).exists() or SubjectTermination.objects.filter(
                        agency=user).exists():
                    return Response({"code": 1, "message": "ok"}, status=status.HTTP_200_OK)
                else:
                    return Response({"code": 2, "message": "您暂无立项评审管理权限"}, status=status.HTTP_200_OK)

    # 评估机构 待指派项目 年度
    @action(detail=False, methods=['get'], url_path='annual')
    def annual_show(self, request):
        user = request.user
        agencies_subject = self.queryset.filter(agencies=user, subjectState='专家评审', state='待指派')
        data = list(set([i.project.category.batch.annualPlan for i in agencies_subject]))
        return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    # 评估机构 待指派项目  批次列
    @action(detail=False, methods=['get'], url_path='batch')
    def batch_show(self, request):
        annual = request.query_params.dict().get("annualPlan")
        user = request.user
        agencies_subject = self.queryset.filter(agencies=user, subjectState='专家评审', state='待指派',
                                                project__category__batch__annualPlan=annual)
        data = list(set([i.project.category.batch.projectBatch for i in agencies_subject]))
        return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    # 评估机构删除专家
    @action(detail=False, methods=['delete'], url_path='delete_experts')
    def delete_experts(self, request):
        experts_id = request.data['expertsId']
        lists = []
        for i in experts_id:
            user = User.objects.get(id=i)
            if user.pExpert_three.filter(Q(subject__subjectState='立项调研') | Q(subject__subjectState='专家评审')).exists():
                lists.append(user.name)
            else:
                user.username = user.username + '-' + str(user.id)
                user.isDelete = True
                user.save()
                user.experts.isDelete = True
                user.experts.save()
        if len(lists) == 0:
            return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)
        return Response({"code": 1, "message": "该专家下有申报项目", "detail": lists}, status=status.HTTP_200_OK)

    # 待指派项目
    # 待指派专家项目列表 展示/评估机构
    @action(detail=False, methods=['get'], url_path='agencies_subject_show')
    def agencies_subject_show(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies, subjectState='专家评审', state='待指派')
        serializers = self.get_serializer(agencies_subject, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 待指派项目
    # 待指派专家项目列表 查询/评估机构
    @action(detail=False, methods=['post'], url_path='agencies_subject_query')
    def agencies_subject_query(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies, subjectState='专家评审', state='待指派')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 待指派项目
    # 单项指派专家/评估机构
    @action(detail=False, methods=['post'], url_path='individual_assigned')
    def individual_assigned(self, request):
        p_experts_id = request.data['pExpertsId']
        queryset = self.queryset.get(id=request.data['subjectId'])
        queryset.reviewWay = request.data['reviewWay']
        queryset.assignWay = '单项指派'
        queryset.state = '未评审'
        queryset.assignedTime = datetime.datetime.now()
        queryset.save()
        for i in p_experts_id:
            if SubjectExpertsOpinionSheet.objects.filter(subject=queryset).count() == 5:
                return Response({"code": 0, "message": "指派人数已达上线"})
            if SubjectExpertsOpinionSheet.objects.filter(subject=queryset, pExperts_id=i).exists():
                pass
            else:
                SubjectExpertsOpinionSheet.objects.create(subject=queryset, pExperts_id=i,
                                                          reviewWay=request.data['reviewWay'])
        return Response({'code': 0, 'message': '指派成功'}, status=status.HTTP_200_OK)

    # 待指派项目1
    # 选择项目 专家立项评审列表条件查询/评估机构1
    @action(detail=False, methods=['post'], url_path='choose_subject_query')
    def choose_subject_query(self, request):
        subject_id = request.data['subjectId']
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies, subjectState='专家评审', state='待指派')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.exclude(id__in=subject_id).filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 待指派项目2
    # 选择项目 建祖指派专家立项评审列表条件查询/评估机构2
    @action(detail=False, methods=['post'], url_path='choose_subject_show')
    def choose_subject_show(self, request):
        subject_id = request.data['subjectId']
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies, subjectState='专家评审', state='待指派')
        queryset = agencies_subject.exclude(id__in=subject_id).filter(
            project__category__batch__annualPlan=request.data["annualPlan"],
            project__category__batch__projectBatch=request.data["projectBatch"])
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 待指派项目
    # 按组指派/评估机构
    @action(detail=False, methods=['post'], url_path='group_assigned')
    def group_assigned(self, request):
        project_team_logo = uuid.uuid4()
        subject_id = request.data['subjectId']
        p_experts_id = request.data['pExpertsId']
        review_way = request.data['reviewWay']
        project_team = request.data['projectTeam']
        project_batch_list = [self.queryset.get(id=i).project.category.batch.projectBatch for i in subject_id]
        project_batch_set = set(project_batch_list)
        if len(project_batch_set) == 1:
            for i in subject_id:
                queryset = self.queryset.get(id=i)
                for j in p_experts_id:
                    SubjectExpertsOpinionSheet.objects.create(subject=queryset, pExperts_id=j, reviewWay=review_way)
                    queryset.projectTeam = project_team
                    queryset.projectTeamLogo = project_team_logo
                    queryset.reviewWay = review_way
                    queryset.assignWay = '按组指派'
                    queryset.state = '未评审'
                    queryset.assignedTime = datetime.datetime.now()
                    queryset.save()
            return Response({'code': 0, 'message': '指派成功'}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 1, 'message': '项目不是同一批次的不支持建组'}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派 展示/查询 /评估机构
    @action(detail=False, methods=['post'], url_path='management_group_subject_query')
    def management_group_subject_query(self, request):
        lists = []
        agencies = request.user
        json_data = request.data
        keys = {
            "projectTeam": "projectTeam__contains",
            "reviewWay": "reviewWay",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        agencies_subject = self.queryset.order_by('-assignedTime').filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'),
            agencies=agencies, subjectState='专家评审', state='未评审', assignWay='按组指派')
        subject_obj = agencies_subject.filter(**data)
        project_team_logo = set([i['projectTeamLogo'] for i in subject_obj.values('projectTeamLogo')])
        for j in project_team_logo:
            subject_obj_num = subject_obj.filter(projectTeamLogo=j)
            for subject in subject_obj_num:
                data = {
                    "projectTeamLogo": j,
                    "projectTeam": subject.projectTeam,
                    "reviewWay": subject.reviewWay,
                    "subjectNumber": subject_obj_num.count(),
                    "expertsNumber": SubjectExpertsOpinionSheet.objects.filter(
                        subject=subject).count()
                }
                lists.append(data)
                break
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理  ---已选择项目
    @action(detail=False, methods=['get'], url_path='management_group_subject_details_show')
    def management_group_subject_details_show(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'),
            agencies=agencies, subjectState='专家评审', state='未评审', assignWay='按组指派')
        json_data = request.query_params.dict()
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理  ---删除已选择项目 调整指派
    @action(detail=False, methods=['delete'], url_path='group_assigned_batch_delete')
    def group_assigned_batch_delete(self, request):
        agencies = request.user
        subject_id = request.data['subjectId']
        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'),
            agencies=agencies, subjectState='专家评审', state='未评审', assignWay='按组指派')
        for s_id in subject_id:
            subject = agencies_subject.get(id=s_id)
            SubjectExpertsOpinionSheet.objects.filter(subject=subject).delete()
            subject.projectTeam = None
            subject.projectTeamLogo = None
            subject.reviewWay = None
            subject.assignWay = None
            subject.assignedTime = None
            subject.state = '待指派'
            subject.save()
        return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理  ---添加项目 调整指派
    @action(detail=False, methods=['post'], url_path='group_assigned_batch_add')
    def group_assigned_batch_add(self, request):
        m = 0
        lists = []
        agencies = request.user
        subject_id = request.data['subjectId']
        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'),
            agencies=agencies, subjectState='专家评审', state='未评审', assignWay='按组指派')
        json_data = request.data
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys}
        queryset = agencies_subject.filter(**data)
        project_batch = [i.project.category.batch.projectBatch for i in queryset]
        for subject in queryset:
            pg_experts = subject.subject_three.values('pExperts')
            for i in pg_experts:
                lists.append(i['pExperts'])
        lists = list(set(lists))
        for s_id in subject_id:
            subject = Subject.objects.get(id=s_id)
            if project_batch[0] != subject.project.category.batch.projectBatch:
                m += 1
                return Response({"code": 0, "message": "添加项目不属于同一批次"}, status=status.HTTP_200_OK)
        if m == 0:
            for i in lists:
                for s_id in subject_id:
                    subject = Subject.objects.get(id=s_id)
                    SubjectExpertsOpinionSheet.objects.create(pExperts_id=i, subject=subject,
                                                              reviewWay=request.data['reviewWay'])
                    subject.assignWay = '按组指派'
                    subject.state = '未评审'
                    subject.projectTeamLogo = request.data['projectTeamLogo']
                    subject.reviewWay = request.data['reviewWay']
                    subject.projectTeam = request.data['projectTeam']
                    subject.assignedTime = datetime.datetime.now()
                    subject.save()
        return Response({"code": 0, "message": "项目添加成功"}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理  ---添加专家 调整指派
    @action(detail=False, methods=['post'], url_path='group_assigned_batch_pg_experts_add')
    def group_assigned_batch_pg_experts_add(self, request):
        agencies = request.user
        p_expert_id = request.data['pExpertId']
        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'), state='未评审',
            agencies=agencies, subjectState='专家评审', assignWay='按组指派')
        json_data = request.data
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys}
        queryset = agencies_subject.filter(**data)
        for subject in queryset:
            for p_id in p_expert_id:
                if not SubjectExpertsOpinionSheet.objects.filter(subject=subject, pExperts_id=p_id,
                                                                 reviewWay=request.data['reviewWay']).exists():
                    SubjectExpertsOpinionSheet.objects.create(subject=subject, pExperts_id=p_id,
                                                              reviewWay=request.data['reviewWay'])
        return Response({"code": 0, "message": "专家添加成功"}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理  ---删除专家  调整指派
    @action(detail=False, methods=['post'], url_path='group_assigned_batch_delete_pg_experts')
    def group_assigned_batch_delete_pg_experts(self, request):
        agencies = request.user
        p_experts_id = request.data['pExpertsId']
        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'), state='未评审',
            agencies=agencies, subjectState='专家评审', assignWay='按组指派')
        json_data = request.data
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys}
        queryset = agencies_subject.filter(**data)
        for expert in p_experts_id:
            for subject in queryset:
                SubjectExpertsOpinionSheet.objects.get(pExperts=expert, subject=subject).delete()
        return Response({"code": 0, "message": "已删除"}, status=status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理  ---调整指派
    @action(detail=False, methods=['post'], url_path='group_adjust_assigned')
    def group_adjust_assigned(self, request):
        lists = []
        agencies = request.user
        # 删除的课题ID
        subject_id2 = request.data['subjectId2']
        # 删除的
        p_expert_id2 = request.data['pExpertId2']
        subject_id = request.data['subjectId']
        p_expert_id = request.data['pExpertId']

        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'), state='未评审',
            agencies=agencies, subjectState='专家评审', assignWay='按组指派')
        json_data = request.data
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys}
        queryset = agencies_subject.filter(**data)
        # 删除项目
        if len(subject_id2) != 0:
            for s_id in subject_id2:
                subject = agencies_subject.get(id=s_id)
                SubjectExpertsOpinionSheet.objects.filter(subject=subject).delete()
                subject.projectTeam = None
                subject.projectTeamLogo = None
                subject.reviewWay = None
                subject.assignWay = None
                subject.assignedTime = None
                subject.state = '待指派'
                subject.save()
        # 删除专家
        if len(p_expert_id2) != 0:
            for expert in p_expert_id2:
                for subject in queryset:
                    SubjectExpertsOpinionSheet.objects.get(pExperts=expert, subject=subject).delete()
        if len(p_expert_id) != 0:
            for subject in queryset:
                for p_id in p_expert_id:
                    if not SubjectExpertsOpinionSheet.objects.filter(subject=subject, pExperts_id=p_id,
                                                                     reviewWay=request.data['reviewWay']).exists():
                        SubjectExpertsOpinionSheet.objects.create(subject=subject, pExperts_id=p_id,
                                                                  reviewWay=request.data['reviewWay'])
        if len(subject_id) != 0:
            for subject in queryset:
                pg_experts = subject.subject_three.values('pExperts')
                for i in pg_experts:
                    lists.append(i['pExperts'])
            lists = list(set(lists))
            for i in lists:
                for s_id in subject_id:
                    subject = Subject.objects.get(id=s_id)
                    SubjectExpertsOpinionSheet.objects.create(pExperts_id=i, subject=subject,
                                                              reviewWay=request.data['reviewWay'])
                    subject.assignWay = '按组指派'
                    subject.state = '未评审'
                    subject.projectTeamLogo = request.data['projectTeamLogo']
                    subject.reviewWay = request.data['reviewWay']
                    subject.projectTeam = request.data['projectTeam']
                    subject.assignedTime = datetime.datetime.now()
                    subject.save()
        return Response({'code': 0, 'message': '调整指派成功'}, status.HTTP_200_OK)

    # 评审管理
    # 建祖指派-评审管理  ---取消指派/评估机构
    @action(detail=False, methods=['post'], url_path='cancel_group_assigned')
    def cancel_group_assigned(self, request):
        project_team_logo = request.data['projectTeamLogo']
        project_team = request.data['projectTeam']
        review_way = request.data['reviewWay']
        agencies = request.user
        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'),
            agencies=agencies, subjectState='专家评审', state='未评审', assignWay='按组指派')
        subject_obj = agencies_subject.filter(projectTeamLogo=project_team_logo, projectTeam=project_team,
                                              reviewWay=review_way)
        for subject in subject_obj:
            subject.assignWay = None
            subject.projectTeam = None
            subject.reviewWay = None
            subject.projectTeamLogo = None
            subject.assignedTime = None
            subject.state = '待指派'
            subject.save()
            SubjectExpertsOpinionSheet.objects.filter(subject=subject).delete()
        return Response({'code': 0, 'message': '取消指派OK'}, status.HTTP_200_OK)

    # 评审管理
    # 单项指派- 展示 查询 /评估机构
    @action(detail=False, methods=['post'], url_path='single_subject_query')
    def single_subject_query(self, request):
        agencies = request.user
        limit = request.query_params.dict().get('limit', None)
        agencies_subject = self.queryset.order_by('-assignedTime').filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'), state='未评审',
            agencies=agencies, subjectState='专家评审', assignWay='单项指派')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "reviewWay": "reviewWay",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 评审管理
    # 单项指派-评审管理  调整指派/评估机构
    @action(detail=False, methods=['post'], url_path='adjust_assigned')
    def adjust_assigned(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(
            Q(project__category__batch__state='待提交') | Q(project__category__batch__state='不同意') | Q(
                project__category__batch__state='待审核'), state='未评审',
            agencies=agencies, subjectState='专家评审', assignWay='单项指派')
        subject_id = request.data['subjectId']
        p_experts = request.data['pExperts']
        p_experts2 = request.data['pExperts2']
        subject = agencies_subject.get(id=subject_id)
        if len(p_experts2) == 0:
            return Response({'code': 1, 'message': '请选择要调整指派的专家'}, status.HTTP_200_OK)
        else:
            for i in p_experts:
                SubjectExpertsOpinionSheet.objects.filter(subject=subject, pExperts_id=i).delete()
            for j in p_experts2:
                if not SubjectExpertsOpinionSheet.objects.filter(subject=subject, pExperts_id=j,
                                                                 reviewWay=subject.reviewWay).exists():
                    SubjectExpertsOpinionSheet.objects.create(subject=subject, pExperts_id=j,
                                                              reviewWay=subject.reviewWay)
            return Response({'code': 0, 'message': '单项指派 调整指派OK'}, status.HTTP_200_OK)

    # 评审管理
    # 单项指派-评审管理  取消指派/评估机构
    @action(detail=False, methods=['post'], url_path='cancel_assigned')
    def cancel_assigned(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies)
        subject_id = request.data['subjectId']
        subject = agencies_subject.get(id=subject_id)
        SubjectExpertsOpinionSheet.objects.filter(subject=subject).delete()
        subject.assignWay = None
        subject.reviewWay = None
        subject.assignedTime = None
        subject.state = '待指派'
        subject.save()
        return Response({'code': 0, 'message': '单项指派 取消指派OK'}, status.HTTP_200_OK)

    # 评审管理1
    # 单项指派-评审管理  提交审核展示/评估机构
    @action(detail=False, methods=['get'], url_path='submit_audit_show')
    def submit_audit_show(self, request):
        agencies = request.user
        agencies_subject = Batch.objects.order_by('-submitTime').filter(agency=agencies)
        lists = [
            {"annualPlan": i.annualPlan, "projectBatch": i.projectBatch, "submitTime": i.submitTime, "state": i.state,
             "returnReason": i.returnReason} for i in agencies_subject]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 评审管理1
    # 单项指派-评审管理  提交审核查询/评估机构
    @action(detail=False, methods=['post'], url_path='submit_audit_query')
    def submit_audit_query(self, request):
        agencies = request.user
        agencies_subject = Batch.objects.order_by('-submitTime').filter(agency=agencies)
        json_data = request.data
        keys = {
            "annualPlan": "annualPlan",
            "projectBatch": "projectBatch",
            "state": "state",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        lists = [
            {"annualPlan": i.annualPlan, "projectBatch": i.projectBatch, "submitTime": i.submitTime, "state": i.state,
             "returnReason": i.returnReason} for i in queryset]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 评审管理2
    # 单项指派-评审管理  提交审核查询/评估机构2
    @action(detail=False, methods=['post'], url_path='submit_audit_to_view')
    def submit_audit_to_view(self, request):
        agencies = request.user
        agencies_subject = Batch.objects.order_by('-submitTime').filter(agency=agencies)
        json_data = request.data
        keys = {
            "annualPlan": "annualPlan",
            "projectBatch": "projectBatch",
            "state": "state",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        lists = [
            {"annualPlan": i.annualPlan, "projectBatch": i.projectBatch, "submitTime": i.submitTime,
             "state": i.state,
             "returnReason": i.returnReason} for i in queryset if i.state != "同意"]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 评审管理
    # 评审管理  提交审核/评估机构
    @action(detail=False, methods=['post'], url_path='submit_audit')
    def submit_audit(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies)
        queryset = agencies_subject.filter(project__category__batch__annualPlan=request.data['annualPlan'],
                                           project__category__batch__projectBatch=request.data['projectBatch'])
        if queryset.filter(state='待指派').exists():
            return Response({"code": 1, "message": "该批次下有项目未指派，请完成指派再提交审核"}, status=status.HTTP_200_OK)
        else:
            submit_time = datetime.datetime.now().strftime("%Y.%m.%d %H:%M")
            Batch.objects.filter(annualPlan=request.data['annualPlan'], projectBatch=request.data['projectBatch'],
                                 agency=agencies).update(state='待审核', submitTime=submit_time)
            return Response({"code": 0, "message": "提交成功，请等待科技局审核"}, status=status.HTTP_200_OK)

    # 初始数据评审意见
    @action(detail=False, methods=['get'], url_path='show_s')
    def pg_experts_opinion_sheet_show_s(self, request):
        lists = []
        data = {}
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(id=subject_id)
        for i in queryset:
            data = {
                "planCategory": i.project.category.planCategory,
                "unitName": i.unitName,
                "subjectName": i.subjectName,
            }
            if i.reviewWay == '网评':
                lists.extend(i.subject_three.values('pExperts__name', 'pExperts__experts__unit',
                                                    'expertOpinionSheet__subjectScore'))
            else:
                lists.extend(i.subject_three.values('pExperts__name', 'pExperts__experts__unit'))
        data["opinionSheet"] = lists
        return Response({"code": 0, "message": "ok", "detail": data}, status.HTTP_200_OK)

    # 初始数据评审意见
    @action(detail=False, methods=['get'], url_path='initial_show')
    def initial_show(self, request):
        lists = []
        data = {}
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(id=subject_id)
        for i in queryset:
            data = {
                "planCategory": i.project.category.planCategory,
                "unitName": i.unitName,
                "subjectName": i.subjectName,
            }
            if i.reviewWay == '网评':
                lists.extend(i.subject_three.values('pExperts__expert__name', 'pExperts__expert__company',
                                                    'expertOpinionSheet__subjectScore'))
            else:
                lists.extend(i.subject_three.values('pExperts__expert__name', 'pExperts__expert__company'))
        data["opinionSheet"] = lists
        return Response({"code": 0, "message": "ok", "detail": data}, status.HTTP_200_OK)

    # 专家组评审意见展示2830
    # 评审结果
    # 建祖指派 建祖指派项目列表展示/评估机构
    @action(detail=False, methods=['get'], url_path='results_group_show')
    def results_group_show(self, request):
        lists = []
        agencies = request.user
        agencies_subject = self.queryset.order_by('-assignedTime').filter(agencies=agencies,
                                                                          subjectState='专家评审', assignWay='按组指派',
                                                                          project__category__batch__state='同意',
                                                                          handOverState=False)
        project_team_logo = set([i['projectTeamLogo'] for i in agencies_subject.values('projectTeamLogo')])
        for j in project_team_logo:
            subject_obj_num = agencies_subject.filter(projectTeamLogo=j)
            for subject in subject_obj_num:
                data = {
                    "projectTeamLogo": j,
                    "projectTeam": subject.projectTeam,
                    "reviewWay": subject.reviewWay,
                    "subjectNumber": subject_obj_num.count(),
                    "expertsNumber": SubjectExpertsOpinionSheet.objects.filter(
                        subject=subject).count()
                }
                lists.append(data)
                break
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 评审管理
    # 建祖指派 建祖指派项目列表查询/评估机构
    @action(detail=False, methods=['post'], url_path='results_group_query')
    def results_group_query(self, request):
        lists = []
        agencies = request.user
        json_data = request.data
        keys = {
            "projectTeam": "projectTeam__contains",
            "reviewWay": "reviewWay"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        agencies_subject = self.queryset.order_by('-assignedTime').filter(agencies=agencies,
                                                                          subjectState='专家评审', assignWay='按组指派',
                                                                          project__category__batch__state='同意',
                                                                          handOverState=False)
        subject_obj = agencies_subject.filter(**data)
        project_team_logo = set([i['projectTeamLogo'] for i in subject_obj.values('projectTeamLogo')])
        for j in project_team_logo:
            subject_obj_num = subject_obj.filter(projectTeamLogo=j)
            for subject in subject_obj_num:
                data = {
                    "projectTeamLogo": j,
                    "projectTeam": subject.projectTeam,
                    "reviewWay": subject.reviewWay,
                    "subjectNumber": subject_obj_num.count(),
                    "expertsNumber": SubjectExpertsOpinionSheet.objects.filter(
                        subject=subject).count()
                }
                lists.append(data)
                break
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 评审管理
    # 建祖指派 建祖会评/网评-评审意见/展示 查询评估机构
    @action(detail=False, methods=['post'], url_path='results_group_rate_query')
    def results_group_rate_query(self, request):
        agencies = request.user
        limit = request.query_params.dict().get('limit', None)
        agencies_subject = self.queryset.filter(agencies=agencies,
                                                subjectState='专家评审', assignWay='按组指派',
                                                project__category__batch__state='同意',
                                                handOverState=False)
        json_data = request.data
        keys = {
            "projectTeamLogo": "projectTeamLogo",
            "projectTeam": "projectTeam",

            "reviewWay": "reviewWay",
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "state": "state",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审管理
    # 单项指派 单项会评、网评-评审意见展示、查询/评估机构
    @action(detail=False, methods=['post'], url_path='results_single_rate_query')
    def results_single_rate_query(self, request):
        agencies = request.user
        limit = request.query_params.dict().get('limit', None)
        agencies_subject = self.queryset.order_by('-assignedTime').filter(agencies=agencies,
                                                                          subjectState='专家评审', assignWay='单项指派',
                                                                          project__category__batch__state='同意',
                                                                          handOverState=False)
        json_data = request.data
        keys = {
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "reviewWay": "reviewWay",
            "state": "state"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 撤销评审/评估机构
    @action(detail=False, methods=['post'], url_path='undo_review')
    def undo_review(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        if queryset.reviewWay == '会评':
            OpinionSheet.objects.filter(subject=queryset).delete()
            queryset.state = '未评审'
            queryset.save()
            SubjectExpertsOpinionSheet.objects.filter(subject=queryset, reviewWay="会评").update(state="待评审")
        else:
            queryset.state = '未评审'
            queryset.save()
            OpinionSheet.objects.filter(subject=queryset).delete()
        return Response({"code": 0, "message": "撤销成功"}, status=status.HTTP_200_OK)

    # 评审结果按年度、批次移交科技局展示1
    @action(detail=False, methods=['get'], url_path='batch_hand_over_show')
    def batch_hand_over_show(self, request):
        lists = []
        agencies = request.user
        batch = Batch.objects.order_by('-annualPlan').filter(agency=agencies)
        for i in batch:
            if self.queryset.filter(Q(state='未评审') | Q(state='待指派'), agencies=agencies, subjectState='专家评审',
                                    handOverState=False,
                                    project__category__batch=i).exists():
                data = {
                    "annualPlan": i.annualPlan,
                    "projectBatch": i.projectBatch,
                    "reviewState": '未完成'
                }
                lists.append(data)
            else:
                if self.queryset.filter(state='已评审', agencies=agencies, subjectState='专家评审',
                                        handOverState=False,
                                        project__category__batch=i).exists():
                    data = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '已完成'
                    }
                    lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)

    # 评审结果按年度、批次移交科技局查询12
    @action(detail=False, methods=['post'], url_path='batch_hand_over_query')
    def batch_hand_over_query(self, request):
        lists = []
        agencies = request.user
        json_data = request.data
        keys = {
            "annualPlan": "annualPlan",
            "projectBatch": "projectBatch",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        batch = Batch.objects.order_by('-annualPlan').filter(**data, agency=agencies)
        if request.data['reviewState'] == '全部':
            for i in batch:
                if self.queryset.filter(Q(state='未评审') | Q(state='待指派'), agencies=agencies, subjectState='专家评审',
                                        handOverState=False,
                                        project__category__batch=i).exists():
                    data_set = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '未完成',
                        "opinionState": "-",

                    }
                    lists.append(data_set)
                else:
                    if self.queryset.filter(state='已评审', agencies=agencies, subjectState='专家评审',
                                            handOverState=False,
                                            project__category__batch=i).exists():
                        data_set = {
                            "annualPlan": i.annualPlan,
                            "projectBatch": i.projectBatch,
                            "reviewState": '已完成',
                            "opinionState": i.get_opinionState_display(),
                            "returnReason": i.returnReason
                        }
                        lists.append(data_set)
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)
        elif request.data['reviewState'] == '已完成':
            for i in batch:
                if self.queryset.filter(Q(state='未评审') | Q(state='待指派'), agencies=agencies, subjectState='专家评审',
                                        handOverState=False,
                                        project__category__batch=i).exists():
                    pass
                else:
                    if self.queryset.filter(state='已评审', agencies=agencies, subjectState='专家评审',
                                            handOverState=False,
                                            project__category__batch=i).exists():
                        data_set = {
                            "annualPlan": i.annualPlan,
                            "projectBatch": i.projectBatch,
                            "reviewState": '已完成',
                            "opinionState": i.get_opinionState_display(),
                            "returnReason": i.returnReason
                        }
                        lists.append(data_set)
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)
        elif request.data['reviewState'] == '未完成':
            for i in batch:
                if self.queryset.filter(Q(state='未评审') | Q(state='待指派'), agencies=agencies, subjectState='专家评审',
                                        handOverState=False,
                                        project__category__batch=i).exists():
                    data_set = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '未完成',
                        "opinionState": "-",

                    }
                    lists.append(data_set)
            return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)

    # 评审结果按年度、批次移交科技局/评估机构1
    @action(detail=False, methods=['post'], url_path='batch_hand_over')
    def batch_hand_over(self, request):
        m = 0
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies,
                                                subjectState='专家评审',
                                                handOverState=False)
        json_data = request.data
        keys = {"annualPlan": "project__category__batch__annualPlan",
                "projectBatch": "project__category__batch__projectBatch"
                }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        for subject in queryset:
            if subject.state != '已评审':
                m += 1
                return Response({"code": 1, "message": "该批次下存在未完成评审项目"}, status=status.HTTP_200_OK)
            for i in subject.subject_three.values('state'):
                if i['state'] == '撤销审核':
                    m += 1
                    return Response({"code": 2, "message": "该批次下的项目有专家申请撤销评审意见，请处理后移交"}, status=status.HTTP_200_OK)
        if m == 0:
            for subject in queryset:
                subject.handOverState = True
                subject.subjectState = '立项调研'
                subject.save()
                Process.objects.create(state='立项调研', subject=subject)
            return Response({"code": 0, "message": "移交成功"}, status=status.HTTP_200_OK)

    # 评审结果按年度、批次移交科技局展示2
    @action(detail=False, methods=['get'], url_path='batch_submit_audit_show')
    def batch_submit_audit_show(self, request):
        lists = []
        agencies = request.user
        batch = Batch.objects.order_by('-annualPlan').filter(agency=agencies)
        for i in batch:
            if self.queryset.filter(Q(state='未评审') | Q(state='待指派'), agencies=agencies, subjectState='专家评审',
                                    handOverState=False,
                                    project__category__batch=i).exists():
                data = {
                    "annualPlan": i.annualPlan,
                    "projectBatch": i.projectBatch,
                    "reviewState": '未完成',
                    "opinionState": "-",
                }
                lists.append(data)
            else:
                if self.queryset.filter(state='已评审', agencies=agencies, subjectState='专家评审',
                                        handOverState=False,
                                        project__category__batch=i).exists():
                    data = {
                        "annualPlan": i.annualPlan,
                        "projectBatch": i.projectBatch,
                        "reviewState": '已完成',
                        "opinionState": i.get_opinionState_display(),
                        "returnReason": i.returnReason
                    }
                    lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_201_CREATED)

    # 评审结果提交审核2
    @action(detail=False, methods=['post'], url_path='batch_submit_audit')
    def batch_submit_audit(self, request):
        m = 0
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies,
                                                subjectState='专家评审',
                                                handOverState=False)
        json_data = request.data
        keys = {"annualPlan": "project__category__batch__annualPlan",
                "projectBatch": "project__category__batch__projectBatch"
                }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        for subject in queryset:
            if subject.state != '已评审':
                m += 1
                return Response({"code": 1, "message": "该批次下存在未完成评审项目"}, status=status.HTTP_200_OK)
            for i in subject.subject_three.values('state'):
                if i['state'] == '撤销审核':
                    m += 1
                    return Response({"code": 2, "message": "该批次下的项目有专家申请撤销评审意见，请处理后移交"}, status=status.HTTP_200_OK)
        if m == 0:
            Batch.objects.filter(annualPlan=request.data['annualPlan'],
                                 projectBatch=request.data['projectBatch']).update(opinionState="2")

            return Response({"code": 0, "message": "提交成功"}, status=status.HTTP_200_OK)

    # 评审结果统计按组指派展示/评估机构
    @action(detail=False, methods=['get'], url_path='statistical_group_show')
    def statistical_group_show(self, request):
        lists = []
        agencies = request.user
        agencies_subject = self.queryset.order_by('-project__category__batch__annualPlan',
                                                  '-project__category__batch__created').filter(agencies=agencies,
                                                                                               assignWay='按组指派',
                                                                                               handOverState=True)
        project_team_logo = list(set([i['projectTeamLogo'] for i in agencies_subject.values('projectTeamLogo')]))
        for j in project_team_logo:
            for i in agencies_subject.filter(projectTeamLogo=j):
                date = {

                    'annualPlan': i.project.category.batch.annualPlan,
                    'projectBatch': i.project.category.batch.projectBatch,
                    'projectTeam': i.projectTeam,
                    'projectTeamLogo': j,
                    'reviewWay': i.reviewWay,
                    'subjectNumber': agencies_subject.filter(projectTeamLogo=j).count(),
                    'expertsNumber': SubjectExpertsOpinionSheet.objects.filter(subject=i).count(),

                }

                lists.append(date)
                break
        lists = sorted(lists, key=lambda x: x['annualPlan'], reverse=True)
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 评审结果统计按组指派条件查询/评估机构
    @action(detail=False, methods=['post'], url_path='statistical_group_query')
    def statistical_group_query(self, request):
        lists = []
        agencies = request.user
        agencies_subject = self.queryset.order_by('-project__category__batch__annualPlan',
                                                  '-project__category__batch__created').filter(agencies=agencies,
                                                                                               assignWay='按组指派',
                                                                                               handOverState=True)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "projectTeam": "projectTeam__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        project_team_logo = list(set([i['projectTeamLogo'] for i in queryset.values('projectTeamLogo')]))
        for j in project_team_logo:
            for i in queryset.filter(projectTeamLogo=j):
                date = {
                    'annualPlan': i.project.category.batch.annualPlan,
                    'projectBatch': i.project.category.batch.projectBatch,
                    'projectTeam': i.projectTeam,
                    'projectTeamLogo': j,
                    'reviewWay': i.reviewWay,
                    'subjectNumber': agencies_subject.filter(projectTeamLogo=j).count(),
                    'expertsNumber': SubjectExpertsOpinionSheet.objects.filter(subject=i).count(),

                }

                lists.append(date)
                break
        lists = sorted(lists, key=lambda x: x['annualPlan'], reverse=True)
        return Response({"code": 0, "message": "ok", "detail": lists}, status.HTTP_200_OK)

    # 评审结果统计项目组指派详情/评估机构
    @action(detail=False, methods=['get'], url_path='statistical_group_details_show')
    def statistical_group_details_show(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies, assignWay='按组指派',
                                                handOverState=True)
        json_data = request.query_params.dict()
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "projectTeam": "projectTeam",
            'projectTeamLogo': "projectTeamLogo",

        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审结果统计项目组指派详情条件查询/评估机构
    @action(detail=False, methods=['post'], url_path='statistical_group_details_query')
    def statistical_group_details_query(self, request):
        agencies = request.user
        agencies_subject = self.queryset.filter(agencies=agencies, assignWay='按组指派',
                                                handOverState=True)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "projectTeam": "projectTeam",
            'projectTeamLogo': "projectTeamLogo",

            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "proposal": "opinion_sheet_subject__proposal",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审结果统计单项指派展示/评估机构
    @action(detail=False, methods=['get'], url_path='statistical_single_show')
    def statistical_single_show(self, request):
        agencies = request.user
        agencies_subject = self.queryset.order_by('-project__category__batch__created').filter(agencies=agencies,
                                                                                               assignWay='单项指派',
                                                                                               handOverState=True)
        serializers = self.get_serializer(agencies_subject, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 评审结果单项指派条件查询/评估机构
    @action(detail=False, methods=['post'], url_path='statistical_single_query')
    def statistical_single_query(self, request):
        agencies = request.user
        agencies_subject = self.queryset.order_by('-project__category__batch__created').filter(agencies=agencies,
                                                                                               assignWay='单项指派',
                                                                                               handOverState=True)
        json_data = request.data
        keys = {

            "planCategory": "project__category__planCategory",
            "proposal": "opinion_sheet_subject__proposal",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = agencies_subject.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 验收
    # 项目结题验收 结题验收审核列表查询查询 展示/
    @action(detail=False, methods=['post'], url_path='acceptance_to_view')
    def acceptance_to_view(self, request):
        agency = request.user
        queryset = self.queryset.filter(subjectState='验收审核', state='移交', subject_concluding__agency=agency,
                                        subject_concluding__concludingState="待审核")
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 结题验收审核退回/
    @action(detail=False, methods=['post'], url_path='acceptance_back_to')
    def acceptance_back_to(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        queryset.returnReason = request.data['returnReason']
        queryset.state = '审核退回'
        queryset.subjectState = '项目执行'
        queryset.concludingState = '审核退回'
        SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
            concludingState='审核退回')
        queryset.save()
        Process.objects.create(state='项目执行', subject=queryset)
        Process.objects.create(state='项目执行', subject=queryset, note='验收申请审核不通过', dynamic=True)
        send_template(name='验收申请退回', subject_id=queryset.id)

        return Response({'code': 0, 'message': "退回成功"}, status=status.HTTP_200_OK)

    # 项目结题验收 结题验收审核同意验收/分管人员
    @action(detail=False, methods=['post'], url_path='acceptance_agree')
    def acceptance_agree(self, request):
        expert_id = request.data['expertId']
        queryset = self.queryset.get(id=request.data['subjectId'])
        acceptance = SubjectConcluding.objects.filter(subject=queryset, concludingState='待审核').get().acceptance
        for k_id in expert_id:
            expert = Expert.objects.get(id=k_id)
            SubjectKExperts.objects.create(subject=queryset, expert=expert, acceptance=acceptance)
        queryset.reviewTime = request.data['reviewTime']
        queryset.state = '组织专家评审'
        queryset.save()
        SubjectConcluding.objects.filter(subject=queryset, concludingState='待审核', acceptance=acceptance).update(
            reviewTime=request.data['reviewTime'])
        return Response({'code': 0, 'message': "指派成功"}, status=status.HTTP_200_OK)

    # 项目结题验收  验收管理列表条件查询/分管员
    @action(detail=False, methods=['post'], url_path='acceptance_review_to_view')
    def acceptance_review_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(subjectState='验收审核', state='组织专家评审', subject_concluding__agency=agency,
                                        subject_concluding__concludingState="待审核")
        json_data = request.data
        keys = {
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "name": "subject_a_t__expert__name__contains",
            "company": "subject_a_t__expert__company__contains",
            "title": "subject_a_t__expert__title__name__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  评审管理展示/分管员
    @action(detail=False, methods=['get'], url_path='subject_choose_expert_show')
    def subject_choose_expert_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(id=subject_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  评审管理取消指派/分管员
    @action(detail=False, methods=['post'], url_path='acceptance_cancel_assigned')
    def acceptance_cancel_assigned(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        # 需要多加参数，才可以准确判断是哪些专家 验收申请书id
        # SubjectKExperts.objects.filter(subject=queryset, acceptance=request.data['acceptance']).delete()
        SubjectKExperts.objects.filter(subject=queryset).delete()
        queryset.state = '移交'
        queryset.reviewTime = None
        queryset.save()
        return Response({'code': 0, "message": '取消指派OK'}, status=status.HTTP_200_OK)

    # 项目结题验收  评审管理调整指派/分管员
    @action(detail=False, methods=['post'], url_path='acceptance_adjust_assigned')
    def acceptance_adjust_assigned(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        expert = request.data['expert']
        expert2 = request.data['expert2']
        review_time = request.data['reviewTime']
        queryset.reviewTime = review_time
        queryset.save()
        SubjectConcluding.objects.filter(subject=queryset, acceptance=request.data['acceptance']).update(
            reviewTime=request.data['reviewTime'])
        for i in expert:
            SubjectKExperts.objects.filter(subject=queryset, expert_id=i,
                                           acceptance=request.data['acceptance']).delete()
        for k_id in expert2:
            SubjectKExperts.objects.create(subject=queryset, expert_id=k_id, acceptance=request.data['acceptance'])
        return Response({'code': 0, "message": '调整指派ok'}, status=status.HTTP_200_OK)

    # 项目结题验收  评审
    @action(detail=False, methods=['post'], url_path='acceptance_review')
    def acceptance_review(self, request):
        user = request.user
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '验收通过':
            queryset.state = '分管员审核'
            queryset.returnReason = None
            queryset.results = '验收通过'
            queryset.save()
            ##fff

            acceptance = SubjectConcluding.objects.get(subject_id=request.data['subjectId'], concludingState='待审核',
                                                       agency=user).acceptance
            SubjectKExperts.objects.filter(subject_id=request.data['subjectId'], acceptance=acceptance).update(
                state=True)
            ##
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核',
                                             agency=user).update(handOverState=True, results='验收通过')
            return Response({'code': 0, "message": '验收通过'}, status=status.HTTP_200_OK)
        elif state == '补正资料':
            queryset.state = '补正资料'
            queryset.concludingState = '待提交'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核').update(
                concludingState='补正资料')
            Process.objects.create(state='验收审核', subject=queryset, note='验收资料退回补正，请完成资料补正并提交审批', dynamic=True)
            send_template(name='验收审核补正资料', subject_id=queryset.id)
            return Response({'code': 0, "message": '分管员 - 补正资料'}, status=status.HTTP_200_OK)
        elif state == '结题复核' \
                :
            if queryset.double == False:
                queryset.state = '分管员审核'
                queryset.returnReason = None
                queryset.results = '结题复核'
                queryset.save()
                ##fff
                acceptance = SubjectConcluding.objects.get(subject_id=request.data['subjectId'], concludingState='待审核',
                                                           agency=user).acceptance
                SubjectKExperts.objects.filter(subject_id=request.data['subjectId'], acceptance=acceptance).update(
                    state=True)
                ##
                SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核',
                                                 agency=user).update(handOverState=True, results='结题复核')
                return Response({'code': 0, "message": '结题复核'}, status=status.HTTP_200_OK)
            else:
                return Response({'code': 1, "message": '不允许第二次结题复核'}, status=status.HTTP_200_OK)
        elif state == '验收不通过':
            queryset.state = '分管员审核'
            queryset.returnReason = None
            queryset.results = '验收不通过'
            queryset.save()
            ##fff

            acceptance = SubjectConcluding.objects.get(subject_id=request.data['subjectId'], concludingState='待审核',
                                                       agency=user).acceptance
            SubjectKExperts.objects.filter(subject_id=request.data['subjectId'], acceptance=acceptance).update(
                state=True)
            ##
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待审核',
                                             agency=user).update(handOverState=True, results='验收不通过')
            return Response({'code': 2, "message": '验收不通过'}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 2, "message": None}, status=status.HTTP_200_OK)

    # 项目结题验收记录  评审
    @action(detail=False, methods=['post'], url_path='acceptance_record_to_view')
    def acceptance_record_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(subject_concluding__agency=agency, subject_concluding__handOverState=True)
        # queryset = self.queryset.filter()

        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  补正资料列表查询/分管员
    @action(detail=False, methods=['post'], url_path='acceptance_correction_to_view')
    def acceptance_correction_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(
            Q(subject_concluding__concludingState="待审核") | Q(subject_concluding__concludingState="补正资料"),
            subject_concluding__agency=agency, subjectState='验收审核', state='补正资料')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "concludingState": "concludingState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 终止2
    @action(detail=False, methods=['post'], url_path='termination_to_view')
    def termination_to_view(self, request):
        agency = request.user
        queryset = self.queryset.filter(subjectState='终止审核', state='移交', subject_termination__agency=agency,
                                        subject_termination__terminationState='待审核')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收 结题验收审核退回/2
    @action(detail=False, methods=['post'], url_path='termination_back_to')
    def termination_back_to(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        if queryset.stateLabel is False:
            queryset.returnReason = request.data['returnReason']
            queryset.state = '审核退回'
            queryset.subjectState = '项目执行'
            queryset.terminationState = '审核退回'
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                terminationState='审核退回')
            queryset.save()
            Process.objects.create(state='项目执行', subject=queryset)
            Process.objects.create(state='项目执行', subject=queryset, note='终止申请审核不通过', dynamic=True)
            send_template(name='终止申请退回', subject_id=queryset.id)

        else:
            queryset.returnReason = request.data['returnReason']
            queryset.state = '审核退回'
            queryset.subjectState = '逾期未结题'
            queryset.terminationState = '审核退回'
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                terminationState='审核退回')
            queryset.save()
            Process.objects.create(state='逾期未结题', subject=queryset, note='终止申请审核不通过', dynamic=True)
            send_template(name='终止申请退回', subject_id=queryset.id)
        return Response({'code': 0, 'message': "退回成功"}, status=status.HTTP_200_OK)

    # 项目结题验收 结题验收审核同意验收/分管人员2
    @action(detail=False, methods=['post'], url_path='termination_agree')
    def termination_agree(self, request):
        expert_id = request.data['expertId']
        queryset = self.queryset.get(id=request.data['subjectId'])
        termination = SubjectTermination.objects.filter(subject=queryset, terminationState='待审核').get().termination
        for k_id in expert_id:
            expert = Expert.objects.get(id=k_id)
            SubjectKExperts.objects.create(subject=queryset, expert=expert, termination=termination)
        queryset.reviewTime = request.data['reviewTime']
        queryset.state = '组织专家评审'
        queryset.save()
        SubjectTermination.objects.filter(subject=queryset, terminationState='待审核', termination=termination).update(
            reviewTime=request.data['reviewTime'])
        return Response({'code': 0, 'message': "指派成功"}, status=status.HTTP_200_OK)

    #  项目结题验收  验收管理列表条件查询/分管员
    @action(detail=False, methods=['post'], url_path='termination_review_to_view')
    def termination_review_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(subjectState='终止审核', state='组织专家评审', subject_termination__agency=agency,
                                        subject_termination__terminationState='待审核')
        json_data = request.data
        keys = {
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "name": "subject_a_t__expert__name__contains",
            "company": "subject_a_t__expert__company__contains",
            "title": "subject_a_t__expert__title__name__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收  评审管理取消指派/分管员
    @action(detail=False, methods=['post'], url_path='termination_cancel_assigned')
    def termination_cancel_assigned(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        # 需要多加参数，才可以准确判断是哪些专家 验收申请书id
        SubjectKExperts.objects.filter(subject=queryset, termination=request.data['termination']).delete()
        queryset.state = '移交'
        queryset.reviewTime = None
        queryset.save()
        return Response({'code': 0, "message": '取消指派OK'}, status=status.HTTP_200_OK)

    # 项目结题验收  评审管理调整指派/分管员
    @action(detail=False, methods=['post'], url_path='termination_adjust_assigned')
    def termination_adjust_assigned(self, request):
        queryset = self.queryset.get(id=request.data['subjectId'])
        expert = request.data['expert']
        expert2 = request.data['expert2']
        review_time = request.data['reviewTime']
        queryset.reviewTime = review_time
        queryset.save()
        SubjectTermination.objects.filter(subject=queryset, termination=request.data['termination']).update(
            reviewTime=review_time)
        for i in expert:
            SubjectKExperts.objects.filter(subject=queryset, expert_id=i,
                                           termination=request.data['termination']).delete()
        for k_id in expert2:
            SubjectKExperts.objects.create(subject=queryset, expert_id=k_id, termination=request.data['termination'])
        return Response({'code': 0, "message": '调整指派ok'}, status=status.HTTP_200_OK)

    # 项目结题验收  评审/分管员
    @action(detail=False, methods=['post'], url_path='termination_review')
    def termination_review(self, request):
        user = request.user
        state = request.data['state']
        queryset = self.queryset.get(id=request.data['subjectId'])
        if state == '终止通过':
            queryset.state = '分管员审核'
            queryset.returnReason = None
            queryset.results = '终止通过'
            queryset.save()
            # fff
            termination = SubjectTermination.objects.get(subject_id=request.data['subjectId'], terminationState='待审核',
                                                         agency=user).termination
            SubjectKExperts.objects.filter(subject_id=request.data['subjectId'], termination=termination).update(
                state=True)
            #
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核',
                                              agency=user).update(handOverState=True, results='终止通过')

            return Response({'code': 0, "message": '分管员 - 终止通过'}, status=status.HTTP_200_OK)
        elif state == '补正资料':
            queryset.state = '补正资料'
            queryset.terminationState = '待提交'
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核').update(
                terminationState='补正资料')
            Process.objects.create(state='终止审核', subject=queryset, note='终止资料退回补正，请完成资料补正并提交审批', dynamic=True)
            send_template(name='终止审核补正资料', subject_id=queryset.id)
            return Response({'code': 1, "message": '分管员 - 补正资料'}, status=status.HTTP_200_OK)
        elif state == '终止不通过':
            queryset.state = '分管员审核'
            queryset.results = '终止不通过'
            queryset.returnReason = None
            queryset.save()
            ##fff
            termination = SubjectTermination.objects.get(subject_id=request.data['subjectId'], terminationState='待审核',
                                                         agency=user).termination
            SubjectKExperts.objects.filter(subject_id=request.data['subjectId'], termination=termination).update(
                state=True)
            ###
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待审核',
                                              agency=user).update(handOverState=True, results='终止不通过')
            return Response({'code': 2, "message": '分管员 - 终止不通过'}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 3, "message": ' 取消'}, status=status.HTTP_200_OK)

    # 项目终止  补正资料列表查询/分管员
    @action(detail=False, methods=['post'], url_path='termination_correction_to_view')
    def termination_correction_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(
            Q(subject_termination__terminationState='待审核') | Q(subject_termination__terminationState='补正资料'),
            subject_termination__agency=agency, subjectState='终止审核', state='补正资料')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "terminationState": "terminationState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 项目结题验收记录  评审
    @action(detail=False, methods=['post'], url_path='termination_record_to_view')
    def termination_record_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.filter(subject_termination__agency=agency, subject_termination__handOverState=True)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)


class PGExpertsSubjectOpinionSheetViewSet(viewsets.ModelViewSet):
    queryset = SubjectExpertsOpinionSheet.objects.all()
    serializer_class = PGExpertsSubjectOpinionSheetSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 立项评审经费统计待导出展示/评估机构
    @action(detail=False, methods=['get'], url_path='funding_show')
    def funding_show(self, request):
        lists = []
        agencies = request.user
        agencies_subject = Subject.objects.order_by('-project__category__batch__created').filter(agencies=agencies,
                                                                                                 handOverState=True)
        for subject in agencies_subject:
            queryset = self.queryset.filter(subject=subject, )
            serializers = self.get_serializer(queryset, many=True)
            lists.extend(serializers.data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 立项评审经费统计待导出条件查询/评估机构
    @action(detail=False, methods=['post'], url_path='funding_query')
    def funding_query(self, request):
        lists = []
        agencies = request.user
        agencies_subject = Subject.objects.order_by('-project__category__batch__created').filter(agencies=agencies,
                                                                                                 handOverState=True)
        json_data = request.data

        keys = {
            "name": "pExperts__name__contains",
            "unitName": "subject__unitName__contains",
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        for subject in agencies_subject:
            instance = self.queryset.filter(subject=subject)
            queryset = instance.filter(**data)
            serializers = self.get_serializer(queryset, many=True)
            lists.extend(serializers.data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 立项评审经费统计导出/评估机构
    @action(detail=False, methods=['post'], url_path='export_data')
    def export_data(self, request):
        data = request.data['data']
        for i in data:
            queryset = self.queryset.get(id=i["id"])
            queryset.money = i["money"]
            queryset.save()
        return Response({"code": 0, "message": "保存成功"}, status=status.HTTP_200_OK)

    # 申请撤销评审意见列表展示/评估机构
    @action(detail=False, methods=['get'], url_path='undo')
    def undo(self, request):
        lists = []
        agencies = request.user
        subject_obj = Subject.objects.filter(Q(state='未评审') | Q(state='已评审'), agencies=agencies, subjectState='专家评审',
                                             handOverState=False)
        for subject in subject_obj:
            queryset = self.queryset.order_by('-declareTime').filter(
                Q(agenciesState='通过') | Q(agenciesState='待审核') | Q(agenciesState='未通过'),
                subject=subject)
            serializer = self.get_serializer(queryset, many=True)
            lists.extend(serializer.data)
        return Response({"codfunding_querye": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 申请撤销评审意见列表条件查询/评估机构
    @action(detail=False, methods=['post'], url_path='undo_query')
    def undo_query(self, request):
        lists = []
        agencies = request.user
        subject_obj = Subject.objects.filter(Q(state='未评审') | Q(state='已评审'), agencies=agencies, subjectState='专家评审',
                                             handOverState=False)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "subjectName": "subject__subjectName__contains",
            "head": "subject__head__contains",
            "unitName": "subject__unitName__contains",
            "name": "pExperts__experts__name__contains",
            "agenciesState": "agenciesState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        for subject in subject_obj:
            queryset = self.queryset.order_by('-declareTime').filter(
                Q(agenciesState='通过') | Q(agenciesState='待审核') | Q(agenciesState='未通过'),
                subject=subject)
            queryset_obj = queryset.filter(**data)
            serializer = self.get_serializer(queryset_obj, many=True)
            lists.extend(serializer.data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 申请撤销评审意见 评审展示/评估机构
    @action(detail=False, methods=['get'], url_path='undo_show')
    def undo_show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        pg_experts_id = request.query_params.dict().get('pExpertsId')
        queryset = self.queryset.filter(subject_id=subject_id, pExperts_id=pg_experts_id).first()
        attachment_pdf = queryset.expertOpinionSheet.attachmentPDF
        return Response({"code": 0, "message": "ok", "detail": attachment_pdf}, status=status.HTTP_201_CREATED)

    # 申请撤销评审意见 评审操作/评估机构
    @action(detail=False, methods=['post'], url_path='undo_operation')
    def undo_operation(self, request):
        agencies_state = request.data['agenciesState']
        pg_experts = request.data['pExpertsId']
        subject_id = request.data['subjectId']
        if agencies_state == "通过":
            subject_expert_opinion_sheet = self.queryset.get(subject_id=subject_id, pExperts_id=pg_experts)
            subject_expert_opinion_sheet.expertOpinionSheet.delete()
            subject_expert_opinion_sheet.expertOpinionSheet = None
            subject_expert_opinion_sheet.state = '待评审'
            subject_expert_opinion_sheet.agenciesState = '通过'
            subject_expert_opinion_sheet.isReview = False
            subject_expert_opinion_sheet.save()
            subject = Subject.objects.get(id=subject_id)
            subject.isEntry = 2
            subject.save()
        else:
            subject_expert_opinion_sheet = self.queryset.get(subject_id=subject_id, pExperts_id=pg_experts)
            subject_expert_opinion_sheet.agenciesState = '未通过'
            subject_expert_opinion_sheet.state = '撤销退回'
            subject_expert_opinion_sheet.save()
        return Response({"code": 0, "message": "操作成功"}, status=status.HTTP_200_OK)


# 评估机构评审单
class OpinionSheetViewSet(viewsets.ModelViewSet):
    queryset = OpinionSheet.objects.all()
    serializer_class = OpinionSheetSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 保存评审单
    def create(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        file = request.data['file']
        file_name = request.data['fileName']
        subject = Subject.objects.get(id=subject_id)
        if subject.opinion_sheet_subject.count() == 0:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            subject = Subject.objects.get(id=subject_id)
            opinion_sheet = self.queryset.get(id=serializer.data['id'])
            if request.data['reviewWay'] == '会评':
                opinion_sheet.attachment = OSS().put_by_backend(path=file_name, data=file.read())
                opinion_sheet.save()
                # ++++
                SubjectExpertsOpinionSheet.objects.filter(subject=subject, reviewWay="会评").update(
                    reviewTime=datetime.datetime.now(), state="完成评审")
            else:
                attachment_pdf = generate_review_single_pdf(opinion_sheet_id=serializer.data['id'])
                opinion_sheet.attachment = attachment_pdf
                opinion_sheet.save()
            opinion_sheet.subject = subject
            opinion_sheet.save()
            subject.state = '已评审'
            subject.save()
            headers = self.get_success_headers(serializer.data)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 展示评审单附件
    @action(detail=False, methods=['get'], url_path='show_attachment')
    def show_attachment(self, request):
        try:
            subject_id = request.query_params.dict().get('subjectId')
            queryset = self.queryset.get(subject_id=subject_id)
            return Response({"code": 0, "message": "ok", "detail": {"attachment": queryset.attachment}},
                            status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(False)

    # 展示评审单附件
    def retrieve(self, request, *args, **kwargs):
        try:
            queryset = self.queryset.get(subject_id=kwargs['pk'])
            return Response({"code": 0, "message": "ok", "detail": {"attachment": queryset.attachment}},
                            status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(False)


# 专家评审单
class PGOpinionSheetViewSet(viewsets.ModelViewSet):
    queryset = ExpertOpinionSheet.objects.all()
    serializer_class = PGOpinionSheetSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 评估机专家填写评审单
    def create(self, request, *args, **kwargs):
        pg_experts = request.user
        subject_id = request.data['subjectId']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        expert_opinion_sheet = self.queryset.get(id=serializer.data['id'])
        experts_review_single_pdf = generate_experts_review_single_pdf(expert_opinion_sheet_id=serializer.data['id'])
        expert_opinion_sheet.attachmentPDF = experts_review_single_pdf
        expert_opinion_sheet.save()
        subject_experts_opinion_sheet = SubjectExpertsOpinionSheet.objects.get(subject_id=subject_id,
                                                                               pExperts_id=pg_experts.id)
        subject_experts_opinion_sheet.expertOpinionSheet = expert_opinion_sheet
        subject_experts_opinion_sheet.state = '完成评审'
        # ++++
        subject_experts_opinion_sheet.reviewTime = datetime.datetime.now()
        #
        subject_experts_opinion_sheet.isReview = True
        subject_experts_opinion_sheet.save()
        headers = self.get_success_headers(serializer.data)
        if SubjectExpertsOpinionSheet.objects.filter(subject_id=subject_id, isReview=False).exists():
            subject = Subject.objects.get(id=subject_id)
            subject.isEntry = 2
            subject.save()
        else:
            subject = Subject.objects.get(id=subject_id)
            subject.isEntry = 3
            subject.save()
        return Response({"code": 0, "message": "提交成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                        headers=headers)

    # 评估机构查看专家组评审意见-pdf
    @action(detail=False, methods=['get'], url_path='group_show')
    def pg_experts_opinion_sheet_group_show(self, request):
        lists = []
        subject_id = request.query_params.dict().get('subjectId')
        subject = Subject.objects.get(id=subject_id)
        pg_group = SubjectExpertsOpinionSheet.objects.filter(subject=subject).values('expertOpinionSheet')
        for i in pg_group:
            if i['expertOpinionSheet']:
                instance = ExpertOpinionSheet.objects.get(id=i['expertOpinionSheet'])
                lists.append(instance.attachmentPDF)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)


class PGExpertsSystemViewSet(viewsets.ModelViewSet):
    queryset = SubjectExpertsOpinionSheet.objects.all()
    serializer_class = PGExpertsSystemSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 专家库首页
    # @action(detail=False, methods=['get'], url_path='to_do_task')
    # def to_do_task(self, request):
    #     experts = request.user
    #     queryset = self.queryset.filter(pExperts=experts, state='待评审',
    #                                     subject__project__category__batch__state='同意')
    #     project_approval_1 = [{"subjectId": i.subject.id, "annualPlan": i.subject.project.category.batch.annualPlan,
    #                            "planCategory": i.subject.project.category.planCategory,
    #                            "subjectName": i.subject.subjectName, "type": "立项评审"} for i in queryset]
    #     acceptance = SubjectKExperts.objects.filter(subject__subjectState='验收审核', expert=experts.expert)
    #     acceptance_approval_1 = [{"subjectId": i.subject.id, "annualPlan": i.subject.project.category.batch.annualPlan,
    #                               "planCategory": i.subject.project.category.planCategory,
    #                               "subjectName": i.subject.subjectName, "type": "验收审核"} for i in acceptance]
    #     termination = SubjectKExperts.objects.filter(subject__subjectState='终止审核', expert=experts.expert)
    #     termination_approval_1 = [{"subjectId": i.subject.id, "annualPlan": i.subject.project.category.batch.annualPlan,
    #                                "planCategory": i.subject.project.category.planCategory,
    #                                "subjectName": i.subject.subjectName, "type": "终止审核"} for i in termination]
    #
    #     project_approval = self.queryset.exclude(state='待评审').filter(pExperts=experts,
    #                                                                  subject__project__category__batch__state='同意').count()
    #
    #     acceptance_approval = SubjectKExperts.objects.exclude(acceptance=None).filter(
    #         Q(subject__subject_concluding__concludingState='验收通过') | Q(
    #             subject__subject_concluding__concludingState='验收不通过') | Q(
    #             subject__subject_concluding__concludingState='结题复核'), expert=experts.expert).distinct().count()
    #
    #     termination_approval = SubjectKExperts.objects.exclude(termination=None).filter(
    #         Q(subject__subject_termination__terminationState='项目终止') | Q(
    #             subject__subject_termination__terminationState='终止不通过'), expert=experts.expert).distinct().count()
    #     data = {"approval": project_approval_1 + acceptance_approval_1 + termination_approval_1,
    #             "projectApproval": project_approval,
    #             "acceptanceApproval": acceptance_approval,
    #             "terminationApproval": termination_approval,
    #             }
    #     return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    # 专家库首页
    @action(detail=False, methods=['get'], url_path='to_do_tasks')
    def to_do_tasks(self, request):
        experts = request.user
        queryset = self.queryset.filter(pExperts=experts, state='待评审',
                                        subject__project__category__batch__state='同意')
        project_approval = [{"subjectId": i.subject.id, "annualPlan": i.subject.project.category.batch.annualPlan,
                             "planCategory": i.subject.project.category.planCategory,
                             "subjectName": i.subject.subjectName, "type": "立项评审"} for i in queryset]

        # acceptance = SubjectKExperts.objects.filter(subject__subjectState='验收审核', expert=experts.expert)
        acceptance = SubjectKExperts.objects.filter(subject__subjectState='验收审核', expert=experts.expert, state=False)

        acceptance_approval = [{"subjectId": i.subject.id, "annualPlan": i.subject.project.category.batch.annualPlan,
                                "planCategory": i.subject.project.category.planCategory,
                                "subjectName": i.subject.subjectName, "type": "验收审核"} for i in acceptance]

        # termination = SubjectKExperts.objects.filter(subject__subjectState='终止审核', expert=experts.expert)
        termination = SubjectKExperts.objects.filter(subject__subjectState='终止审核', expert=experts.expert, state=False)
        termination_approval = [{"subjectId": i.subject.id, "annualPlan": i.subject.project.category.batch.annualPlan,
                                 "planCategory": i.subject.project.category.planCategory,
                                 "subjectName": i.subject.subjectName, "type": "终止审核"} for i in termination]
        return Response(
            {"code": 0, "message": "ok", "detail": project_approval + acceptance_approval + termination_approval},
            status=status.HTTP_200_OK)

    # 专家库首页
    @action(detail=False, methods=['get'], url_path='complete_task')
    def complete_task(self, request):
        experts = request.user
        project_approval = self.queryset.exclude(state='待评审'). \
            filter(pExperts=experts, subject__project__category__batch__state='同意').count()
        no_project_approval = self.queryset.filter(state='待评审', pExperts=experts, subject__project__category__batch__state='同意').count()

        # acceptance_approval = SubjectKExperts.objects.exclude(acceptance=None).filter(
        #     Q(subject__subject_concluding__concludingState='验收通过') | Q(
        #         subject__subject_concluding__concludingState='验收不通过') | Q(
        #         subject__subject_concluding__concludingState='结题复核'), expert=experts.expert).distinct().count()
        acceptance_approval = SubjectKExperts.objects.exclude(acceptance=None).filter(state=True,
                                                                                      expert=experts.expert).count()
        no_acceptance_approval = SubjectKExperts.objects.exclude(acceptance=None).filter(state=False, expert=experts.expert).count()


        # termination_approval = SubjectKExperts.objects.exclude(termination=None).filter(
        #     Q(subject__subject_termination__terminationState='项目终止') | Q(
        #         subject__subject_termination__terminationState='终止不通过'), expert=experts.expert).distinct().count()
        termination_approval = SubjectKExperts.objects.exclude(termination=None).filter(state=True,
                                                                                        expert=experts.expert).count()
        no_termination_approval = SubjectKExperts.objects.exclude(termination=None).filter(state=False,
                                                                                        expert=experts.expert).count()
        data = {
            "projectApproval": project_approval,
            "acceptanceApproval": acceptance_approval,
            "terminationApproval": termination_approval,
            "noProjectApproval": no_project_approval,
            "noAcceptanceApproval": no_acceptance_approval,
            "noTerminationApproval": no_termination_approval,

        }
        return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    # 专家待评审项目列表1
    @action(detail=False, methods=['get'], url_path='experts_subject_show')
    def experts_subject_show(self, request):
        experts = request.user
        queryset = self.queryset.filter(pExperts=experts, state='待评审', reviewWay='网评',
                                        subject__project__category__batch__state='同意')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 专家待评审项目列表条件查询1
    @action(detail=False, methods=['post'], url_path='experts_subject_query')
    def experts_subject_query(self, request):
        experts = request.user
        queryset = self.queryset.filter(pExperts=experts, state='待评审', reviewWay='网评',
                                        subject__project__category__batch__state='同意')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 专家待评审项目列表条件查询2
    @action(detail=False, methods=['post'], url_path='project_approval_to_view')
    def project_approval_to_view(self, request):
        limit = request.query_params.dict().get('limit', None)
        experts = request.user
        queryset = self.queryset.filter(pExperts=experts, state='待评审',
                                        subject__project__category__batch__state='同意')
        json_data = request.data
        keys = {
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
            "reviewWay": "reviewWay",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        page = self.paginate_queryset(instance)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 专家评审记录项目列表1
    @action(detail=False, methods=['get'], url_path='experts_subject_review_show')
    def experts_subject_review_show(self, request):
        experts = request.user
        queryset = self.queryset.exclude(state='待评审').filter(pExperts=experts, reviewWay='网评',
                                                             subject__project__category__batch__state='同意')
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 专家评审记录项目列表条件查询1
    @action(detail=False, methods=['post'], url_path='experts_subject_review_query')
    def experts_subject_review_query(self, request):
        experts = request.user
        queryset = self.queryset.exclude(state='待评审').filter(pExperts=experts, reviewWay='网评',
                                                             subject__project__category__batch__state='同意')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
            "proposal": "expertOpinionSheet__proposal",
            "state": "state",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 专家评审记录项目列表条件查询2
    @action(detail=False, methods=['post'], url_path='project_results_to_view')
    def project_results_to_view(self, request):
        limit = request.query_params.dict().get('limit', None)
        experts = request.user
        queryset = self.queryset.exclude(state='待评审').order_by("-reviewTime").filter(pExperts=experts,
                                                                                     subject__project__category__batch__state='同意')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        instance = queryset.filter(**data)
        page = self.paginate_queryset(instance)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 初始数据专家评审单 /专家/
    @action(detail=False, methods=['get'], url_path='experts_show_s')
    def experts_show_s(self, request):
        user = request.user
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subject_id=subject_id)
        for i in queryset:
            data = {
                "planCategory": i.subject.project.category.planCategory,
                "unitName": i.subject.unitName,
                "subjectName": i.subject.subjectName,
                "name": user.name,
                "unit": user.experts.unit,
            }
            return Response({"code": 0, "message": "ok", "detail": data}, status.HTTP_200_OK)

    # 初始数据专家评审单 /专家/
    @action(detail=False, methods=['get'], url_path='initial_show')
    def initial_show(self, request):
        user = request.user
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subject_id=subject_id)
        for i in queryset:
            data = {
                "planCategory": i.subject.project.category.planCategory,
                "unitName": i.subject.unitName,
                "subjectName": i.subject.subjectName,
                "name": user.expert.name,
                "unit": user.expert.company,
            }
            return Response({"code": 0, "message": "ok", "detail": data}, status.HTTP_200_OK)

    # 评估机构撤销评审/评估机构专家
    @action(detail=False, methods=['post'], url_path='pg_experts_undo')
    def pg_experts_undo(self, request):
        user = request.user
        subject = Subject.objects.get(id=request.data['subjectId'])
        if subject.handOverState == False:
            queryset = self.queryset.get(pExperts=user, subject=subject)
            queryset.state = '撤销审核'
            queryset.agenciesState = '待审核'
            queryset.declareTime = datetime.date.today()
            queryset.returnReason = request.data['returnReason']
            queryset.save()
            subject.save()
            return Response({'code': 0, 'message': '撤销审核 - ok'}, status.HTTP_200_OK)
        else:
            return Response({'code': 0, 'message': '撤销失败，该项目已被移回科技局'}, status.HTTP_200_OK)

    # 专家附件展示
    @action(detail=False, methods=['get'], url_path='attachmentPDF_show')
    def attachmentPDF_show(self, request):
        user = request.user
        subject = Subject.objects.get(id=request.query_params.dict().get('subjectId'))
        queryset = self.queryset.get(pExperts_id=user.id, subject=subject)
        return Response({'code': 0, 'message': 'ok', "detail": queryset.expertOpinionSheet.attachmentPDF},
                        status.HTTP_200_OK)


class SubjectKExpertsViewSet(viewsets.ModelViewSet):
    queryset = SubjectKExperts.objects.all()
    serializer_class = SubjectKExpertsSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 管理服务机构 专家展示
    @action(detail=False, methods=['post'], url_path='experts_to_view')
    def experts_to_view(self, request):
        subject_id = request.data['subjectId']
        id = request.data['id']
        if request.data['tag'] == "验收":
            queryset = self.queryset.filter(subject_id=subject_id, acceptance=id)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

        elif request.data['tag'] == "终止":
            queryset = self.queryset.filter(subject_id=subject_id, termination=id)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # # 管理服务机构验收评审经费
    # @action(detail=False, methods=['post'], url_path='acceptance_funding_statistical')
    # def acceptance_funding_statistical(self, request):
    #     lists = []
    #     agency = request.user
    #     agencies_subject = Subject.objects.filter(
    #         Q(subject_concluding__concludingState="结题复合") | Q(subject_concluding__concludingState="验收通过") | Q(
    #             subject_concluding__concludingState="验收不通过")).filter(subject_concluding__agency=agency,
    #                                                                  subject_concluding__handOverState=True).distinct()
    #     json_data = request.data
    #
    #     keys = {
    #         "annualPlan": "subject__project__category__batch__annualPlan",
    #         "planCategory": "subject__project__category__planCategory",
    #         "subjectName": "subject__subjectName__contains",
    #         "unitName": "subject__unitName__contains",
    #
    #     }
    #     data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
    #     for subject in agencies_subject:
    #         instance = self.queryset.exclude(acceptance=None).filter(subject=subject)
    #         queryset = instance.filter(**data)
    #         serializers = self.get_serializer(queryset, many=True)
    #         lists.extend(serializers.data)
    #     return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)
    #
    # 管理员验收评审经费
    @action(detail=False, methods=['post'], url_path='acceptance_funding_statistical')
    def acceptance_funding_statistical(self, request):
        lists = []
        page = int(request.query_params.dict().get('page'))
        limit = int(request.query_params.dict().get('limit'))
        agencies_subject = Subject.objects.filter(
            Q(subject_concluding__concludingState="结题复合") | Q(subject_concluding__concludingState="验收通过") | Q(
                subject_concluding__concludingState="验收不通过")).filter(subject_concluding__handOverState=True).distinct()
        json_data = request.data

        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        for subject in agencies_subject:
            instance = self.queryset.exclude(acceptance=None).filter(subject=subject)
            queryset = instance.filter(**data)
            serializers = self.get_serializer(queryset, many=True)
            lists.extend(serializers.data)
        list1 = lists
        if page == 1:
            lists = lists[0: limit]
        else:
            lists = lists[page*limit-limit: page*limit]

        return Response({"code": 0, "message": "ok", "detail": lists, "count": len(list1)}, status=status.HTTP_200_OK)

    # 管理员验收评审经费
    # @action(detail=False, methods=['post'], url_path='acceptance_funding_statistical_c')
    # def acceptance_funding_statistical_c(self, request):
    #     json_data = request.data
    #     keys = {
    #         "annualPlan": "subject__project__category__batch__annualPlan",
    #         "planCategory": "subject__project__category__planCategory",
    #         "subjectName": "subject__subjectName__contains",
    #         "unitName": "subject__unitName__contains",
    #
    #     }
    #     data = {keys[k]: v for k, v in json_data.items() if
    #             k in keys and json_data[k] != '全部' and json_data[k] != ''}
    #     instance = self.queryset.exclude(acceptance=None).filter(Q(subject__subject_concluding__concludingState="结题复合") | Q(subject__subject_concluding__concludingState="验收通过") | Q(
    #             subject__subject_concluding__concludingState="验收不通过")).filter(subject__subject_concluding__handOverState=True)
    #     queryset = instance.filter(**data)
    #     serializers = self.get_serializer(queryset, many=True)
    #     return Response({"code": 0, "message": "ok", "detail": serializers.data},
    #                     status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='money_data')
    def money_data(self, request):
        data = request.data['data']
        for i in data:
            queryset = self.queryset.get(id=i["id"])
            queryset.money = i["money"]
            queryset.save()
        return Response({"code": 0, "message": "保存成功"}, status=status.HTTP_200_OK)

    # 管理服务机构终止评审经费
    @action(detail=False, methods=['post'], url_path='termination_funding_statistical')
    def termination_funding_statistical(self, request):
        lists = []
        page = int(request.query_params.dict().get('page'))
        limit = int(request.query_params.dict().get('limit'))
        # agency = request.user
        # agencies_subject = Subject.objects.filter(
        #     Q(subject_termination__terminationState="项目终止") | Q(
        #         subject_termination__terminationState="终止不通过"),
        #     subject_termination__agency=agency,
        #     subject_termination__handOverState=True).distinct()
        agencies_subject = Subject.objects.filter(Q(subject_termination__terminationState="项目终止") |
                                                  Q(subject_termination__terminationState="终止不通过"),
                                                    subject_termination__handOverState=True).distinct()

        json_data = request.data

        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",

        }
        data = {keys[k]: v for k, v in json_data.items() if
                k in keys and json_data[k] != '全部' and json_data[k] != ''}
        for subject in agencies_subject:
            instance = self.queryset.exclude(termination=None).filter(subject=subject)
            queryset = instance.filter(**data)
            serializers = self.get_serializer(queryset, many=True)
            lists.extend(serializers.data)
        list1 = lists
        if page == 1:
            lists = lists[0: limit]
        else:
            lists = lists[page*limit-limit: page*limit]
        return Response({"code": 0, "message": "ok", "detail": lists, "count": len(list1)}, status=status.HTTP_200_OK)

    # 专家 验收 待评审
    @action(detail=False, methods=['post'], url_path='acceptance_audit_to_view')
    def acceptance_audit_to_view(self, request):
        user = request.user
        queryset = self.queryset.order_by('id', "subject__subject_concluding__reviewTime").filter(
            subject__subjectState='验收审核', expert=user.expert, state=False).distinct('id')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 专家 验收 已评审
    @action(detail=False, methods=['post'], url_path='acceptance_results_to_view')
    def acceptance_results_to_view(self, request):
        user = request.user
        # queryset = self.queryset.exclude(acceptance=None).filter(
        #     Q(subject__subject_concluding__concludingState='验收通过')
        #     | Q(subject__subject_concluding__concludingState='验收不通过')
        #     | Q(subject__subject_concluding__concludingState='结题复核'), expert=user.expert).distinct()
        queryset = self.queryset.exclude(acceptance=None).order_by('-id',
                                                                   '-subject__subject_concluding__reviewTime').filter(
            expert=user.expert, state=True).distinct('id')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 专家 终止 待评审
    @action(detail=False, methods=['post'], url_path='termination_audit_to_view')
    def termination_audit_to_view(self, request):
        user = request.user
        queryset = self.queryset.order_by("id", "subject__subject_termination__reviewTime").filter(
            subject__subjectState='终止审核', expert=user.expert, state=False).distinct('id')

        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 专家 终止 已评审
    @action(detail=False, methods=['post'], url_path='termination_results_to_view')
    def termination_results_to_view(self, request):
        user = request.user
        # queryset = self.queryset.exclude(termination=None).filter(
        #     Q(subject__subject_termination__terminationState='项目终止') | Q(
        #         subject__subject_termination__terminationState='终止不通过'), expert=user.expert).distinct()
        queryset = self.queryset.exclude(termination=None).order_by("id",
                                                                    "-subject__subject_termination__reviewTime").filter(
            expert=user.expert, state=True).distinct("id")

        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)


# 数据导出
class ExportDataViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializers

    # 专家 终止 已评审
    @action(detail=False, methods=['post'], url_path='export_data')
    def export_data(self, request):
        lists = []
        subject = Subject.objects.exclude(subjectState='待提交')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "subjectState": "subjectState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject_obj = subject.order_by('-project__category__batch__annualPlan').filter(**data)
        for i in subject_obj:
            subject_info = SubjectInfo.objects.filter(subjectId=i.id).first()
            funding_budget = FundingBudget.objects.filter(subjectId=i.id).first()
            data = {
                "annualPlan": i.project.category.batch.annualPlan,  # 年度啊
                "projectBatch": i.project.category.batch.projectBatch,  # 批次
                "planCategory": i.project.category.planCategory,  # 类别
                "projectName": i.project.projectName,  # 项目名称
                "subjectName": i.subjectName,  # 课题名称
                "unitName": i.unitName,  # 单位名称
                "head": i.head,  # 项目负责人
                "overallGoal": subject_info.overallGoal,  # 课题总体指标
                "startStopYear": i.startStopYear,  # 起止年限
                "assessmentIndicators": subject_info.assessmentIndicators,  # 考核指标
                "scienceFunding": funding_budget.scienceFunding / 10000 / 100,  # 申请科技经费（课题申报书中的申请科技经费）
                "unitSelfRaised": funding_budget.unitSelfRaised / 10000 / 100,  # 单位自筹（申请下立项--课题申报书中的单位自筹经费）
                # "otherFunding": funding_budget.otherFunding,  # 其他
                # "combined": funding_budget.combined,  # 经费合计
                "subjectState": i.subjectState,  # 项目状态
                "state": i.state
            }
            if OpinionSheet.objects.filter(subject=i).exists():
                a = {
                    "subjectScore": i.opinion_sheet_subject.get().subjectScore,  # 专家立项评分
                    "proposal": i.opinion_sheet_subject.get().proposal,  # 专家立项建议
                    "proposalFunding": i.opinion_sheet_subject.get().proposalFunding/ 10000 / 100,  # 专家建议经费
                }
                data["a"] = a
            else:
                a = {
                    "subjectScore": '-',  # 专家立项评分
                    "proposal": '-',  # 专家立项建议
                    "proposalFunding": '-',  # 专家建议经费
                }
                data["a"] = a
            if i.proposal:
                b = {
                    "scienceProposal": i.proposal.scienceProposal,  # 科技局立项建议
                    "scienceFunding": i.proposal.scienceFunding/ 10000 / 100,  # 科技局建议经费
                    # "firstFunding": i.proposal.firstFunding,  # 首笔经费
                }
                data["b"] = b
            else:
                b = {
                    "scienceProposal": '-',  # 立项建议
                    "scienceFunding": 0,  # 建议经费
                    # "firstFunding": 0,  # 首笔经费
                }
                data["b"] = b
            if i.contract_subject.exists() and i.contract_subject.get().contractState == '通过':
                contract_content = ContractContent.objects.get(id=i.contract_subject.get().contractContent)

                c = {
                    "executionTime": i.executionTime,  # 执行时间
                    "contractNo": i.contract_subject.get().contractNo,  # 合同编号
                    "scienceFunding": Decimal(contract_content.combined[0]['scienceFunding']) / 10000 / 100,  # 立项科研经费（合同里的科研经费）
                    "unitRaiseFunds": Decimal(contract_content.combined[0]['unitRaiseFunds']) / 10000 / 100   # 单位自筹经费（合同里的单位自筹）

                }
                data["c"] = c
            else:
                c = {
                    "executionTime": '-',  # 执行时间
                    "contractNo": '-',  # 合同编号
                    "unitRaiseFunds": '-',
                    "scienceFunding": '-',
                }
                data["c"] = c
            if i.contract_subject.exists():
                if GrantSubject.objects.filter(state='通过', subject=i).exists():
                    had_allocated = sum(
                        [j['money'] for j in GrantSubject.objects.filter(state='通过', subject=i).values('money')])
                    d = {
                        "had_allocated": had_allocated / 10000 / 100 # 已拨付
                    }
                    data["d"] = d
                    if i.subjectState in ['验收不通过', '项目终止', '逾期未结题'] and i.contract_subject.get().approvalMoney > had_allocated:
                        e = {
                            "dishonest_money": (i.contract_subject.get().approvalMoney - had_allocated)/ 10000 / 100  # 失信
                        }
                        data["e"] = e
                        f = {
                            "no_allocated": 0
                        }
                        data["f"] = f
                    else:
                        e = {
                            "dishonest_money": 0  # 失信
                        }
                        data["e"] = e
                        if i.contract_subject.get().approvalMoney < had_allocated:
                            f = {
                                "no_allocated": 0
                            }
                            data["f"] = f
                        else:
                            f = {
                                "no_allocated": (i.contract_subject.get().approvalMoney - had_allocated)/ 10000 / 100
                            }
                            data["f"] = f
                else:
                    d = {
                        "had_allocated": 0  # 已拨付
                    }
                    data["d"] = d
                    if i.subjectState in ['验收不通过', '项目终止', '逾期未结题']:
                        e = {
                            "dishonest_money": i.contract_subject.get().approvalMoney/ 10000 / 100  # 失信
                        }
                        data["e"] = e
                        f = {
                            "no_allocated": 0
                        }
                        data["f"] = f
                    else:
                        e = {
                            "dishonest_money": 0  # 失信
                        }
                        data["e"] = e
                        f = {
                            "no_allocated": i.contract_subject.get().approvalMoney/ 10000 / 100
                        }
                        data["f"] = f
            else:
                d = {
                    "had_allocated": 0,  # 已拨付
                }
                e = {
                    "dishonest_money": 0  # 失信
                }
                f = {
                    "no_allocated": 0
                }
                data["d"] = d
                data["e"] = e
                data["f"] = f

            if i.subjectState == '验收通过':
                acceptance = SubjectConcluding.objects.get(concludingState='验收通过', subject=i).acceptance
                output = Output.objects.get(acceptance=acceptance)
                aa = {
                    "importedTechnology": output.importedTechnology,  # 引进技术
                    "applicationTechnology": output.applicationTechnology,  # 集成应用技术
                    "scientificTechnologicalAchievementsTransformed": output.scientificTechnologicalAchievementsTransformed,
                    # 科技成果转化
                    "technicalTrading": output.technicalTrading  / 10000 / 100,  # 技术交易
                    "newIndustrialProducts": output.newIndustrialProducts,  # 工业新产品
                    "newAgriculturalVariety": output.newAgriculturalVariety,  # 农业新品种
                    "newProcess": output.newProcess,  # 新工艺
                    "newMaterial": output.newMaterial,  # 新材料
                    "newDevice": output.newDevice,  # 新装置
                    "cs": output.cs,  # 申请登记计算机软件
                    "researchPlatform": output.researchPlatform,  # 研发平台
                    "TS": output.TS,  # 科技信息服务平台
                    "pilotStudies": output.pilotStudies,  # 示范点
                    "pilotLine": output.pilotLine,  # 中试线
                    "productionLine": output.productionLine,  # 生产线
                    "experimentalBase": output.experimentalBase,  # 试验基地
                    "applyInventionPatent": output.applyInventionPatent,  # 申请专利 -发明专利
                    "applyUtilityModel": output.applyUtilityModel,  # 申请专利 -实用新型
                    "authorizedInventionPatent": output.authorizedInventionPatent,  # 授权专利-发明专利
                    "authorizedUtilityModel": output.authorizedUtilityModel,  # 授权专利-实用新型
                    "internationalStandard": output.internationalStandard,  # 国际标准
                    "nationalStandard": output.nationalStandard,  # 国家标准
                    "industryStandard": output.industryStandard,  # 行业标准
                    "localStandards": output.localStandards,  # 地方标准
                    "enterpriseStandard": output.enterpriseStandard,  # 企业标准
                    "generalJournal": output.generalJournal,  # 一般期刊

                    "coreJournals": output.coreJournals,  # 核心期刊
                    "highLevelJournal": output.highLevelJournal,  # 高水平期刊
                    "postdoctoralTraining": output.postdoctoralTraining,  # 培养博士后
                    "trainingDoctors": output.trainingDoctors,  # 培养博士
                    "trainingMaster": output.trainingMaster,  # 培养硕士
                    "monographs": output.monographs,  # 专著
                    "academicReport": output.academicReport,  # 学术报告
                    "trainingCourses": output.trainingCourses,  # 举办培训班
                    "trainingNumber": output.trainingNumber,  # 参加培训人数
                    "salesRevenue": output.salesRevenue / 10000 / 100,  # 直接经济效益-新增销售收入
                    "newProduction": output.newProduction / 10000 / 100,  # 直接经济效益-新增产值、
                    "newTax": output.newTax / 10000 / 100,  # 直接经济效益-新增税收
                    "export": output.export / 10000 / 100,  # 直接经济效益-出口创汇
                    "salesRevenue2": output.salesRevenue2 / 10000 / 100,  # 间接经济效益-新增销售收入
                    "newProduction2": output.newProduction2 / 10000 / 100,  # 间接经济效益-新增产值、
                    "newTax2": output.newTax2 / 10000 / 100,  # 间接经济效益-新增税收
                    "export2": output.export2/10000 / 100,  # 间接经济效益-出口创汇

                }
                data["aa"] = aa
            else:
                aa = {
                    "importedTechnology": '-',  # 引进技术
                    "applicationTechnology": '-',  # 集成应用技术
                    "scientificTechnologicalAchievementsTransformed": '-',  # 科技成果转化
                    "technicalTrading": '-',
                    "newIndustrialProducts": '-',  # 工业新产品
                    "newAgriculturalVariety": '-',  # 农业新品种
                    "newProcess": '-',  # 新工艺
                    "newMaterial": '-',  # 新材料
                    "newDevice": '-',  # 新装置
                    "cs": '-',  # 申请登记计算机软件
                    "researchPlatform": '-',  # 研发平台
                    "TS": '-',  # 科技信息服务平台
                    "pilotStudies": '-',  # 示范点
                    "pilotLine": '-',  # 中试线
                    "productionLine": '-',  # 生产线
                    "experimentalBase": '-',  # 试验基地
                    "applyInventionPatent": '-',  # 申请专利 -发明专利
                    "applyUtilityModel": '-',  # 申请专利 -实用新型
                    "authorizedInventionPatent": '-',  # 授权专利-发明专利
                    "authorizedUtilityModel": '-',  # 授权专利-实用新型
                    "internationalStandard": '-',  # 国际标准
                    "nationalStandard": '-',  # 国家标准
                    "industryStandard": '-',  # 行业标准
                    "localStandards": '-',  # 地方标准
                    "enterpriseStandard": '-',  # 企业标准
                    "generalJournal": '-',  # 一般期刊

                    "coreJournals": '-',  # 核心期刊
                    "highLevelJournal": '-',  # 高水平期刊
                    "postdoctoralTraining": '-',  # 培养博士后
                    "trainingDoctors": '-',  # 培养博士
                    "trainingMaster": '-',  # 培养硕士
                    "monographs": '-',  # 专著
                    "academicReport": '-',  # 学术报告
                    "trainingCourses": '-',  # 举办培训班
                    "trainingNumber": '-',  # 参加培训人数
                    "salesRevenue": '-',  # 直接经济效益-新增销售收入
                    "newProduction": '-',  # 直接经济效益-新增产值、
                    "newTax": '-',  # 直接经济效益-新增税收
                    "export": '-',  # 直接经济效益-出口创汇
                    "salesRevenue2": '-',  # 间接经济效益-新增销售收入
                    "newProduction2": '-',  # 间接经济效益-新增产值、
                    "newTax2": '-',  # 间接经济效益-新增税收
                    "export2": '-',  # 间接经济效益-出口创汇

                }
                data["aa"] = aa
            lists.append(data)
        return Response({"code": 0, "message": "请求成功", "detail": lists}, status=status.HTTP_200_OK)

    # 专家 终止 已评审
    @action(detail=False, methods=['post'], url_path='export_operation')
    def export_operation(self, request):
        lists = []
        subject = Subject.objects.exclude(subjectState='待提交')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "projectBatch": "project__category__batch__projectBatch",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName",
            "subjectName": "subjectName__contains",
            "unitName": "unitName__contains",
            "head": "head__contains",
            "subjectState": "subjectState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject_obj = subject.filter(**data)
        for i in subject_obj:
            subject_info = SubjectInfo.objects.filter(subjectId=i.id).first()
            funding_budget = FundingBudget.objects.filter(subjectId=i.id).first()
            data = {
                "annualPlan": i.project.category.batch.annualPlan,  # 年度啊
                "projectBatch": i.project.category.batch.projectBatch,  # 批次
                "planCategory": i.project.category.planCategory,  # 类别
                "projectName": i.project.projectName,  # 项目名称
                "subjectName": i.subjectName,  # 课题名称
                "unitName": i.unitName,  # 单位名称
                "head": i.head,  # 项目负责人
                "overallGoal": subject_info.overallGoal,  # 课题总体指标
                "startStopYear": i.startStopYear,  # 起止年限
                "assessmentIndicators": subject_info.assessmentIndicators,  # 考核指标
                "scienceFunding": funding_budget.scienceFunding / 10000 / 100,  # 申请科技经费（课题申报书中的申请科技经费）
                "unitSelfRaised": funding_budget.unitSelfRaised / 10000 / 100,  # 单位自筹（申请下立项--课题申报书中的单位自筹经费）
                # "otherFunding": funding_budget.otherFunding,  # 其他
                # "combined": funding_budget.combined,  # 经费合计
                "subjectState": i.subjectState,  # 项目状态
            }
            if OpinionSheet.objects.filter(subject=i).exists():
                a = {
                    "subjectScore": i.opinion_sheet_subject.get().subjectScore,  # 专家立项评分
                    "proposal": i.opinion_sheet_subject.get().proposal,  # 专家立项建议
                    "proposalFunding": i.opinion_sheet_subject.get().proposalFunding / 10000 / 100,  # 专家建议经费
                }
                data["a"] = a
            else:
                a = {
                    "subjectScore": '-',  # 专家立项评分
                    "proposal": '-',  # 专家立项建议
                    "proposalFunding": '-',  # 专家建议经费
                }
                data["a"] = a
            if i.proposal:
                b = {
                    "scienceProposal": i.proposal.scienceProposal,  # 科技局立项建议
                    "scienceFunding": i.proposal.scienceFunding / 10000 / 100,  # 科技局建议经费
                    # "firstFunding": i.proposal.firstFunding,  # 首笔经费
                }
                data["b"] = b
            else:
                b = {
                    "scienceProposal": '-',  # 立项建议
                    "scienceFunding": 0,  # 建议经费
                    # "firstFunding": 0,  # 首笔经费
                }
                data["b"] = b
            if i.contract_subject.exists() and i.contract_subject.get().contractState == '通过':
                contract_content = ContractContent.objects.get(id=i.contract_subject.get().contractContent)

                c = {
                    "executionTime": i.executionTime,  # 执行时间
                    "contractNo": i.contract_subject.get().contractNo,  # 合同编号
                    "scienceFunding": Decimal(contract_content.combined[0]['scienceFunding']) / 10000 / 100,  # 立项科研经费（合同里的科研经费）
                    "unitRaiseFunds": Decimal(contract_content.combined[0]['unitRaiseFunds']) / 10000 / 100  # 单位自筹经费（合同里的单位自筹）

                }
                data["c"] = c
            else:
                c = {
                    "executionTime": '-',  # 执行时间
                    "contractNo": '-',  # 合同编号
                    "unitRaiseFunds": '-',
                    "scienceFunding": '-',
                }
                data["c"] = c
            if i.contract_subject.exists():
                if GrantSubject.objects.filter(state='通过', subject=i).exists():
                    had_allocated = sum(
                        [j['money'] for j in GrantSubject.objects.filter(state='通过', subject=i).values('money')])
                    d = {
                        "had_allocated": had_allocated / 10000 / 100 # 已拨付
                    }
                    data["d"] = d
                    if i.subjectState in ['验收不通过', '项目终止', '逾期未结题'] and i.contract_subject.get().approvalMoney > had_allocated:
                        e = {
                            "dishonest_money": (i.contract_subject.get().approvalMoney - had_allocated)/ 10000 / 100  # 失信
                        }
                        data["e"] = e
                        f = {
                            "no_allocated": 0
                        }
                        data["f"] = f
                    else:
                        e = {
                            "dishonest_money": 0  # 失信
                        }
                        data["e"] = e
                        if i.contract_subject.get().approvalMoney < had_allocated:
                            f = {
                                "no_allocated": 0
                            }
                            data["f"] = f
                        else:
                            f = {
                                "no_allocated": (i.contract_subject.get().approvalMoney - had_allocated)/ 10000 / 100
                            }
                            data["f"] = f
                else:
                    d = {
                        "had_allocated": 0  # 已拨付
                    }
                    data["d"] = d
                    if i.subjectState in ['验收不通过', '项目终止', '逾期未结题']:
                        e = {
                            "dishonest_money": i.contract_subject.get().approvalMoney / 10000 / 100 # 失信
                        }
                        data["e"] = e
                        f = {
                            "no_allocated": 0
                        }
                        data["f"] = f
                    else:
                        e = {
                            "dishonest_money": 0  # 失信
                        }
                        data["e"] = e
                        f = {
                            "no_allocated": i.contract_subject.get().approvalMoney/ 10000 / 100
                        }
                        data["f"] = f
            else:
                d = {
                    "had_allocated": 0,  # 已拨付
                }
                e = {
                    "dishonest_money": 0  # 失信
                }
                f = {
                    "no_allocated": 0
                }
                data["d"] = d
                data["e"] = e
                data["f"] = f

            if i.subjectState == '验收通过':
                acceptance = SubjectConcluding.objects.get(concludingState='验收通过', subject=i).acceptance
                output = Output.objects.get(acceptance=acceptance)
                aa = {
                    "importedTechnology": output.importedTechnology,  # 引进技术
                    "applicationTechnology": output.applicationTechnology,  # 集成应用技术
                    "scientificTechnologicalAchievementsTransformed": output.scientificTechnologicalAchievementsTransformed,
                    # 科技成果转化
                    "technicalTrading": output.technicalTrading / 10000 / 100,  # 技术交易
                    "newIndustrialProducts": output.newIndustrialProducts,  # 工业新产品
                    "newAgriculturalVariety": output.newAgriculturalVariety,  # 农业新品种
                    "newProcess": output.newProcess,  # 新工艺
                    "newMaterial": output.newMaterial,  # 新材料
                    "newDevice": output.newDevice,  # 新装置
                    "cs": output.cs,  # 申请登记计算机软件
                    "researchPlatform": output.researchPlatform,  # 研发平台
                    "TS": output.TS,  # 科技信息服务平台
                    "pilotStudies": output.pilotStudies,  # 示范点
                    "pilotLine": output.pilotLine,  # 中试线
                    "productionLine": output.productionLine,  # 生产线
                    "experimentalBase": output.experimentalBase,  # 试验基地
                    "applyInventionPatent": output.applyInventionPatent,  # 申请专利 -发明专利
                    "applyUtilityModel": output.applyUtilityModel,  # 申请专利 -实用新型
                    "authorizedInventionPatent": output.authorizedInventionPatent,  # 授权专利-发明专利
                    "authorizedUtilityModel": output.authorizedUtilityModel,  # 授权专利-实用新型
                    "internationalStandard": output.internationalStandard,  # 国际标准
                    "nationalStandard": output.nationalStandard,  # 国家标准
                    "industryStandard": output.industryStandard,  # 行业标准
                    "localStandards": output.localStandards,  # 地方标准
                    "enterpriseStandard": output.enterpriseStandard,  # 企业标准
                    "generalJournal": output.generalJournal,  # 一般期刊

                    "coreJournals": output.coreJournals,  # 核心期刊
                    "highLevelJournal": output.highLevelJournal,  # 高水平期刊
                    "postdoctoralTraining": output.postdoctoralTraining,  # 培养博士后
                    "trainingDoctors": output.trainingDoctors,  # 培养博士
                    "trainingMaster": output.trainingMaster,  # 培养硕士
                    "monographs": output.monographs,  # 专著
                    "academicReport": output.academicReport,  # 学术报告
                    "trainingCourses": output.trainingCourses,  # 举办培训班
                    "trainingNumber": output.trainingNumber,  # 参加培训人数
                    "salesRevenue": output.salesRevenue / 10000 / 100,  # 直接经济效益-新增销售收入
                    "newProduction": output.newProduction / 10000 / 100,  # 直接经济效益-新增产值、
                    "newTax": output.newTax / 10000 / 100,  # 直接经济效益-新增税收
                    "export": output.export/ 10000 / 100,  # 直接经济效益-出口创汇
                    "salesRevenue2": output.salesRevenue2 / 10000 / 100,  # 间接经济效益-新增销售收入
                    "newProduction2": output.newProduction2 / 10000 / 100,  # 间接经济效益-新增产值、
                    "newTax2": output.newTax2/ 10000 / 100,  # 间接经济效益-新增税收
                    "export2": output.export2/ 10000/100,  # 间接经济效益-出口创汇

                }
                data["aa"] = aa
            else:
                aa = {
                    "importedTechnology": '-',  # 引进技术
                    "applicationTechnology": '-',  # 集成应用技术
                    "scientificTechnologicalAchievementsTransformed": '-',  # 科技成果转化
                    "technicalTrading": '-',
                    "newIndustrialProducts": '-',  # 工业新产品
                    "newAgriculturalVariety": '-',  # 农业新品种
                    "newProcess": '-',  # 新工艺
                    "newMaterial": '-',  # 新材料
                    "newDevice": '-',  # 新装置
                    "cs": '-',  # 申请登记计算机软件
                    "researchPlatform": '-',  # 技术研发平台
                    "TS": '-',  # 科技信息服务平台
                    "pilotStudies": '-',  # 示范点
                    "pilotLine": '-',  # 中试线
                    "productionLine": '-',  # 生产线
                    "experimentalBase": '-',  # 试验基地
                    "applyInventionPatent": '-',  # 申请专利 -发明专利
                    "applyUtilityModel": '-',  # 申请专利 -实用新型
                    "authorizedInventionPatent": '-',  # 授权专利-发明专利
                    "authorizedUtilityModel": '-',  # 授权专利-实用新型
                    "internationalStandard": '-',  # 国际标准
                    "nationalStandard": '-',  # 国家标准
                    "industryStandard": '-',  # 行业标准
                    "localStandards": '-',  # 地方标准
                    "enterpriseStandard": '-',  # 企业标准
                    "generalJournal": '-',  # 一般期刊

                    "coreJournals": '-',  # 核心期刊
                    "highLevelJournal": '-',  # 高水平期刊
                    "postdoctoralTraining": '-',  # 培养博士后
                    "trainingDoctors": '-',  # 培养博士
                    "trainingMaster": '-',  # 培养硕士
                    "monographs": '-',  # 专著
                    "academicReport": '-',  # 学术报告
                    "trainingCourses": '-',  # 举办培训班
                    "trainingNumber": '-',  # 参加培训人数
                    "salesRevenue": '-',  # 直接经济效益-新增销售收入
                    "newProduction": '-',  # 直接经济效益-新增产值、
                    "newTax": '-',  # 直接经济效益-新增税收
                    "export": '-',  # 直接经济效益-出口创汇
                    "salesRevenue2": '-',  # 间接经济效益-新增销售收入
                    "newProduction2": '-',  # 间接经济效益-新增产值、
                    "newTax2": '-',  # 间接经济效益-新增税收
                    "export2": '-',  # 间接经济效益-出口创汇

                }
                data["aa"] = aa
            lists.append(data)
        path = Excel_data(lists)
        # n = datetime.date.today()
        # n = '测试'
        # with open(path, 'rb') as p:
        #     file_bytes = p.read()
        #     f = BytesIO()
        #     f.write(file_bytes)
        # response = HttpResponse(
        #     content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        # name = 'attachment; filename={0}.xlsx'.format(n)
        # response['Content-Disposition'] = name.encode("utf-8")
        # response["Access-Control-Expose-Headers"] = "Content-Disposition"
        # response.write(f.getvalue())
        # print(response)
        # return response

        path = OSS().put_pdfPath(path=path)
        return Response({"code": 0, "message": "导出成功", "detail": path}, status=status.HTTP_200_OK)
