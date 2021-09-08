import calendar
import datetime

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from change.models import ProjectLeaderChange, ProjectDelayChange, ChangeSubject, TechnicalRouteChange
from change.serializers import ProjectLeaderChangeSerializers, \
    ProjectDelayChangeSerializers, ChangeSubjectSerializers, TechnicalRouteChangeSerializers
from report.models import ProgressReport
from subject.models import Subject, Process
from tpl.views_download import generate_project_leader_change_pdf, \
    generate_project_delay_change_pdf, generate_technical_route_change_pdf
from utils.oss import OSS
from utils.sms_template import send_template


class ChangeSubjectViewSet(viewsets.ModelViewSet):
    queryset = ChangeSubject.objects.all()
    serializer_class = ChangeSubjectSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 申请变更初识值
    @action(detail=False, methods=['get'], url_path='show_init')
    def show_init(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        subject = Subject.objects.get(id=subject_id)
        data = {
            'name': subject.subjectName,
            'unit': subject.unitName,
            'head': subject.head,
            'contractNo': subject.contract_subject.values('contractNo'),
        }
        return Response({"code": 0, "message": "ok", "detail": data}, status.HTTP_201_CREATED)

    # 申请变更展示/单位
    @action(detail=False, methods=['post'], url_path='change')
    def change(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        subject = Subject.objects.get(id=subject_id)
        start_stop_year = subject.executionTime.split('-')
        stop_time = start_stop_year[1].split('.')
        x, y = calendar.monthrange(int(stop_time[0]), int(stop_time[1]))
        last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=y)
        new_time = datetime.date.today()
        if new_time > last_day:
            return Response({"code": 1, "message": "ok", "detail": "超过执行时间不支持变更"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)

    # 申请变更展示/单位
    @action(detail=False, methods=['post'], url_path='change_a')
    def change_a(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        change_type = request.data['changeType']
        if change_type == '项目延期':
            subject = Subject.objects.get(id=subject_id)
            start_stop_year = subject.executionTime.split('-')
            stop_time = start_stop_year[1].split('.')
            x, y = calendar.monthrange(int(stop_time[0]), int(stop_time[1]))
            last_day = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=y)
            three_month_gae = datetime.date(year=int(stop_time[0]), month=int(stop_time[1]), day=1) - relativedelta(months=2)
            new_time = datetime.date.today()
            if subject.subject_change.filter(Q(state="通过") | Q(state="审核中"), changeType='项目延期').count() != 0:
                return Response({'code': 1, 'message': '该项目已申请过延期，不允许申请延期'}, status=status.HTTP_200_OK)
            if three_month_gae > new_time or last_day < new_time:
                return Response({'code': 2, 'message': '项目剩余执行时间超过三个月，不允许申请延期'}, status=status.HTTP_200_OK)
            else:
                return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)
        else:
            return Response({"code": 0, "message": "ok"}, status=status.HTTP_200_OK)

    # 申请变更展示/单位
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request, *args, **kwargs):
        enterprise = request.user
        subject_obj = Subject.objects.filter(enterprise=enterprise, subjectState='项目执行')
        lists = [{"id": i.id,
                  "annualPlan": i.project.category.batch.annualPlan,
                  "planCategory": i.project.category.planCategory,
                  "projectName": i.project.projectName,
                  "contractNo": i.contract_subject.values('contractNo'),
                  "subjectName": i.subjectName,
                  "head": i.head} for i in subject_obj]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 申请变更查询/单位
    @action(detail=False, methods=['post'], url_path='query')
    def query(self, request, *args, **kwargs):
        enterprise = request.user
        subject_obj = Subject.objects.filter(enterprise=enterprise, subjectState='项目执行')
        json_data = request.data
        keys = {
            "annualPlan": "project__category__batch__annualPlan",
            "subjectName": "subjectName__contains",
            "head": "head__contains"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = subject_obj.filter(**data)
        lists = [{"id": i.id,
                  "annualPlan": i.project.category.batch.annualPlan,
                  "planCategory": i.project.category.planCategory,
                  "projectName": i.project.projectName,
                  "contractNo": i.contract_subject.values('contractNo'),
                  "subjectName": i.subjectName,
                  "head": i.head} for i in queryset]
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)

    # 项目变更 待审核变更记录列表展示/单位
    def list(self, request, *args, **kwargs):
        limit = request.query_params.dict().get('limit', None)
        enterprise = request.user
        queryset = self.queryset.filter(subject__enterprise=enterprise)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "ok", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目变更 待审核变更记录列表查询/单位
    @action(detail=False, methods=['post'], url_path='query_list')
    def query_list(self, request, *args, **kwargs):
        enterprise = request.user
        queryset = self.queryset.filter(subject__enterprise=enterprise)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "subjectName": "subject__subjectName__contains",
            "head": "subject__head__contains",
            "state": "state",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 项目变更 上传附件/单位
    @action(detail=False, methods=['post'], url_path='upload')
    def upload_attachment(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        c_id = request.data['id']
        file = request.data['file']
        file_name = request.data['fileName']
        queryset = self.queryset.get(id=c_id, subject_id=subject_id)
        queryset.attachment = OSS().put_by_backend(path=file_name, data=file.read())
        queryset.isUpload = True
        queryset.save()
        return Response({'code': 0, 'message': '上传成功'}, status=status.HTTP_200_OK)

    # 项目变更 撤销变更/单位
    @action(detail=False, methods=['post'], url_path='undo_change')
    def undo_change(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        c_id = request.data['id']
        queryset = self.queryset.get(id=c_id, subject_id=subject_id)
        if queryset.changeType == '项目负责人':
            ProjectLeaderChange.objects.filter(changeSubject=queryset).delete()
            path = queryset.attachment
            if path:
                file_name = path.split("/")[-1]
                OSS().delete(bucket_name='file', file_name=file_name)
            queryset.delete()
        elif queryset.changeType == '重大技术路线调整':
            TechnicalRouteChange.objects.filter(changeSubject=queryset).delete()
            path = queryset.attachment
            if path:
                file_name = path.split("/")[-1]
                OSS().delete(bucket_name='file', file_name=file_name)
            queryset.delete()
        elif queryset.changeType == '项目延期':
            ProjectDelayChange.objects.filter(changeSubject=queryset).delete()
            path = queryset.attachment
            if path:
                file_name = path.split("/")[-1]
                OSS().delete(bucket_name='file', file_name=file_name)
            queryset.delete()
        return Response({"code": 0, "message": "撤销成功"}, status=status.HTTP_200_OK)

    """
    分管人员
    
    """

    # 变更管理 申请变更记录列表条件查询/分管人员
    @action(detail=False, methods=['post'], url_path='change_user_management_query_wx')
    def change_user_management_query_wx(self, request):
        charge = request.user
        queryset = self.queryset.filter(subject__project__charge=charge, state='审核中')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan__in",
            "planCategory": "subject__project__category__planCategory__in",
            "subjectName": "subject__subjectName__contains",
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != [] and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 变更管理 申请变更记录列表/分管人员
    @action(detail=False, methods=['get'], url_path='change_user_management_show')
    def change_user_management_show(self, request):
        limit = request.query_params.dict().get('limit', None)
        charge = request.user
        queryset = self.queryset.filter(subject__project__charge=charge, state='审核中')
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "保存成功", "detail": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)


    # 变更管理 申请变更记录列表条件查询/分管人员
    @action(detail=False, methods=['post'], url_path='change_user_management_query')
    def change_user_management_query(self, request):
        charge = request.user
        queryset = self.queryset.filter(subject__project__charge=charge, state='审核中')
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "projectBatch": "subject__project__category__batch__projectBatch",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "contractNo": "subject__contract_subject__contractNo__contains",
            "subjectName": "subject__subjectName__contains",
            "unitName": "subject__unitName__contains",
            "changeType": "changeType",

        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        queryset = queryset.filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 变更管理 变更审核
    @action(detail=False, methods=['post'], url_path='change_user_management')
    def change_user_management(self, request):
        change_subject_id = request.data['changeSubjectId']
        state = request.data['state']
        queryset = self.queryset.get(id=change_subject_id)
        if state == '通过':
            if queryset.changeType == '项目负责人':
                project_leader_change = ProjectLeaderChange.objects.get(changeSubject=queryset)
                project_leader_change.kOpinion = request.data['kOpinion']
                queryset.subject.head = project_leader_change.changeHead
                queryset.subject.idNumber = project_leader_change.idNumber
                queryset.subject.mobile = project_leader_change.phone
                queryset.state = state
                project_leader_change.save()
                queryset.subject.save()
                queryset.attachment = generate_project_leader_change_pdf(project_leader_change_id=project_leader_change.id)
                queryset.save()
                # Subject.objects.get(id=queryset.subject.id)
                ProgressReport.objects.filter(subject_id=queryset.subject.id, state='待提交').update(head=project_leader_change.changeHead)
            elif queryset.changeType == '重大技术路线调整':
                TechnicalRouteChange.objects.filter(changeSubject=queryset).update(kOpinion=request.data['kOpinion'])
                technical_route_change = TechnicalRouteChange.objects.get(changeSubject=queryset)
                queryset.state = state
                queryset.attachment = generate_technical_route_change_pdf(technical_route_change_id=technical_route_change.id)
                queryset.save()
            elif queryset.changeType == '项目延期':
                project_delay_change = ProjectDelayChange.objects.get(changeSubject=queryset)
                project_delay_change.kOpinion = request.data['kOpinion']
                if queryset.subject.executionTime != '-':
                    start_stop_year = queryset.subject.executionTime.split('-')
                    start_time = start_stop_year[0]
                    start_stop_year = start_stop_year[1]
                    start_stop_year = start_stop_year.split('.')
                    last_day = datetime.date(year=int(start_stop_year[0]), month=int(start_stop_year[1]), day=1)
                    if project_delay_change.delayTime == '6个月':
                        stop_time = last_day + relativedelta(months=6)
                    else:
                        stop_time = last_day + relativedelta(months=12)
                    stop_time = str(stop_time).replace('-', '.')[0:7]
                    queryset.state = state
                    queryset.subject.executionTime = start_time + '-' + stop_time
                    queryset.subject.save()
                    project_delay_change.save()
                    queryset.attachment = generate_project_delay_change_pdf(project_delay_change_id=project_delay_change.id)
                    queryset.save()
                    ProgressReport.objects.filter(subject_id=queryset.subject.id, state='待提交').update(
                        startStopYear=start_time + '-' + stop_time)
            Process.objects.create(state='项目执行', subject=queryset.subject, note='变更申请审核通过，请上传变更申请表附件', dynamic=True)
            send_template(name='变更审核通过', subject_id=queryset.subject.id)
            return Response({"code": 0, "message": "完成审核"}, status=status.HTTP_200_OK)
        else:
            if queryset.changeType == '项目负责人':
                ProjectLeaderChange.objects.filter(changeSubject=queryset).update(kOpinion=request.data['kOpinion'])
                project_leader_change = ProjectLeaderChange.objects.get(changeSubject=queryset)
                queryset.state = '不通过'
                queryset.attachment = generate_project_leader_change_pdf(
                    project_leader_change_id=project_leader_change.id)
                queryset.save()
            elif queryset.changeType == '重大技术路线调整':
                TechnicalRouteChange.objects.filter(changeSubject=queryset).update(kOpinion=request.data['kOpinion'])
                technical_route_change = TechnicalRouteChange.objects.get(changeSubject=queryset)
                queryset.state = '不通过'
                queryset.attachment = generate_technical_route_change_pdf(technical_route_change_id=technical_route_change.id)
                queryset.save()
            elif queryset.changeType == '项目延期':
                ProjectDelayChange.objects.filter(changeSubject=queryset).update(kOpinion=request.data['kOpinion'])
                project_delay_change = ProjectDelayChange.objects.get(changeSubject=queryset)
                queryset.state = '不通过'
                queryset.attachment = generate_project_delay_change_pdf(project_delay_change_id=project_delay_change.id)
                queryset.save()
            Process.objects.create(state='项目执行', subject=queryset.subject, note='变更申请审核不通过', dynamic=True)
            send_template(name='变更审核不通过', subject_id=queryset.subject.id)

            return Response({"code": 0, "message": "完成审核"}, status=status.HTTP_200_OK)

    # 当前课题所有变更文件的展示
    @action(detail=False, methods=['get'], url_path='show_change')
    def show_change(self, request, *args, **kwargs):
        lists = []
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(subject_id=subject_id, state='通过')
        for change in queryset:
            if change.attachment:
                data = {
                    "changeTime": change.changeTime,
                    "type": change.changeType,
                    "attachment": change.attachment
                }
                lists.append(data)
        return Response({"code": 0, "message": "ok", "detail": lists}, status=status.HTTP_200_OK)


class ProjectLeaderChangeViewSet(viewsets.ModelViewSet):
    queryset = ProjectLeaderChange.objects.all()
    serializer_class = ProjectLeaderChangeSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        queryset = self.queryset.get(id=serializer.data['id'])
        attachment = generate_project_leader_change_pdf(project_leader_change_id=queryset.id)
        change_subject = ChangeSubject.objects.create(state='审核中', changeType=request.data['changeType'],
                                                      subject_id=request.data['subjectId'], attachment=attachment)
        queryset.changeSubject = change_subject
        queryset.save()
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                        headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request, *args, **kwargs):
        change_subject_id = request.query_params.dict().get('changeSubjectId')
        queryset = self.queryset.filter(changeSubject_id=change_subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

# 重大技术路线调整
class TechnicalRouteChangeViewSet(viewsets.ModelViewSet):
    queryset = TechnicalRouteChange.objects.all()
    serializer_class = TechnicalRouteChangeSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        queryset = self.queryset.get(id=serializer.data['id'])
        attachment = generate_technical_route_change_pdf(technical_route_change_id=queryset.id)
        change_subject = ChangeSubject.objects.create(state='审核中', changeType=request.data['changeType'],
                                                      subject_id=request.data['subjectId'], attachment=attachment)
        queryset.changeSubject = change_subject
        queryset.save()
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request, *args, **kwargs):
        change_subject_id = request.query_params.dict().get('changeSubjectId')
        queryset = self.queryset.filter(changeSubject_id=change_subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)

# 项目延期申请
class ProjectDelayChangeViewSet(viewsets.ModelViewSet):
    queryset = ProjectDelayChange.objects.all()
    serializer_class = ProjectDelayChangeSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        queryset = self.queryset.get(id=serializer.data['id'])
        attachment = generate_project_delay_change_pdf(project_delay_change_id=queryset.id)
        change_subject = ChangeSubject.objects.create(state='审核中', changeType=request.data['changeType'],
                                                      subject_id=request.data['subjectId'], attachment=attachment)
        queryset.changeSubject = change_subject
        queryset.save()
        return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request, *args, **kwargs):
        change_subject_id = request.query_params.dict().get('changeSubjectId')
        queryset = self.queryset.filter(changeSubject_id=change_subject_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)
