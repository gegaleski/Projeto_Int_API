from rest_framework.routers import DefaultRouter
from .views import (
    EquipamentoViewSet,
    MovimentacaoViewSet,
    OrdemServicoViewSet,
)

router = DefaultRouter()

router.register(
    'equipamentos',
    EquipamentoViewSet,
    basename='equipamento'
)
router.register(
    'movimentacoes',
    MovimentacaoViewSet,
    basename='movimentacao'
)
router.register(
    'ordens-servico',
    OrdemServicoViewSet,
    basename='ordem-servico'
)

urlpatterns = router.urls