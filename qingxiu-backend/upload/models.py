from django.db import models


# Create your models here.
from users.models import User


class Templates(models.Model):
    types = models.CharField(max_length=252, verbose_name='状态')
    version = models.CharField(max_length=252, verbose_name='版本')
    name = models.CharField(max_length=252, verbose_name='文件名')
    path = models.CharField(max_length=252, verbose_name='路径')

    class Meta:
        db_table = 'templates'


class LoginLog(models.Model):
    user = models.ForeignKey(to=User, verbose_name='用户', on_delete=models.SET_NULL, null=True, blank=True)
    ip = models.CharField(max_length=20, verbose_name='ip')
    address = models.CharField(max_length=20, verbose_name='IP归属地', null=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', null=True)

    class Meta:
        db_table = 'login_log'