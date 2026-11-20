
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Equipamento,
    Movimentacao,
    OrdemServico,
    PerfilUsuario,
)
from .serializers import (
    EquipamentoSerializer,
    MovimentacaoSerializer,
    OrdemServicoSerializer,
    CadastroUsuarioSerializer,
    UsuarioAdminSerializer,
    recalcular_status_equipamento,
)


User = get_user_model()


class IsMasterAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        try:
            perfil = request.user.perfil
        except PerfilUsuario.DoesNotExist:
            return False

        return (
            request.user.is_active
            and perfil.status_aprovacao == 'APROVADO'
            and perfil.role == 'MASTER_ADMIN'
        )


class CadastroUsuarioView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CadastroUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'detail': (
                    'Cadastro realizado com sucesso! '
                    'Aguarde a liberação do administrador.'
                )
            },
            status=status.HTTP_201_CREATED
        )


class EquipamentoViewSet(viewsets.ModelViewSet):
    queryset = Equipamento.objects.all().order_by(
        'codigo_patrimonial'
    )
    serializer_class = EquipamentoSerializer

    def destroy(self, request, *args, **kwargs):
        equipamento = self.get_object()

        try:
            self.perform_destroy(equipamento)

            return Response(
                {'detail': 'Equipamento excluído com sucesso.'},
                status=status.HTTP_200_OK
            )

        except ProtectedError:
            return Response(
                {
                    'detail': (
                        'Não é possível excluir este equipamento, '
                        'pois existem movimentações ou ordens de serviço '
                        'vinculadas a ele.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class MovimentacaoViewSet(viewsets.ModelViewSet):
    queryset = Movimentacao.objects.select_related(
        'equipamento'
    ).all().order_by('-data_movimentacao')

    serializer_class = MovimentacaoSerializer


class OrdemServicoViewSet(viewsets.ModelViewSet):
    queryset = OrdemServico.objects.select_related(
        'equipamento'
    ).all().order_by('-data_abertura')

    serializer_class = OrdemServicoSerializer

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        ordem = self.get_object()

        if ordem.status in ['CONCLUIDA', 'CANCELADA']:
            raise ValidationError(
                'Ordens concluídas ou canceladas não podem ser excluídas.'
            )

        equipamento = ordem.equipamento

        response = super().destroy(request, *args, **kwargs)

        recalcular_status_equipamento(equipamento)

        return response


class UsuarioAdminViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.select_related('perfil').all().order_by(
        '-date_joined'
    )
    serializer_class = UsuarioAdminSerializer
    permission_classes = [IsMasterAdmin]

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def aprovar(self, request, pk=None):
        usuario = self.get_object()

        if usuario.is_superuser:
            raise ValidationError(
                'Não é possível alterar este usuário por esta operação.'
            )

        try:
            perfil = usuario.perfil
        except PerfilUsuario.DoesNotExist:
            perfil = PerfilUsuario.objects.create(
                usuario=usuario,
                role='VISUALIZADOR',
                status_aprovacao='PENDENTE'
            )

        if perfil.status_aprovacao == 'APROVADO':
            raise ValidationError('Este cadastro já foi aprovado.')

        role = request.data.get('role', 'VISUALIZADOR')

        roles_validas = dict(PerfilUsuario.ROLE_CHOICES)

        if role not in roles_validas:
            raise ValidationError({'role': 'Role inválida.'})

        perfil.role = role
        perfil.status_aprovacao = 'APROVADO'
        perfil.aprovado_por = request.user
        perfil.data_aprovacao = timezone.now()
        perfil.save()

        usuario.is_active = True
        usuario.save(update_fields=['is_active'])

        return Response({
            'detail': 'Cadastro aprovado com sucesso.',
            'usuario': self.get_serializer(usuario).data
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def rejeitar(self, request, pk=None):
        usuario = self.get_object()

        if usuario.is_superuser or usuario.id == request.user.id:
            raise ValidationError(
                'Não é possível rejeitar este usuário.'
            )

        try:
            perfil = usuario.perfil
        except PerfilUsuario.DoesNotExist:
            perfil = PerfilUsuario.objects.create(
                usuario=usuario,
                role='VISUALIZADOR',
                status_aprovacao='PENDENTE'
            )

        if perfil.status_aprovacao == 'APROVADO':
            raise ValidationError(
                'Este usuário já foi aprovado. '
                'Utilize a opção de desativação.'
            )

        perfil.status_aprovacao = 'REJEITADO'
        perfil.aprovado_por = request.user
        perfil.data_aprovacao = timezone.now()
        perfil.save()

        usuario.is_active = False
        usuario.save(update_fields=['is_active'])

        return Response({'detail': 'Cadastro rejeitado.'})

    @action(detail=True, methods=['patch'])
    @transaction.atomic
    def alterar_role(self, request, pk=None):
        usuario = self.get_object()

        if usuario.id == request.user.id:
            raise ValidationError(
                'Você não pode alterar sua própria role.'
            )

        role = request.data.get('role')
        roles_validas = dict(PerfilUsuario.ROLE_CHOICES)

        if role not in roles_validas:
            raise ValidationError({'role': 'Role inválida.'})

        try:
            perfil = usuario.perfil
        except PerfilUsuario.DoesNotExist:
            raise ValidationError(
                'Este usuário ainda não possui um perfil.'
            )

        if perfil.status_aprovacao != 'APROVADO':
            raise ValidationError(
                'A role só pode ser alterada após a aprovação.'
            )

        perfil.role = role
        perfil.save(update_fields=['role'])

        return Response({
            'detail': 'Role atualizada com sucesso.',
            'usuario': self.get_serializer(usuario).data
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def desativar(self, request, pk=None):
        usuario = self.get_object()

        if usuario.id == request.user.id or usuario.is_superuser:
            raise ValidationError(
                'Não é possível desativar este usuário.'
            )

        usuario.is_active = False
        usuario.save(update_fields=['is_active'])

        return Response({'detail': 'Usuário desativado com sucesso.'})

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reativar(self, request, pk=None):
        usuario = self.get_object()

        if usuario.is_superuser:
            raise ValidationError(
                'Não é possível alterar este usuário por esta operação.'
            )

        try:
            perfil = usuario.perfil
        except PerfilUsuario.DoesNotExist:
            raise ValidationError(
                'Este usuário ainda não possui um perfil.'
            )

        if perfil.status_aprovacao != 'APROVADO':
            raise ValidationError(
                'Somente usuários aprovados podem ser reativados.'
            )

        usuario.is_active = True
        usuario.save(update_fields=['is_active'])

        return Response({'detail': 'Usuário reativado com sucesso.'})
