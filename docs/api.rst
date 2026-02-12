Api
===

Este módulo implementa una ``API REST`` utilizando ``Django REST Framework`` (``DRF``) para gestionar datos relacionados con perforaciones,
vehículos y reportes operacionales dentro de un sistema de gestión de perforaciones mineras.


Funciones principales de la ``API``:
- Consultar datos de perforaciones, vehículos y reportes operacionales.
- Registrar reportes operacionales, incluyendo perforaciones, controles horarios, insumos y observaciones.
- Gestionar checklists de materiales usados en perforaciones.


Importaciones Principales
-------------------------

Este módulo utiliza ``Django REST Framework`` para manejar las vistas de la ``API`` y la interacción con la base de datos.

-  Librerías principales:
    -  ``Django REST Framework`` (``DRF``): 
        - ``APIView``, ``Response``, ``generics``, ``status`` → Manejo de vistas y respuestas ``HTTP``.
        - ``decorators`` → Uso de decoradores para definir vistas.
- Modelos de base de datos:
    - ``core.models`` → Perforaciones (Perforistas, Sondas, Sondajes, etc.).
    - ``user.models`` → Usuarios y autenticación (User).
    - ``drilling.models`` → Reportes operacionales (ReportesOperacionales, DetallesPerforaciones, etc.).
    - ``vehicle.models`` → Gestión de vehículos (Vehiculo, InformacionTecnicaVehiculo, etc.).
    - ``mining.models`` → Asignaciones de vehículos a faenas (VehiculoAsignado).
    - ``checklist.models`` → Checklists de materiales (ChecklistMaterialesSonda, ChecklistMaterialesCaseta).
    - ``Serializadores`` (``.serializers``) → Transforman modelos en JSON y viceversa.
- Transacciones y validaciones:
    - ``transaction.atomic()`` → Garantiza la consistencia en operaciones de base de datos.
    - ``ValidationError`` → Manejo de errores personalizados en validaciones.
- Consultas avanzadas:
    - ``Q`` → Construcción de consultas dinámicas.
- Manejo de fechas:
    - ``timezone``, ``datetime`` → Facilitan la gestión de fechas y horas en los reportes.

Clases y Métodos
----------------

Este módulo define varias vistas basadas en clases (``APIView``) para manejar operaciones ``CRUD`` en la ``API``.

1. DataPerforacionesListView (``APIView``)
    - **Propósito**: Recupera datos activos de perforaciones, perforistas, sondas y reportes operacionales.
    - **Método**: ``GET``
    - **Salida**: ``JSON`` con perforaciones activas.

2. VehiculosListView (``APIView``)
    - **Propósito**: Obtiene la lista de vehículos registrados.
    - **Método**: ``GET``
    - **Salida**: ``JSON`` con vehículos.

3. VehiculosKilometrajesListView (``APIView``)
    - **Propósito**: Consulta los registros de kilometraje de vehículos.
    - **Método**: ``GET``
    - **Salida**: ``JSON`` con kilometrajes de vehículos.

4. VehiculosFaenasListView (``APIView``)
    - **Propósito**: Obtiene asignaciones de vehículos a faenas.
    - **Método**: ``GET``
    - **Salida**: ``JSON`` con asignaciones.

5. SaveReporteOperacionalAPI (``APIView``)
    - **Propósito**: Guarda reportes operacionales y sus detalles asociados.
    - **Método**: ``POST``
    - **Entrada**: ``JSON`` con datos del reporte.
    - **Tipos de datos procesados**:
        - **reporte** → Crea un nuevo ReportesOperacionales.
        - **perforacion** → Registra detalles en DetallesPerforaciones.
        - **controlHorario** → Guarda registros en ControlesHorarios.
        - **longitud** → Almacena información de pozos (LongitudPozos).
        - **insumos** → Registra insumos usados (Insumos).
        - **aditivo** → Guarda aditivos (DetalleAditivos).
        - **observacion** → Almacena observaciones (ObservacionesReportes).
    - Se usa ``transaction.atomic()`` para garantizar la consistencia de los datos.

6. SaveReporteMaterialesSonda (``APIView``)
    - **Propósito**: Maneja checklists de materiales usados en perforaciones.
    - **Método**: POST
    - **Entrada**: JSON con detalles del checklist.
    - **Tipos de datos procesados**:
        - **checklistEntrada** → Registra materiales al inicio de la operación.
        - **checklistSalida** → Registra materiales al final de la operación.
    - Utiliza transacciones para mantener la integridad de los datos.

