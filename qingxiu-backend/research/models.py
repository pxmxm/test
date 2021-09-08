from django.db import models

# Create your models here.
# 实地调研
from users.models import User


class FieldResearch(models.Model):
    planCategory = models.CharField(max_length=252, verbose_name='计划类别', null=True, blank=True)
    unitName = models.CharField(max_length=252, verbose_name='单位名称', null=True, blank=True)
    subjectName = models.CharField(max_length=252, verbose_name='课题名称', null=True, blank=True)
    times = models.DateField(verbose_name='实地调研时间')
    place = models.CharField(max_length=252, verbose_name='调研地点')
    personnel = models.CharField(max_length=252, verbose_name='调研人员')
    opinion = models.TextField(verbose_name='调研意见')
    attachmentPDF = models.CharField(max_length=252, verbose_name='附件', null=True, blank=True)

    class Meta:
        db_table = 'field_research'


# 立项建议
class Proposal(models.Model):
    scienceFunding = models.BigIntegerField(verbose_name='科技局建议经费（万元）', )
    scienceProposal = models.CharField(verbose_name='科技局立项建议', max_length=252)
    firstFunding = models.BigIntegerField(verbose_name='首笔经费金额（万元）')
    charge = models.ForeignKey(to=User, verbose_name='分管员', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'proposal'
