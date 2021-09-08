# Create your models here.
from django.db import models


# 项目批次
from users.models import User


class Batch(models.Model):
    annualPlan = models.CharField(max_length=252, verbose_name='年度计划')
    projectBatch = models.CharField(max_length=252, verbose_name='项目批次')
    declareTime = models.CharField(max_length=252, verbose_name='申报时间', null=True, blank=True)
    isActivation = models.CharField(max_length=252, verbose_name='是否禁用 启用', null=True, blank=True)
    state = models.CharField(max_length=252, verbose_name='评审专家审核状态', default='-')
    OPINION = (('0', '-'), ('1', '待提交'), ('2', '待审核'), ('3', '通过'), ('4', '不通过'))
    opinionState = models.CharField(max_length=2, verbose_name='评审意见审核状态', choices=OPINION, default=0)
    returnReason = models.CharField(max_length=252, verbose_name='退回原因', null=True, blank=True)
    submitTime = models.CharField(max_length=252, verbose_name='提交时间', default='-')
    agency = models.ForeignKey(to=User, verbose_name='管理服务机构', on_delete=models.SET_NULL, null=True, blank=True)
    handOverState = models.BooleanField(verbose_name='是否移交评估机构', default=False)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'batch'


# 项目类别
class Category(models.Model):
    planCategory = models.CharField(max_length=252, verbose_name='计划类别')
    batch = models.ForeignKey(to=Batch, verbose_name='项目名称', related_name='batch_category', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'category'


# 项目名称
class Project(models.Model):
    projectName = models.CharField(max_length=252, verbose_name='项目名称')
    category = models.ForeignKey(to=Category, verbose_name='项目类别', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间', )
    # 分管员
    charge = models.ManyToManyField(to=User, verbose_name='分管员', related_name='charge_user', blank=True)

    class Meta:
        db_table = 'project'

