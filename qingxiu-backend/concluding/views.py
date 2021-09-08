from django.db.models import Q
from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_mongoengine import viewsets as mongodb_viewsets

from change.models import ChangeSubject
from concluding.models import Acceptance, Researchers, Output, ExpenditureStatement, \
    AcceptanceAttachment, CheckList, KOpinionSheet, SubjectConcluding, AcceptanceOpinion
from concluding.serializers import AcceptanceSerializers, ResearchersSerializers, OutputSerializers, \
    ExpenditureStatementSerializers, AcceptanceAttachmentSerializers, \
    CheckListSerializers, KOpinionSheetSerializers, SubjectConcludingSerializers, AcceptanceOpinionSerializers
from contract.models import Contract, ContractContent
from subject.models import Subject, SubjectUnitInfo, SubjectPersonnelInfo, Attachment, Process
from termination.models import SubjectTermination
from tpl.views_download import generate_concluding_pdf
from utils.oss import OSS


class SubjectConcludingViewSet(mongodb_viewsets.ModelViewSet):
    queryset = SubjectConcluding.objects.all()
    serializer_class = SubjectConcludingSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 评估机构
    # 项目结题验收记录  评审
    @action(detail=False, methods=['post'], url_path='acceptance_record_to_view')
    def acceptance_record_to_view(self, request):
        agency = request.user
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by("-reviewTime").filter(agency=agency, handOverState=True)
        # queryset = self.queryset.filter()
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 可申请结题项目 展示/单位
    @action(detail=False, methods=['get'], url_path='subject_show')
    def subject_show(self, request, *args, **kwargs):
        enterprise = request.user
        subject_obj = Subject.objects.filter(Q(subjectState='项目执行') | Q(subjectState='结题复核'),
                                             enterprise=enterprise)
        lists = [{"id": i.id,
                  "annualPlan": i.project.category.batch.annualPlan,
                  "planCategory": i.project.category.planCategory, "projectName": i.project.projectName,
                  "contractNo": i.contract_subject.values('contractNo'), "subjectName": i.subjectName,
                  "unitName": i.unitName, "head": i.head,
                  "executionTime": i.executionTime, } for i in subject_obj if
                 self.queryset.filter(subject=i, concludingState='结题复核').count() == 1 and self.queryset.filter(
                     subject=i).count() == 1
                 or self.queryset.filter(subject=i).count() == 0]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 可申请结题项目 查询/单位
    @action(detail=False, methods=['post'], url_path='subject_query')
    def subject_query(self, request, *args, **kwargs):
        enterprise = request.user
        subject_obj = Subject.objects.filter(Q(subjectState='项目执行') | Q(subjectState='结题复核'),
                                             enterprise=enterprise)
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "planCategory": "project__category__planCategory",
            "projectName": "project__projectName",
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
                  "executionTime": i.executionTime, } for i in queryset if
                 self.queryset.filter(subject=i, concludingState='结题复核').count() == 1 and self.queryset.filter(
                     subject=i).count() == 1
                 or self.queryset.filter(subject=i).count() == 0]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 申请结题项目 检测/单位
    @action(detail=False, methods=['post'], url_path='detection')
    def detection(self, request, *args, **kwargs):
        subject = Subject.objects.get(id=request.data['subjectId'])
        if ChangeSubject.objects.filter(subject=subject, state='审核中').exists():
            return Response({'code': 1, 'message': '该项目有未完成审批的变更申请，无法验收项目'}, status=status.HTTP_200_OK)
        if ChangeSubject.objects.filter(subject=subject, state='通过', isUpload=False).exists():
            return Response({'code': 2, 'message': '请上传该项目的变更申请表附件'}, status=status.HTTP_200_OK)
        if SubjectTermination.objects.filter(Q(terminationState='待提交') | Q(terminationState='审核退回'),
                                             subject=subject).exists():
            return Response({'code': 3, 'message': '当前项目已申请终止，请删除记录后再申请验收'}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 0, 'message': 'ok'}, status=status.HTTP_200_OK)

    # 申请结题验收项目信息列表/单位
    @action(detail=False, methods=['get'], url_path='unit_concluding_show')
    def unit_concluding_show(self, request):
        enterprise = request.user
        queryset = self.queryset.filter(subject__enterprise=enterprise)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    # 申请结题验收项目信息列表条件查询/单位
    @action(detail=False, methods=['post'], url_path='unit_concluding_query')
    def unit_concluding_query(self, request):
        enterprise = request.user
        queryset = self.queryset.filter(subject__enterprise=enterprise)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName",
            "subjectName": "subject__subjectName__contains",
            "head": "subject__head__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
            "concludingState": "concludingState",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='show_list')
    def show_list(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(
            Q(concludingState='结题复核') | Q(concludingState='验收通过') | Q(concludingState='验收不通过'), subject=subject_id, )
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)

    # 结题验收PDF展示/管理员导入资料
    @action(detail=False, methods=['get'], url_path='show_pdf')
    def show_pdf(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        acceptance_id = request.query_params.dict().get('acceptanceId')
        types = request.query_params.dict().get('types')
        queryset = self.queryset.get(subject_id=subject_id, acceptance=acceptance_id)
        if queryset.attachmentPDF:
            return Response({'code': 0, 'message': 'ok ', "detail": queryset.attachmentPDF},
                            status=status.HTTP_200_OK)
        else:
            try:
                lists = Attachment.objects.filter(subject=subject_id, types=types).values('attachmentPath')
                return Response({'code': 0, 'message': 'ok ', "detail": lists}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'code': 1, 'message': '没有数据'}, status=status.HTTP_200_OK)


