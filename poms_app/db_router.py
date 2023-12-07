from django.conf import settings


class DbRouter:
    route_app_labels = settings.INSTALLED_APPS

    def db_for_read(self, model, **hints):
        """
        Which db to use for readingR
        """
        return settings.DB_DEFAULT

    def db_for_write(self, model, **hints):
        """
        Which db to use for writing
        """
        return settings.DB_DEFAULT

    def allow_relation(self, obj_1, obj_2, **hints):
        """
        Allow relations between objects in replica & master
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Migrations are allowed only in master/default db
        """
        return db == settings.DB_DEFAULT
