from django.contrib.postgres.fields import JSONField
from mongoengine import Document, fields
from django.db import models

from expert.models import Expert
from project.models import Project
from research.models import Proposal, FieldResearch
from users.models import User, KExperts


class Subject(models.Model):
    subjectName = models.CharField(max_length=252, verbose_name='课题名称', null=True, blank=True)
    unitName = models.CharField(max_length=252, verbose_name='单位名称', null=True, blank=True)
    head = models.CharField(max_length=252, verbose_name='课题负责人', null=True, blank=True)
    idNumber = models.CharField(max_length=252, verbose_name='课题负责人身份证号', null=True, blank=True)
    phone = models.CharField(max_length=252, verbose_name='负责人电话', null=True, blank=True)
    mobile = models.CharField(max_length=252, verbose_name='负责人电话', null=True, blank=True)
    email = models.EmailField(verbose_name='负责人邮箱', null=True, blank=True)
    startStopYear = models.CharField(max_length=252, verbose_name='起止年限', null=True, blank=True)
    declareTime = models.DateField(verbose_name='申报日期', null=True, blank=True)
    executionTime = models.CharField(max_length=252, verbose_name='执行时间', default='-')
    TYPE_CHOICE = (('1', '未预警'), ('2', '三个月'), ('3', '一个月'), ('4', '逾期三个月内'), ('5', '逾期超过三个月'))
    warning = models.CharField(choices=TYPE_CHOICE, default='1', max_length=10, verbose_name='合同预警')
    subjectState = models.CharField(max_length=252, verbose_name='课题状态', default='待提交')
    state = models.CharField(max_length=252, verbose_name='状态', null=True, blank=True)
    stateLabel = models.BooleanField(verbose_name='是否逾期期未结题', default=False)
    concludingState = models.CharField(max_length=252, verbose_name='结题状态', null=True, blank=True)
    terminationState = models.CharField(max_length=252, verbose_name='终止状态', null=True, blank=True)
    terminationOriginator = models.CharField(max_length=252, verbose_name='终止发起人', null=True, blank=True)
    applyTime = models.DateField(verbose_name='申请时间', null=True, blank=True)
    double = models.BooleanField(verbose_name='是否是第二次结题复核', default=False)
    research = models.BooleanField(verbose_name='立项调研 f没有完成 t已完成', default=False)
    advice = models.BooleanField(verbose_name='立项建议 f没有完成 t已完成', default=False)
    reviewState = models.CharField(max_length=252, verbose_name='状态', default='未完成')
    handOverState = models.BooleanField(verbose_name='评估机构是否移交回科技局 是t, 否f', default=False)
    returnReason = models.CharField(max_length=252, verbose_name='退回原因', null=True, blank=True)
    reviewWay = models.CharField(max_length=252, verbose_name='评审方式', null=True, blank=True)
    projectTeam = models.CharField(max_length=252, verbose_name='项目组名称', null=True, blank=True)
    projectTeamLogo = models.CharField(max_length=252, verbose_name='项目组唯一ID', null=True, blank=True)
    assignWay = models.CharField(max_length=252, verbose_name='指派方式', null=True, blank=True)
    assignedTime = models.DateTimeField(verbose_name='指派时间', null=True)
    reviewTime = models.DateTimeField(verbose_name='结题评审时间/终止评审时间', null=True, blank=True)
    signedState = models.BooleanField(verbose_name='合同签订', default=False)
    giveTime = models.DateField(verbose_name='下达时间', null=True, blank=True)
    results = models.CharField(max_length=252, verbose_name='评审结果', null=True, blank=True)
    REVIEW_CHOICE = ((1, '未评审'), (2, '部分完成评审'), (3, '全部完成评审'))
    isEntry = models.IntegerField(choices=REVIEW_CHOICE, default=1)
    attachmentPDF = models.CharField(max_length=252, verbose_name='申报书附件', null=True, blank=True)
    # 实地调研
    fieldResearch = models.ForeignKey(to=FieldResearch, verbose_name='实地调研', on_delete=models.SET_NULL, null=True,
                                      blank=True)
    # 立项建议
    proposal = models.ForeignKey(to=Proposal, verbose_name='立项建议', on_delete=models.SET_NULL, null=True,
                                 blank=True)
    project = models.ForeignKey(to=Project, verbose_name='项目名称', on_delete=models.SET_NULL, null=True, blank=True)
    # 企业
    enterprise = models.ForeignKey(to=User, verbose_name='企业', related_name='enterprise_user',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    # # 分管员
    # charge = models.ManyToManyField(to=User, verbose_name='分管员', related_name='charge_user', blank=True)
    # 评估机构
    agencies = models.ManyToManyField(to=User, verbose_name='评估机构', related_name='agencies_user',
                                      blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'subject'


class Process(models.Model):
    state = models.CharField(max_length=252, verbose_name='状态', null=True, blank=True)
    time = models.DateTimeField(auto_now_add=True, verbose_name='时间')
    note = models.CharField(max_length=252, verbose_name='备注', null=True, blank=True)
    dynamic = models.BooleanField(verbose_name="首True", default=False)
    subject = models.ForeignKey(to=Subject, verbose_name='课题', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'process'


class Attachment(Document):
    types = fields.StringField(max_length=252, verbose_name='附件类型', null=True, blank=True)
    attachmentPath = fields.ListField(verbose_name='附件路径+名称')
    subject = fields.IntField(verbose_name='课题', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'attachment'


# 课题基本信息
class SubjectInfo(Document):
    IAR = fields.StringField(verbose_name='产学研联合', null=True, blank=True)
    innovationType = fields.StringField(verbose_name='创新类型', null=True, blank=True)
    formCooperation = fields.StringField(verbose_name='合作形式', null=True, blank=True)
    phase = fields.StringField(verbose_name='所处阶段', null=True, blank=True)
    overallGoal = fields.StringField(verbose_name='课题总体目标', null=True, blank=True)
    assessmentIndicators = fields.StringField(verbose_name='考核指标', null=True, blank=True)
    subjectId = fields.IntField(verbose_name='课题id')

    class Meta:
        db_table = 'subject_info'


# 课题申报单位
class SubjectUnitInfo(Document):
    # 申报单位信息
    unitInfo = fields.ListField(verbose_name='申报单位信息')
    # 联合申报单位
    jointUnitInfo = fields.ListField(verbose_name='联合申报单位信息')
    subjectId = fields.IntField(verbose_name='课题id')

    class Meta:
        db_table = 'subject_unit_info'


# 预期成果及经济效益
class ExpectedResults(Document):
    # （一）预期成果
    # 专利授权
    inventionPatent = fields.IntField(verbose_name='发明专利', null=True, blank=True)
    utilityModelPatent = fields.IntField(verbose_name='实用新型专利', null=True, blank=True)
    newIndustrialProducts = fields.IntField(verbose_name='工业新产品', null=True, blank=True)
    newAgriculturalVariety = fields.IntField(verbose_name='农业新品种', null=True, blank=True)
    demonstrationBase = fields.IntField(verbose_name='创新/示范基地', null=True, blank=True)
    cs = fields.IntField(verbose_name='申请登记计算机软件', null=True, blank=True)
    # 科技成果转化
    scientificTechnologicalAchievementsTransformed = fields.IntField(verbose_name='科技成果转化个数',
                                                                     null=True, blank=True)
    importedTechnology = fields.IntField(verbose_name='引进技术', null=True, blank=True)
    researchPlatform = fields.IntField(verbose_name='研发平台', null=True, blank=True)
    technicalTrading = fields.IntField(verbose_name='技术交易额', decimal_places=2, max_digits=None, null=True)
    applicationTechnology = fields.IntField(verbose_name='集成应用技术', null=True, blank=True)
    pilotStudies = fields.IntField(verbose_name='示范点', null=True, blank=True)
    # 制定技术标准
    internationalStandard = fields.IntField(verbose_name='国际标准', null=True, blank=True)
    nationalStandard = fields.IntField(verbose_name='国家标准', null=True, blank=True)
    industryStandard = fields.IntField(verbose_name='行业标准', null=True, blank=True)
    localStandards = fields.IntField(verbose_name='地方标准', null=True, blank=True)
    enterpriseStandard = fields.IntField(verbose_name='企业标准', null=True, blank=True)
    newTechnology = fields.IntField(verbose_name='新技术', null=True, blank=True)
    newDevice = fields.IntField(verbose_name='新装置', null=True, blank=True)
    newMaterial = fields.IntField(verbose_name='新材料', null=True, blank=True)
    productionLine = fields.IntField(verbose_name='生产线', null=True, blank=True)
    pilotLine = fields.IntField(verbose_name='中试线', null=True, blank=True)
    postdoctoralTraining = fields.IntField(verbose_name='培养博士后', null=True, blank=True)
    trainingDoctors = fields.IntField(verbose_name='培养博士', null=True, blank=True)
    trainingMaster = fields.IntField(verbose_name='培养硕士', null=True, blank=True)

    # 论文研究论著
    generalJournal = fields.IntField(verbose_name='一般期刊', null=True, blank=True)
    coreJournals = fields.IntField(verbose_name='核心期刊', null=True, blank=True)
    highLevelJournal = fields.IntField(verbose_name='高水平期刊', null=True, blank=True)

    trainingCourses = fields.IntField(verbose_name='举办培训班', null=True, blank=True)
    trainingNumber = fields.IntField(verbose_name='参加培训人数', null=True, blank=True)
    TS = fields.IntField(verbose_name='科技信息服务平台', null=True, blank=True)
    monographs = fields.IntField(verbose_name='专著', null=True, blank=True)
    academicReport = fields.IntField(verbose_name='学术报告', null=True, blank=True)

    # （二）预期经济收益
    # 效益分类：直接经济效益
    newProduction = fields.IntField(verbose_name='新增产值', decimal_places=2, max_digits=None, null=True)
    newTax = fields.IntField(verbose_name='新增税收', decimal_places=2, max_digits=None, null=True)
    export = fields.IntField(verbose_name='出口创汇', decimal_places=2, max_digits=None, null=True)
    subjectId = fields.IntField(verbose_name='课题id')

    class Meta:
        db_table = 'expected_results'


# 经费预算
class FundingBudget(Document):
    # 经费预算
    # （一）课题经费来源预算
    combined = fields.IntField(verbose_name='合计', null=True)
    scienceFunding = fields.IntField(verbose_name='申请科技经费', null=True)
    unitSelfRaised = fields.IntField(verbose_name='单位自筹', null=True)
    stateFunding = fields.IntField(verbose_name='国家）部门提供经费', null=True)
    departmentFunding = fields.IntField(verbose_name='自治区）部门提供经费', null=True)
    municipalFunding = fields.IntField(verbose_name='市级）部门提供经费', null=True)
    otherFunding = fields.IntField(verbose_name='其他经费', null=True)
    # （二）课题经费开支预算
    # 直接费用
    directCostsCombined = fields.IntField(verbose_name='直接费用合计', null=True)
    directScienceFunding = fields.IntField(verbose_name='直接费用申请科技经费', null=True)
    directRestFunding = fields.IntField(verbose_name='直接费用其余经费', null=True)
    directUseInstructions = fields.StringField(verbose_name='直接费用途说明', null=True, blank=True)

    equipmentCostsCombined = fields.IntField(verbose_name='设备费合计', null=True)
    equipmentScienceFunding = fields.IntField(verbose_name='设备费申请科技经费', null=True)
    equipmentRestFunding = fields.IntField(verbose_name='设备费其余经费', null=True)
    equipmentUseInstructions = fields.StringField(verbose_name='设备费用途说明', null=True, blank=True)

    materialsCostsCombined = fields.IntField(verbose_name='材料费合计', null=True)
    materialsScienceFunding = fields.IntField(verbose_name='材料费申请科技经费', null=True)
    materialsRestFunding = fields.IntField(verbose_name='材料费其余经费', null=True)
    materialsUseInstructions = fields.StringField(verbose_name='材料费用途说明', null=True, blank=True)

    testCostsCombined = fields.IntField(verbose_name='测试化验加工费合计', null=True)
    testScienceFunding = fields.IntField(verbose_name='测试化验加工费申请科技经费', null=True)
    testRestFunding = fields.IntField(erbose_name='测试化验加工费其余经费', null=True)
    testUseInstructions = fields.StringField(verbose_name='测试化验加工费用途说明', null=True, blank=True)

    fuelCostCombined = fields.IntField(verbose_name='燃料动力费合计', null=True)
    fuelScienceFunding = fields.IntField(verbose_name='燃料动力费申请科技经费', null=True)
    fuelRestFunding = fields.IntField(verbose_name='燃料动力费其余经费', null=True)
    fuelUseInstructions = fields.StringField(verbose_name='燃料动力费用途说明', null=True, blank=True)

    travelCostCombined = fields.IntField(verbose_name='差旅费合计', null=True)
    travelScienceFunding = fields.IntField(verbose_name='差旅费合计差旅费合计', null=True)
    travelRestFunding = fields.IntField(verbose_name='差旅费其余经费', null=True)
    travelUseInstructions = fields.StringField(verbose_name='差旅费其余经费', null=True, blank=True)

    meetingCostCombined = fields.IntField(verbose_name='会议费合计', null=True)
    meetingScienceFunding = fields.IntField(verbose_name='会议费申请科技经费', null=True)
    meetingRestFunding = fields.IntField(verbose_name='会议费其余经费', null=True)
    meetingUseInstructions = fields.StringField(verbose_name='会议费用途说明', null=True, blank=True)

    internationalCostCombined = fields.IntField(verbose_name='国际合作与交流费合计', null=True)
    internationalScienceFunding = fields.IntField(verbose_name='国际合作与交流费申请科技经费', null=True)
    internationalRestFunding = fields.IntField(verbose_name='国际合作与交流费其余经费', null=True)
    internationalUseInstructions = fields.StringField(verbose_name='国际合作与交流费用途说明', null=True,
                                                      blank=True)

    publishedCostCombined = fields.IntField(verbose_name='出版/文献/信息传播/知识产权事务费合计', null=True)
    publishedScienceFunding = fields.IntField(verbose_name='出版/文献/信息传播/知识产权事务费申请科技经费', null=True)
    publishedRestFunding = fields.IntField(verbose_name='出版/文献/信息传播/知识产权事务费其余经费', null=True)
    publishedUseInstructions = fields.StringField(verbose_name='出版/文献/信息传播/知识产权事务费用途说明', null=True,
                                                  blank=True)

    laborCostCombined = fields.IntField(verbose_name='劳务费合计', null=True)
    laborScienceFunding = fields.IntField(verbose_name='劳务费申请科技经费', null=True)
    laborRestFunding = fields.IntField(verbose_name='劳务费其余经费', null=True)
    laborUseInstructions = fields.StringField(verbose_name='劳务费用途说明', null=True, blank=True)

    expertCostCombined = fields.IntField(verbose_name='专家咨询费合计', null=True)
    expertScienceFunding = fields.IntField(verbose_name='专家咨询费申请科技经费', null=True)
    expertRestFunding = fields.IntField(verbose_name='专家咨询费其余经费', null=True)
    expertUseInstructions = fields.StringField(verbose_name='专家咨询费用途说明', null=True, blank=True)

    otherCostCombined = fields.IntField(verbose_name='其他费用合计', null=True)
    otherScienceFunding = fields.IntField(verbose_name='其他费用申请科技经费', null=True)
    otherRestFunding = fields.IntField(verbose_name='其他费用其余经费', null=True)
    otherUseInstruction = fields.StringField(verbose_name='其他费用用途说明', null=True, blank=True)
    # 间接费用
    indirectCostCombined = fields.IntField(verbose_name='间接费用合计', null=True)
    indirectScienceFunding = fields.IntField(verbose_name='间接费用申请科技经费', null=True)
    indirectRestFunding = fields.IntField(verbose_name='间接费用其余经费', null=True)
    indirectUseInstruction = fields.StringField(verbose_name='间接费用用途说明', null=True, blank=True)
    useInstructions = fields.StringField(verbose_name='合计用途说明', null=True, blank=True)
    subjectId = fields.IntField(verbose_name='课题id')
    #

    class Meta:
        db_table = 'funding_budget'


# 知识产权
class IntellectualProperty(Document):
    # 一）申报单位拥有知识产权状况
    totalNumberPatentApplications = fields.IntField(verbose_name='专利申请数', null=True, blank=True)
    inventionApplication = fields.IntField(verbose_name='发明申请', null=True, blank=True)
    applicationUtilityModel = fields.IntField(verbose_name='实用新型申请', null=True, blank=True)
    softwareCopyright = fields.IntField(verbose_name='软件版权', null=True, blank=True)
    totalNumberPatentLicenses = fields.IntField(verbose_name='专利授权总数', null=True, blank=True)
    inventionAuthorization = fields.IntField(verbose_name='发明授权', null=True, blank=True)
    authorizationUtilityModel = fields.IntField(verbose_name='实用新型授权', null=True, blank=True)
    # 其中：近三年
    totalNumberPatentApplications3 = fields.IntField(verbose_name='专利申请数3', null=True, blank=True)
    inventionApplication3 = fields.IntField(verbose_name='发明申请3', null=True, blank=True)
    applicationUtilityModel3 = fields.IntField(verbose_name='实用新型申请3', null=True, blank=True)
    softwareCopyright3 = fields.IntField(verbose_name='软件版权3', null=True, blank=True)
    totalNumberPatentLicenses3 = fields.IntField(verbose_name='专利授权总数3', null=True, blank=True)
    inventionAuthorization3 = fields.IntField(verbose_name='发明授权3', null=True, blank=True)
    authorizationUtilityModel3 = fields.IntField(verbose_name='实用新型授权3', null=True, blank=True)
    # 申报单位及合作单位拥有本课题相关技术知识产权状况
    totalNumberPatentApplications2 = fields.IntField(verbose_name='专利申请数2', null=True, blank=True)
    inventionApplication2 = fields.IntField(verbose_name='发明申请2', null=True, blank=True)
    applicationUtilityModel2 = fields.IntField(verbose_name='实用新型申请2', null=True, blank=True)
    softwareCopyright2 = fields.IntField(verbose_name='软件版权2', null=True, blank=True)
    totalNumberPatentLicenses2 = fields.IntField(verbose_name='专利授权总数2', null=True, blank=True)
    inventionAuthorization2 = fields.IntField(verbose_name='发明授权2', null=True, blank=True)
    authorizationUtilityModel2 = fields.IntField(verbose_name='实用新型授权2', null=True, blank=True)
    # 三）其他知识产权现状说明
    instructions = fields.StringField(verbose_name='说明', null=True, blank=True)
    subjectId = fields.IntField(verbose_name='课题id')

    class Meta:
        db_table = 'intellectual_property'


# 课题人员信息
class SubjectPersonnelInfo(Document):
    name = fields.StringField(verbose_name='课题负责人姓名', null=True, blank=True)
    idNumber = fields.StringField(verbose_name='课题负责人身份证号码', null=True, blank=True)
    recordSchooling = fields.StringField(verbose_name='课题负责人学历', null=True, blank=True)
    workUnit = fields.StringField(verbose_name='课题负责人工作单位', null=True, blank=True)
    divisionSubject = fields.StringField(verbose_name='课题负责人课题分工', null=True, blank=True)
    gender = fields.StringField(verbose_name='课题负责人性别', null=True, blank=True)
    age = fields.StringField(verbose_name='课题负责人年龄', null=True, blank=True)
    title = fields.StringField(verbose_name='课题负责人职称', null=True, blank=True)
    professional = fields.StringField(verbose_name='课题负责人从事专业', null=True, blank=True)
    # 研究开发人员
    researchDevelopmentPersonnel = fields.ListField()
    subjectId = fields.IntField(verbose_name='课题id')


# 其他信息
class SubjectOtherInfo(Document):
    otherMatters = fields.ListField()
    financialFundsOtherSupport = fields.StringField(null=True)
    subjectId = fields.IntField(verbose_name='课题id')


# 申报单位承诺及推荐意见
class UnitCommitment(Document):
    commitment = fields.StringField(verbose_name='承诺', null=True)
    subjectId = fields.IntField(verbose_name='课题id')


# 附件清单
class AttachmentList(Document):
    attachmentName = fields.StringField(max_length=252, verbose_name='附件名称')
    attachmentShows = fields.StringField(max_length=252, verbose_name='附件说明')
    attachmentContent = fields.ListField(verbose_name='附件路径+名称')
    subjectId = fields.IntField(verbose_name='课题id')


# 评估机构评审意见表
class OpinionSheet(models.Model):
    planCategory = models.CharField(max_length=252, verbose_name='计划类别')
    unitName = models.CharField(max_length=252, verbose_name='申报单位')
    subjectName = models.CharField(max_length=252, verbose_name='课题名称')
    subjectScore = models.CharField(max_length=252, verbose_name='课题得分')
    proposal = models.CharField(max_length=252, verbose_name='立项建议', null=True)
    proposalFunding = models.BigIntegerField(verbose_name='科技项目经费建议额度（万元）')
    projectProposal = models.TextField(verbose_name='立项建议书', null=True)
    expertsList = JSONField('专家列', null=True, blank=True)
    # state = models.CharField(max_length=252, verbose_name='是否提交', null=True, blank=True)
    attachment = models.CharField(max_length=252, verbose_name='附件', null=True, blank=True)
    subject = models.ForeignKey(to=Subject, verbose_name='课题', on_delete=models.SET_NULL,
                                related_name='opinion_sheet_subject',
                                null=True, blank=True)

    class Meta:
        db_table = 'opinion_sheet'


# 专家评审意见表
class ExpertOpinionSheet(models.Model):
    planCategory = models.CharField(max_length=252, verbose_name='计划类别')
    unitName = models.CharField(max_length=252, verbose_name='申报单位')
    subjectName = models.CharField(max_length=252, verbose_name='课题名称')
    subjectScore = models.CharField(max_length=252, verbose_name='课题得分')
    proposal = models.CharField(max_length=252, verbose_name='立项建议')
    proposalFunding = models.BigIntegerField(verbose_name='科技项目经费建议额度（万元）')
    projectProposal = models.TextField(verbose_name='立项建议书')
    expertName = models.CharField(max_length=252, verbose_name='专家姓名')
    expertUnit = models.CharField(max_length=252, verbose_name='专家所在单位')
    attachmentPDF = models.CharField(max_length=252, verbose_name='专家评审单pdf', null=True, blank=True)

    class Meta:
        db_table = 'expert_opinion_sheet'


# 专家 课题 评审单（专家）
class SubjectExpertsOpinionSheet(models.Model):
    expertOpinionSheet = models.ForeignKey(to=ExpertOpinionSheet, verbose_name='专家评审意见表',
                                           related_name='expert_opinion_sheet_three', on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='subject_three', on_delete=models.SET_NULL,
                                null=True, blank=True)
    pExperts = models.ForeignKey(to=User, verbose_name='评估机构专家', related_name='pExpert_three',
                                 on_delete=models.SET_NULL, null=True, blank=True)
    state = models.CharField(max_length=252, verbose_name='专家评审状态', default='待评审')
    reviewTime = models.DateTimeField(verbose_name='立项评审时间', null=True, blank=True)
    declareTime = models.DateField(max_length=252, verbose_name='评估机构专家撤销评审单的时间申请日期', null=True, blank=True)
    agenciesState = models.CharField(max_length=252, verbose_name='评估机构撤销评审状态', null=True, blank=True)
    returnReason = models.CharField(max_length=252, verbose_name='专家撤销原因', null=True, blank=True)
    reviewWay = models.CharField(max_length=252, verbose_name='评审方式', null=True, blank=True)
    money = models.CharField(max_length=252, verbose_name='经费金额', null=True, blank=True)
    isReview = models.BooleanField(verbose_name='是否完成评审', default=False)

    class Meta:
        db_table = 'subject_experts_opinion_sheet'


class SubjectKExperts(models.Model):
    expert = models.ForeignKey(to=Expert, verbose_name='专家', related_name='expert_three', on_delete=models.SET_NULL, blank=True, null=True)
    subject = models.ForeignKey(to=Subject, verbose_name='课题ID', on_delete=models.SET_NULL, null=True, blank=True, related_name='subject_a_t')
    reviewState = models.BooleanField(verbose_name='是否复核', default=False)
    # reviewTime = models.DateTimeField(verbose_name='结题评审时间/终止评审时间', null=True, blank=True)
    money = models.CharField(max_length=252, verbose_name='经费金额', null=True, blank=True)
    state = models.BooleanField(verbose_name='结果', default=False)
    # acceptance = models.ForeignKey(to=SubjectConcluding, verbose_name='验收申请书id', on_delete=models.SET_NULL, null=True, blank=True)
    # termination = models.ForeignKey(to=SubjectTermination, verbose_name='验收申请书id', on_delete=models.SET_NULL, null=True, blank=True)
    acceptance = models.CharField(max_length=252, verbose_name='验收申请书id', null=True, blank=True)
    termination = models.CharField(max_length=252, verbose_name='验收申请书id', null=True, blank=True)

    class Meta:
        db_table = 'subject_k_experts'