class AcceptanceViewSet(mongodb_viewsets.ModelViewSet):
    queryset = Acceptance.objects.all()
    serializer_class = AcceptanceSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 结题验收初始数据
    # @action(detail=False, methods=['get'], url_path='initial')
    # def initial_data(self, request):
    #     subject_id = request.query_params.dict().get('subjectId')
    #     subject = Subject.objects.get(id=subject_id)
    #     unit = SubjectUnitInfo.objects.get(subjectId=subject_id)
    #     unit_name = ContractContent.objects.get(id=Contract.objects.get(subject=subject).contractContent).unit
    #     unit_name = '、'.join(unit_name)
    #     data = {
    #         "contractNo": subject.contract_subject.values('contractNo'),
    #         "subjectName": subject.subjectName,
    #         "unitName": unit_name,
    #         # "applyUnit": unit.unitInfo[0]['unitName'],
    #         "applyUnit": unit_name,
    #         "registeredAddress": subject.enterprise.enterprise.registeredAddress,
    #         "contact": subject.enterprise.contact,
    #         "mobile": subject.enterprise.mobile,
    #         # "contact": subject.head,
    #         # "mobile": subject.mobile,
    #         "zipCode": unit.unitInfo[0]['zipCode'],
    #         "email": subject.email,
    #         "industry": subject.enterprise.enterprise.industry,
    #         "startStopYear": subject.executionTime,
    #         "grantAmount": subject.contract_subject.values('approvalMoney')
    #     }
    #     return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    # 结题验收 项目终止 初始数据
    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        subject = Subject.objects.get(id=subject_id)
        unit = SubjectUnitInfo.objects.get(subjectId=subject_id)
        unit_name = ContractContent.objects.get(id=Contract.objects.get(subject=subject).contractContent).unit
        unit_name = '、'.join(unit_name)
        data = {
            "contractNo": subject.contract_subject.values('contractNo'),
            "subjectName": subject.subjectName,
            "unitName": unit_name,
            "applyUnit": unit_name,
            "startStopYear": subject.executionTime,
            "grantAmount": subject.contract_subject.values('approvalMoney'),
            "unitInfo": [
                {"unitName": unit.unitInfo[0]['unitName'],
                 "registeredAddress": unit.unitInfo[0]['registeredAddress'],
                 "contact": unit.unitInfo[0]['contact'],
                 "mobile": unit.unitInfo[0]["mobile"],
                 "zipCode": unit.unitInfo[0]['zipCode'],
                 "email": unit.unitInfo[0]['email'],
                 "industry": unit.unitInfo[0]['industry'],
                 }
            ]
        }
        if len(unit.jointUnitInfo) == 0:
            return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)
        else:
            lists = [{"unitName": i['unitName'],
                      "registeredAddress": i['registeredAddress'],
                      "contact": i['contact'],
                      "mobile": i['mobile'],
                      "zipCode": i['zipCode'],
                      "email": i['email'],
                      "industry": i['industry']} for i in unit.jointUnitInfo]
            data['jointUnitInfo'] = lists
            return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        subject = Subject.objects.get(id=request.data['subjectId'])
        if not ChangeSubject.objects.filter(subject=subject, state='审核中').exists():
            if not ChangeSubject.objects.filter(subject=subject, state='通过', isUpload=False).exists():
                if SubjectConcluding.objects.filter(
                        subject_id=request.data['subjectId']).count() < 1 or SubjectConcluding.objects.filter(
                    subject_id=request.data['subjectId'],
                    concludingState='结题复核').count() == 1 and SubjectConcluding.objects.filter(
                    subject_id=request.data['subjectId']).count() == 1:
                    # if self.queryset.filter(subject=request.data['subjectId']).count() < 1 or self.queryset.filter(
                    #         subject=request.data['subjectId'], concludingState='结题复核').count() == 1:
                    serializer = self.get_serializer(data=request.data)
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    headers = self.get_success_headers(serializer.data)
                    queryset = self.queryset.get(id=serializer.data['id'])
                    queryset.subject = request.data['subjectId']
                    subject.concludingState = '待提交'
                    subject.save()
                    queryset.save()
                    SubjectConcluding.objects.create(acceptance=str(queryset.id), subject_id=request.data['subjectId'],
                                                     concludingState='待提交', declareTime=queryset.declareTime)
                    return Response({"code": 0, "message": "ok", "detail": serializer.data},
                                    status=status.HTTP_201_CREATED, headers=headers)
                else:
                    partial = kwargs.pop('partial', False)
                    subject_concluding = SubjectConcluding.objects.get(
                        Q(concludingState='待提交') | Q(concludingState='审核退回') | Q(concludingState='补正资料'),
                        subject_id=request.data['subjectId'])
                    queryset = self.queryset.get(id=subject_concluding.acceptance)
                    serializers = self.get_serializer(queryset, data=request.data, partial=partial)
                    serializers.is_valid(raise_exception=True)
                    self.perform_update(serializers)
                    return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)
            else:
                return Response({'code': 2, 'message': '请上传变更申请表'}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 1, 'message': '当前项目有未完成审核的变更申请，待变更申请完成后再申请结题验收'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        try:
            acceptance_id = request.query_params.dict().get('acceptanceId')
            queryset = self.queryset.filter(id=acceptance_id)
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({})

    @action(detail=False, methods=['delete'], url_path='delete')
    def delete(self, request):
        acceptance_id = request.data['acceptanceId']
        queryset = self.queryset.get(id=acceptance_id)
        Researchers.objects.filter(acceptance=acceptance_id).delete()
        Output.objects.filter(acceptance=acceptance_id).delete()
        CheckList.objects.filter(acceptance=acceptance_id).delete()
        ExpenditureStatement.objects.filter(acceptance=acceptance_id).delete()
        AcceptanceAttachment.objects.filter(acceptance=acceptance_id).delete()
        queryset.delete()
        SubjectConcluding.objects.filter(acceptance=acceptance_id).delete()

        return Response({"code": 0, "message": "已删除"}, status=status.HTTP_200_OK)

    # 提交 结题验收1
    @action(detail=False, methods=['post'], url_path='submit')
    def submit(self, request):
        subject = Subject.objects.get(id=request.data['subjectId'])
        if subject.subjectState == '项目执行' and subject.concludingState == '审核退回':
            subject.state = '已提交'
            subject.subjectState = '验收审核'
            subject.concludingState = '待审核'
            subject.save()
            Process.objects.create(state='验收审核', subject=subject)
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='审核退回')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='审核退回')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='审核退回').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "审核退回 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '验收审核' and subject.state == '补正资料':
            subject.concludingState = '待审核'
            subject.save()
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='补正资料')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='补正资料')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='补正资料').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "补正资料 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '结题复核' and subject.state == '结题复核':
            subject.state = '已提交'
            subject.subjectState = '验收审核'
            subject.concludingState = '待审核'
            subject.save()
            Process.objects.create(state='验收审核', subject=subject)
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='待提交')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='待提交')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待提交').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "项目执行 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '项目执行':
            subject.state = '已提交'
            subject.subjectState = '验收审核'
            subject.concludingState = '待审核'
            subject.save()
            Process.objects.create(state='验收审核', subject=subject)
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='待提交')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='待提交')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待提交').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "项目执行 - 已提交"}, status=status.HTTP_200_OK)
        else:
            return Response()

    # 提交 结题验收2
    @action(detail=False, methods=['post'], url_path='submit_to')
    def submit_to(self, request):
        subject = Subject.objects.get(id=request.data['subjectId'])
        if subject.subjectState == '项目执行' and subject.concludingState == '审核退回':
            subject.state = '移交'
            subject.subjectState = '验收审核'
            subject.concludingState = '待审核'
            subject.save()
            Process.objects.create(state='验收审核', subject=subject)
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='审核退回')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='审核退回')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='审核退回').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "审核退回 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '验收审核' and subject.state == '补正资料':
            subject.concludingState = '待审核'
            subject.save()
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='补正资料')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='补正资料')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='补正资料').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "补正资料 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '结题复核' and subject.state == '结题复核':
            subject.state = '已提交'
            subject.subjectState = '验收审核'
            subject.concludingState = '待审核'
            subject.save()
            Process.objects.create(state='验收审核', subject=subject)
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='待提交')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='待提交')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待提交').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "项目执行 - 已提交"}, status=status.HTTP_200_OK)
        elif subject.subjectState == '项目执行':
            subject.state = '已提交'
            subject.subjectState = '验收审核'
            subject.concludingState = '待审核'
            subject.save()
            Process.objects.create(state='验收审核', subject=subject)
            subject_concluding = SubjectConcluding.objects.filter(subject_id=request.data['subjectId'],
                                                                  concludingState='待提交')
            if subject_concluding.exists():
                attachment_pdf = SubjectConcluding.objects.get(subject_id=request.data['subjectId'],
                                                               concludingState='待提交')
                pdf_url = generate_concluding_pdf(acceptance_id=attachment_pdf.acceptance)
                attachment_pdf.attachmentPDF = pdf_url
                attachment_pdf.save()
            SubjectConcluding.objects.filter(subject_id=request.data['subjectId'], concludingState='待提交').update(
                concludingState='待审核')
            return Response({"code": 0, "message": "项目执行 - 已提交"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 1, "message": "已提交，请勿重复操作"}, status=status.HTTP_200_OK)


