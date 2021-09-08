from rest_framework import serializers
from rest_framework_mongoengine import serializers as mongodb_serializers

from subject.models import Subject
from termination.models import Termination, TResearchers, TOutput, TExpenditureStatement, \
    TCheckList, TerminationAttachment, TReport, TKOpinionSheet, SubjectTermination, ChargeTermination, \
    TerminationOpinion


class SubjectTerminationSerializers(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    contract = serializers.SerializerMethodField(read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)
    attachmentPDF = serializers.CharField(read_only=True)
    chargeTerminationId = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SubjectTermination
        fields = ('id', 'termination', 'declareTime', 'terminationState', 'reviewTime', 'results', 'subject', 'project', 'contract', 'attachmentPDF', 'chargeTerminationId')


    def get_subject(self, obj):
        try:
            return {"id": obj.subject.id,
                    "head": obj.subject.head,
                    "unitName": obj.subject.unitName,
                    "subjectName": obj.subject.subjectName,
                    "executionTime": obj.subject.executionTime,
                    "terminationOriginator": obj.subject.terminationOriginator,
                    "returnReason": obj.subject.returnReason
                    }
        except Exception as e:
            return None

    def get_project(self, obj):
        try:
            return {"annualPlan": obj.subject.project.category.batch.annualPlan,
                    "planCategory": obj.subject.project.category.planCategory,
                    "projectName": obj.subject.project.projectName}
        except Exception as e:
            return None

    def get_contract(self, obj):
        try:
            return obj.subject.contract_subject.values('id', 'contractNo')
        except Exception as e:
            return None

    def get_chargeTerminationId(self, obj):
        try:
            charge_termination = ChargeTermination.objects.get(state='项目终止', subject=obj.subject.id)
            return {"id": charge_termination.id}
        except Exception as e:
            return None

# 终止申请书
class TerminationSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = Termination
        fields = '__all__'


# 主要承担人员
class TResearchersSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = TResearchers
        fields = '__all__'


# 项目投入产出基本情况表
class TOutputSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = TOutput
        fields = '__all__'


class TCheckListSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = TCheckList
        fields = '__all__'


# 终止意见
class TerminationOpinionSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = TerminationOpinion
        fields = '__all__'


# 用户使用情况报告
class TReportSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = TReport
        fields = '__all__'


# 项目经费支出决算表
class TExpenditureStatementSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = TExpenditureStatement
        fields = '__all__'


# 附件
class TerminationAttachmentSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = TerminationAttachment
        fields = '__all__'


# 附件情况表
class TKOpinionSheetSerializers(mongodb_serializers.DocumentSerializer):
    returnReason = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TKOpinionSheet
        fields = '__all__'

    def get_returnReason(self, obj):
        try:
            charge_termination = ChargeTermination.objects.get(id=obj.chargeTermination)
            return {"returnReason": charge_termination.returnReason, "auditTime": charge_termination.auditTime}
        except Exception as e:

            print(e)
            return None


class ChargeTerminationSerializers(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    contract = serializers.SerializerMethodField(read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChargeTermination
        fields = ('id', 'state', 'declareTime', 'returnReason', 'auditTime', 'subject', 'project', 'contract')

    def get_subject(self, obj):
        try:
            return {"id": obj.subject.id,
                    "head": obj.subject.head,
                    "subjectName": obj.subject.subjectName,
                    "executionTime": obj.subject.executionTime,
                    "terminationOriginator": obj.subject.terminationOriginator,
                    "phone": obj.subject.phone,
                    "unitName": obj.subject.unitName,
                    }
        except Exception as e:
            return None

    def get_project(self, obj):
        try:
            return {"annualPlan": obj.subject.project.category.batch.annualPlan,
                    'projectBatch':obj.subject.project.category.batch.projectBatch,
                    "planCategory": obj.subject.project.category.planCategory,
                    "projectName": obj.subject.project.projectName}
        except Exception as e:
            return None

    def get_contract(self, obj):
        try:
            return obj.subject.contract_subject.values('id', 'contractNo')
        except Exception as e:
            return None