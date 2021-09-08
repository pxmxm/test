# 申报单位承诺及推荐意见
from decimal import Decimal

from django.db.models import Q
from django.utils.datetime_safe import strftime
from rest_framework import serializers
from rest_framework_mongoengine import serializers as mongodb_serializers

from concluding.models import SubjectConcluding
from expert.models import Expert, ExpertField
from expert.serializers import InnerExpertFieldSerializers
from research.serializers import ProposalSerializers
from subject.models import Subject, OpinionSheet, SubjectExpertsOpinionSheet, ExpertOpinionSheet, ExpectedResults, \
    FundingBudget, IntellectualProperty, SubjectUnitInfo, SubjectPersonnelInfo, \
    SubjectOtherInfo, AttachmentList, UnitCommitment, SubjectKExperts, SubjectInfo, Process, Attachment

from termination.models import SubjectTermination, ChargeTermination
from users.models import KExperts


# 课题
from utils.birthday import GetInformation


class SubjectSerializers(serializers.ModelSerializer):
    projectInfo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Subject
        fields = (
            'id', 'subjectName', 'unitName', 'head', 'phone', 'mobile', 'email', 'startStopYear', 'declareTime',
            'projectInfo')

    def get_projectInfo(self, obj):
        try:
            return {"annualPlan": obj.project.category.batch.annualPlan,
                    "planCategory": obj.project.category.planCategory,
                    "projectName": obj.project.projectName}
        except Exception as e:
            return None


