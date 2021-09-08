from rest_framework import serializers
from tpl.models import Template


class TemplateSerializers(serializers.ModelSerializer):
    date = serializers.DateTimeField(format="%Y-%m-%d %H:%M", required=False, read_only=True)

    class Meta:
        model = Template
        fields = '__all__'
