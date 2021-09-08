from django.db.models import Q
from django.shortcuts import render

# Create your views here.
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_mongoengine import viewsets as mongodb_viewsets

from change.models import ChangeSubject
from concluding.models import SubjectConcluding
from subject.models import Subject, Attachment, Process
from termination.models import Termination, TResearchers, TOutput, TCheckList, TExpenditureStatement, \
    TerminationAttachment, TReport, TKOpinionSheet, SubjectTermination, ChargeTermination, TerminationOpinion
from termination.serializers import TerminationSerializers, TResearchersSerializers, TOutputSerializers, \
    TCheckListSerializers, TReportSerializers, TExpenditureStatementSerializers, \
    TerminationAttachmentSerializers, TKOpinionSheetSerializers, SubjectTerminationSerializers, \
    ChargeTerminationSerializers, TerminationOpinionSerializers
from tpl.views_download import generate_termination_pdf
from utils.oss import OSS


class SubjectTerminationViewSet(mongodb_viewsets.ModelViewSet):
    queryset = SubjectTermination.objects.all()
    serializer_class = SubjectTerminationSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 评估机构
    # 项目结题验收记录  评审
    @action(detail=False, methods=['post'], url_path='termination_record_to_view')
    def termination_record_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by("-reviewTime").filter(agency=agency, handOverState=True)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
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

    # 可申请终止项目 展示/单位
    @action(detail=False, methods=['get'], url_path='subject_show')
    def subject_show(self, request, *args, **kwargs):
        enterprise = request.user
        subject_obj = Subject.objects.exclude(terminationState='分管员发起').filter(
            Q(subjectState='项目执行') | Q(subjectState='逾期未结题') | Q(subjectState='结题复核'),
            enterprise=enterprise)
        lists = [{"id": i.id,
                  "annualPlan": i.project.category.batch.annualPlan,
                  "planCategory": i.project.category.planCategory, "projectName": i.project.projectName,
                  "contractNo": i.contract_subject.values('contractNo'), "subjectName": i.subjectName,
                  "unitName": i.unitName, "head": i.head,
                  "executionTime": i.executionTime, } for i in subject_obj if self.queryset.filter(
            subject=i).count() == 0 or self.queryset.exclude(
            Q(terminationState='终止不通过') | Q(terminationState='项目终止')).filter(subject=i).count() == 0]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 可申请终止项目 查询/单位
    @action(detail=False, methods=['post'], url_path='subject_query')
    def subject_query(self, request, *args, **kwargs):
        enterprise = request.user
        subject_obj = Subject.objects.exclude(terminationState='分管员发起').filter(
            Q(subjectState='项目执行') | Q(subjectState='逾期未结题'),
            enterprise=enterprise)
        json_data = request.data
        keys = {

            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName__contains",
            "subjectName": "subjectName__contains",
            "contractNo": "contract_subject__contractNo__contains",
            "head": "head__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = subject_obj.filter(**data)
        lists = [{"id": i.id,
                  "annualPlan": i.project.category.batch.annualPlan,
                  "planCategory": i.project.category.planCategory, "projectName": i.project.projectName,
                  "contractNo": i.contract_subject.values('contractNo'), "subjectName": i.subjectName,
                  "unitName": i.unitName, "head": i.head,
                  "executionTime": i.executionTime, } for i in queryset if self.queryset.filter(
            subject=i).count() == 0 or self.queryset.exclude(
            Q(terminationState='终止不通过') | Q(terminationState='项目终止')).count() == 0]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 申请终止项目 检测/单位
    @action(detail=False, methods=['post'], url_path='detection')
    def detection(self, request, *args, **kwargs):
        subject = Subject.objects.get(id=request.data['subjectId'])
        if ChangeSubject.objects.filter(subject=subject, state='审核中').exists():
            return Response({'code': 1, 'message': '该项目有未完成审批的变更申请，无法终止项目'}, status=status.HTTP_200_OK)
        if ChangeSubject.objects.filter(subject=subject, state='通过', isUpload=False).exists():
            return Response({'code': 2, 'message': '请上传该项目的变更申请表附件'}, status=status.HTTP_200_OK)
        if SubjectConcluding.objects.filter(Q(concludingState='待提交') | Q(concludingState='审核退回'),
                                            subject=subject).exists():
            return Response({'code': 3, 'message': '当前项目已申请验收，请删除记录后再申请终止'}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 0, 'message': 'ok'}, status=status.HTTP_200_OK)

    # 申请终止项目信息列表/单位
    @action(detail=False, methods=['get'], url_path='t_unit_show')
    def t_unit_show(self, request):
        enterprise = request.user
        queryset = self.queryset.filter(subject__enterprise=enterprise)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 申请终止项目信息列表条件查询/单位
    @action(detail=False, methods=['post'], url_path='t_unit_query')
    def t_unit_query(self, request):
        enterprise = request.user
        queryset = self.queryset.filter(subject__enterprise=enterprise)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName",
            "subjectName": "subject__subjectName__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
            "head": "subject__head__contains",
            "terminationState": "terminationState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 展示当前课题下所有终止资料
    @action(detail=False, methods=['get'], url_path='show_list')
    def show_list(self, request):
        lists = []
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.exclude(termination=None).filter(
            Q(terminationState='终止不通过') | Q(terminationState='项目终止'), subject_id=subject_id)
        serializers = self.get_serializer(queryset, many=True)
        lists.append(serializers.data)
        if ChargeTermination.objects.filter(subject=subject_id, state='项目终止').exists():
            charge_termination = ChargeTermination.objects.filter(subject=subject_id, state='项目终止').get().id
            return Response({"code": 0, "message": "ok", "detail": {"unit": lists, "charge": charge_termination}},
                            status=status.HTTP_201_CREATED)
        return Response({"code": 0, "message": "ok", "detail": {"unit": lists}},
                        status=status.HTTP_201_CREATED)

    # 项目申报PDF展示
    @action(detail=False, methods=['get'], url_path='show_pdf')
    def show_pdf(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        termination_id = request.query_params.dict().get('terminationId')
        types = request.query_params.dict().get('types')
        queryset = self.queryset.get(subject_id=subject_id, termination=termination_id)
        if queryset.attachmentPDF:
            return Response({'code': 0, 'message': 'ok ', "detail": queryset.attachmentPDF},
                            status=status.HTTP_200_OK)
        else:
            try:
                lists = Attachment.objects.filter(subject=subject_id, types=types).values('attachmentPath')
                return Response({'code': 0, 'message': 'ok ', "detail": lists}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'code': 1, 'message': '没有数据'}, status=status.HTTP_200_OK)