# 项目流程
class ProcessSerializers(serializers.ModelSerializer):
    time = serializers.DateTimeField(format="%Y.%m.%d %H:%M:%S", required=False, read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Process
        fields = '__all__'

    def get_subject(self, obj):
        try:
            return obj.subject.subjectName
        except Exception as e:
            return None


# 导入附件清单
class AttachmentSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'


# 课题基本信息
class SubjectInfoSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = SubjectInfo
        fields = ('id', 'IAR', 'innovationType', 'formCooperation', 'phase', 'overallGoal', 'assessmentIndicators',
                  'subjectId')


# 单位、联合申报单位信息
class SubjectUnitInfoSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = SubjectUnitInfo
        fields = '__all__'


# 预期成果及经济效益
class ExpectedResultsSerializers(mongodb_serializers.DocumentSerializer):
    # newProduction = serializers.FloatField(format='')
    # newProduction = serializers.DecimalField(decimal_places=2, max_digits=None)
    # technicalTrading = serializers.FloatField()

    class Meta:
        model = ExpectedResults
        fields = '__all__'

    # def create(self, validated_data):
    #     Decimal(validated_data['technicalTrading'])*10000*100
    #     instance = super(ExpectedResultsSerializers, self).create(validated_data)
    #     return instance

    # def update(self, instance, validated_data):
    #     Decimal(validated_data['technicalTrading'])*10000*100
    #     instance = super(KExpertsSerializers, self).update(instance, validated_data)
    #     return instance


# 经费预算
class FundingBudgetSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = FundingBudget
        fields = '__all__'


# 知识产权
class IntellectualPropertySerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = IntellectualProperty
        fields = '__all__'


# 课题人员信息
class SubjectPersonnelInfoSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = SubjectPersonnelInfo
        fields = '__all__'


# 课题其他信息
class SubjectOtherInfoSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = SubjectOtherInfo
        fields = '__all__'


# 申报单位承诺及推荐意见
class UnitCommitmentSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = UnitCommitment
        fields = '__all__'


# 附件信息
class AttachmentListSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = AttachmentList
        fields = '__all__'


class SubjectUnitSerializers(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    contract = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Subject
        fields = ('id', 'subjectName', 'unitName', 'head', 'startStopYear', 'declareTime', 'executionTime', 'warning',
                  'subjectState', 'state', 'concludingState', 'terminationState', 'reviewState',
                  'returnReason', 'project', 'contract',)

    def get_project(self, obj):
        try:
            return {"annualPlan": obj.project.category.batch.annualPlan,
                    "planCategory": obj.project.category.planCategory,
                    "projectName": obj.project.projectName,
                    "charge": obj.project.charge.values('id', 'name') if obj.subjectState != '待提交' else '-'}
        except Exception as e:
            return None

    def get_contract(self, obj):
        try:
            return obj.contract_subject.values('id', 'contractNo', 'approvalMoney', 'state', 'contractState')
        except Exception as e:
            return None


class SubjectAdminSerializers(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    chargeName = serializers.SerializerMethodField(read_only=True)
    opinionSheet = serializers.SerializerMethodField(read_only=True)
    proposal = ProposalSerializers(read_only=True)
    contract = serializers.SerializerMethodField(read_only=True)
    # 结题申请时间
    concludingDeclareTime = serializers.SerializerMethodField(read_only=True)
    # 终止申请时间
    terminationDeclareTime = serializers.SerializerMethodField(read_only=True)
    chargeTerminationDeclareTime = serializers.SerializerMethodField(read_only=True)
    unitType = serializers.SerializerMethodField(read_only=True)
    terminationID = serializers.SerializerMethodField(read_only=True)
    acceptanceId = serializers.SerializerMethodField(read_only=True)
    pExperts = serializers.SerializerMethodField(read_only=True)
    chargeTerminationId = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Subject
        fields = (
            'id', 'subjectName', 'unitName', 'head', 'phone', 'mobile', 'warning', 'declareTime', 'reviewWay',
            'giveTime',
            'startStopYear', 'executionTime', 'subjectState', 'state', 'concludingState', 'terminationState',
            'returnReason',
            'terminationOriginator', 'results', 'project', 'chargeName', 'opinionSheet',
            'proposal', 'contract', 'unitType', 'concludingDeclareTime', 'terminationDeclareTime',
            'chargeTerminationDeclareTime',
            'terminationID', 'acceptanceId', 'pExperts', 'chargeTerminationId')

    def get_pExperts(self, obj):
        try:
            lists = []
            for i in obj.subject_three.values('pExperts__id',
                                              'pExperts__name',
                                              'pExperts__experts__mobile',
                                              'pExperts__experts__unit',
                                              'pExperts__experts__title', ):
                p_experts = {"pExpertsId": i['pExperts__id'],
                             "name": i['pExperts__name'],
                             "mobile": i['pExperts__experts__mobile'],
                             "unit": i['pExperts__experts__unit'],
                             "title": i['pExperts__experts__title'],
                             }
                lists.append(p_experts)
            return lists
        except Exception as e:
            return None

    def get_project(self, obj):
        try:
            return {"annualPlan": obj.project.category.batch.annualPlan,
                    "projectBatch": obj.project.category.batch.projectBatch,
                    "planCategory": obj.project.category.planCategory,
                    "projectName": obj.project.projectName,
                    "agency": obj.project.category.batch.agency.name}
        except Exception as e:
            return {"annualPlan": obj.project.category.batch.annualPlan,
                    "projectBatch": obj.project.category.batch.projectBatch,
                    "planCategory": obj.project.category.planCategory,
                    "projectName": obj.project.projectName,
                    "agency": '-'}

    def get_chargeName(self, obj):
        try:
            return obj.project.charge.values('id', 'name')
        except Exception as e:
            return None

    def get_opinionSheet(self, obj):
        try:
            return obj.opinion_sheet_subject.values('proposal', 'proposalFunding', 'subjectScore', 'expertsList')
        except Exception as e:
            return None

    def get_contract(self, obj):
        try:
            return obj.contract_subject.values('id', 'contractNo', 'approvalMoney')
        except Exception as e:
            return None

    def get_concludingDeclareTime(self, obj):
        try:
            return obj.subject_concluding.filter(subject_id=obj.id, concludingState='待审核').values('declareTime',
                                                                                                  'reviewTime',
                                                                                                  'results')
        except Exception as e:
            return None

    def get_terminationDeclareTime(self, obj):
        try:
            return obj.subject_termination.filter(terminationState='待审核', subject_id=obj.id).values('declareTime',
                                                                                                    'reviewTime',
                                                                                                    'results')
        except Exception as e:
            return None

    def get_chargeTerminationDeclareTime(self, obj):
        try:
            return obj.charge_termination_subject.values('declareTime')
        except Exception as e:
            return None

    def get_unitType(self, obj):
        try:
            unit = SubjectUnitInfo.objects.get(subjectId=obj.id)
            data = {
                "unitType": [unit.unitInfo[0]['unitName'], unit.unitInfo[0]['industry'],
                             unit.unitInfo[0]['fundsAccounted']],
                "jointUnitType": [(i['unitName'], i['industry'], i['fundsAccounted']) for i in unit.jointUnitInfo]
            }
            return data
        except Exception as e:
            return None

    def get_terminationID(self, obj):
        try:
            subject_termination = SubjectTermination.objects.exclude(subject_id=obj.id,
                                                                     terminationState='终止不通过').filter(subject_id=obj.id)

            return [i.termination for i in subject_termination]
        except Exception as e:
            return None

    def get_acceptanceId(self, obj):
        try:
            subject_concluding = SubjectConcluding.objects.exclude(subject_id=obj.id, concludingState='结题复核').filter(
                subject_id=obj.id)

            return [i.acceptance for i in subject_concluding]
        except Exception as e:
            return None

    def get_chargeTerminationId(self, obj):
        try:
            charge_termination = ChargeTermination.objects.get(state='待审核', subject=obj)
            return {"id": charge_termination.id, "returnReason": charge_termination.returnReason}
        except Exception as e:
            return None


class SubjectChargeSerializers(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    proposal = ProposalSerializers(read_only=True)
    contract = serializers.SerializerMethodField(read_only=True)
    unitType = serializers.SerializerMethodField(read_only=True)
    AkExperts = serializers.SerializerMethodField(read_only=True)
    TkExperts = serializers.SerializerMethodField(read_only=True)
    # 结题申请时间
    concludingDeclareTime = serializers.SerializerMethodField(read_only=True)
    # 终止申请时间
    terminationDeclareTime = serializers.SerializerMethodField(read_only=True)
    terminationID = serializers.SerializerMethodField(read_only=True)
    acceptanceId = serializers.SerializerMethodField(read_only=True)
    reviewTime = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)


    class Meta:
        model = Subject
        fields = (
            'id', 'subjectName', 'unitName', 'head', 'mobile', 'phone', 'startStopYear', 'declareTime', 'executionTime',
            'warning', 'subjectState', 'state', 'concludingState', 'terminationState', 'terminationOriginator',
            'giveTime', 'returnReason',
            'reviewTime', 'project', 'proposal', 'contract', 'AkExperts', 'TkExperts', 'unitType',
            'concludingDeclareTime',
            'terminationDeclareTime', 'applyTime', 'terminationID', 'double', 'acceptanceId', 'results',)

    def get_project(self, obj):
        try:
            return {"annualPlan": obj.project.category.batch.annualPlan,
                    "projectBatch": obj.project.category.batch.projectBatch,
                    "planCategory": obj.project.category.planCategory,
                    "projectName": obj.project.projectName,}
        except Exception as e:
            return None

    def get_contract(self, obj):
        try:
            return obj.contract_subject.values('id', 'contractNo', 'approvalMoney', 'contractState')
        except Exception as e:
            return None

    def get_AkExperts(self, obj):
        try:
            subject_concluding = SubjectConcluding.objects.exclude(subject_id=obj.id, concludingState='结题复核').filter(
                subject_id=obj.id)
            subject_concluding = [i.acceptance for i in subject_concluding]
            k_experts = [i['kExperts'] for i in
                         SubjectKExperts.objects.filter(subject=obj.id, reviewState=False,
                                                        acceptance=subject_concluding[0]).values('kExperts')]
            return [{
                "id": k,
                "name": KExperts.objects.get(id=k).name,
                "unit": KExperts.objects.get(id=k).unit,
                "mobile": KExperts.objects.get(id=k).mobile,
                "title": KExperts.objects.get(id=k).title} for k in k_experts]
        except Exception as e:
            return None

    def get_TkExperts(self, obj):
        try:
            subject_termination = SubjectTermination.objects.exclude(subject_id=obj.id,
                                                                     terminationState='终止不通过').filter(subject_id=obj.id)
            subject_termination = [i.termination for i in subject_termination]

            k_experts = [i['kExperts'] for i in
                         SubjectKExperts.objects.filter(subject=obj.id, reviewState=False,
                                                        termination=subject_termination[0]).values('kExperts')]
            return [{
                "id": k,
                "name": KExperts.objects.get(id=k).name,
                "unit": KExperts.objects.get(id=k).unit,
                "mobile": KExperts.objects.get(id=k).mobile,
                "title": KExperts.objects.get(id=k).title} for k in k_experts]
        except Exception as e:
            return None

    def get_concludingDeclareTime(self, obj):
        try:
            return obj.subject_concluding.filter(Q(concludingState='补正资料') | Q(concludingState='待审核'),
                                                 subject_id=obj.id).values('declareTime',
                                                                           'reviewTime',
                                                                           'results')
        except Exception as e:
            return None

    def get_terminationDeclareTime(self, obj):
        try:
            return obj.subject_termination.filter(Q(terminationState='待审核') | Q(terminationState='补正资料'),
                                                  subject_id=obj.id).values('declareTime',
                                                                            'reviewTime',
                                                                            'results')

        except Exception as e:
            return None

    def get_unitType(self, obj):
        try:
            unit = SubjectUnitInfo.objects.get(subjectId=obj.id)
            data = {
                "unitType": [unit.unitInfo[0]['unitName'], unit.unitInfo[0]['industry'],
                             unit.unitInfo[0]['fundsAccounted']],
                "jointUnitType": [(i['unitName'], i['industry'], i['fundsAccounted']) for i in unit.jointUnitInfo]
            }
            return data
        except Exception as e:
            return None

    def get_terminationID(self, obj):
        try:
            subject_termination = SubjectTermination.objects.exclude(subject_id=obj.id,
                                                                     terminationState='终止不通过').filter(subject_id=obj.id)
            return [i.termination for i in subject_termination]
        except Exception as e:
            return None

    def get_acceptanceId(self, obj):
        try:
            subject_concluding = SubjectConcluding.objects.exclude(subject_id=obj.id, concludingState='结题复核').filter(
                subject_id=obj.id)

            return [i.acceptance for i in subject_concluding]
        except Exception as e:
            return None


class SubjectOrganSerializers(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    pExperts = serializers.SerializerMethodField(read_only=True)
    opinionSheet = serializers.SerializerMethodField(read_only=True)
    acceptance = serializers.SerializerMethodField(read_only=True)
    AExpert = serializers.SerializerMethodField(read_only=True)
    contract = serializers.SerializerMethodField(read_only=True)
    termination = serializers.SerializerMethodField(read_only=True)
    TExpert = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Subject
        fields = (
            'id', 'subjectName', 'unitName', 'head', 'mobile', 'executionTime', 'subjectState', 'state',
            'terminationState', 'reviewWay', 'projectTeam', 'double', 'project', 'pExperts', 'opinionSheet',
            'isEntry', 'acceptance', 'AExpert', 'concludingState', 'contract', 'termination', 'TExpert')

    def get_project(self, obj):
        try:
            return {"annualPlan": obj.project.category.batch.annualPlan,
                    "projectBatch": obj.project.category.batch.projectBatch,
                    "planCategory": obj.project.category.planCategory,
                    "projectName": obj.project.projectName,
                    "state": obj.project.category.batch.state,
                    "opinionState": obj.project.category.batch.opinionState}
        except Exception as e:
            return None

    # def get_pExperts(self, obj):
    #     try:
    #         lists = []
    #         for i in obj.subject_three.values('pExperts__id',
    #                                           'pExperts__name',
    #                                           'pExperts__experts__mobile',
    #                                           'pExperts__experts__unit',
    #                                           'pExperts__experts__title',
    #                                           'isReview',
    #                                           'expertOpinionSheet__attachmentPDF'):
    #             p_experts = {"pExpertsId": i['pExperts__id'],
    #                          "name": i['pExperts__name'],
    #                          "mobile": i['pExperts__experts__mobile'],
    #                          "unit": i['pExperts__experts__unit'],
    #                          "title": i['pExperts__experts__title'],
    #                          'isReview': i['isReview'],
    #                          'attachmentPDF': i['expertOpinionSheet__attachmentPDF']
    #                          }
    #             lists.append(p_experts)
    #         return lists
    #     except Exception as e:
    #         return None

    def get_pExperts(self, obj):
        try:
            lists = []
            for i in obj.subject_three.values('pExperts__id',
                                              'pExperts__expert__name',
                                              'pExperts__expert__mobile',
                                              'pExperts__expert__company',
                                              'pExperts__expert__title__name',
                                              'isReview',
                                              'expertOpinionSheet__attachmentPDF'):
                p_experts = {"pExpertsId": i['pExperts__id'],
                             "name": i['pExperts__expert__name'],
                             "mobile": i['pExperts__expert__mobile'],
                             "unit": i['pExperts__expert__company'],
                             "title": i['pExperts__expert__title__name'],
                             'isReview': i['isReview'],
                             'attachmentPDF': i['expertOpinionSheet__attachmentPDF']
                             }
                lists.append(p_experts)
            return lists
        except Exception as e:
            return None

    def get_opinionSheet(self, obj):
        try:

            return obj.opinion_sheet_subject.values('proposal', 'proposalFunding', 'subjectScore', 'expertsList',
                                                    'attachment')
        except Exception as e:
            return None

    def get_acceptance(self, obj):
        try:
            # return obj.subject_concluding.filter(concludingState='待审核').values("acceptance", "reviewTime",
            #                                                                      "declareTime", "concludingState",
            #                                                                      "results")
            return obj.subject_concluding.exclude(concludingState='结题复核').values("acceptance", "reviewTime",
                                                                                 "declareTime", "concludingState",
                                                                                 "results")
            # return obj.subject_concluding.values("acceptance", "reviewTime", "declareTime", "concludingState",
            #                                      "results")
        except Exception as e:
            return None

    def get_termination(self, obj):
        try:
            # return obj.subject_termination.values("termination", "reviewTime", "declareTime", "terminationState",
            #                                       "results")
            return obj.subject_termination.exclude(terminationState='终止不通过').values("termination", "reviewTime",
                                                                                    "declareTime", "terminationState",
                                                                                    "results")
        except Exception as e:
            return None

    def get_contract(self, obj):
        try:
            return obj.contract_subject.values('id', 'contractNo', 'approvalMoney', 'contractState')
        except Exception as e:
            return None

    def get_AExpert(self, obj):
        try:
            acceptance = SubjectConcluding.objects.exclude(subject_id=obj.id, concludingState='结题复核').filter(
                subject_id=obj.id, concludingState='待审核').get().acceptance
            expert = [i['expert'] for i in
                      SubjectKExperts.objects.filter(subject=obj.id, reviewState=False, acceptance=acceptance).values(
                          'expert')]
            return [{
                "id": k,
                "name": Expert.objects.get(id=k).name,
                "company": Expert.objects.get(id=k).company,
                "mobile": Expert.objects.get(id=k).mobile,
                "title": Expert.objects.get(id=k).title.name,
                "tags": Expert.objects.get(id=k).tags,
                "idCardNo": Expert.objects.get(id=k).id_card_no,
                'gender': GetInformation(Expert.objects.get(id=k).id_card_no).get_sex(),
                "field": [InnerExpertFieldSerializers(instance=ExpertField.objects.get(id=i['id']), many=False).data
                          for i in Expert.objects.get(id=k).field.values("id", "name", "parent", "enable")]}
                for k in expert]
        except Exception as e:
            return None

    def get_TExpert(self, obj):
        try:
            subject_termination = SubjectTermination.objects.exclude(subject_id=obj.id,
                                                                     terminationState='终止不通过').filter(subject_id=obj.id)
            subject_termination = [i.termination for i in subject_termination]

            expert = [i['expert'] for i in
                      SubjectKExperts.objects.filter(subject=obj.id, reviewState=False,
                                                     termination=subject_termination[0]).values('expert')]
            return [{
                "id": k,
                "name": Expert.objects.get(id=k).name,
                "company": Expert.objects.get(id=k).company,
                "mobile": Expert.objects.get(id=k).mobile,
                "title": Expert.objects.get(id=k).title.name,
                "tags": Expert.objects.get(id=k).tags,
                "idCardNo": Expert.objects.get(id=k).id_card_no,
                'gender': GetInformation(Expert.objects.get(id=k).id_card_no).get_sex(),
                "field": [InnerExpertFieldSerializers(instance=ExpertField.objects.get(id=i['id']), many=False).data
                          for i in Expert.objects.get(id=k).field.values("id", "name", "parent", "enable") if
                          i['enable'] is True]} for k in expert]

            # "field": Expert.objects.get(id=k).field.values('name')}for k in expert]

        except Exception as e:
            return None


class PGExpertsSubjectOpinionSheetSerializers(serializers.ModelSerializer):
    pExperts = serializers.SerializerMethodField(read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SubjectExpertsOpinionSheet
        fields = (
            'id', 'pExperts', 'subject', 'state', 'money', 'agenciesState', 'returnReason', 'declareTime')

    # def get_pExperts(self, obj):
    #     try:
    #         return {"id": obj.pExperts.id, "name": obj.pExperts.name, "mobile": obj.pExperts.experts.mobile,
    #                 "unit": obj.pExperts.experts.unit, "title": obj.pExperts.experts.title}
    #     except Exception as e:
    #         return None

    def get_pExperts(self, obj):
        try:
            return {"id": obj.pExperts.id, "expertId": obj.pExperts.expert.id, "name": obj.pExperts.expert.name,
                    "mobile": obj.pExperts.expert.mobile,
                    "unit": obj.pExperts.expert.company, "title": obj.pExperts.expert.title.name,
                    "bank": obj.pExperts.expert.bank, "bankBranch": obj.pExperts.expert.bank_branch,
                    "bankAccount": obj.pExperts.expert.bank_account}
        except Exception as e:
            return None

    def get_subject(self, obj):
        try:
            return {"id": obj.subject.id,
                    "annualPlan": obj.subject.project.category.batch.annualPlan,
                    "projectBatch": obj.subject.project.category.batch.projectBatch,
                    "planCategory": obj.subject.project.category.planCategory,
                    "projectName": obj.subject.project.projectName,
                    "subjectName": obj.subject.subjectName,
                    "unitName": obj.subject.unitName,
                    "head": obj.subject.head}
        except Exception as e:
            return None


# 评估机构评审意见表
class OpinionSheetSerializers(serializers.ModelSerializer):
    class Meta:
        model = OpinionSheet
        fields = ('id', 'planCategory', 'unitName', 'subjectName', 'subjectScore', 'proposal', 'proposalFunding',
                  'projectProposal', 'expertsList', 'attachment')


# 专家评审意见表
class PGOpinionSheetSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertOpinionSheet
        fields = ('id', 'planCategory', 'unitName', 'subjectName', 'subjectScore', 'proposal', 'proposalFunding',
                  'projectProposal', 'expertName', 'expertUnit')


class PGExpertsSystemSerializers(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField(read_only=True)
    expertOpinionSheet = serializers.SerializerMethodField(read_only=True)
    reviewTime = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = SubjectExpertsOpinionSheet
        fields = ('id', 'subject', 'state', 'reviewWay', 'reviewTime', 'expertOpinionSheet', 'returnReason')

    def get_subject(self, obj):
        try:
            return {"id": obj.subject.id,
                    "annualPlan": obj.subject.project.category.batch.annualPlan,
                    "planCategory": obj.subject.project.category.planCategory,
                    "projectName": obj.subject.project.projectName,
                    "subjectName": obj.subject.subjectName,
                    "unitName": obj.subject.unitName,
                    "head": obj.subject.head,
                    "startStopYear": obj.subject.startStopYear,
                    "executionTime": obj.subject.executionTime,
                    "handOverState": obj.subject.handOverState,
                    "scienceFunding": FundingBudget.objects.get(subjectId=obj.subject.id).scienceFunding}
        except Exception as e:
            return None

    def get_expertOpinionSheet(self, obj):
        try:
            return {"id": obj.expertOpinionSheet.id, "proposal": obj.expertOpinionSheet.proposal,
                    'attachmentPDF': obj.expertOpinionSheet.attachmentPDF}
        except Exception as e:
            return None


class SubjectKExpertsSerializers(serializers.ModelSerializer):
    expert = serializers.SerializerMethodField(read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)
    reviewTime_a = serializers.SerializerMethodField(read_only=True)
    reviewTime_t = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SubjectKExperts
        fields = ('id', 'expert', 'subject', 'money', 'acceptance', 'termination', 'reviewTime_a', 'reviewTime_t')

    def get_expert(self, obj):
        try:
            return {"id": obj.expert.id, "name": obj.expert.name, "mobile": obj.expert.mobile,
                    "idCardNo": obj.expert.id_card_no, "company": obj.expert.company, "title": obj.expert.title.name,
                    "bank": obj.expert.bank, "bankBranch": obj.expert.bank_branch,
                    "bankAccount": obj.expert.bank_account,
                    "tags":obj.expert.tags,
                    "field": [InnerExpertFieldSerializers(instance=ExpertField.objects.get(id=i['id']), many=False).data for i in obj.expert.field.values('id')]
                    }
        except Exception as e:
            return None

    def get_subject(self, obj):
        try:
            return {"id": obj.subject.id,
                    "annualPlan": obj.subject.project.category.batch.annualPlan,
                    "projectBatch": obj.subject.project.category.batch.projectBatch,
                    "planCategory": obj.subject.project.category.planCategory,
                    "projectName": obj.subject.project.projectName,
                    "subjectName": obj.subject.subjectName,
                    "unitName": obj.subject.unitName,
                    "head": obj.subject.head,
                    "executionTime": obj.subject.executionTime}
        except Exception as e:
            return None

    def get_reviewTime_a(self, obj):
        try:
            # review_time_a = SubjectConcluding.objects.filter(acceptance=obj.acceptance).values('reviewTime', "results")
            review_time_a = SubjectConcluding.objects.filter(acceptance=obj.acceptance).extra(
                select={"reviewTime": '''to_date("reviewTime"::text,'yyyy-MM-dd')'''}).values('reviewTime', "results")

            return review_time_a
        except Exception as e:

            return None

    def get_reviewTime_t(self, obj):
        try:
            review_time_t = SubjectTermination.objects.filter(termination=obj.termination).values('reviewTime',
                                                                                                  "results")
            return review_time_t
        except Exception as e:
            return None
