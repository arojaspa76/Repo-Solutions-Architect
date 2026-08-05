"""
Herramienta: Weather — Sesión 7
==================================
Herramienta de clima para el agente LLM.

NOTA PEDAGÓGICA: Esta es una implementación MOCK para la clase.
En producción conectarías a:
  - OpenWeatherMap API: https://openweathermap.org/api
  - WeatherAPI: https://www.weatherapi.com
  - Azure Maps Weather: https://docs.microsoft.com/azure/azure-maps/weather-coverage

Por qué mockear en clase:
  1. No requiere API key → todos pueden ejecutarlo
  2. Latencia predecible para pruebas de carga
  3. El foco pedagógico es el agente y el autoescalado, no el clima

Para conectar a una API real, solo reemplazar el método _fetch_real()
y el resto del agente no cambia — ese es el poder de la arquitectura.
"""

import asyncio
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

# Datos climáticos simulados para ciudades de LATAM y el mundo
_MOCK_WEATHER: dict[str, dict] = {
    # LATAM
    "bogotá":     {"temp": 14, "feels": 12, "desc": "parcialmente nublado", "humidity": 75, "wind": 8},
    "bogota":     {"temp": 14, "feels": 12, "desc": "parcialmente nublado", "humidity": 75, "wind": 8},
    "medellín":   {"temp": 22, "feels": 21, "desc": "soleado", "humidity": 60, "wind": 5},
    "medellin":   {"temp": 22, "feels": 21, "desc": "soleado", "humidity": 60, "wind": 5},
    "lima":       {"temp": 18, "feels": 17, "desc": "nublado", "humidity": 85, "wind": 12},
    "santiago":   {"temp": 20, "feels": 19, "desc": "despejado", "humidity": 45, "wind": 15},
    "buenos aires": {"temp": 25, "feels": 24, "desc": "soleado", "humidity": 55, "wind": 10},
    "ciudad de mexico": {"temp": 19, "feels": 18, "desc": "lluvioso", "humidity": 80, "wind": 6},
    "ciudad de méxico": {"temp": 19, "feels": 18, "desc": "lluvioso", "humidity": 80, "wind": 6},
    "caracas":    {"temp": 26, "feels": 28, "desc": "caluroso y húmedo", "humidity": 90, "wind": 4},
    "quito":      {"temp": 16, "feels": 15, "desc": "lluvia ligera", "humidity": 82, "wind": 7},
    "cali":       {"temp": 28, "feels": 30, "desc": "soleado y caliente", "humidity": 70, "wind": 3},
    "barranquilla": {"temp": 32, "feels": 36, "desc": "muy caluroso", "humidity": 85, "wind": 5},
    # Europa
    "madrid":     {"temp": 22, "feels": 21, "desc": "soleado", "humidity": 40, "wind": 14},
    "barcelona":  {"temp": 24, "feels": 23, "desc": "despejado", "humidity": 55, "wind": 10},
    "paris":      {"temp": 18, "feels": 16, "desc": "nublado", "humidity": 70, "wind": 18},
    "london":     {"temp": 15, "feels": 13, "desc": "lluvioso", "humidity": 80, "wind": 20},
    "berlin":     {"temp": 12, "feels": 10, "desc": "fresco y nublado", "humidity": 65, "wind": 16},
    # NA
    "new york":   {"temp": 20, "feels": 19, "desc": "parcialmente nublado", "humidity": 60, "wind": 22},
    "san francisco": {"temp": 17, "feels": 15, "desc": "niebla matutina", "humidity": 75, "wind": 25},
    # Asia
    "tokyo":      {"temp": 21, "feels": 20, "desc": "despejado", "humidity": 50, "wind": 8},
    "beijing":    {"temp": 23, "feels": 22, "desc": "smog moderado", "humidity": 45, "wind": 10},
}


class WeatherTool:
    """
    Herramienta de clima para el agente LLM.

    Uso por el agente:
        Action: weather
        Action Input: Bogotá
        Observation: Bogotá: 14°C (sensación 12°C), parcialmente nublado,
                     humedad 75%, viento 8 km/h
    """

    name = "weather"
    description = (
        "Obtiene el clima actual de una ciudad. "
        "Input: nombre de la ciudad (ej: 'Bogotá', 'Madrid', 'New York'). "
        "Retorna temperatura, descripción, humedad y viento."
    )

    async def run(self, city: str) -> str:
        """
        Obtener clima de una ciudad.

        Args:
            city: Nombre de la ciudad

        Returns:
            String con datos del clima
        """
        # Simular latencia de API real (50-150ms)
        await asyncio.sleep(random.uniform(0.05, 0.15))

        city_key = city.lower().strip()
        data = _MOCK_WEATHER.get(city_key)

        if not data:
            # Ciudad no en el mock — generar datos plausibles
            logger.info(f"🌤 Weather: ciudad '{city}' no en mock — generando datos")
            data = {
                "temp": random.randint(10, 35),
                "feels": random.randint(8, 38),
                "desc": random.choice(["soleado", "nublado", "parcialmente nublado", "lluvia ligera"]),
                "humidity": random.randint(40, 90),
                "wind": random.randint(5, 30),
            }

        hora = datetime.now().strftime("%H:%M")
        result = (
            f"{city}: {data['temp']}°C (sensación {data['feels']}°C), "
            f"{data['desc']}, humedad {data['humidity']}%, "
            f"viento {data['wind']} km/h. [Actualizado: {hora}]"
        )

        logger.info(f"🌤 Weather: {result}")
        return result
