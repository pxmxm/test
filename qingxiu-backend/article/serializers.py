from rest_framework import serializers

from article.models import Article

from rest_framework_mongoengine import serializers as mongodb_serializers


class ArticleSerializers(mongodb_serializers.DocumentSerializer):
    updated = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)
    subscribe = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'content', 'author', 'source', 'types', 'state', 'subscribe', 'updated')

    def create(self, validated_data):
        instance = super(ArticleSerializers, self).create(validated_data)
        return instance

    def update(self, instance, validated_data):
        instance = super(ArticleSerializers, self).update(instance, validated_data)
        return instance

