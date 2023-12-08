from django.conf import settings


class DbRouter:
    route_app_labels = settings.INSTALLED_APPS

    @staticmethod
    def db_for_read(model, **hints):
        """
        Which db to use for reading
        """
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
