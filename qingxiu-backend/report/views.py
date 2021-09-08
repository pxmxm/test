from django.db.models import Q
from django.shortcuts import render

# Create your views here.
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.decorators import action

from report.models import ProgressReport
from report.serializers import ProgressReportSerializers
from subject.models import Subject
from tpl.views_download import generate_progress_report_pdf


class ProgressReportViewSet(viewsets.ModelViewSet):
    queryset = ProgressReport.objects.all()
    serializer_class = ProgressReportSerializers
    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 填写进度实施报告
    def create(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        partial = kwargs.pop('partial', False)
        queryset = self.queryset.get(subject_id=subject_id, state='待提交')
        serializer = self.get_serializer(queryset, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        queryset.state = '已提交'
        queryset.attachmentPDF = generate_progress_report_pdf(progress_report_id=queryset.id)
        queryset.save()
        return Response({"code": 0, "message": "已提交"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        actions = request.query_params.dict().get('action')
        queryset = self.queryset.filter(subject_id=subject_id)
        if actions == '查看':
            instance = queryset.filter(state='已提交')
            serializer = self.get_serializer(instance, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
        else:
            queryset.filter(state='待提交').update(startStopYear=Subject.objects.get(id=subject_id).executionTime)
            instance = queryset.filter(state='待提交')
            serializer = self.get_serializer(instance, many=True)
            return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 实施进度报告 待填写待填写实施进度列
    @action(detail=False, methods=['get'], url_path='progress_report_show')
    def progress_report_show(self, request):
        enterprise = request.user
        queryset = self.queryset.filter(Q(state='待提交') | Q(state='已提交'), subject__enterprise=enterprise)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 实施进度报告 待填写待填写实施进度列表查询
    @action(detail=False, methods=['post'], url_path='progress_report_query')
    def progress_report_query(self, request):
        unit_user = request.user
        queryset = self.queryset.filter(Q(state='待提交') | Q(state='已提交'), subject__enterprise=unit_user)
        json_data = request.data
        keys = {
            "annualPlan": "subject__project__category__batch__annualPlan",
            "planCategory": "subject__project__category__planCategory",
            "projectName": "subject__project__projectName__contains",
            "subjectName": "subject__subjectName__contains",
            "state": "state"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''}
        subject_obj = queryset.filter(**data)
        serializer = self.get_serializer(subject_obj, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)

    # 当前课题所有的实施进度报告
    @action(detail=False, methods=['get'], url_path='show_report')
    def show_report(self, request):
        subject_id = request.query_params.dict().get('subjectId')
        queryset = self.queryset.filter(state='已提交', subject_id=subject_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializer.data}, status=status.HTTP_200_OK)
