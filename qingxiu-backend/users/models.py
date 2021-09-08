from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.db import models

# Create your models here.
from expert.models import Expert


class Permissions(models.Model):
    name = models.CharField(max_length=20, verbose_name='权限名称')

    class Meta:
        db_table = 'permissions'


# 企业
class Enterprise(models.Model):
    # 单位信息
    registeredAddress = models.CharField(max_length=252, verbose_name='注册地址')
    registeredTime = models.DateField(verbose_name='注册时间')
    registeredCapital = models.CharField(max_length=252, verbose_name='注册资本', null=True, blank=True)
    zipCode = models.CharField(max_length=6, verbose_name='邮政编码', null=True, blank=True)
    unit = models.CharField(max_length=5, verbose_name='钱-单位')
    industry = models.CharField(max_length=252, verbose_name='行业 单位类别')
    registeredType = models.CharField(max_length=252, verbose_name='企业注册类型')
    registeredCategory = models.CharField(max_length=252, verbose_name='注册类别')
    highTechEnterprise = models.BooleanField(verbose_name='是否是高新技术企业', null=True, blank=True)
    smallMediumTechnologyEnterprises = models.BooleanField(verbose_name='是否是中小型科技企业', null=True, blank=True)
    industryNationalEconomy = models.CharField(max_length=252, verbose_name='所属国民经济行业')
    technicalField = models.CharField(max_length=252, verbose_name='所属技术领域')
    # 职工信息
    workerNumber = models.IntegerField(verbose_name='职工人数')
    seniorTitle = models.IntegerField(verbose_name='高级职称')
    bachelorDegreeOrAbove = models.IntegerField(verbose_name='本科及以上学历')
    intermediateTitle = models.IntegerField(verbose_name='中级职称')
    technicalPersonnel = models.IntegerField(verbose_name='技术人员')
    primaryTitle = models.IntegerField(verbose_name='初级职称')
    # 法人信息
    legalRepresentative = models.CharField(max_length=252, verbose_name='法人代表')
    documentType = models.CharField(max_length=5, verbose_name='法人代表证件类型')
    documentNumber = models.CharField(max_length=252, verbose_name='法人代表证件号')
    # 知识产权
    totalNumberPatentApplications = models.IntegerField(verbose_name='专利申请总数')
    totalNumberPatentLicenses = models.IntegerField(verbose_name='专利授权总数')
    inventionApplication = models.IntegerField(verbose_name='发明申请')
    inventionAuthorization = models.IntegerField(verbose_name='发明授权')
    applicationUtilityModel = models.IntegerField(verbose_name='实用新型申请')
    authorizationUtilityModel = models.IntegerField(verbose_name='实用新型授权')
    softwareCopyright = models.IntegerField(verbose_name='软件版权')
    # 其中：近三年
    totalNumberPatentApplications3 = models.IntegerField(verbose_name='专利申请总数3')
    totalNumberPatentLicenses3 = models.IntegerField(verbose_name='专利授权总数3')
    inventionApplication3 = models.IntegerField(verbose_name='发明申请3')
    inventionAuthorization3 = models.IntegerField(verbose_name='发明授权3')
    applicationUtilityModel3 = models.IntegerField(verbose_name='实用新型申请3')
    authorizationUtilityModel3 = models.IntegerField(verbose_name='实用新型授权3')
    softwareCopyright3 = models.IntegerField(verbose_name='软件版权3')
    # 银行开户信息
    accountName = models.CharField(max_length=252, verbose_name='开户户名')
    bank = models.CharField(max_length=252, verbose_name='开户银行')
    bankAccount = models.CharField(max_length=252, verbose_name='银行账号')

    class Meta:
        db_table = 'enterprise'


