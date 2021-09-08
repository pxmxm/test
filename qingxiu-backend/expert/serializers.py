from rest_framework import serializers
from expert.models import Expert, ExpertField, ExpertProjectType, ExpertTitle, ExpertEducation, ExpertWork, ExpertDuty, \
    ExpertAgency, AvoidanceUnit, Enclosure, ExpertRecordExit, ExpertRecordEdit
from subject.models import Subject, SubjectExpertsOpinionSheet, SubjectKExperts
from users.models import Enterprise, User
from utils.birthday import GetInformation


class EnterpriseSerializers(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    info = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.enterprise.id if obj.enterprise else None

    def get_info(self, obj):
        return {
            'name': obj.name,
            'id_card_no': obj.username,
            'user_id': obj.id,
        }

    class Meta:
        model = User
        fields = ['id', 'info']


class ExpertRecordExitSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertRecordExit
        fields = '__all__'


class ExpertRecordEditSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertRecordEdit
        fields = '__all__'


class EnclosureSerializers(serializers.ModelSerializer):
    class Meta:
        model = Enclosure
        fields = '__all__'


class AvoidanceUnitSerializers(serializers.ModelSerializer):
    class Meta:
        model = AvoidanceUnit
        fields = '__all__'


class ExpertEducationSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertEducation
        fields = '__all__'


class ExpertWorkSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertWork
        fields = '__all__'


class ExpertDutySerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertDuty
        fields = '__all__'


class ExpertAgencySerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertAgency
        fields = '__all__'


class ExpertProjectTypeSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertProjectType
        fields = '__all__'


class ExpertFieldSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertField
        fields = '__all__'


class ExpertFieldTreeSerializers(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        fields = ExpertField.objects.filter(parent=obj.id)
        res = ExpertFieldTreeSerializers(instance=fields, many=True).data
        return res

    class Meta:
        model = ExpertField
        fields = '__all__'


class ExpertTitleSerializers(serializers.ModelSerializer):
    class Meta:
        model = ExpertTitle
        fields = '__all__'


class InnerExpertFieldSerializers(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField(read_only=True)

    def get_parent(self, obj):
        return InnerExpertFieldSerializers(instance=obj.parent, many=False).data

    class Meta:
        model = ExpertField
        fields = '__all__'


class SubjectSerializers(serializers.ModelSerializer):
    projectInfo = serializers.SerializerMethodField(read_only=True)

    def get_projectInfo(self, obj):
        try:
            return {"annualPlan": obj.project.category.batch.annualPlan,
                    "planCategory": obj.project.category.planCategory,
                    "projectName": obj.project.projectName}
        except Exception as e:
            return None

    class Meta:
        model = Subject
        fields = (
            'id', 'subjectName', 'unitName', 'head', 'phone', 'mobile', 'email', 'startStopYear', 'declareTime',
            'subjectState', 'state', 'projectInfo')


class ExpertSerializers(serializers.ModelSerializer):
    title = ExpertTitleSerializers(many=False)
    field = InnerExpertFieldSerializers(many=True)
    participate = ExpertProjectTypeSerializers(many=True)
    exits = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    record = serializers.SerializerMethodField()
    date = serializers.DateField(format="%Y-%m-%d")

    def get_exits(self, obj):
        es = ExpertRecordExit.objects.filter(expert=obj)
        exits = ExpertRecordExitSerializers(instance=es, many=True).data
        return exits

    def get_subjects(self, obj):
        h1 = SubjectExpertsOpinionSheet.objects.filter(pExperts=User.objects.filter(expert=obj).first(),
                                                       state='待评审',
                                                       subject__project__category__batch__state='同意')
        h2 = SubjectKExperts.objects.filter(
            subject__subjectState='验收审核', expert=obj)
        h3 = SubjectKExperts.objects.filter(
            subject__subjectState='终止审核', expert=obj)
        if h1 or h2 or h3:
            return True
        return False

    def get_record(self, obj):
        ss = ExpertRecordEdit.objects.filter(expert=obj).order_by('-id')
        return ExpertRecordEditSerializers(instance=ss, many=True).data

    class Meta:
        model = Expert
        fields = ['id', 'name', 'id_card_no', 'mobile', 'email', 'education', 'degree', 'title_no', 'company', 'duty',
                  'academician', 'supervisor', 'overseas',
                  'laboratory', 'tags', 'bank', 'bank_branch', 'bank_account', 'state', 'created', 'updated', 'title',
                  'participate', 'field', 'exits', 'reason', 'subjects', 'record', 'date']


class ExpertsSerializers(serializers.ModelSerializer):
    user = serializers.SerializerMethodField(read_only=True)
    field = InnerExpertFieldSerializers(many=True)


    class Meta:
        model = Expert
        fields = '__all__'

    def get_user(self, obj):
        try:
            return obj.user_set.values("id")
        except Exception as e:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.title:
            data.update(gender=GetInformation(instance.id_card_no).get_sex(), title=instance.title.name,
                        education=instance.get_education_display())
            return data
        else:
            data.update(gender=GetInformation(instance.id_card_no).get_sex(), title=None,
                        education=instance.get_education_display())
            return data
