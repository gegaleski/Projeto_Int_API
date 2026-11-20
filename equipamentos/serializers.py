
from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from rest_framework import serializers

from .models import (
    Equipamento,
    Movimentacao,
    OrdemServico,
    PerfilUsuario,
)


User = get_user_model()


def recalcular_status_equipamento(equipamento):
    ultima_movimentacao_manutencao = (
        Movimentacao.objects
        .filter(
            equipamento=equipamento,
            tipo__in=[
                'ENVIO_MANUTENCAO',
                'RETORNO_MANUTENCAO',
            ],
        )
        .order_by('-data_movimentacao', '-id')
        .first()
    )

    if (
        ultima_movimentacao_manutencao
        and ultima_movimentacao_manutencao.tipo == 'ENVIO_MANUTENCAO'
    ):
        novo_status = 'EM_MANUTENCAO'

    elif OrdemServico.objects.filter(
        equipamento=equipamento,
        status='EM_ANDAMENTO',
    ).exists():
        novo_status = 'EM_USO'

    else:
        novo_status = 'DISPONIVEL'

    if equipamento.status != novo_status:
        equipamento.status = novo_status
        equipamento.save(
            update_fields=['status', 'data_atualizacao']
        )


class EquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = '__all__'


class EquipamentoResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = ('codigo_patrimonial', 'nome')


class MovimentacaoSerializer(serializers.ModelSerializer):
    novo_status = serializers.ChoiceField(
        choices=Equipamento.STATUS_CHOICES,
        write_only=True,
        required=False,
    )

    class Meta:
        model = Movimentacao
        fields = '__all__'
        read_only_fields = ('data_movimentacao',)

    def validate(self, attrs):
        tipo = attrs.get('tipo')

        if tipo == 'TRANSFERENCIA' and not attrs.get('novo_status'):
            raise serializers.ValidationError({
                'novo_status': (
                    'Selecione o novo status do equipamento '
                    'para registrar uma transferência.'
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        novo_status = validated_data.pop('novo_status', None)

        equipamento_id = validated_data['equipamento'].id

        equipamento = Equipamento.objects.select_for_update().get(
            id=equipamento_id
        )

        validated_data['equipamento'] = equipamento

        movimentacao = Movimentacao.objects.create(**validated_data)

        if movimentacao.tipo == 'TRANSFERENCIA':
            equipamento.status = novo_status
            equipamento.save(
                update_fields=['status', 'data_atualizacao']
            )
        else:
            recalcular_status_equipamento(equipamento)

        return movimentacao


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

    def validate(self, attrs):
        if self.instance and self.instance.status in [
            'CONCLUIDA',
            'CANCELADA',
        ]:
            raise serializers.ValidationError(
                'Esta ordem de serviço já foi finalizada e não pode '
                'mais ser alterada.'
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        equipamento_id = validated_data['equipamento'].id

        equipamento = Equipamento.objects.select_for_update().get(
            id=equipamento_id
        )

        validated_data['equipamento'] = equipamento

        ordem = OrdemServico.objects.create(**validated_data)

        recalcular_status_equipamento(equipamento)

        return ordem

    @transaction.atomic
    def update(self, instance, validated_data):
        if instance.status in ['CONCLUIDA', 'CANCELADA']:
            raise serializers.ValidationError(
                'Esta ordem de serviço já foi finalizada e não pode '
                'mais ser alterada.'
            )

        equipamento_anterior = instance.equipamento

        equipamento_id = validated_data.get(
            'equipamento',
            equipamento_anterior,
        ).id

        equipamento_novo = Equipamento.objects.select_for_update().get(
            id=equipamento_id
        )

        instance = OrdemServico.objects.select_for_update().get(
            id=instance.id
        )

        if instance.status in ['CONCLUIDA', 'CANCELADA']:
            raise serializers.ValidationError(
                'Esta ordem de serviço já foi finalizada e não pode '
                'mais ser alterada.'
            )

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        instance.save()

        recalcular_status_equipamento(equipamento_novo)

        if equipamento_anterior.id != equipamento_novo.id:
            recalcular_status_equipamento(equipamento_anterior)

        return instance


class CadastroUsuarioSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    senha = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False
    )

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'Já existe uma conta cadastrada com este e-mail.'
            )

        if User.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError(
                'Este e-mail já está sendo utilizado.'
            )

        return email

    def validate_senha(self, value):
        password_validation.validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        nome = validated_data['nome'].strip()
        email = validated_data['email']
        senha = validated_data['senha']

        usuario = User.objects.create_user(
            username=email,
            email=email,
            first_name=nome,
            password=senha,
            is_active=False,
        )

        PerfilUsuario.objects.create(
            usuario=usuario,
            role='VISUALIZADOR',
            status_aprovacao='PENDENTE',
        )

        return usuario


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(
        source='get_role_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_aprovacao_display',
        read_only=True
    )
    aprovado_por_nome = serializers.CharField(
        source='aprovado_por.first_name',
        read_only=True,
        default=None
    )

    class Meta:
        model = PerfilUsuario
        fields = (
            'role',
            'role_display',
            'status_aprovacao',
            'status_display',
            'aprovado_por_nome',
            'data_aprovacao',
            'data_criacao',
        )


class UsuarioAdminSerializer(serializers.ModelSerializer):
    perfil = PerfilUsuarioSerializer(read_only=True)
    nome = serializers.CharField(
        source='first_name',
        read_only=True
    )

    class Meta:
        model = User
        fields = (
            'id',
            'nome',
            'username',
            'email',
            'is_active',
            'date_joined',
            'perfil',
        )
        read_only_fields = fields
