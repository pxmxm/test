from rest_framework import serializers

from research.models import FieldResearch, Proposal


class FieldResearchSerializers(serializers.ModelSerializer):
    times = serializers.DateField(format="%Y-%m-%d")

    class Meta:
        model = FieldResearch
        fields = ('id', 'planCategory', 'unitName', 'subjectName', 'times', 'place', 'personnel', 'opinion')


class ProposalSerializers(serializers.ModelSerializer):
    class Meta:
        model = Proposal

        fields = ('id', 'scienceFunding', 'scienceProposal', 'firstFunding')
