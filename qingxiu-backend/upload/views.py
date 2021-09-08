# -*- coding: utf-8 -*-
# @Time : 2020/09/08
# @Author : hongjian

import os
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from backend.settings import MINIO_HOST, MINIO_PORT
from subject.serializers import SubjectSerializers
from upload.models import Templates, LoginLog
from upload.serializers import TemplatesSerializers, LoginLogSerializers
from utils.oss import OSS


class UploadView(APIView):
    """
    处理所有文件上传和下载的视图类
    """

    mime = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.pdf': 'application/pdf',
        '.txt': 'text/plain'
    }

    def get(self, request):
        """
        :param request: request
        :return: 返回文件
        """
        path = request.GET.get('name')
        file = OSS().get(path)
        ext = os.path.splitext(path)[1].lower()
        m = self.mime[ext] if self.mime.__contains__(ext) else 'application/octet-stream'
        return HttpResponse(file, content_type=m)

    def post(self, request):
        """
        :param request: request
        :return: 返回文件访问路径
        """
        file = request.FILES.get('file')
        if not file:
            return Response({'error_code': '文件 file 不存在'})
        hex_name = OSS().put(file.name, file.read())
        return Response({'url': '%s:%s/file/%s' % (MINIO_HOST, MINIO_PORT, hex_name)})


class TemplatesViewSet(viewsets.ModelViewSet):
    queryset = Templates.objects.all()
    serializer_class = TemplatesSerializers

    #  上传
    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        file = request.data['file']
        file_name = request.data['fileName']
        types = request.data['types']
        name = request.data['name']
        path = OSS().put_by_temples(path=file_name, data=file.read())
        self.queryset.create(name=name, types=types, version='1.3', path=path)
        return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)

    # 展示
    @action(detail=False, methods=['get'], url_path='show')
    def show(self, request):
        types = request.query_params.dict().get('types')
        version = request.query_params.dict().get('version')
        queryset = self.queryset.filter(version=version, types=types)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)

    # 专家上传模版展示
    @action(detail=False, methods=['get'], url_path='shows')
    def shows(self, request):
        queryset = self.queryset.filter(version='1.3', types='专家上传模版')
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK)


class LoginLogViewSet(viewsets.ModelViewSet):
    queryset = LoginLog.objects.all()
    serializer_class = LoginLogSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def list(self, request, *args, **kwargs):
        user = request.user
        limit = request.query_params.dict().get('limit', None)
        if user.type == '管理员':
            instance = self.queryset.order_by('-created').filter(user__type__in=['管理员', '分管员'])
        else:
            instance = self.queryset.order_by('-created').filter(user=user)
        page = self.paginate_queryset(instance)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"code": 0, "message": "请求成功", "detail": serializer.data})
        serializer = self.get_serializer(instance, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data})

    @action(detail=False, methods=['post'], url_path='retrieve')
    def retrieve_log(self, request, *args, **kwargs):
        json_data = request.data
        keys = {
            "name": "user__username__contains",
            "type": "user__type",
            "startStop": "created__range"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '全部' and json_data[k] != ''
                and json_data[k] != None}
        queryset = self.queryset.filter(user__type__in=['管理员', '分管员']).filter(**data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "请求成功", "detail": serializer.data})
