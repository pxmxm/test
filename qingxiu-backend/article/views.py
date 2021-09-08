from datetime import datetime

# Create your views here.
from rest_framework import status
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from article.models import Article
from article.serializers import ArticleSerializers
from rest_framework_mongoengine import viewsets as mongodb_viewsets

from users.models import User
from utils.oss import OSS


class ArticleViewSet(mongodb_viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializers

    # 移动端查询
    @action(detail=False, methods=['post'], url_path='app_query')
    def app_query(self, request):
        title = request.data['title']
        if title:
            limit = request.query_params.dict().get('limit', None)
            queryset = self.queryset.order_by('-updated').filter(title__contains=title, state='已发布')
            page = self.paginate_queryset(queryset)
            if page is not None and limit is not None:
                serializers = self.get_serializer(page, many=True)
                return self.get_paginated_response({"code": 0, "message": "请求成功", "detail": serializers.data})
            serializers = self.get_serializer(queryset, many=True)
            return Response({"code": 0, "message": "请求成功", "detail": serializers.data}, status=status.HTTP_200_OK, )
        else:
            return Response({"code": 0, "message": "请输入文件名"}, status=status.HTTP_200_OK)

    # 政策、通知公告展示
    @action(detail=False, methods=['get'], url_path='types/(?P<types>\w+)')
    def get_article_by_type(self, request, types):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-updated').filter(types=types, state='已发布')
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK)


class ArticlesViewSet(mongodb_viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializers

    # 判断用户登录态
    permission_classes = [IsAuthenticated, ]
    authentication_classes = (JSONWebTokenAuthentication,)

    def create(self, request, *args, **kwargs):
        # 判断用户登录态
        user = request.user
        if User.objects.filter(id=user.id, isDelete=False).exists():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            queryset = self.queryset.get(id=serializer.data['id'])
            if queryset.state == '预约发布':
                queryset.subscribe = request.data['subscribe']
                queryset.updated = request.data['subscribe']
                queryset.save()
            else:
                queryset.updated = datetime.now()
                queryset.save()
            return Response({"code": 0, "message": "保存成功", "detail": serializer.data}, status=status.HTTP_201_CREATED,
                            headers=headers)
        else:
            return Response({"code": 1, "message": "身份认证信息未提供"}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        user = request.user
        if User.objects.filter(id=user.id, isDelete=False).exists():
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            queryset = self.queryset.get(id=serializer.data['id'])
            if queryset.state == '预约发布':
                queryset.subscribe = request.data['subscribe']
                queryset.updated = request.data['subscribe']
                queryset.save()
            else:
                queryset.updated = datetime.now()
                queryset.save()
            return Response(serializer.data)
        else:
            return Response({"code": 1, "message": "身份认证信息未提供"}, status=status.HTTP_401_UNAUTHORIZED)

    """
    管理员系统
    """

    # 政策通知公告发布管理  已发布 已删除 预约发布 草稿箱展示
    @action(detail=False, methods=['get'], url_path='state/(?P<state>\w+)')
    def get_article_by_state(self, request, state):
        limit = request.query_params.dict().get('limit', None)
        queryset = self.queryset.order_by('-updated').filter(state=state)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK, )

    # 管理员系统
    # 政策、通知公告 条件查询
    @action(detail=False, methods=['post'], url_path='query')
    def conditions(self, request):
        limit = request.query_params.dict().get('limit', None)
        json_data = request.data
        keys = {
            "title": "title__contains",
            "author": "author__contains",
            "state": "state",
            "types": "types"
        }
        data = {keys[k]: v for k, v in json_data.items() if k in keys and json_data[k] != '' and json_data[k] != '全部'}
        queryset = self.queryset.order_by('-updated').filter(**data)
        page = self.paginate_queryset(queryset)
        if page is not None and limit is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializers = self.get_serializer(queryset, many=True)
        return Response({"code": 0, "message": "ok", "detail": serializers.data}, status=status.HTTP_200_OK, )

    # 管理员系统
    # 根据ID删除已发布公告 逻辑删除 批量删除
    @action(detail=False, methods=['delete'], url_path='delete')
    def del_article_by_id(self, request):
        delete_id = request.data['deleteId']
        # delete_id = literal_eval(delete_id)
        for i in delete_id:
            try:
                queryset = self.queryset.get(id=i)
                if queryset.state == '已发布':
                    queryset.state = '已删除'
                    queryset.save()
                elif queryset.state == '预约发布' or queryset.state == '草稿箱':
                    self.perform_destroy(queryset)
            except Exception as e:
                return Response({"code": 1, "message": "错误操作"})
        return Response({"code": 0, "message": '公告已删除'}, )

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        data = request.data
        file_name = str(list(data.values())[0])
        path = OSS().put_by_backend(path=file_name, data=list(data.values())[0].read())
        return Response({"code": 0, "message": "上传成功", "detail": path}, status=status.HTTP_200_OK)
