from rest_framework import serializers
from .models import Equipamento, Movimentacao, OrdemServico


class EquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = '__all__'


class MovimentacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        fields = '__all__'
        read_only_fields = ('data_movimentacao',)


class OrdemServicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemServico
        fields = '__all__'
        read_only_fields = ('data_abertura', 'data_atualizacao')