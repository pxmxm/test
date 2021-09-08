from rest_framework_mongoengine import serializers as mongodb_serializers

from rest_framework import serializers

from contract.models import ContractContent
from funding.models import GrantSubject, AllocatedSingle


class GrantSubjectSerializers(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField(read_only=True)
    scienceFunding = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GrantSubject
        fields = (
            'id', 'grantType', 'money', 'state', 'attachmentName', 'attachment', 'attachments', 'subject', 'scienceFunding')

    def get_subject(self, obj):
        try:
            return {"subjectId": obj.subject.id,
                    "annualPlan": obj.subject.project.category.batch.annualPlan,
                    "projectBatch": obj.subject.project.category.batch.projectBatch,
                    "planCategory": obj.subject.project.category.planCategory,
                    "projectName": obj.subject.project.projectName,
                    "contractNo": obj.subject.contract_subject.values('contractNo'),
                    "subjectName": obj.subject.subjectName,
                    "unitName": obj.subject.unitName,
                    "head": obj.subject.head,
                    "mobile": obj.subject.mobile,
                    }
        except Exception as e:
            print(e)
            return None

    def get_scienceFunding(self, obj):
        try:
            contract_content = [i['contractContent'] for i in obj.subject.contract_subject.values('contractContent')]
            for j in contract_content:
                contract_content = ContractContent.objects.get(id=j)
            return contract_content.scienceFunding
        except Exception as e:
            print(e)
            return None


class AllocatedSingleSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = AllocatedSingle
        fields = '__all__'
