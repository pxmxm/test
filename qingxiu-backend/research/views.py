from ast import literal_eval
from decimal import Decimal

from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from research.models import FieldResearch, Proposal
from research.serializers import FieldResearchSerializers, ProposalSerializers
from subject.models import Subject, Process

# 实地调研
from tpl.views_download import generate_field_research_pdf


class FieldResearchViewSet(viewsets.ModelViewSet):
    queryset = FieldResearch.objects.all()
    serializer_class = FieldResearchSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    @action(detail=False, methods=['get'], url_path='initial')
    def initial_data(self, request):
        user = request.user
        subject_id = request.query_params.dict().get('subjectId')
        subject = Subject.objects.get(id=subject_id)
        data = {
            "planCategory": subject.project.category.planCategory,
            "unitName": subject.unitName,
            "subjectName": subject.subjectName,
            "personnel": user.name,
        }
        return Response({"code": 0, "message": "请求成功", "detail": data},status=status.HTTP_200_OK)

    # 立项调研 创建实地调研/分管员
    def create(self, request, *args, **kwargs):
        subject_id = request.data['subjectId']
        subject = Subject.objects.get(id=subject_id)
        if subject.fieldResearch:
            partial = kwargs.pop('partial', False)
            queryset = self.queryset.get(id=subject.fieldResearch_id)
            serializers = self.get_serializer(queryset, data=request.data, partial=partial)
            serializers.is_valid(raise_exception=True)
            self.perform_update(serializers)
            queryset.attachmentPDF = generate_field_research_pdf(field_research_id=queryset.id)
            queryset.save()
            return Response({'code': 0, 'message': 'ok', 'detail': serializers.data}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            subject.fieldResearch_id = serializer.data['id']
            subject.research = True
            subject.save()
            queryset = self.queryset.get(id=serializer.data['id'])
            queryset.attachmentPDF = generate_field_research_pdf(field_research_id=queryset.id)
            queryset.save()
            return Response({'code': 0, 'message': 'ok', 'detail': serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)

    # 实地调研展示
    @action(detail=False, methods=['get'], url_path='show')
    def show_field_research(self, request, *args, **kwargs):
        subject_id = request.query_params.dict().get('subjectId')
        subject = Subject.objects.get(id=subject_id)
        queryset = self.queryset.filter(id=subject.fieldResearch_id)
        serializers = self.get_serializer(queryset, many=True)
        return Response({'code': 0, 'message': 'ok', 'detail': serializers.data}, status=status.HTTP_200_OK)


# 立项建议
class ProposalViewSet(viewsets.ModelViewSet):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializers
    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    # 立项建议提交
    @action(detail=False, methods=['post'], url_path='proposal_submit')
    def proposal_submit(self, request):
        user = request.user
        data = request.data["data"]
        for i in data:
            subject = Subject.objects.get(id=(i["subjectId"]))
            queryset = self.queryset.create(scienceFunding=int(Decimal(i["scienceFunding"])),
                                            scienceProposal=i["scienceProposal"],
                                            firstFunding=int(Decimal(i['firstFunding'])),
                                            charge=user)
            subject.proposal = queryset
            subject.advice = True
            subject.subjectState = '项目下达'
            subject.save()
            Process.objects.create(state='项目下达', subject=subject)
        return Response({"code": 0, "message": "提交成功，立项审批通过后请前往项目下达页面下达立项结果"}, status=status.HTTP_200_OK)
