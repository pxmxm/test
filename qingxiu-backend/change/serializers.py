import calendar
import datetime

from dateutil.relativedelta import relativedelta
from rest_framework import serializers

from backend.exceptions import CustomValidationError
from change.models import ProjectLeaderChange, ProjectDelayChange, ChangeSubject, TechnicalRouteChange
from subject.models import Subject


# 项目负责人变更
class ProjectLeaderChangeSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    kOpinion = serializers.CharField(read_only=True)

    class Meta:
        model = ProjectLeaderChange
        fields = (
            'id', 'name', 'contractNo', 'unit', 'head', 'changeHead', 'phone', 'idNumber', 'changeReason',
            'unitOpinion', 'kOpinion',
            'created', 'updated')


# 重大技术路线调整
class TechnicalRouteChangeSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    kOpinion = serializers.CharField(read_only=True)

    class Meta:
        model = TechnicalRouteChange
        fields = (
            'id', 'name', 'contractNo', 'unit', 'head', 'adjustmentContent', 'adjustmentAfter',
            'adjustmentReason', 'unitOpinion', 'kOpinion', 'created', 'updated')


# 项目延期申请
class ProjectDelayChangeSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    kOpinion = serializers.CharField(read_only=True)
    subjectId = serializers.CharField(required=True, allow_blank=False, write_only=True)

    class Meta:
        model = ProjectDelayChange
        fields = (
            'id', 'name', 'contractNo', 'unit', 'head', 'delayTime', 'delayReason',
            'unitOpinion', 'kOpinion', 'created', 'updated', 'subjectId')

    def validate(self, attrs):
        subject = Subject.objects.get(id=attrs['subjectId'])
        if subject.executionTime == '-':
            raise CustomValidationError(detail={'code': 3, 'message': '执行时间为空'})
        start_stop_year = subject.executionTime.split('-')
        start_stop_year = start_stop_year[1]
        start_stop_year = start_stop_year.split('.')
        x, y = calendar.monthrange(int(start_stop_year[0]), int(start_stop_year[1]))
        last_day = datetime.date(year=int(start_stop_year[0]), month=int(start_stop_year[1]), day=y)
        new_time = datetime.date.today()
        three_month_gae = datetime.date(year=int(start_stop_year[0]), month=int(start_stop_year[1]),
                                        day=1) - relativedelta(months=2)
        if subject.subject_change.filter(changeType='项目延期', state="通过").count() != 0:
            raise CustomValidationError(detail={'code': 1, 'message': '只能申请一次'})
        if three_month_gae > new_time or last_day < new_time:
            raise CustomValidationError(detail={'code': 2, 'message': '项目剩余执行时间超过三个月，不允许申请延期'})
        del (attrs['subjectId'])
        return attrs


# 项目变更类型
class ChangeSubjectSerializers(serializers.ModelSerializer):
    changeTime = serializers.DateTimeField(format="%Y-%m-%d", required=False, read_only=True)
    subject = serializers.SerializerMethodField(read_only=True)
    ProjectLeaderChange = serializers.SerializerMethodField(read_only=True)
    TechnicalRouteChange = serializers.SerializerMethodField(read_only=True)
    ProjectDelayChange = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChangeSubject
        fields = (
            'id', 'changeType', 'state', 'changeTime', 'attachment', 'subject', 'isUpload', 'ProjectLeaderChange',
            'TechnicalRouteChange', 'ProjectDelayChange')

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
                    }
        except Exception as e:
            return None

    def get_ProjectDelayChange(self, obj):
        try:
            project_delay_change = ProjectDelayChange.objects.get(changeSubject_id=obj.id)
            return {"name": project_delay_change.name,
                    "contractNo": project_delay_change.contractNo,
                    "unit": project_delay_change.unit,
                    "head": project_delay_change.head,
                    "delayTime": project_delay_change.delayTime,
                    "delayReason": project_delay_change.delayReason,
                    "unitOpinion": project_delay_change.unitOpinion,
                    "kOpinion": project_delay_change.kOpinion,
                    }
        except Exception as e:
            return None

    def get_TechnicalRouteChange(self, obj):

        try:
            technical_route_change = TechnicalRouteChange.objects.get(changeSubject_id=obj.id)
            return {"name": technical_route_change.name,
                    "contractNo": technical_route_change.contractNo,
                    "unit": technical_route_change.unit,
                    "head": technical_route_change.head,
                    "adjustmentContent": technical_route_change.adjustmentContent,
                    "adjustmentAfter": technical_route_change.adjustmentAfter,
                    "adjustmentReason": technical_route_change.adjustmentReason,
                    "unitOpinion": technical_route_change.unitOpinion,
                    "kOpinion": technical_route_change.kOpinion,
                    }
        except Exception as e:
            return None

    def get_ProjectLeaderChange(self, obj):

        try:
            project_leader_change = ProjectLeaderChange.objects.get(changeSubject_id=obj.id)
            return {"name": project_leader_change.name,
                    "contractNo": project_leader_change.contractNo,
                    "unit": project_leader_change.unit,
                    "head": project_leader_change.head,
                    "changeHead": project_leader_change.changeHead,
                    "phone": project_leader_change.phone,
                    "idNumber": project_leader_change.idNumber,
                    "changeReason": project_leader_change.changeReason,
                    "unitOpinion": project_leader_change.unitOpinion,
                    "kOpinion": project_leader_change.kOpinion,

                    }
        except Exception as e:
            return None