# 申请终止项目信息列表
class TerminationViewSet(mongodb_viewsets.ModelViewSet):
    queryset = Termination.objects.all()
    serializer_class = TerminationSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 创建终止申请书
    def create(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        subject = Subject.objects.get(id=subject_id)
        if not ChangeSubject.objects.filter(subject=subject, state='审核中').exists():
            if not ChangeSubject.objects.filter(subject=subject, state='通过', isUpload=False).exists():
                if SubjectTermination.objects.filter(
                        subject_id=subject_id).count() == 0 or SubjectTermination.objects.filter(
                    subject_id=subject_id, terminationState='终止不通过').count() > 0 and SubjectTermination.objects.exclude(
                    terminationState='终止不通过').filter(subject_id=subject_id).count() == 0:
                    serializer = self.get_serializer(data=request.data)
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    headers = self.get_success_headers(serializer.data)
                    queryset = self.queryset.get(id=serializer.data['id'])
                    queryset.subject = subject_id
                    queryset.terminationState = '待提交'
                    queryset.save()
                    subject.terminationState = '待提交'
                    subject.save()
                    SubjectTermination.objects.create(termination=str(queryset.id), subject_id=subject_id,
                                                      terminationState='待提交', declareTime=queryset.declareTime)
                    return Response({"code": 0, "message": "ok", "detail": serializer.data},
                                    status=status.HTTP_201_CREATED, headers=headers)
                else:
                    termination = SubjectTermination.objects.get(Q(terminationState='待提交') | Q(terminationState='审核退回') | Q(terminationState="补正资料"), subject=subject_id)
                    partial = kwargs.pop('partial', False)
                    queryset = self.queryset.get(subject=subject_id, id=termination.termination)
                    serializers = self.get_serializer(queryset, data=request.data, partial=partial)
                    serializers.is_valid(raise_exception=True)
                    self.perform_update(serializers)
                    return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)
            else:
                return Response({'code': 2, 'message': '请上传变更申请表'}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 1, 'message': '当前项目有未完成审核的变更申请，待变更申请完成后再申请结题验收'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show_list(self, request):
        termination = request.query_params.dict().get('termination')
        queryset = self.queryset.filter(id=termination)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='delete')
    def delete(self, request):
        subject_id = request.data['subjectId']
        subject_termination = SubjectTermination.objects.get(subject_id=subject_id,
                                                             terminationState=request.data['terminationState'])

        queryset = self.queryset.get(id=subject_termination.termination)
        queryset_id = str(queryset.id)
        TResearchers.objects.filter(termination=queryset_id).delete()
        TOutput.objects.filter(termination=queryset_id).delete()
        TCheckList.objects.filter(termination=queryset_id).delete()
        # TerminationOpinion.objects.filter(termination=queryset_id).delete()
        TReport.objects.filter(termination=queryset_id).delete()
        TExpenditureStatement.objects.filter(termination=queryset_id).delete()
        TerminationAttachment.objects.filter(termination=queryset_id).delete()
        queryset.delete()
        Subject.objects.filter(id=subject_id).update(terminationState=None)
        subject_termination.delete()
        return Response({"code": 0, "message": "已删除"}, status=status.HTTP_200_OK)

    # 提交 项目终止验收
    @action(detail=False, methods=['post'], url_path='submit')
    def submit(self, request):
        subject = Subject.objects.get(id=request.data['subjectId'])
        if subject.subjectState == '终止审核' and subject.state == '补正资料':
            subject.terminationState = '待审核'
            subject.terminationOriginator = '承担单位'
            subject.save()
            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='补正资料')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='补正资料')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='补正资料').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "补正资料 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '项目执行' and subject.terminationState == '审核退回':
            subject.terminationState = '待审核'
            subject.terminationOriginator = '承担单位'
            subject.subjectState = '终止审核'
            subject.save()
            Process.objects.create(state='终止审核', subject=subject)

            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='审核退回')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='审核退回')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='审核退回').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "补正资料 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '项目执行' or subject.subjectState == '逾期未结题':
            subject.state = '已提交'
            subject.terminationOriginator = '承担单位'
            subject.terminationState = '待审核'
            subject.subjectState = '终止审核'
            subject.save()
            Process.objects.create(state='终止审核', subject=subject)
            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='待提交')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='待提交')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待提交').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "项目终止 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '结题复核' and subject.state == '结题复核':
            subject.state = '已提交'
            subject.terminationOriginator = '承担单位'
            subject.terminationState = '待审核'
            subject.subjectState = '终止审核'
            subject.save()
            Process.objects.create(state='终止审核', subject=subject)
            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='待提交')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='待提交')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待提交').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "结题复核 - 已提交"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, "message": "该课题已由科技局提交终止，不允许重复操作"}, status=status.HTTP_200_OK)

    # 提交 项目终止验收
    @action(detail=False, methods=['post'], url_path='submit_to')
    def submit_to(self, request):
        subject = Subject.objects.get(id=request.data['subjectId'])
        if subject.subjectState == '终止审核' and subject.state == '补正资料':
            subject.terminationState = '待审核'
            subject.terminationOriginator = '承担单位'
            subject.save()
            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='补正资料')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='补正资料')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='补正资料').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "补正资料 已提交"}, status=status.HTTP_200_OK)
        elif (subject.subjectState == '项目执行' or subject.subjectState == '逾期未结题') and subject.terminationState == '审核退回':
            subject.state = '移交'
            subject.terminationState = '待审核'
            subject.terminationOriginator = '承担单位'
            subject.subjectState = '终止审核'
            subject.save()
            Process.objects.create(state='终止审核', subject=subject)

            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='审核退回')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='审核退回')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='审核退回').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "补正资料 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '项目执行' or subject.subjectState == '逾期未结题':
            subject.state = '已提交'
            subject.terminationOriginator = '承担单位'
            subject.terminationState = '待审核'
            subject.subjectState = '终止审核'
            subject.save()
            Process.objects.create(state='终止审核', subject=subject)
            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='待提交')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='待提交')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待提交').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "项目终止 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '结题复核' and subject.state == '结题复核':
            subject.state = '已提交'
            subject.terminationOriginator = '承担单位'
            subject.terminationState = '待审核'
            subject.subjectState = '终止审核'
            subject.save()
            Process.objects.create(state='终止审核', subject=subject)
            subject_termination = SubjectTermination.objects.filter(subject_id=request.data['subjectId'],
                                                                    terminationState='待提交')
            if subject_termination.exists():
                attachment_pdf = SubjectTermination.objects.get(subject_id=request.data['subjectId'],
                                                                terminationState='待提交')
                pdf_url = generate_termination_pdf(termination_id=attachment_pdf.termination)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectTermination.objects.filter(subject_id=request.data['subjectId'], terminationState='待提交').update(
                terminationState='待审核')
            return Response({"code": 0, "message": "结题复核 - 已提交"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, "message": "该课题已由科技局提交终止，不允许重复操作"}, status=status.HTTP_200_OK)

