from django.contrib.postgres.fields import JSONField
from django.db import models


# 曾参评审与过的项目类型
class ExpertProjectType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='项目类别名称')

    class Meta:
        db_table = 'expert_project_type'


# 专家职称
class ExpertTitle(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='职称')

    class Meta:
        db_table = 'expert_title'


# 专家领域
class ExpertField(models.Model):
    enable = models.BooleanField(default=False, verbose_name='是否为 可选择的领域')
    name = models.CharField(max_length=100, verbose_name='专家领域')
    parent = models.ForeignKey(
        to='self', on_delete=models.CASCADE, null=True, default=None, verbose_name='父级选项')

    class Meta:
        db_table = 'expert_field_info'


# 专家信息表
class Expert(models.Model):
    name = models.CharField(max_length=150, verbose_name='姓名')
    id_card_no = models.CharField(max_length=20, verbose_name='身份证号')
    mobile = models.CharField(max_length=20, verbose_name='联系电话')
    email = models.EmailField(default='', verbose_name='邮箱')
    EDUCATION = ((0, '博士'), (1, '硕士'), (2, '学士'), (3, '其他'))
    education = models.SmallIntegerField(
        null=True, choices=EDUCATION, verbose_name='最高学历')
    DEGREE = ((0, '博士研究生'), (1, '硕士研究生'), (2, '大学本科'), (3, '大学专科'), (4, '其他'))
    degree = models.SmallIntegerField(
        null=True, choices=DEGREE, verbose_name='最高学位')
    TITLE = ((0, '无'), (1, '高级工程师'))
    title = models.ForeignKey(
        to=ExpertTitle, verbose_name='职称', on_delete=models.SET_NULL, null=True)
    title_no = models.CharField(
        max_length=100, default='', verbose_name='职称证书号')
    company = models.CharField(max_length=150, default='', verbose_name='所在单位')
    duty = models.CharField(max_length=100, default='', verbose_name='职务')
    academician = models.BooleanField(default=None, null=True, verbose_name='院士')
    supervisor = models.BooleanField(default=None, null=True, verbose_name='博士生导师')
    overseas = models.BooleanField(default=None, null=True, verbose_name='留学回国')
    reason = models.CharField(max_length=200, default='', verbose_name='原因')
    date = models.DateField(default=None, null=True, verbose_name='时间')
    LABORATORY = ((0, '国家级'), (1, '省（市）部级'))
    laboratory = models.SmallIntegerField(
        null=True, choices=LABORATORY, verbose_name='所在重点实验室级别')

    participate = models.ManyToManyField(
        to=ExpertProjectType, verbose_name='曾参与评审过的项目类型')

    field = models.ManyToManyField(
        to=ExpertField, related_name='expert', verbose_name='专家领域')

    tags = models.CharField(max_length=252, default='', verbose_name='专家标签')

    bank = models.CharField(max_length=100, default='', verbose_name='开户银行')
    bank_branch = models.CharField(
        max_length=100, default='', verbose_name='开户银行所属支行')
    bank_account = models.CharField(
        max_length=100, default='', verbose_name='银行账号')

    active = models.BooleanField(default=False, verbose_name='是否可以登陆')
    deleted = models.BooleanField(default=False, verbose_name='是否删除')

    STATE = (
        (0, '未入库'),
        (1, '审核中'),
        (2, '审核未通过'),
        (3, '已入库'),
        (4, '已被动移出'),
        (5, '退库审批'),
        (6, '已退库')
    )
    state = models.SmallIntegerField(
        choices=STATE, default=0, verbose_name='专家账号状态')

    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'expert'


# 教育简历
class ExpertEducation(models.Model):
    school = models.CharField(max_length=100, verbose_name='学校')
    major = models.CharField(max_length=100, verbose_name='专业')
    EDUCATION = ((0, '博士'), (1, '硕士'), (2, '学士'), (3, '其他'))
    education = models.SmallIntegerField(choices=EDUCATION, verbose_name='学位')
    date_start = models.DateField(verbose_name='开始日期')
    date_stop = models.DateField(null=True, verbose_name='结束日期')

    expert = models.ForeignKey(
        to=Expert, verbose_name='专家', on_delete=models.CASCADE)

    class Meta:
        ordering = ('id',)
        db_table = 'expert_experience_education'


