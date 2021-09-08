from django.db import models
from mongoengine import Document, fields

# Create your models here.
from subject.models import Subject
from users.models import User


class ContractContent(Document):
    subjectName = fields.StringField(verbose_name='项目名称')
    unit = fields.ListField(verbose_name='承担单位')
    subjectTotalGoal = fields.StringField(max_length=25250, verbose_name='课题总目标，课题主要内容', null=True)
    subjectAssessmentIndicators = fields.StringField(max_length=25250, verbose_name='课题考核指标', null=True)
    executionTime = fields.StringField(max_length=252, verbose_name='项目实施时间')
    subjectSchedule = fields.ListField(verbose_name='项目进度')
    responsibility = fields.StringField(max_length=25250, verbose_name='研究开发中的责任分工', null=True)
    personnel = fields.ListField(verbose_name='主要研究 开发人员及责分工')
    scienceFunding = fields.IntField(verbose_name='科技经费')
    unitFunding = fields.ListField(verbose_name='款项')
    # 合计
    combined = fields.ListField()
    directCosts = fields.ListField(verbose_name='直接费用')
    equipmentCosts = fields.ListField(verbose_name='设备费')
    materialsCosts = fields.ListField(verbose_name='材料费')
    testCosts = fields.ListField(verbose_name='测试化验加工费')
    fuelCost = fields.ListField(verbose_name='燃料动力费')
    travelCost = fields.ListField(verbose_name='差旅费')
    meetingCost = fields.ListField(verbose_name='会议费')
    internationalCost = fields.ListField(verbose_name='国际合作与交流费')
    # 出版/文献/信息传播/知识产权事务费
    publishedCost = fields.ListField(verbose_name='出版/文献/信息传播/知识产权事务费')
    # 劳务费
    laborCost = fields.ListField()
    expertCost = fields.ListField(verbose_name='专家咨询费')
    otherCost = fields.ListField(verbose_name='其他费用')
    indirectCost = fields.ListField(verbose_name='间接费用')
    # 钱
    money = fields.StringField(verbose_name='', null=True)
    # 负责落实资金的承担单位（或协作单位）名称
    contractResearchersList = fields.ListField()
    # 甲方
    firstParty = fields.ListField()
    # 乙方
    secondParty = fields.ListField()
    # 乙方联系人
    secondPartyContact = fields.ListField()
    created = fields.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = fields.DateTimeField(auto_now=True, verbose_name='更新时间')
    # jointAgreement = fields.StringField(verbose_name='联合实施协议', null=True)

    class Meta:
        db_table = 'contract_content'


class ContractAttachment(Document):
    types = fields.StringField(max_length=252, verbose_name='附件类型', null=True, blank=True)
    attachmentShows = fields.StringField(max_length=252, verbose_name='附件说明')
    attachmentPath = fields.ListField(verbose_name='附件路径+名称')
    contract = fields.IntField(verbose_name='合同id', on_delete=models.SET_NULL, null=True, blank=True)


class Contract(models.Model):
    contractNo = models.CharField(max_length=252, verbose_name='合同编号')
    approvalMoney = models.BigIntegerField(verbose_name='批复经费')
    chargeUser = models.ForeignKey(to=User, verbose_name='分管员', related_name='contract_user', on_delete=models.SET_NULL,
                                   null=True, blank=True)
    state = models.CharField(max_length=252, verbose_name='合同状态', default='待提交')
    contractState = models.CharField(max_length=252, verbose_name='合同附件状态', default='-')
    attachment = models.URLField(max_length=252, verbose_name='合同附件', null=True, blank=True)
    created = models.DateTimeField(auto_now=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='contract_subject', on_delete=models.SET_NULL, null=True, blank=True)
    contractContent = models.CharField(max_length=252, verbose_name='合同内容', null=True, blank=True)

    class Meta:
        db_table = 'contract'
