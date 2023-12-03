from django.conf import settings


class DbRouter:
    route_app_labels = [
        "reports",
        "transactions",
        "csv_import",
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

    def allow_relation(self, *args, **hints):
        """
        Relations between objects in replica & master are not allowed
        """

    def allow_migrate(self, db, *args, **hints):
        """
        Migrations are allowed only in master/default db
        """
        return db == settings.DB_DEFAULT
