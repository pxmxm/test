from django.db import models
# Create your models here.
from subject.models import Subject


# 项目变更类型
class ChangeSubject(models.Model):
    changeType = models.CharField(max_length=252, verbose_name='变更类型', null=True, blank=True)
    state = models.CharField(max_length=252, verbose_name='状态', null=True, blank=True)
    isUpload = models.BooleanField(default=False, verbose_name='是否上传附件')
    attachment = models.CharField(max_length=252, verbose_name='附件', null=True, blank=True)
    changeTime = models.DateTimeField(auto_now_add=True, verbose_name='变更时间', null=True, blank=True)
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间', null=True, blank=True)
    subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='subject_change', on_delete=models.SET_NULL,
                                null=True, blank=True)

    class Meta:
        db_table = 'change_subject'


# 项目负责人
class ProjectLeaderChange(models.Model):
    name = models.CharField(max_length=252, verbose_name='项目名称')
    contractNo = models.CharField(max_length=252, verbose_name='合同编号')
    unit = models.CharField(max_length=252, verbose_name='承担单位')
    head = models.CharField(max_length=252, verbose_name='负责人')
    changeHead = models.CharField(max_length=252, verbose_name='变更后负责人')
    phone = models.CharField(max_length=12, verbose_name='联系电话', null=True, blank=True)
    idNumber = models.CharField(max_length=252, verbose_name='课题负责人身份证号码', null=True, blank=True)
    changeReason = models.TextField(max_length=2520, verbose_name='变更理由')
    unitOpinion = models.TextField(max_length=2520, verbose_name='申请单位意见')
    kOpinion = models.TextField(max_length=2520, verbose_name='科技局意见', null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    changeSubject = models.ForeignKey(to=ChangeSubject, verbose_name='课题变更类型', on_delete=models.SET_NULL, null=True,
                                      blank=True)

    class Meta:
        db_table = 'project_leader_change'


# 重大技术路线调整
class TechnicalRouteChange(models.Model):
    name = models.CharField(max_length=252, verbose_name='项目名称')
    contractNo = models.CharField(max_length=252, verbose_name='合同编号')
    unit = models.CharField(max_length=252, verbose_name='承担单位')
    head = models.CharField(max_length=252, verbose_name='负责人')
    adjustmentContent = models.TextField(max_length=2520, verbose_name='调整内容')
    adjustmentAfter = models.TextField(max_length=2520, verbose_name='调整后')
    adjustmentReason = models.TextField(max_length=2520, verbose_name='调整理由')
    unitOpinion = models.TextField(max_length=2520, verbose_name='申请单位意见')
    kOpinion = models.TextField(max_length=2520, verbose_name='科技局意见', null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    changeSubject = models.ForeignKey(to=ChangeSubject, verbose_name='课题变更类型', on_delete=models.SET_NULL, null=True,
                                      blank=True)

    class Meta:
        db_table = 'technical_route_change'


# 项目延期
class ProjectDelayChange(models.Model):
    name = models.CharField(max_length=252, verbose_name='项目名称')
    contractNo = models.CharField(max_length=252, verbose_name='合同编号')
    unit = models.CharField(max_length=252, verbose_name='承担单位')
    head = models.CharField(max_length=252, verbose_name='负责人')
    delayTime = models.CharField(max_length=252, verbose_name='延期时间', default=None)
    delayReason = models.TextField(max_length=2520, verbose_name='延期理由')
    unitOpinion = models.TextField(max_length=2520, verbose_name='申请单位意见')
    kOpinion = models.TextField(max_length=2520, verbose_name='科技局意见', null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    changeSubject = models.ForeignKey(to=ChangeSubject, verbose_name='课题变更类型', on_delete=models.SET_NULL, null=True,
                                      blank=True)

    class Meta:
        db_table = 'project_delay_change'
