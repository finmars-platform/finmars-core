from django.contrib.contenttypes.models import ContentType
from django.db import models
from poms.users.models import MasterUser


class DataImportSchema(models.Model):
    '''
    это схема импорта
    '''
    model = models.ForeignKey(ContentType)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class DataImport(models.Model):

    '''
    модель импорта сущностей
    '''

    STATUS = (
        (0, 'READY'),
        (1, 'IN PROGRESS'),
        (2, 'DONE'),
        (3, 'FAIL'),
    )
    master_user = models.ForeignKey(MasterUser, blank=True, null=True)
    schema = models.ForeignKey(DataImportSchema)
    status = models.IntegerField(choices=STATUS, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    # def __str__(self):
    #     return self.model.model + '/' + datetime.strftime(self.modified_at, '%Y-%m-%d')


class DataImportSchemaFields(models.Model):
    '''
    здесь хранятся импортируемые колонки
    '''
    schema = models.ForeignKey(DataImportSchema)
    source = models.CharField(max_length=100)
    num = models.SmallIntegerField(default=0)

    def __str__(self):
        return self.source


class DataImportSchemaMatching(models.Model):
    '''
    модель для матчинга полей импорта и сущности
    '''
    schema = models.ForeignKey(DataImportSchema)
    model_field = models.CharField(max_length=100)
    expression = models.CharField(max_length=100)

    def __str__(self):
        return self.model_field
