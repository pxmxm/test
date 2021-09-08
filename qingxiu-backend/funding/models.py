from django.contrib.postgres.fields import JSONField
from django.db import models

# Create your models here.
from subject.models import Subject
from mongoengine import Document, fields


class GrantSubject(models.Model):
    grantType = models.CharField(max_length=252, verbose_name='拨款类型', null=True, blank=True)
    # unit = models.CharField(max_length=252, verbose_name='承担单位', null=True, blank=True)
    state = models.CharField(max_length=252, verbose_name='是否申请', default='待提交')
    money = models.BigIntegerField(verbose_name='请款金额', default=0,)
    attachmentName = models.CharField(max_length=252, verbose_name='附件名称', null=True, blank=True)
    attachment = models.URLField(max_length=252, verbose_name='附件', null=True, blank=True)
    attachments = JSONField('拨款申请附件', null=True, blank=True)
    subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='subject_grant_type',
                                on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'grant_subject'


class AllocatedSingle(Document):
    approvalNumber = fields.StringField(max_length=252, verbose_name='批文编号')
    projectNumber = fields.StringField(max_length=252, verbose_name='项目序号')
    pleaseParagraphDate = fields.DateField(verbose_name='请款日期')
    subjectName = fields.StringField(max_length=252, verbose_name='项目名称')
    contractNo = fields.StringField(max_length=252, verbose_name='合同编号')
    unitName = fields.StringField(max_length=252, verbose_name='项目承担单位')
    head = fields.StringField(max_length=252, verbose_name='课题联系人')
    mobile = fields.StringField(max_length=252, verbose_name='收款单位电话')
    money = fields.IntField(verbose_name='请款金额', default=0)
    initial = fields.IntField(verbose_name='请款金额', null=True)
    storage = fields.BooleanField(default=False, verbose_name='是否保存')
    sourcesFunds = fields.StringField(max_length=252, verbose_name='款项来源')
    receivingUnit = fields.StringField(max_length=252, verbose_name='收款单位')
    bankAccount = fields.StringField(max_length=252, verbose_name='开户账号')
    bank = fields.StringField(max_length=252, verbose_name='开户银行')
    grantSubject = fields.IntField(verbose_name='经费类型')