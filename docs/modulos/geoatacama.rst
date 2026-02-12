##########
Geoatacama
##########

Descripción General
*******************

Este archivo contiene la configuración base del proyecto, incluyendo la base de datos, aplicaciones instaladas y middleware.

Configuración de Producción (production.py)
*******************************************

Este archivo gestiona las configuraciones específicas para el entorno de producción.

Configuración de Celery (celery.py)
***********************************

Celery se usa para manejar tareas en segundo plano, como procesamiento de datos o envío de correos electrónicos.

Configuración de ASGI (asgi.py)
*******************************

Este archivo permite la ejecución de Django con ASGI, útil para WebSockets y aplicaciones asincrónicas.

Configuración de WSGI (wsgi.py)
*******************************

Este archivo permite el despliegue en servidores WSGI, como Gunicorn o uWSGI.

Definición de Rutas Globales (urls.py)
**************************************

Este archivo define las rutas principales del proyecto Django.

isamax
======

Ruta para acceder al panel de administración de Django.

URL
---

- ``/isamax/``

Vista asociada
--------------

- ``admin.site.urls``

---

core.urls
=========

Ruta para incluir las URLs del módulo de ``core``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('core.urls')``

---

user.urls
=========

Ruta para incluir las URLs del módulo de ``user``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('user.urls')``

---

vehicle.urls
============

Ruta para incluir las URLs del módulo de ``vehicle``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('vehicle.urls')``

---

mining.urls
===========

Ruta para incluir las URLs del módulo de ``mining``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('mining.urls')``

---

maintenance.urls
================

Ruta para incluir las URLs del módulo de ``maintenance``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('maintenance.urls')``

---

machine.urls
============

Ruta para incluir las URLs del módulo de ``machine``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('machine.urls')``

---

documentation.urls
==================

Ruta para incluir las URLs del módulo de ``documentation``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('documentation.urls')``

---

messenger.urls
==============

Ruta para incluir las URLs del módulo de ``messenger``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('messenger.urls')``

---

planning.urls
=============

Ruta para incluir las URLs del módulo de ``planning``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('planning.urls')``

---

drilling.urls
=============

Ruta para incluir las URLs del módulo de ``drilling``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('drilling.urls')``

---

offline.urls
============

Ruta para incluir las URLs del módulo de ``offline``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('offline.urls')``

---

api.urls
========

Ruta para incluir las URLs del módulo de ``api``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('api.urls')``

---

checklist.urls
==============

Ruta para incluir las URLs del módulo de ``checklist``.

URL
---

- ``/``

Vista asociada
--------------

- ``include('checklist.urls')``

---

STATIC_URL
==========

Ruta para servir archivos estáticos.

URL
---

- ``/static/``

Vista asociada
--------------

- ``static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)``

---

MEDIA_URL
=========

Ruta para servir archivos multimedia.

URL
---

- ``/media/``

Vista asociada
--------------

- ``static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)``

---

DEBUG
=====

Si el entorno está en modo de depuración, se sirven archivos multimedia de manera específica.

URL
---

- ``/media/``

Vista asociada
--------------

- ``if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)``
