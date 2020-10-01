# Getting started (Local) 

**Works for python 3.5.0**

* Install NPM
* Install Python 3
* Install Docker and Docker Compose

* Create Virtual Environment (VENV)

`python3 -m venv venv`
* Activate VENV

`source venv/bin/activate`

* Install Dependencies

`pip install -r requirements.txt`

* Install Celery

`pip install celery`

* Start Postgres Database and Redis in docker

`docker-compose -f docker-compose-dev.yml up`

* Run Migrations

`./local-develoment/run_migrate.sh`

* Start Celery Server

`./local-develoment/run_celery.sh`

* Start Django Server

`./local-develoment/run_server.sh`

Success!


How to compile django app

1) Activate venv

    `source venv/bin/activate`

2) Install PyInstaller==3.4

    `pip install pyinstaller==3.4.`
    
3) Execute following command to build

   `REDIS_HOST=localhost DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 python3 -m PyInstaller backend.spec -y --debug --log-level TRACE`
    
4) Execute following command to runserver

   `REDIS_HOST=localhost DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 dist/backend/backend manage.py runserver 8080`
   

## Backend Settings

We can setup backend in several ways passing ENV VARIABLE `BACKEND_ROLES`:
Possible values of `BACKEND_ROLES`:

* `ALL` - Default role, if nothing is passed. Backend instance do all services.
* `SIMPLE` - Simple backend instance - Auth / CRUD for all entities / Configuration Export/Import
* `REPORTER` - All Reports 
* `FILE_IMPORTER` - Simple Entity Import / Complex Transaction  File imports
* `DATA_PROVIDER` - Providers (Bloomberg) interaction 

You can pass several roles to Backend instance. 
Example : `REPORTER, FILE_IMPORTER, DATA_PROVIDER`

P.S. You also need to specify your nginx config to route correctly. 


`docker-compose.yml` - Сейчас нигде не используется

`docker-compose-dev.yml` - Используется для локальной разработки

`Dokerfile` - тот файл который использует Jenkins для сборки итогового билда

`docker` - набор скриптов которые использует Dokerfile для итогового image


Что можно сделать
1) Сделать сборки локальной версии и той что на серверах максимально похожими (Сейчас очень сильно олтичаются Celery)


















Usefull code: Replace to_representation in rest_framework/serializers.py with code below, and you will get time explanation of each field serializaton

```
def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = self._readable_fields

        st = time.perf_counter()

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue

            field_st = time.perf_counter()

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

            if 'item_' in field.field_name:
                if hasattr(instance, 'is_report'):
                    print('Field %s ' % field.field_name)
                    print('Field to representation done %s' % (time.perf_counter() - field_st))

        if hasattr(instance, 'is_report'):
            print('Report to representation done %s' % (time.perf_counter() - st))

        return ret

```

### IDEA settings

#### SQL proper formatting in python string

Settings -> Tools -> Database -> User Parameters -> Enable in string literals with SQL injection  
`\{(\w+)\}` for Python