# 工作简历
class ExpertWork(models.Model):
    company = models.CharField(max_length=150, verbose_name='工作单位')
    duty = models.CharField(max_length=100, verbose_name='职务')
    content = models.CharField(max_length=100, verbose_name='工作内容')
    date_start = models.DateField(verbose_name='开始日期')
    date_stop = models.DateField(null=True, verbose_name='结束日期')

    expert = models.ForeignKey(
        to=Expert, verbose_name='专家', on_delete=models.CASCADE)

    class Meta:
        ordering = ('id',)
        db_table = 'expert_experience_work'


# 担任社会职务经历
class ExpertDuty(models.Model):
    organization = models.CharField(max_length=100, verbose_name='组织或团体名称')
    duty = models.CharField(max_length=100, verbose_name='职务')
    remarks = models.CharField(max_length=100, verbose_name='备注')
    date_start = models.DateField(verbose_name='开始日期')
    date_stop = models.DateField(null=True, verbose_name='结束日期')

    expert = models.ForeignKey(
        to=Expert, verbose_name='专家', on_delete=models.CASCADE)

    class Meta:
        ordering = ('id',)
        db_table = 'expert_history_duty'


# 担任其他评审专家机构情况
class ExpertAgency(models.Model):
    agency = models.CharField(max_length=100, verbose_name='评审机构名称')
    duty = models.CharField(max_length=100, verbose_name='职务')
    remarks = models.CharField(max_length=100, verbose_name='备注')
    date_start = models.DateField(verbose_name='开始日期')
    date_stop = models.DateField(null=True, verbose_name='结束日期')

    expert = models.ForeignKey(
        to=Expert, verbose_name='专家', on_delete=models.CASCADE)

    class Meta:
        ordering = ('id',)
        db_table = 'expert_history_agency'


# 退库申请记录
class ExpertRecordExit(models.Model):
    user = models.CharField(max_length=100, null=True,
                            default=None, verbose_name='操作管理员')
    date = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    reason = models.CharField(max_length=100, verbose_name='原因')
    expert = models.ForeignKey(
        to=Expert, on_delete=models.CASCADE, verbose_name='专家')

    class Meta:
        db_table = 'expert_record_exit'


# 专家修改信息记录
class ExpertRecordEdit(models.Model):
    date = models.DateTimeField(auto_now_add=True, verbose_name='修改时间')
    MODULE = (
        (0, '个人基本信息'), (1, '专家类型'), (2, '银行账号信息'), (3, '教育简历'), (4, '工作简历'),
        (4, '担任社会职务经历'), (5, '担任社会职务经历'), (6, '担任其他评审专家机构情况'), (6, '附件')
    )
    module = models.SmallIntegerField(choices=MODULE, verbose_name='修改模块')
    old = JSONField(verbose_name='修改前的内容')
    new = JSONField(verbose_name='修改后的内容')
    expert = models.ForeignKey(
        to=Expert, on_delete=models.CASCADE, verbose_name='专家')

    class Meta:
        db_table = 'expert_record_edit'


# 专家回避单位表
class AvoidanceUnit(models.Model):
    name = models.CharField(max_length=100, null=True,
                            default=None, verbose_name='操作管理员')
    credit_code = models.CharField(max_length=100, verbose_name='原因')
    date = models.DateTimeField(auto_now_add=True, verbose_name='回避时间')
    expert = models.ForeignKey(
        to=Expert, on_delete=models.CASCADE, verbose_name='专家')

    class Meta:
        db_table = 'expert_avoidance_unit'


class Enclosure(models.Model):
    url = models.URLField(default='', verbose_name='附件地址')
    name = models.URLField(default='', verbose_name='附件名称')
    TYPE = ((0, '身份证附件'), (1, '学历证书附件'), (2, '学位证书附件'),
            (3, '职称证书附件'), (4, '执业资格证书'))
    type = models.SmallIntegerField(
        choices=TYPE, default=0, verbose_name='附件类型')
    expert = models.ForeignKey(
        to=Expert, on_delete=models.CASCADE, verbose_name='专家')

    class Meta:
        db_table = 'expert_enclosure'
