from rest_framework import serializers
from rest_framework_mongoengine import serializers as mongodb_serializers

from backend.exceptions import CustomValidationError
from contract.models import Contract, ContractContent, ContractAttachment


class ContractAttachmentSerializers(mongodb_serializers.DocumentSerializer):
    class Meta:
        model = ContractAttachment
        fields = '__all__'


class ContractContentSerializers(mongodb_serializers.DocumentSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    executionTime = serializers.CharField()

    class Meta:
        model = ContractContent
        fields = '__all__'

    def validate(self, attr):
        if '-' not in self.initial_data['executionTime']:
            raise CustomValidationError(detail={'code': 1, 'message': '项目实施时间格式不正确'})
        return attr


class ContractSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    jointAgreement = ContractContentSerializers(read_only=True)
    attachment = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contract
        fields = (
            'id', 'contractNo', 'approvalMoney', 'created', 'updated', 'jointAgreement')

    def get_joint_agreement(self, obj):
        try:
            return ContractContent.objects.get(id=obj.contract_content).jointAgreement
        except Exception as e:
            return None
