from django.db import models

# Create your models here.
from subject.models import Subject


# 实施进度报告
class ProgressReport(models.Model):
    name = models.CharField(max_length=252, verbose_name='项目名称')
    contractNo = models.CharField(max_length=252, verbose_name='合同编号')
    unit = models.CharField(max_length=252, verbose_name='承担单位')
    head = models.CharField(max_length=252, verbose_name='负责人')
    fillTime = models.DateField(verbose_name='填表时间', null=True, blank=True)
    startStopYear = models.CharField(max_length=252, verbose_name='起止时间')
    workProgress = models.TextField(verbose_name='工作进度及具体实施情况')
    problem = models.TextField(verbose_name='存在问题及未按进度完成的原因')
    planMeasures = models.TextField(verbose_name='下一步计划及措施')
    state = models.CharField(max_length=252, verbose_name='进度实时报告状态', default='待提交')
    subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='progress_report_subject',
                                on_delete=models.SET_NULL, null=True, blank=True)
    attachmentPDF = models.CharField(max_length=252, verbose_name='附件', null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'progress_report'