# 主要承担人员名单
class TResearchersViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TResearchers.objects.all()
    serializer_class = TResearchersSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(termination=request.data['terminationId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.termination = request.data['terminationId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(termination=request.data['terminationId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination = request.query_params.dict().get('termination')
        termination = Termination.objects.get(id=termination)
        queryset = self.queryset.filter(termination=str(termination.id))
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 项目投入产出基本情况
class TOutputViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TOutput.objects.all()
    serializer_class = TOutputSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(termination=request.data['terminationId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.termination = request.data['terminationId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(termination=request.data['terminationId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination = request.query_params.dict().get('termination')
        termination = Termination.objects.get(id=termination)
        queryset = self.queryset.filter(termination=str(termination.id))
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 财务自查报告
class TCheckListViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TCheckList.objects.all()
    serializer_class = TCheckListSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(termination=request.data['terminationId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.termination = request.data['terminationId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(termination=request.data['terminationId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination = request.query_params.dict().get('termination')
        if self.queryset.filter(termination=termination):
            subject_termination = SubjectTermination.objects.get(termination=termination)
            self.queryset.filter(termination=termination).update(startStopYear=subject_termination.subject.executionTime)
        queryset = self.queryset.filter(termination=termination)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)

class TerminationOpinionViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TerminationOpinion.objects.all()
    serializer_class = TerminationOpinionSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(termination=request.data['terminationId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.termination = request.data['terminationId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(termination=request.data['terminationId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination = request.query_params.dict().get('termination')
        termination = Termination.objects.get(id=termination)
        queryset = self.queryset.filter(termination=str(termination.id))
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 用户使用情况报告
class TReportViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TReport.objects.all()
    serializer_class = TReportSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(termination=request.data['terminationId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.termination = request.data['terminationId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(termination=request.data['terminationId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination = request.query_params.dict().get('termination')
        termination = Termination.objects.get(id=termination)
        queryset = self.queryset.filter(termination=str(termination.id))
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 项目经费支出决算表
class TExpenditureStatementViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TExpenditureStatement.objects.all()
    serializer_class = TExpenditureStatementSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(termination=request.data['terminationId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.termination = request.data['terminationId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(termination=request.data['terminationId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination = request.query_params.dict().get('termination')
        termination = Termination.objects.get(id=termination)
        queryset = self.queryset.filter(termination=str(termination.id))
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 附件清单
class TerminationAttachmentViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TerminationAttachment.objects.all()
    serializer_class = TerminationAttachmentSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        file = request.data['file']
        file_name = request.data['fileName']
        types = request.data['types']
        termination_id = request.data['terminationId']
        path = OSS().put_by_backend(path=file_name, data=file.read())
        if self.queryset.filter(termination=termination_id, types=types):
            attachment = self.queryset.get(termination=termination_id, types=types)
            attachment.attachmentContent.append({"name": file_name, "path": path})
            attachment.save()
            return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)
        else:
            self.queryset.create(types=types, termination=termination_id,
                                 attachmentContent=[{"name": file_name, "path": path}])
            return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)


    # 删除附件
    @action(detail=False, methods=['post'], url_path='delete')
    def delete(self, request):
        types = request.data['types']
        termination_id = request.data['terminationId']
        attachment_path = request.data['attachmentPath']
        if attachment_path:
            queryset = self.queryset.get(termination=termination_id, types=types)
            for j in attachment_path:
                for i in queryset.attachmentContent:
                    if i['name'] == j['name'] and i['path'] == j['path']:
                        queryset.attachmentContent.remove(i)
                        queryset.save()
                        if len(queryset.attachmentContent) == 0:
                            queryset.delete()
                        file_name = j['path'].split("/")[-1]
                        OSS().delete(bucket_name='file', file_name=file_name)
            return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)
        return Response({"code": 0, "message": "蹦跶"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination = request.query_params.dict().get('termination')
        try:
            termination = Termination.objects.get(id=termination)
            queryset = self.queryset.filter(termination=str(termination.id))
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({}, status=status.HTTP_201_CREATED)


# 验收申请书 附件
class TKOpinionSheetViewSet(mongodb_viewsets.ModelViewSet):
    queryset = TKOpinionSheet.objects.all()
    serializer_class = TKOpinionSheetSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = request.data['file']
        file_name = request.data['fileName']
        path = OSS().put_by_backend(path=file_name, data=file.read())
        if request.data['termination']:
            if self.queryset.filter(termination=request.data['termination'], types=request.data['types']):
                attachment = self.queryset.get(termination=request.data['termination'], types=request.data['types'])
                attachment.attachmentContent.append({"name": file_name, "path": path})
                attachment.save()
            else:
                self.queryset.create(types=request.data['types'],
                                     attachmentContent=[{"name": file_name, "path": path}],
                                     termination=request.data['termination'],
                                     )
        else:
            if request.data['chargeTermination']:
                if self.queryset.filter(chargeTermination=request.data['chargeTermination'],
                                        types=request.data['types'], subject=request.data['chargeTermination']):
                    attachment = self.queryset.get(chargeTermination=request.data['chargeTermination'],
                                                   types=request.data['types'],
                                                   subject=request.data['chargeTermination'])
                    attachment.attachmentContent.append({"name": file_name, "path": path})
                    attachment.save()
                else:
                    self.queryset.create(types=request.data['types'],
                                         attachmentContent=[{"name": file_name, "path": path}],
                                         chargeTermination=request.data['chargeTermination'],
                                         subject=request.data['chargeTermination']
                                         )
        return Response({"code": 0, "message": "已上传"}, status=status.HTTP_201_CREATED, )

    # 展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        termination_id = request.query_params.dict().get('termination')
        charge_termination_id = request.query_params.dict().get('chargeTermination')
        if termination_id:
            queryset = self.queryset.filter(termination=termination_id)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializers.data},
                            status=status.HTTP_201_CREATED)
        if charge_termination_id:
            queryset = self.queryset.filter(chargeTermination=charge_termination_id)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializers.data},
                            status=status.HTTP_201_CREATED)

    # 删除附件
    @action(detail=False, methods=['delete'], url_path='delete_attachment_data')
    def delete_attachment_data(self, request):
        types = request.data['types']
        termination_id = request.data['terminationId']
        attachment_path = request.data['attachmentPath']
        charge_termination = request.data['chargeTermination']
        if attachment_path:
            if termination_id:
                queryset = self.queryset.get(termination=termination_id, types=types)
                for j in attachment_path:
                    for i in queryset.attachmentContent:
                        if i['name'] == j['name'] and i['path'] == j['path']:
                            queryset.attachmentContent.remove(i)
                            queryset.save()
                            if len(queryset.attachmentContent) == 0:
                                queryset.delete()
                            file_name = j['path'].split("/")[-1]
                            OSS().delete(bucket_name='file', file_name=file_name)
                return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)
            else:
                if charge_termination:
                    queryset = self.queryset.get(chargeTermination=charge_termination, types=types)
                    for j in attachment_path:
                        for i in queryset.attachmentContent:
                            if i['name'] == j['name'] and i['path'] == j['path']:
                                queryset.attachmentContent.remove(i)
                                queryset.save()
                                if len(queryset.attachmentContent) == 0:
                                    queryset.delete()
                                file_name = j['path'].split("/")[-1]
                                OSS().delete(bucket_name='file', file_name=file_name)
                    return Response({"code": 0, "message": "删除成功"}, status=status.HTTP_200_OK)
        return Response({"code": 0, "message": "蹦跶"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show_certificate')
    def show_certificate(self, request):
        termination_id = request.query_params.dict().get("termination")
        queryset = self.queryset.filter(termination=termination_id)
        for i in queryset:
            if i.types == '终止意见书':
                return Response({"code": 0, "message": "ok", "detail": i.attachmentContent}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 1, "message": "不存在"}, status=status.HTTP_200_OK)

        return Response({"code": 2, "message": "??"}, status=status.HTTP_200_OK)


class ChargeTerminationViewSet(viewsets.ModelViewSet):
    queryset = ChargeTermination.objects.all()
    serializer_class = ChargeTerminationSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        charge = request.user
        queryset = self.queryset.filter(charge=charge)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='query')
    def query(self, request):
        charge = request.user
        queryset = self.queryset.filter(charge=charge)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
            "state": "state",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)
