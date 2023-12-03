from django.conf import settings


class DbRouter:
    route_app_labels = [
        "reports",
    ]

    def db_for_read(self, model, **hints):
        """
        Reads always from replica db
        """
        return settings.DB_REPLICA

    def db_for_write(self, model, **hints):
        """
        Write always into master/default db
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
