# -*- coding: utf-8 -*-
# @Time : 2020/09/08
# @Author : hongjian
import os
import re
import uuid
from datetime import datetime

from minio import Minio
from io import BytesIO
from django.conf import settings

from backend.settings import MINIO_HOST, MINIO_PORT, MEDIA_ROOT
from utils.scanning import get_file_content

MINIO = settings.MINIO  # 从 setting.py 导入配置


class OSS:
    """
    文件服务器对象存储操作类，包含 get put 方法
    """

    def __init__(self):
        """
        初始化 MinIO 连接客户端
        MIME 映射
        """
        self.minioClient = Minio(MINIO['SERVER'] + ':' + MINIO['PORT'], access_key=MINIO['ACCESS_KEY'],
                                 secret_key=MINIO['SECRET_KEY'], secure=False)

        self.mimes = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain'
        }

    def put(self, path, data):
        """
        :param path: 文件系统的路径 (包含文件名的全路径 eg: path/filename.jpg)
        :param data: 文件数据 （bytes）
        """

        filename = path
        ext = os.path.splitext(filename)[1]
        hex_name = re.sub(r':|\.', '', datetime.now().__str__().split(' ')[1]) + ext
        mine = self.mimes[ext] if self.mimes.__contains__(ext) else 'application/octet-stream'
        file = BytesIO(data)
        self.minioClient.put_object('file', hex_name, file, len(data), mine)
        return hex_name

    def get(self, path):
        """
        :param path: 文件系统的路径 (包含文件名的全路径 eg: path/filename.jpg)
        :return: 文件数据 （bytes）
        """
        response = self.minioClient.get_object('file', path)
        return response.read()

    def put_by_backend(self, path, data):
        """
        :param path: 文件系统的路径 (包含文件名的全路径 eg: path/filename.jpg)
        :param data: 文件数据 （bytes）
        """
        filename = path
        ext = os.path.splitext(filename)[1]
        hex_name = re.sub(r':|\.', '', datetime.now().__str__().split(' ')[1]) + ext
        mine = self.mimes[ext] if self.mimes.__contains__(ext) else 'application/octet-stream'
        file = BytesIO(data)
        self.minioClient.put_object('file', hex_name, file, len(data), mine)
        return 'http://%s:%s/file/%s' % (MINIO_HOST, MINIO_PORT, hex_name)

    def put_by_temples(self, path, data):
        """
        :param path: 文件系统的路径 (包含文件名的全路径 eg: path/filename.jpg)
        :param data: 文件数据 （bytes）
        """
        filename = path
        ext = os.path.splitext(filename)[1]
        # hex_name = re.sub(r':|\.', '', datetime.now().__str__().split(' ')[1]) + ext
        mine = self.mimes[ext] if self.mimes.__contains__(ext) else 'application/octet-stream'
        file = BytesIO(data)
        self.minioClient.put_object('file', filename, file, len(data), mine)
        return 'http://%s:%s/file/%s' % (MINIO_HOST, MINIO_PORT, filename)

    # 根据路径上传附件
    def put_pdfPath(self, path):
        """
        :param path: 文件系统的路径 (包含文件名的全路径 eg: path/filename.jpg)
        :param data: 文件数据 （bytes）
        """
        filename = path
        ext = os.path.splitext(filename)[1]
        hex_name = re.sub(r':|\.', '', datetime.now().__str__().split(' ')[1]) + ext
        mine = self.mimes[ext] if self.mimes.__contains__(ext) else 'application/octet-stream'
        self.minioClient.fput_object('file', hex_name, path, mine, metadata=None)
        return 'http://%s:%s/file/%s' % (MINIO_HOST, MINIO_PORT, hex_name)

    def delete(self, bucket_name, file_name):
        self.minioClient.remove_object(bucket_name, file_name)
        return "删除失败"

    def put_tpl(self, path, data):
        """
        :param path: 文件系统的路径 (包含文件名的全路径 eg: path/filename.jpg)
        :param data: 文件数据 （bytes）
        """
        filename = path
        ext = os.path.splitext(filename)[1]
        hex_name = re.sub(r':|\.', '', datetime.now().__str__().split(' ')[1]) + ext
        mine = self.mimes[ext] if self.mimes.__contains__(ext) else 'application/octet-stream'
        file = BytesIO(data)
        self.minioClient.put_object('template', hex_name, file, len(data), mine)
        return 'http://%s:%s/template/%s' % (MINIO_HOST, MINIO_PORT, hex_name)

    def del_tpl(self, filename):
        self.minioClient.remove_object('template', filename)
        return True

    def get_tpl(self, path):
        response = self.minioClient.get_object('template', path)
        return response.read()


if __name__ == '__main__':
    # 上传测试
    with open('../file/192908240324.png', 'rb') as f:
        OSS().put('192908240324.png', f.read())

    # 获取测试
    print(type(OSS().get('192908240324.png')))
