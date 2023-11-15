# Getting started (Local) 

**Works for python 3.9.0**

* Install NPM
* Install Python 3.9
* Install Docker and Docker Compose

* Install ubuntu applications

`apt-get update && apt-get install -y apt-utils && apt-get upgrade -y && apt-get install -y wget htop curl build-essential openssl libssl-dev python3.9-dev python3-pip python3.9-venv python3-setuptools python3-wheel libpq-dev libgdal-dev libgeos-dev libproj-dev libtiff5-dev libjpeg-turbo8-dev libzip-dev zlib1g-dev libffi-dev git libgeoip-dev geoip-bin geoip-database supervisor`

* Create Virtual Environment (VENV)

`python3.9 -m venv venv`

* Activate VENV

`source venv/bin/activate`

* Install Dependencies

`pip install "setuptools<58.0.0"
pip install -U pip wheel uwsgitop
pip install -U pip boto3
pip install -U pip azure-storage-blob
pip install -r requirements.txt
pip install -U pip flower
pip install -U pip uwsgi`

* Create file for logs

`mkdir -p /var/log/finmars`
`chmod 777 /var/log/finmars/`
`touch /var/log/finmars/django.log`
`chmod 777 /var/log/finmars/django.log`

* Install Celery

`pip install celery`

* Start Postgres Database and Redis in docker

`docker-compose -f docker-compose-dev.yml up`

* Run Migrations

`./local-development/run_migrate.sh`

* Start Celery Server

`./local-development/run_celery.sh`

* Start Django Server

`./local-development/run_server.sh`

Success!


How to run django app

1) Activate venv

    `source venv/bin/activate`

2) Install PyInstaller==3.4

    `pip install pyinstaller==3.4.`
    
3) Execute following command to build

   `REDIS_HOST=localhost DB_NAME=finmars_dev DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost DB_PORT=5434 python3 -m PyInstaller backend.spec -y --debug --log-level TRACE`

4) Execute following script to runserver

   `./local-development/run_server.sh`
   
Profile uWSGI server 
1) Activate venv  
`source /var/app-venv/bin/activate`
2) Run Profiler  
`uwsgitop /tmp/stats.socket`


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


- Token Refrsh



CELERY


Celery worker 
    Сам не процессить, генерит процессы, поэтому вроде как финмарсу нету смысла иметь больше 1 воркера на проект


Apple Silicon

export LIBRARY_PATH=$LIBRARY_PATH:/opt/homebrew/opt/openssl/lib
pip install -r requirements.txt

Reset sequence

python manage.py sqlsequencereset app_label | python manage.py dbshell
e.g.
python manage.py sqlsequencereset portfolios | python manage.py dbshell



# Install all required libs
pip install django
pip install celery
pip install colorlog
pip install django-modeltranslation
pip install django-filter # django-filter==2.4.0, latest version is not work
pip install django-mptt
pip install django-crispy-forms
pip install djangorestframework
pip install django-rest-swagger
pip install django-cors-headers
pip install django-celery-results
pip install django-celery-beat
pip install django-debug-toolbar
pip install psycopg2
pip install psycopg2-binary # for db connection
pip install pandas # possibly can be removed
pip install geoip2 # possibly can be removed
pip install babel # possibly can be removed
pip install croniter # used in formulas
pip install django-storages # storages
pip install django-storages-azure # storages
pip install azure-storage-blob # storages
pip install boto3 # storages 
pip install paramiko # storages
pip install scipy # possibly can be removed
pip install websockets
pip install filtration # used in import schemes
pip install openpyxl # used in imports (load .xlsx files)
pip install pycryptodome # used in decrypt files from external provider
pip install python-jose # for jwt, possibly deprecated
pip install psutil # for healthcheck
pip install pyotp # possibly can be removed
pip install uwsgi
pip install django-cprofile-middleware
pip install flower
pip install deepdiff
pip install pyopenssl
pip install suds
pip install drf_yasg

==== TODO ====
Move generated documentation to another project

How to generate documentation
```
if [ "${ENABLE_DEV_DOCUMENTATION}" == "True" ]; then
echo "Generating dev documentation"
cd /var/app/docs/source && sphinx-apidoc -o ./files ../../ ../../*migrations* ../../*tests* ../../*admin* ../../*apps* --separate --module-first
echo "Documentation generated. Going to create html"
cd /var/app/docs && make html
echo "HTML Documentation generated"
else
echo "Dev documentation skip"
fi
```

# Postgresql Magic

## Reset sequence

python manage.py sqlsequencereset transactions

## Find duplicates

from django.db.models import Count
from poms.transactions.models import ComplexTransaction
ComplexTransaction.objects.values("id").annotate(did=Count("id")).filter(did__gt=1)


from django.db.models import Count
from poms.transactions.models import Transaction
Transaction.objects.values("id").annotate(did=Count("id")).filter(did__gt=1)

## Show Duplicates

(SELECT ctid
FROM
(SELECT id, ctid,
ROW_NUMBER() OVER( PARTITION BY id
ORDER BY  id ) AS row_num
FROM transactions_complextransaction ) t
WHERE t.row_num > 1 );

## Delete duplicated ids

DELETE FROM transactions_complextransaction
WHERE ctid IN
(SELECT ctid
FROM
(SELECT id, ctid,
ROW_NUMBER() OVER( PARTITION BY id
ORDER BY  id ) AS row_num
FROM transactions_complextransaction ) t
WHERE t.row_num > 1 );

DELETE FROM transactions_transaction
WHERE ctid IN
(SELECT ctid
FROM
(SELECT id, ctid,
ROW_NUMBER() OVER( PARTITION BY id
ORDER BY  id ) AS row_num
FROM transactions_transaction ) t
WHERE t.row_num > 1 );



# Access policy

frn:[service]:[content_type]:[user_code]
frn:finmars:portfolios.portfolio:portfolio_1

# Celery articles
https://engineering.backmarket.com/a-story-of-kubernetes-celery-resource-and-a-rabbit-ec2ef9e37e9f
https://ayushshanker.com/posts/celery-in-production-bugfixes/



### Guideline

Не используются тернарные операторы (e.g. foo ? bar : buz)
Не используется синтаксический сахар вида `i++ (а не i = i + 1)`
использование camelCase а не camel_case в названии переменных и методов (классы обязательно называть CamelCaseModel и тд)
мне не нравится сложный код, я бы сократил возможно использование лямда функций
мне нравится декларация функций внутри функции, такое просто надо сносить в utils.py какой нибудь
Если пишет про джангу то, стараться к моделям сразу делать и админку, также прописывать все сериализаторы, чтобы в веб интерфейсе можно было запустить точку апи
При объявлении полей модели писать help_text
На текущий момент все @finmars_task как входной параметр должны принимать task_id (от CeleryTask)
В таска nice to have прописывать progress этого таска



Еще мне очень нравится пример:
```
router.register(
r"csv",
csv_import.CsvDataImportViewSet,
"import_csv",
)
```

```
router.register(r"csv", csv_import.CsvDataImportViewSet, "import_csv")
```
то есть я что имею ввиду, если идет много однотипных деклараций, то лучше их без word-wrap писать
Если функция принимает на вход хотябы 5 параметров, тогда я могу понять перенос по параметрам
но если мы переносим по параметрам, я бы делал вид

```
router.register(
prefix=r"csv",
viewset=csv_import.CsvDataImportViewSet,
basename="import_csv",
)
```