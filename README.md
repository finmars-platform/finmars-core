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

   `REDIS_HOST=localhost RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 python3 -m PyInstaller backend.spec -y --debug --log-level TRACE`
    
4) Execute following command to runserver

   `REDIS_HOST=localhost RDS_DB_NAME=finmars_dev RDS_USERNAME=postgres RDS_PASSWORD=postgres RDS_HOSTNAME=localhost RDS_PORT=5434 dist/backend/backend manage.py runserver 8080`
   
   
Spec file (backend.spec)

```

# -*- mode: python -*-

block_cipher = None

import sys
sys.setrecursionlimit(100000)

a = Analysis(['backend/manage.py'],
             pathex=['/home/szhitenev/projects/cython-tests/test2'],
             binaries=[],
             datas=[],
             hiddenimports=['logstash', 'modeltranslation', 'modeltranslation.apps', 'poms.users.apps'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='backend',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='backend')



```
    