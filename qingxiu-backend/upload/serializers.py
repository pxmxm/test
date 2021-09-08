


# 课题
from rest_framework import serializers

from upload.models import Templates, LoginLog


class TemplatesSerializers(serializers.ModelSerializer):

    class Meta:
        model = Templates
        fields = '__all__'


class LoginLogSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = LoginLog
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user.type == '评估机构':
            data.update(user={"id": instance.user.id, "username": instance.user.agency.creditCode, "type": instance.user.type})
            return data
        else:
            data.update(user={"id": instance.user.id, "username": instance.user.username, "type": instance.user.type})
            return data