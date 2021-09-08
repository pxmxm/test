# Create your models here.
from django.db import models

from mongoengine import Document, fields


class Article(Document):
    """
    政策、通知公告
    """
    # TYPES = (('T', '通知公告'), ('Z', '政策'))
    title = fields.StringField(max_length=252, verbose_name='标题')
    content = fields.StringField(verbose_name='内容')
    author = fields.StringField(verbose_name='作者')
    source = fields.StringField(verbose_name='来源')
    types = fields.StringField(verbose_name='公告类型', choices=['通知公告', '政策'])
    state = fields.StringField(verbose_name='公告状态', choices=['已发布', '已删除', '预约发布', '草稿箱'])
    subscribe = fields.DateTimeField(null=True, verbose_name='预约发布时间')
    updated = fields.DateTimeField(verbose_name='更新时间')

