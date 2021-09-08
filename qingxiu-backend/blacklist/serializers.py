from rest_framework import serializers

from blacklist.models import UnitBlacklist, ProjectLeader, ExpertsBlacklist, AgenciesBlacklist


# 单位黑名单
class UnitBlacklistSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    class Meta:
        model = UnitBlacklist
        fields = '__all__'


# 项目负责人黑名单
class ProjectLeaderSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    class Meta:
        model = ProjectLeader
        fields = '__all__'


# 专家黑名单黑名单
class ExpertsBlacklistSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    class Meta:
        model = ExpertsBlacklist
        fields = '__all__'


# 机构黑名单
class AgenciesBlacklistSerializers(serializers.ModelSerializer):
    created = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)
    updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", required=False, read_only=True)

    class Meta:
        model = AgenciesBlacklist
        fields = '__all__'
