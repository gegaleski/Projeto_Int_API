from django.db import models

# Create your models here.
from django.db import models


class Equipamento(models.Model):
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('EM_USO', 'Em uso'),
        ('EM_MANUTENCAO', 'Em manutenção'),
        ('INATIVO', 'Inativo'),
    ]

    codigo_patrimonial = models.CharField(
        max_length=50,
        unique=True
    )
    nome = models.CharField(max_length=150)
    numero_serie = models.CharField(
        max_length=100,
        blank=True
    )
    localizacao = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DISPONIVEL'
    )
    descricao = models.TextField(blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.codigo_patrimonial} - {self.nome}'


class Movimentacao(models.Model):
    TIPO_CHOICES = [
        ('TRANSFERENCIA', 'Transferência'),
        ('ENVIO_MANUTENCAO', 'Envio para manutenção'),
        ('RETORNO_MANUTENCAO', 'Retorno de manutenção'),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.PROTECT,
        related_name='movimentacoes'
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES
    )
    origem = models.CharField(max_length=150)
    destino = models.CharField(max_length=150)
    responsavel = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    data_movimentacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.equipamento.codigo_patrimonial} - {self.get_tipo_display()}'


class OrdemServico(models.Model):
    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]

    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('EM_ANDAMENTO', 'Em andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.PROTECT,
        related_name='ordens_servico'
    )
    titulo = models.CharField(max_length=150)
    descricao = models.TextField()
    prioridade = models.CharField(
        max_length=10,
        choices=PRIORIDADE_CHOICES,
        default='MEDIA'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ABERTA'
    )
    responsavel = models.CharField(
        max_length=150,
        blank=True
    )
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'OS #{self.pk} - {self.titulo}'