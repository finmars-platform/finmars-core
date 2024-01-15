from django.conf import settings


APPS = {
    "poms.history",
    "poms.system",
    "poms.users",
    "poms.iam",
    "poms.notifications",
    "poms.obj_attrs",
    "poms.ui",
    "poms.accounts",
    "poms.counterparties",
    "poms.currencies",
    "poms.instruments",
    "poms.portfolios",
    "poms.strategies",
    "poms.transactions",
    "poms.integrations",
    "poms.reports",
    "poms.csv_import",
    "poms.transaction_import",
    "poms.complex_import",
    "poms.reference_tables",
    "poms.celery_tasks",
    "poms.reconciliation",
    "poms.file_reports",
    "poms.pricing",
    "poms.schedules",
    "poms.procedures",
    "poms.credentials",
    "poms.vault",
    "poms.system_messages",
    "poms.configuration",
    "poms.auth_tokens",
    "poms.widgets",
}


class DbRouter:
    route_app_labels = APPS

    @staticmethod
    def db_for_read(model, **hints):
        """
        Which db to use for reading
        """

        instance = hints.get("instance")  # to handle objects stuck to db
        if instance is not None and instance._state.db:
            return instance._state.db

        return settings.DB_REPLICA if settings.USE_DB_REPLICA else settings.DB_DEFAULT

    @staticmethod
    def db_for_write(model, **hints):
        """
        Which db to use for writing
        """
        return settings.DB_DEFAULT

    @staticmethod
    def allow_relation(obj_1, obj_2, **hints):
        """
        Allow relations between objects in replica & master
        """
        return True

    @staticmethod
    def allow_migrate(db, app_label, model_name=None, **hints):
        """
        Migrations are allowed only in master/default db
        """
        return db == settings.DB_DEFAULT
