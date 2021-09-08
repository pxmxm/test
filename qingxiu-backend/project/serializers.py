import datetime

from rest_framework import serializers

from project.models import Category, Batch, Project


# 项目批次
class BatchSerializers(serializers.ModelSerializer):
    # created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    # updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    category = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Batch
        fields = (
            'id', 'annualPlan', 'projectBatch', 'declareTime', 'isActivation', 'category')

    def get_category(self, obj):
        try:
            return obj.batch_category.values('planCategory')
        except Exception as e:
            return None


# 项目类别
class CategorySerializers(serializers.ModelSerializer):
    batch = BatchSerializers(read_only=True)

    # created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    # updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    class Meta:
        model = Category
        fields = (
            'id', 'planCategory', 'batch')


# 项目名称
class ProjectSerializers(serializers.ModelSerializer):
    category = serializers.SerializerMethodField(read_only=True)

    # created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    # updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    class Meta:
        model = Project
        fields = ('id', 'projectName', 'category', 'charge')

    def get_category(self, obj):
        try:
            return {"annualPlan": obj.category.batch.annualPlan,
                    "projectBatch": obj.category.batch.projectBatch,
                    "planCategory": obj.category.planCategory,
                    "isActivation": obj.category.batch.isActivation,
                    }

        except Exception as e:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.update(charge=instance.charge.values('id', 'name'))
        return data
