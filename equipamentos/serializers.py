from rest_framework import serializers
from .models import Equipamento, Movimentacao, OrdemServico


class EquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = '__all__'


class EquipamentoResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = ('codigo_patrimonial', 'nome')


class MovimentacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        fields = '__all__'
        read_only_fields = ('data_movimentacao',)


class OrdemServicoSerializer(serializers.ModelSerializer):
    equipamento_detalhes = EquipamentoResumoSerializer(
        source='equipamento',
        read_only=True,
    )

    class Meta:
        model = OrdemServico
        fields = '__all__'
        read_only_fields = (
            'data_abertura',
            'data_atualizacao',
        )