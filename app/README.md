# RouteIQ

RouteIQ es un optimizador universal de rutas de entrega para negocios como restaurantes, farmacias, florerías y tiendas. El proyecto combina un motor de optimización en Python con una API FastAPI que puede ejecutarse localmente o desplegarse en AWS Lambda con Mangum.

## ¿Qué hace?

- Calcula rutas eficientes para entregas usando un enfoque basado en:
  - Clarke-Wright Savings
  - 2-opt intra
  - 2-opt* inter
- Geocodifica direcciones usando enlaces de Google Maps o OpenStreetMap Nominatim.
- Considera tiempos de viaje con OSRM y un factor de tráfico configurable.
- Genera una salida estructurada para el frontend o para consumo de API.

## Estructura del proyecto

- `lambda_function.py`: expone la API FastAPI y el handler de AWS Lambda.
- `optimizer.py`: motor principal de optimización, carga de configuración, geocodificación y generación de rutas.
- `requirements.txt`: dependencias de Python.
- `configs/`: ejemplos de configuraciones por negocio.

## Dependencias

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

## Ejecutar el optimizador por línea de comandos

Puedes ejecutar el motor con una configuración de ejemplo:

```bash
python optimizer.py --config configs/config_restaurante.json
```

También puedes usar otras configuraciones:

```bash
python optimizer.py --config configs/config_farmacia.json
python optimizer.py --config configs/config_floreria.json
```

## Ejecutar la API localmente

El proyecto expone una API con FastAPI en `lambda_function.py`.

```bash
uvicorn lambda_function:app --reload
```

Endpoints principales:

- `GET /` → mensaje de bienvenida
- `GET /health` → estado del servicio
- `POST /optimizar` → recibe pedidos y devuelve el plan de rutas optimizado

## Ejemplo de request

```json
{
  "pedidos": [
    {
      "nombre": "Cliente 1",
      "direccion": "Monterrey, Nuevo León, México",
      "turno": "M",
      "tipo": "ch",
      "telefono": "5551234567",
      "notas": "Entrega rápida"
    }
  ],
  "config": {
    "negocio": {
      "nombre": "Mi negocio",
      "ciudad": "Monterrey, Nuevo León, México",
      "deposito": "25.6800, -100.3500",
      "moneda": "MXN"
    },
    "turnos": [
      {"id": "M", "nombre": "Matutino", "inicio": "08:00", "fin": "13:00", "hora_salida": 8.0}
    ],
    "vehiculos": {
      "cantidad": 2,
      "capacidad_max": 10
    },
    "items": {
      "tipos": [
        {"id": "ch", "nombre": "Chico", "puntos": 1}
      ],
      "tipo_default": "ch"
    }
  }
}
```

## Configuración del negocio

La carpeta `configs/` contiene ejemplos con la estructura base necesaria para adaptar el proyecto a diferentes negocios.

Cada archivo JSON incluye:

- `negocio`: nombre, ciudad, depósito y moneda
- `turnos`: horarios de operación
- `vehiculos`: cantidad y capacidad máxima
- `items`: tipos de pedido y su peso/capacidad

## Observaciones

- Si no se envía una configuración en la solicitud, la API usa la configuración por defecto definida en `optimizer.py`.
- El servicio usa OSRM y Nominatim, por lo que la conexión a internet es necesaria para geocodificar rutas y calcular tiempos reales.
- Para despliegue en AWS Lambda, la aplicación está preparada con `Mangum` en `lambda_function.py`.

## Licencia

Este proyecto se entrega como código fuente funcional para uso interno o de desarrollo. Ajusta la licencia según tus necesidades antes de desplegarlo en producción.
