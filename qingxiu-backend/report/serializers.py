from rest_framework import serializers

from report.models import ProgressReport


class ProgressReportSerializers(serializers.ModelSerializer):
    subject = serializers.SerializerMethodField(read_only=True)
    fillTime = serializers.DateField(format="%Y-%m-%d")
    attachmentPDF = serializers.CharField(read_only=True)

    class Meta:
        model = ProgressReport
        fields = (
            'id', 'name', 'contractNo', 'unit', 'head', 'fillTime', 'startStopYear', 'workProgress', 'problem',
            'planMeasures', 'state', 'subject', 'attachmentPDF')

    def get_subject(self, obj):
        try:
            return {'id': obj.subject.id,
                    'annualPlan': obj.subject.project.category.batch.annualPlan,
                    'contractNo': obj.subject.contract_subject.values('contractNo'),
                    'planCategory': obj.subject.project.category.planCategory,
                    'projectName': obj.subject.project.projectName,
                    'subjectName': obj.subject.subjectName,
                    'head': obj.subject.head,
                    'startStopYear': obj.subject.startStopYear,
                    "executionTime": obj.subject.executionTime
                    }
        except Exception as e:
            return None
