
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CadastroUsuarioView,
    EquipamentoViewSet,
    MovimentacaoViewSet,
    OrdemServicoViewSet,
    UsuarioAdminViewSet,
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

router.register(
    'usuarios',
    UsuarioAdminViewSet,
    basename='usuario'
)


urlpatterns = [
    path('cadastro/', CadastroUsuarioView.as_view(), name='cadastro'),
    path('', include(router.urls)),
]
