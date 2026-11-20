
from django.contrib.auth import get_user_model

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import PerfilUsuario


User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        try:
            perfil = user.perfil
            token['role'] = perfil.role
            token['status_aprovacao'] = perfil.status_aprovacao
        except PerfilUsuario.DoesNotExist:
            token['role'] = None
            token['status_aprovacao'] = None

        token['nome'] = user.first_name
        token['email'] = user.email

        return token

    def validate(self, attrs):
        email = attrs.get('username', '').strip()
        senha = attrs.get('password', '')

        usuarios = User.objects.filter(email__iexact=email)

        if usuarios.count() != 1:
            raise AuthenticationFailed(
                'E-mail ou senha incorretos.'
            )

        usuario = usuarios.first()

        if not usuario.check_password(senha):
            raise AuthenticationFailed(
                'E-mail ou senha incorretos.'
            )

        try:
            perfil = usuario.perfil
        except PerfilUsuario.DoesNotExist:
            raise AuthenticationFailed(
                'Seu perfil ainda não foi configurado. '
                'Entre em contato com o administrador.'
            )

        if perfil.status_aprovacao == 'PENDENTE':
            raise AuthenticationFailed(
                'Seu cadastro foi realizado com sucesso, '
                'mas ainda aguarda a aprovação do administrador.'
            )

        if perfil.status_aprovacao == 'REJEITADO':
            raise AuthenticationFailed(
                'Seu cadastro não foi aprovado. '
                'Entre em contato com o administrador.'
            )

        if not usuario.is_active:
            raise AuthenticationFailed(
                'Sua conta está desativada. '
                'Entre em contato com o administrador.'
            )

        attrs['username'] = usuario.get_username()

        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
