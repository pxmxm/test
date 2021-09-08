from rest_framework import serializers
from rest_framework_mongoengine import serializers as mongodb_serializers

# 验收申请书
from concluding.models import Acceptance, Researchers, Output, ExpenditureStatement, \
    AcceptanceAttachment, CheckList, KOpinionSheet, SubjectConcluding, AcceptanceOpinion


class SubjectConcludingSerializers(serializers.ModelSerializer):
    project = serializers.SerializerMethodField(read_only=True)
    contract = serializers.SerializerMethodField(read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)
    attachmentPDF = serializers.CharField(read_only=True)

    class Meta:
        model = SubjectConcluding
        fields = ('id', 'acceptance', 'declareTime', 'concludingState', 'reviewTime', 'results', 'subject', 'project', 'contract', 'attachmentPDF')

    def get_subject(self, obj):
            try:
                return {"id": obj.subject.id,
                        "head": obj.subject.head,
                        "subjectName": obj.subject.subjectName,
                        "executionTime": obj.subject.executionTime,
                        "returnReason": obj.subject.returnReason,
                        "unitName": obj.subject.unitName
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


class AcceptanceSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = Acceptance
        fields = (
            'id', 'contractNo', 'subjectName', 'unitName', 'applyUnit', 'declareTime', 'registeredAddress',
            'contact', 'mobile', 'zipCode', 'email', 'industry', 'startStopYear',
            'indicatorsCompletion', 'otherInstructions', 'unitInfo', 'jointUnitInfo')


# 主要承担人员
class ResearchersSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = Researchers
        fields = "__all__"


# 项目投入产出基本情况表
class OutputSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = Output
        fields = '__all__'

# 财务自查表
class CheckListSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = CheckList
        fields = '__all__'

# 验收意见
class AcceptanceOpinionSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = AcceptanceOpinion
        fields = '__all__'


# 项目经费支出决算表
class ExpenditureStatementSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = ExpenditureStatement
        fields = '__all__'


# 附件情况表
class AcceptanceAttachmentSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = AcceptanceAttachment
        fields = '__all__'


# 附件情况表
class KOpinionSheetSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = KOpinionSheet
        fields = '__all__'