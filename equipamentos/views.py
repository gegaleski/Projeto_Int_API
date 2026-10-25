from rest_framework import viewsets
from .models import Equipamento, Movimentacao, OrdemServico
from .serializers import (
    EquipamentoSerializer,
    MovimentacaoSerializer,
    OrdemServicoSerializer,
)


class EquipamentoViewSet(viewsets.ModelViewSet):
    queryset = Equipamento.objects.all().order_by('codigo_patrimonial')
    serializer_class = EquipamentoSerializer


class MovimentacaoViewSet(viewsets.ModelViewSet):
    queryset = Movimentacao.objects.select_related('equipamento').all()
    serializer_class = MovimentacaoSerializer


class OrdemServicoViewSet(viewsets.ModelViewSet):
    queryset = OrdemServico.objects.select_related('equipamento').all()
    serializer_class = OrdemServicoSerializer