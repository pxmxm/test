from django.db import models
from mongoengine import Document, fields

from subject.models import Subject
from users.models import User


class SubjectTermination(models.Model):
    termination = models.CharField(max_length=252, verbose_name='验收申请书id', null=True, blank=True)
    subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='subject_termination',
                                on_delete=models.SET_NULL, null=True, blank=True)
    declareTime = models.DateField(max_length=252, verbose_name='申请日期', null=True, blank=True)
    attachmentPDF = models.CharField(max_length=252, verbose_name='申报书附件', null=True, blank=True)
    terminationState = models.CharField(max_length=252, verbose_name='状态', blank=True)
    reviewTime = models.DateTimeField(verbose_name='结题评审时间/终止评审时间', null=True, blank=True)
    handOverState = models.BooleanField(verbose_name='管理服务机构将项目是否移交回科技局 是True, 否False', default=False)
    results = models.CharField(max_length=252, verbose_name='评审结果', default='-')
    agency = models.ForeignKey(to=User, verbose_name='管理服务机构', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'subject_termination'


# 结题
class Termination(Document):
    contractNo = fields.StringField(verbose_name='合同编号', null=True)
    subjectName = fields.StringField(verbose_name='项目名称', null=True)
    unitName = fields.StringField(verbose_name='申请单位', null=True)
    applyUnit = fields.StringField(max_length=252, verbose_name='申请终止单位', null=True)
    declareTime = fields.DateField(max_length=252, verbose_name='申请日期', null=True)
    registeredAddress = fields.StringField(max_length=252, verbose_name='通信地址', null=True)
    contact = fields.StringField(max_length=252, verbose_name='联系人', null=True)
    mobile = fields.StringField(max_length=252, verbose_name='联系电话', null=True)
    zipCode = fields.IntField(max_length=252, verbose_name='邮政编码', null=True)
    email = fields.EmailField(max_length=252, verbose_name='电子邮箱', null=True)
    industry = fields.StringField(max_length=252, verbose_name='单位性质', null=True)
    startStopYear = fields.StringField(max_length=252, verbose_name='项目合同书约定的项目实施起止时间', null=True)
    grantAmount = fields.IntField(verbose_name='青秀区财政拨款金额（万元）', null=True)
    useFunds = fields.IntField(verbose_name='使用经费', null=True)
    surplusFunds = fields.IntField(verbose_name='剩余经费', null=True)

    # 申报单位信息
    unitInfo = fields.ListField(verbose_name='申报单位信息', null=True)
    # 联合申报单位
    jointUnitInfo = fields.ListField(verbose_name='联合申报单位信息', null=True)

    indicatorsCompletion = fields.ListField(verbose_name='合同约定考核指标，实际完成情况', blank=True, null=True)
    terminationReason = fields.StringField(verbose_name='项目终止原因详述', null=True)
    fileDirectory = fields.StringField(verbose_name='提交的文件和资料目录', null=True)
    # terminationState = fields.StringField(max_length=252, verbose_name='状态', null=True)
    subject = fields.IntField(verbose_name='课题ID')


# 主要承担人员
class TResearchers(Document):
    researcher = fields.ListField(null=True)
    termination = fields.StringField(verbose_name='终止申请书id')


# 项目投入产出基本情况表
class TOutput(Document):
    unitsNumber = fields.IntField(verbose_name='参加单位个数', null=True)
    # 项目组人员情况
    projectTeamPersonnelCombined = fields.IntField(max_length=252, verbose_name='项目组人员合计', null=True)
    seniorTitle = fields.IntField(max_length=252, verbose_name='高级职称', null=True)
    intermediateTitle = fields.IntField(max_length=252, verbose_name='中级职称', null=True)
    primaryTitle = fields.IntField(max_length=252, verbose_name='初级职称', null=True)
    Dr = fields.IntField(max_length=252, verbose_name='博士', null=True)
    master = fields.IntField(max_length=252, verbose_name='硕士', null=True)
    bachelor = fields.IntField(max_length=252, verbose_name='学士', null=True)
    # 项目经费情况
    fundingCombined = fields.IntField(verbose_name='项目经费合计', null=True)
    cityFunding = fields.IntField(verbose_name='城区财政科技经费', null=True)
    departmentFunding = fields.IntField(verbose_name='部门提供科技经费', null=True)
    unitSelfRaised = fields.IntField(verbose_name='单位自筹', null=True)
    bankLoan = fields.IntField(verbose_name='银行贷款', null=True)
    otherSources = fields.IntField(verbose_name='其他来源', null=True)
    # 项目主要成果情况
    importedTechnology = fields.IntField(max_length=252, verbose_name='引进技术', null=True)
    applicationTechnology = fields.IntField(max_length=10, verbose_name='集成应用技术', null=True)
    scientificTechnologicalAchievementsTransformed = fields.IntField(max_length=10, verbose_name='科技成果转化个数', null=True)
    technicalTrading = fields.IntField(max_length=10, verbose_name='技术交易额', null=True)
    newIndustrialProducts = fields.IntField(max_length=10, verbose_name='工业新产品', null=True)
    newAgriculturalVariety = fields.IntField(max_length=10, verbose_name='农业新品种', null=True)
    newProcess = fields.IntField(max_length=10, verbose_name='新工艺', null=True)
    newMaterial = fields.IntField(max_length=10, verbose_name='新材料', null=True)
    newDevice = fields.IntField(max_length=10, verbose_name='新装置', null=True)
    cs = fields.IntField(max_length=10, verbose_name='申请登记计算机软件', null=True)
    researchPlatform = fields.IntField(max_length=10, verbose_name='研发平台', null=True)
    TS = fields.IntField(max_length=10, verbose_name='科技信息服务平台', null=True)
    pilotStudies = fields.IntField(max_length=10, verbose_name='示范点', null=True)
    pilotLine = fields.IntField(max_length=10, verbose_name='中试线', null=True)
    productionLine = fields.IntField(max_length=10, verbose_name='生产线', null=True)
    experimentalBase = fields.IntField(max_length=10, verbose_name='试验基地', null=True)
    applyPatent = fields.IntField(max_length=252, verbose_name='申请专利', null=True)
    applyInventionPatent = fields.IntField(max_length=252, verbose_name='申请专利 -发明专利', null=True)
    applyUtilityModel = fields.IntField(max_length=252, verbose_name='申请专利 -实用新型', null=True)
    authorizedPatents = fields.IntField(max_length=252, verbose_name='授权专利', null=True)
    authorizedInventionPatent = fields.IntField(max_length=252, verbose_name='授权专利-发明专利', null=True)
    authorizedUtilityModel = fields.IntField(max_length=252, verbose_name='授权专利-实用新型', null=True)
    technicalStandards = fields.IntField(max_length=252, verbose_name='参与制定技术标准', null=True)
    internationalStandard = fields.IntField(max_length=10, verbose_name='国际标准', null=True)
    nationalStandard = fields.IntField(max_length=10, verbose_name='国家标准', null=True)
    industryStandard = fields.IntField(max_length=10, verbose_name='行业标准', null=True)
    localStandards = fields.IntField(max_length=10, verbose_name='地方标准', null=True)
    enterpriseStandard = fields.IntField(max_length=10, verbose_name='企业标准', null=True)
    thesisResearchReport = fields.IntField(max_length=252, verbose_name='论文研究报告', null=True, blank=True)
    coreJournals = fields.IntField(max_length=10, verbose_name='核心期刊', null=True)
    highLevelJournal = fields.IntField(max_length=10, verbose_name='高水平期刊', null=True)
    generalJournal = fields.IntField(max_length=10, verbose_name='一般期刊', null=True)
    postdoctoralTraining = fields.IntField(max_length=10, verbose_name='培养博士后', null=True)
    trainingDoctors = fields.IntField(max_length=10, verbose_name='培养博士', null=True)
    trainingMaster = fields.IntField(max_length=10, verbose_name='培养硕士', null=True)
    monographs = fields.IntField(max_length=100, verbose_name='专著', null=True)
    academicReport = fields.IntField(max_length=100, verbose_name='学术报告', null=True, blank=True)
    trainingCourses = fields.IntField(max_length=10, verbose_name='举办培训班', null=True)
    trainingNumber = fields.IntField(max_length=10, verbose_name='参加培训人数', null=True)
    # 项目实施期间累计取得的经济效益 直接经济效益
    salesRevenue = fields.IntField(verbose_name='新增销售收入', decimal_places=2, max_digits=None, null=True)
    newProduction = fields.IntField(verbose_name='新增产值', decimal_places=2, max_digits=None, null=True)
    newTax = fields.IntField(verbose_name='新增税收', decimal_places=2, max_digits=None, null=True)
    export = fields.IntField(verbose_name='出口创汇', decimal_places=2, max_digits=None, null=True)
    # 项目实施期间累计取得的经济效益 间接经济效益
    salesRevenue2 = fields.IntField(verbose_name='新增销售收入', decimal_places=2, max_digits=None, null=True)
    newProduction2 = fields.IntField(verbose_name='新增产值', decimal_places=2, max_digits=None, null=True)
    newTax2 = fields.IntField(verbose_name='新增税收', decimal_places=2, max_digits=None, null=True)
    export2 = fields.IntField(verbose_name='出口创汇', decimal_places=2, max_digits=None, null=True)
    termination = fields.StringField(verbose_name='终止申请书id')


# 财务自查表
class TCheckList(Document):
    name = fields.StringField(verbose_name='项目名称', null=True)
    data = fields.DateField(verbose_name='日期', null=True)
    head = fields.StringField(verbose_name='项目负责人', null=True)
    contractNo = fields.StringField(verbose_name='合同编号', null=True)
    unitName = fields. StringField(verbose_name='承担单位', null=True)
    startStopYear = fields.StringField(verbose_name='项目实施起止时间', null=True)
    headName = fields.StringField(verbose_name='项目实施负责人姓名', null=True)
    headTitle = fields.StringField(verbose_name='项目实施负责人职称', null=True)

    # totalBudget = fields.FloatField(verbose_name='项目总预算')
    # scienceFunding = fields.FloatField(verbose_name='科技经费')
    # unitSelfRaised = fields.FloatField(verbose_name='单位自筹经费')
    # actualFunding = fields.FloatField(verbose_name='项目总经费到位情况')
    # -----
    totalBudget = fields.IntField(verbose_name='项目总预算', null=True)
    departmentSelfRaised = fields.IntField(verbose_name='部门自筹', null=True)
    financialAid = fields.IntField(verbose_name='财政科技补助', null=True)
    selfRaised = fields.IntField(verbose_name='自筹', null=True)
    actualFunding = fields.IntField(verbose_name='项目总经费到位情况', null=True)
    scienceFunding = fields.IntField(verbose_name='科技经费', null=True)

    # fundingSituation = fields.StringField(verbose_name='经费情况')
    equipmentCosts = fields.ListField(verbose_name='设备费', null=True)
    materialsCosts = fields.ListField(verbose_name='材料费', null=True)
    testCosts = fields.ListField(verbose_name='测试化验加工费', null=True)
    fuelCost = fields.ListField(verbose_name='燃料动力费', null=True)
    travelCost = fields.ListField(verbose_name='差旅费', null=True)
    meetingCost = fields.ListField(verbose_name='会议费', null=True)
    internationalCost = fields.ListField(verbose_name='国际合作与交流费', null=True)
    publishedCost = fields.ListField(verbose_name='出版/文献/信息传播/知识产权事务费', null=True)
    personnelCost = fields.ListField(verbose_name='人员费', null=True)
    expertCost = fields.ListField(verbose_name='专家咨询费', null=True)
    managementCost = fields.ListField(verbose_name='管理费', null=True)
    otherCost = fields.ListField(verbose_name='其他费用', null=True)
    Combined = fields.ListField(verbose_name='经费支出合计', null=True)
    balance = fields.StringField(verbose_name='项目经费结余情况', null=True)
    conclusion = fields.StringField(verbose_name='自查结论', null=True)
    termination = fields.StringField(verbose_name='终止申请书id')


# 终止意见
class TerminationOpinion(Document):
    unitOpinion = fields.StringField(null=True)
    termination = fields.StringField(verbose_name='终止申请书id')


# 用户使用情况报告
class TReport(Document):
    subjectName = fields.StringField(max_length=252, verbose_name='项目名称', null=True)
    contractNo = fields.StringField(max_length=252, verbose_name='合同编号', null=True)
    userName = fields.StringField(max_length=252, verbose_name='用户名称', null=True)
    registeredAddress = fields.StringField(max_length=252, verbose_name='通信地址', null=True)
    contact = fields.StringField(max_length=252, verbose_name='联系人', null=True)
    mobile = fields.StringField(max_length=252, verbose_name='联系电话', null=True)
    economicBenefits = fields.ListField(verbose_name='经济效益', null=True)
    socialBenefits = fields.StringField(verbose_name='应用情况及社会效益', null=True)
    termination = fields.StringField(verbose_name='终止申请书id')

    class Meta:
        db_table = 't_report'


# 项目经费支出决算表
class TExpenditureStatement(Document):
    unit = fields.StringField(max_length=252, verbose_name='申请单位', null=True)
    fillFrom = fields.DateField(verbose_name='填表日期', null=True)
    subjectName = fields.StringField(max_length=252, verbose_name='项目名称', null=True)
    contractNo = fields.StringField(max_length=252, verbose_name='合同编号', null=True)
    executionTime = fields.StringField(max_length=252, verbose_name='执行时间', null=True)
    planFundingCombined = fields.IntField(verbose_name='项目计划经费总额（万元)', decimal_places=2, max_digits=None, null=True)
    fiscalGrantFunding = fields.IntField(verbose_name='青秀区财政拨款金额（万元)', decimal_places=2, max_digits=None, null=True)
    remainingFunding = fields.IntField(verbose_name='结余科技经费（万元', decimal_places=2, max_digits=None, null=True)
    # head = fields.StringField(max_length=252, verbose_name='项目负责人')
    # financialHead = fields.StringField(max_length=252, verbose_name='财务负责人')
    # preparer = fields.StringField(max_length=252, verbose_name='填表人')
    # mobile = fields.StringField(max_length=252, verbose_name='联系电话')
    # 资金来源（万元）
    fiscalGrant = fields.ListField(verbose_name='青秀区财政拨款（含单位垫付科技款', null=True, blank=True)
    yearMonth = fields.ListField(verbose_name='年  月拨入', null=True)
    departmentProvide = fields.ListField(verbose_name='部门提供', null=True)
    bankLoan = fields.ListField(verbose_name='银行贷款', null=True)
    unitSelfRaised = fields.ListField(verbose_name='单位自筹', null=True)
    otherSources = fields.ListField(verbose_name='其他来源', null=True)
    fundingCombined = fields.ListField(verbose_name='经费来源合计', null=True)
    # 经费支出（万元）
    equipmentFee = fields.ListField(verbose_name='设备费', null=True)
    purchaseFee = fields.ListField(verbose_name='购置费', null=True)
    testFee = fields.ListField(verbose_name='试制费', null=True)
    equipmentRentalFee = fields.ListField(verbose_name='仪器设备租赁费', null=True)
    relatedOperatingExpenses = fields.ListField(verbose_name='相关业务费', null=True)
    materialsCosts = fields.ListField(verbose_name='材料费', null=True)
    testCost = fields.ListField(verbose_name='测试化验加工费', null=True)
    fuelCost = fields.ListField(verbose_name='燃料动力费', null=True)
    travelCost = fields.ListField(verbose_name='差旅费', null=True)
    meetingCost = fields.ListField(verbose_name='会议费', null=True)
    internationalCost = fields.ListField(verbose_name='国际合作与交流费', null=True)
    publishedCost = fields.ListField(verbose_name='出版/文献/信息传播/知识产权事务费', null=True)
    personnelCost = fields.ListField(verbose_name='人员费', null=True)
    laborCost = fields.ListField(verbose_name='劳务费', null=True)
    projectTeamPersonnel = fields.ListField(verbose_name='项目组人员', null=True)
    temporaryStaff = fields.ListField(verbose_name='临时聘用人员', null=True)
    expertCost = fields.ListField(verbose_name='专家咨询费', null=True)
    managementCost = fields.ListField(verbose_name='管理费', null=True)
    otherCost = fields.ListField(verbose_name='其他费用', null=True)
    indirectCost = fields.ListField(verbose_name='间接费用', null=True)
    Combined = fields.ListField(verbose_name='经费支出合计', null=True)
    termination = fields.StringField(verbose_name='终止申请书id')


# 附件
class TerminationAttachment(Document):
    types = fields.StringField(verbose_name='附件类型')
    attachmentContent = fields.ListField(verbose_name='附件路径+名称')
    termination = fields.StringField(verbose_name='终止申请书id')


class TKOpinionSheet(Document):
    types = fields.StringField(verbose_name='附件类型')
    attachmentContent = fields.ListField(verbose_name='附件路径+名称')
    termination = fields.StringField(verbose_name='终止申请书id', null=True)
    chargeTermination = fields.IntField(verbose_name='分管员发起终止申请书', null=True)
    subject = fields.IntField(verbose_name='课题ID', null=True)

    # subject = fields.StringField(verbose_name='课题id')
    # # returnReason = fields.StringField()
    # isArchives = fields.BooleanField(verbose_name='课题id', default=False)


class ChargeTermination(models.Model):
    subject = models.ForeignKey(to=Subject, verbose_name='课题', related_name='charge_termination_subject',
                                on_delete=models.SET_NULL, null=True, blank=True)
    state = models.CharField(max_length=252, verbose_name='状态', null=True)
    returnReason = models.CharField(max_length=252, verbose_name='终止原因', null=True, blank=True)
    declareTime = models.DateField(max_length=252, verbose_name='申请日期', null=True, blank=True)
    auditTime = models.DateField(max_length=252, verbose_name='审核时间', null=True, blank=True)
    charge = models.ForeignKey(to=User, verbose_name='分管员', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'charge_termination'
