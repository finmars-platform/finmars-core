from django.db import models


class HealthcheckTestModel(models.Model):
    name = models.CharField(max_length=128)