# 验收申请书主要承担人员
class ResearchersViewSet(mongodb_viewsets.ModelViewSet):
    queryset = Researchers.objects.all()
    serializer_class = ResearchersSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(acceptance=request.data['acceptanceId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.acceptance = request.data['acceptanceId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(acceptance=request.data['acceptanceId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        queryset = self.queryset.filter(acceptance=acceptance_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request):
        subject_id = request.query_params.dict().get("subjectId")
        contract_content = Contract.objects.get(subject_id=subject_id).contractContent
        personnel = ContractContent.objects.get(id=contract_content).personnel
        return Response({"code": 0, "message": "ok", "detail": personnel}, status=status.HTTP_201_CREATED)


# 验收申请书项目投入产出基本情况表
class OutputViewSet(mongodb_viewsets.ModelViewSet):
    queryset = Output.objects.all()
    serializer_class = OutputSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(acceptance=request.data['acceptanceId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.acceptance = request.data['acceptanceId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(acceptance=request.data['acceptanceId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        queryset = self.queryset.filter(acceptance=acceptance_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# CheckList
class CheckListViewSet(mongodb_viewsets.ModelViewSet):
    queryset = CheckList.objects.all()
    serializer_class = CheckListSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 财务自查表初始数据
    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        subject = Subject.objects.get(id=subject_id)
        head = SubjectPersonnelInfo.objects.get(subjectId=subject_id)
        unit_name = ContractContent.objects.get(id=Contract.objects.get(subject=subject).contractContent).unit
        data = {
            "name": subject.subjectName,
            "head": subject.head,
            "contractNo": subject.contract_subject.values('contractNo'),
            "startStopYear": subject.executionTime,
            "headTitle": head.title,
            "unitName": unit_name,
            # "totalBudget": ContractContent.objects.get(
            #     id=Contract.objects.get(subject=subject).contractContent).scienceFunding
            "totalBudget": ContractContent.objects.get(
                id=Contract.objects.get(subject=subject).contractContent).money
        }
        return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(acceptance=request.data['acceptanceId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.acceptance = request.data['acceptanceId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(acceptance=request.data['acceptanceId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        if self.queryset.filter(acceptance=acceptance_id):
            subject_concluding = SubjectConcluding.objects.get(acceptance=acceptance_id)
            self.queryset.filter(acceptance=acceptance_id).update(
                startStopYear=subject_concluding.subject.executionTime)
        queryset = self.queryset.filter(acceptance=acceptance_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 单位验证申请意见
class AcceptanceOpinionViewSet(mongodb_viewsets.ModelViewSet):
    queryset = AcceptanceOpinion.objects.all()
    serializer_class = AcceptanceOpinionSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(acceptance=request.data['acceptanceId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.acceptance = request.data['acceptanceId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(acceptance=request.data['acceptanceId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        queryset = self.queryset.filter(acceptance=acceptance_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 验收申请书 项目经费支出决算表
class ExpenditureStatementViewSet(mongodb_viewsets.ModelViewSet):
    queryset = ExpenditureStatement.objects.all()
    serializer_class = ExpenditureStatementSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 项目经费支出决算表初始数据
    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        subject = Subject.objects.get(id=subject_id)
        data = {
            "unit": subject.enterprise.name,
            "subjectName": subject.subjectName,
            "contractNo": subject.contract_subject.values('contractNo'),
            "head": subject.head,
            "executionTime": subject.executionTime,
            "fiscalGrantFunding": subject.contract_subject.values('approvalMoney')
        }
        return Response({"code": 0, "message": "ok", "detail": data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if not self.queryset.filter(acceptance=request.data['acceptanceId']):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.acceptance = request.data['acceptanceId']
            queryset.save()
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            partial = kwargs.pop('partial', False)
            instance = self.queryset.get(acceptance=request.data['acceptanceId'])
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        queryset = self.queryset.filter(acceptance=acceptance_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_201_CREATED)


# 验收申请书 附件
class AcceptanceAttachmentViewSet(mongodb_viewsets.ModelViewSet):
    queryset = AcceptanceAttachment.objects.all()
    serializer_class = AcceptanceAttachmentSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        file = request.data['file']
        file_name = request.data['fileName']
        types = request.data['types']
        acceptance_id = request.data['acceptanceId']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        path = OSS().put_by_backend(path=file_name, data=file.read())
        if self.queryset.filter(acceptance=acceptance_id, types=types):
            attachment = self.queryset.get(acceptance=acceptance_id, types=types)
            attachment.attachmentContent.append({"name": file_name, "path": path})
            attachment.save()
            serializer = self.get_serializer(attachment)
            return Response({"code": 0, "message": "上传成功", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            self.queryset.create(types=types, acceptance=acceptance_id,
                                 attachmentContent=[{"name": file_name, "path": path}])
            return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)

    # 删除附件
    @action(detail=False, methods=['delete'], url_path='delete_attachment_data')
    def delete_attachment_data(self, request):
        types = request.data['types']
        acceptance_id = request.data['acceptanceId']
        attachment_path = request.data['attachmentPath']
        if attachment_path:
            queryset = self.queryset.get(acceptance=acceptance_id, types=types)
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

    # 验收申请书附件展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        queryset = self.queryset.filter(acceptance=acceptance_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)


# 科技局关于验收申请书 附件
class KOpinionSheetViewSet(mongodb_viewsets.ModelViewSet):
    queryset = KOpinionSheet.objects.all()
    serializer_class = KOpinionSheetSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        file = request.data['file']
        file_name = request.data['fileName']
        types = request.data['types']
        acceptance_id = request.data['acceptanceId']
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        path = OSS().put_by_backend(path=file_name, data=file.read())
        if self.queryset.filter(acceptance=acceptance_id, types=types):
            attachment = self.queryset.get(acceptance=acceptance_id, types=types)
            attachment.attachmentContent.append({"name": file_name, "path": path})
            attachment.save()
            serializer = self.get_serializer(attachment)
            return Response({"code": 0, "message": "上传成功", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            self.queryset.create(types=types, acceptance=acceptance_id,
                                 attachmentContent=[{"name": file_name, "path": path}])
            return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)

    # 删除附件
    @action(detail=False, methods=['delete'], url_path='delete_attachment_data')
    def delete_attachment_data(self, request):
        types = request.data['types']
        acceptance_id = request.data['acceptanceId']
        attachment_path = request.data['attachmentPath']
        if attachment_path:
            queryset = self.queryset.get(acceptance=acceptance_id, types=types)
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

    # 验收申请书附件展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        queryset = self.queryset.filter(acceptance=acceptance_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show_certificate')
    def show_certificate(self, request):
        acceptance_id = request.query_params.dict().get("acceptanceId")
        queryset = self.queryset.filter(acceptance=acceptance_id)
        for i in queryset:
            if i.types == '验收证书':
                return Response({"code": 0, "message": "ok", "detail": i.attachmentContent}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 1, "message": "不存在", }, status=status.HTTP_200_OK)
        return Response({"code": 2, "message": "??"}, status=status.HTTP_200_OK)
