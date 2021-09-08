from django.db import models


# Create your models here.


# 企业黑名单
from subject.models import Subject


class UnitBlacklist(models.Model):
    unitName = models.CharField(max_length=252, verbose_name='单位名称')
    creditCode = models.CharField(max_length=252, verbose_name='统一社会信用代码')
    contact = models.CharField(max_length=252, verbose_name='联系人')
    mobile = models.CharField(max_length=252, verbose_name='联系电话')
    degreeOf = models.CharField(max_length=151, verbose_name='失信程度')
    breachTime = models.DateField(verbose_name='列为失信人时间')
    disciplinaryTime = models.DateField(verbose_name='失信惩戒')
    returnReason = models.CharField(max_length=2520, verbose_name='移入原因')
    # subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='unit_blacklist_subject', on_delete=models.SET_NULL, null=True, blank=True)
    subjectName = models.CharField(max_length=252, verbose_name='课题名称', null=True, blank=True)
    annualPlan = models.CharField(max_length=252, verbose_name='计划年度', null=True, blank=True)
    declareTime = models.DateField(verbose_name='申报时间', null=True, blank=True)
    contractNo = models.CharField(max_length=252, verbose_name='合同编号', null=True, blank=True)
    isArchives = models.BooleanField(verbose_name='是否留存未档案', default=False)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'unit_blacklist'


# 项目负责人黑名单
class ProjectLeader(models.Model):
    name = models.CharField(max_length=252, verbose_name='课题负责人姓名')
    idNumber = models.CharField(max_length=252, verbose_name='课题负责人身份证号码')
    unitName = models.CharField(max_length=252, verbose_name='工作单位', null=True)
    mobile = models.CharField(max_length=252, verbose_name='联系电话')
    degreeOf = models.CharField(max_length=151, verbose_name='失信程度')
    breachTime = models.DateField(verbose_name='列为失信人时间')
    disciplinaryTime = models.DateField(verbose_name='失信惩戒')
    returnReason = models.CharField(max_length=2520, verbose_name='移入原因')
    subjectName = models.CharField(max_length=252, verbose_name='课题名称', null=True, blank=True)
    annualPlan = models.CharField(max_length=252, verbose_name='计划年度', null=True, blank=True)
    declareTime = models.DateField(verbose_name='申报时间', null=True, blank=True)
    contractNo = models.CharField(max_length=252, verbose_name='合同编号', null=True, blank=True)
    isArchives = models.BooleanField(verbose_name='是否留存未档案', default=False)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'project_leader'


# 专家黑名单
class ExpertsBlacklist(models.Model):
    name = models.CharField(max_length=252, verbose_name='姓名')
    idNumber = models.CharField(max_length=252, verbose_name='身份证号码')
    mobile = models.CharField(max_length=252, verbose_name='联系电话')
    unitName = models.CharField(max_length=252, verbose_name='工作单位')
    degreeOf = models.CharField(max_length=151, verbose_name='失信程度')
    breachTime = models.DateField(verbose_name='列为失信人时间')
    disciplinaryTime = models.DateField(verbose_name='失信惩戒')
    returnReason = models.CharField(max_length=2520, verbose_name='移入原因')
    subjectName = models.CharField(max_length=252, verbose_name='课题名称', null=True, blank=True)
    annualPlan = models.CharField(max_length=252, verbose_name='计划年度', null=True, blank=True)
    declareTime = models.DateField(verbose_name='申报时间', null=True, blank=True)
    contractNo = models.CharField(max_length=252, verbose_name='合同编号', null=True, blank=True)
    isArchives = models.BooleanField(verbose_name='是否留存未档案', default=False)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'experts_blacklist'


# 机构黑名单
class AgenciesBlacklist(models.Model):
    name = models.CharField(max_length=252, verbose_name='服务机构名称')
    creditCode = models.CharField(max_length=252, verbose_name='信用代码')
    contact = models.CharField(max_length=252, verbose_name='联系人')
    mobile = models.CharField(max_length=252, verbose_name='联系电话')
    degreeOf = models.CharField(max_length=151, verbose_name='失信程度')
    breachTime = models.DateField(verbose_name='列为失信人时间')
    disciplinaryTime = models.DateField(verbose_name='失信惩戒')
    returnReason = models.CharField(max_length=2520, verbose_name='移入原因')
    subjectName = models.CharField(max_length=252, verbose_name='课题名称', null=True, blank=True)
    annualPlan = models.CharField(max_length=252, verbose_name='计划年度', null=True, blank=True)
    declareTime = models.DateField(verbose_name='申报时间', null=True, blank=True)
    contractNo = models.CharField(max_length=252, verbose_name='合同编号', null=True, blank=True)
    isArchives = models.BooleanField(verbose_name='是否留存未档案', default=False)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'agencies_blacklist'