# 科技局专家
class KExperts(models.Model):
    name = models.CharField(max_length=252, verbose_name='姓名')
    gender = models.CharField(max_length=252, verbose_name='性别')
    birthday = models.DateField(null=True, verbose_name='生日')  # 日期 年月日
    email = models.EmailField(verbose_name='邮箱')
    mobile = models.CharField(max_length=252, verbose_name='联系电话')
    unit = models.CharField(max_length=252, verbose_name='所在单位')
    title = models.CharField(max_length=252, verbose_name='职称')
    position = models.CharField(max_length=252, verbose_name='职务')
    learnProfessional = models.CharField(max_length=252, verbose_name='所学专业')
    engagedProfessional = models.CharField(max_length=252, verbose_name='从事专业')
    isDelete = models.BooleanField(default=False, verbose_name='逻辑删除')
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'k_experts'


class PExperts(models.Model):
    name = models.CharField(max_length=252, verbose_name='姓名')
    gender = models.CharField(max_length=252, verbose_name='性别')
    birthday = models.DateField(null=True, verbose_name='生日')  # 日期 年月日
    email = models.EmailField(verbose_name='邮箱')
    mobile = models.CharField(max_length=252, verbose_name='联系电话')
    unit = models.CharField(max_length=252, verbose_name='所在单位')
    title = models.CharField(max_length=252, verbose_name='职称')
    position = models.CharField(max_length=252, verbose_name='职务')
    learnProfessional = models.CharField(max_length=252, verbose_name='所学专业')
    engagedProfessional = models.CharField(max_length=252, verbose_name='从事专业')
    ratingAgencies = models.CharField(max_length=252, verbose_name='所属评估机构ID')
    isDelete = models.BooleanField(default=False, verbose_name='逻辑删除')
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'p_experts'


class Agency(models.Model):
    name = models.CharField(max_length=252, verbose_name='单位名称')
    creditCode = models.CharField(max_length=252, verbose_name='统一社会信用代码')
    contact = models.CharField(max_length=252, verbose_name='联系人', null=True)
    mobile = models.CharField(max_length=252, verbose_name='联系电话', null=True)
    qualification = JSONField(verbose_name='资质资料')
    businessLicense = models.URLField(max_length=252, verbose_name='营业执照', null=True, blank=True)
    permissions = models.ManyToManyField(to=Permissions, verbose_name='权限外健', related_name='permissions_3', blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '管理服务机构'
        db_table = 'agency'


class User(AbstractUser):
    username = models.CharField(max_length=252, unique=True, verbose_name='用户名')
    name = models.CharField(max_length=252, verbose_name='姓名 单位名称')
    logo = models.CharField(max_length=10, verbose_name='唯一表示', unique=True, null=True, blank=True)
    CreditCode = models.CharField(max_length=252, verbose_name='统一社会信用代码', null=True, blank=True)
    registeredAddress = models.CharField(max_length=252, verbose_name='单位注册地址', null=True, blank=True)
    phone = models.CharField(max_length=252, verbose_name='联系电话', null=True, blank=True)
    mobile = models.CharField(max_length=11, verbose_name='手机号', null=True, blank=True)
    contact = models.CharField(max_length=252, verbose_name='联系人', null=True, blank=True)
    QQ = models.CharField(max_length=20, verbose_name='QQ', null=True, blank=True)
    type = models.CharField(max_length=6, default='企业', verbose_name='身份类型')
    isActivation = models.CharField(max_length=252, verbose_name='是否禁用/启用', default='启用')
    enterprise = models.ForeignKey(to=Enterprise, verbose_name='企业信息', on_delete=models.SET_NULL, null=True, blank=True)
    experts = models.ForeignKey(to=PExperts, verbose_name='平局机构专家', on_delete=models.SET_NULL, null=True, blank=True)
    isDelete = models.BooleanField(default=False, verbose_name='逻辑删除')
    businessLicense = models.URLField(max_length=252, verbose_name='营业执照', null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', null=True)

    agency = models.ForeignKey(to=Agency, verbose_name='管理服务机构', on_delete=models.SET_NULL, null=True, blank=True)

    expert = models.ForeignKey(to=Expert, verbose_name='专家', on_delete=models.DO_NOTHING, null=True, blank=True)

    class Meta:
        verbose_name = '用户表'
        db_table = 'user'
