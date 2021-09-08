from django.db import models
# Create your models here.

# 申报项目
class DeclareProject(models.Model):
    annualPlan = models.CharField(max_length=252, verbose_name='年度计划', null=True, blank=True)
    projectBatch = models.CharField(max_length=252, verbose_name='项目批次', null=True, blank=True)
    planCategory = models.CharField(max_length=252, verbose_name='计划类别', null=True, blank=True)
    projectName = models.CharField(max_length=252, verbose_name='项目名称', null=True, blank=True)
    projectNumber = models.BigIntegerField(verbose_name='申报项目数量', default=0)

    class Meta:
        db_table = 'declare_project'
