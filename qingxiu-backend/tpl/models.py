from django.db import models


class Template(models.Model):
    TYPE = (
        (1, '申报书'),
        (2, '合同'),
        (3, '项目终止'),
        (4, '拨款申请单'),
        (5, '专家评审意见'),
        (6, '专家组评审意见'),
        (7, '技术路线变更'),
        (8, '项目负责人变更'),
        (9, '项目延期'),
        (10, '课题组成员变更'),
        (11, '结题验收'),
        (12, '实时进度'),
        (13, '调研'),
    )
    name = models.CharField(max_length=254, null=False)
    url = models.CharField(max_length=254, null=False)
    type = models.IntegerField(choices=TYPE)
    version = models.CharField(max_length=254, null=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['type', 'version']
        db_table = 'template'
