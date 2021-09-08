from rest_framework import serializers

from sms.models import TextTemplate, MessageRecord, TemporaryTemplate


class TextTemplateSerializers(serializers.ModelSerializer):

    class Meta:
        model = TextTemplate
        fields = '__all__'


class MessageRecordSerializers(serializers.ModelSerializer):
    sendTime = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)



    class Meta:
        model = MessageRecord
        fields = '__all__'




class TemporaryTemplateSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    class Meta:
        model = TemporaryTemplate
        fields = '__all__'
