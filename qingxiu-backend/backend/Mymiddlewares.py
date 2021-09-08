import time
import json

from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
import urllib.parse
# 获取日志logger
import logging

from rest_framework import status

logger = logging.getLogger(__name__)


class LogMiddle(MiddlewareMixin):
    # 日志处理中间件
    def process_request(self, request):
        # 存放请求过来时的时间
        request.init_time = time.time()
        return None

    def process_response(self, request, response):
        try:
            # 用户
            username = request.user
            # 耗时
            localtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            # 请求路径
            path = request.path
            # 请求方式
            method = request.method
            # 响应状态码
            status_code = response.status_code
            # 响应内容
            content = response.content
            # 记录信息
            content = str(content.decode('utf-8'))
            content = urllib.parse.unquote(content)
            content = (json.loads(content))
            message = '%s %s %s %s %s %s' % (username, localtime, path, method, status_code, content)
            logger.info(message)
        except Exception as e:
            print(e)
            logger.critical('系统错误')
        return response


class get_token(MiddlewareMixin):
    def process_request(self, request):
        if request.META.get('HTTP_AUTHORIZATION', None) is not None:
            token = request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
            if cache.get('%s' % token, None) is None:
                return '请重新登录'
        return None

    def process_response(self, request, response):
        if request.META.get('HTTP_AUTHORIZATION', None) is not None:
            token = request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
            if cache.get('%s' % token, None) is None:
                return HttpResponse("请重新登录")
            if cache.ttl('%s' % token) < 60*60:
                cache.set('%s' % token, {'token': token}, 60*60)
        return response


class get_username_token(MiddlewareMixin):
    def process_request(self, request):
        if request.META.get('HTTP_AUTHORIZATION', None) is not None:
            token = request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
            if cache.get('%s' % token, None) is None:
                return '请重新登录'
        return None

    def process_response(self, request, response):
        if request.META.get('HTTP_AUTHORIZATION', None) is not None:
            token = request.META.get('HTTP_AUTHORIZATION').split(' ')[1]
            if request.user:
                if not request.user.is_anonymous:
                    if request.user.type == '管理员' or request.user.type == '分管员':
                        if cache.get('%s' % request.user.username, None) is not None:
                            if token != cache.get('%s' % request.user.username)['token']:
                                return HttpResponse("账号已在其他设备登录，请重新登录")
        return response