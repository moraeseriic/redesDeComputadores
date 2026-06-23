"""
sensor.py - Simulacao de um sensor IoT.

Gera leituras de temperatura e umidade com pequena variacao aleatoria,
imitando um sensor fisico (ex.: DHT22). O mesmo gerador alimenta tanto o
cliente HTTP quanto o cliente CoAP, garantindo que a comparacao entre os
protocolos use exatamente o mesmo tipo de dado.
"""

import json
import random
import time


class Sensor:
    """Sensor virtual de temperatura/umidade."""

    def __init__(self, sensor_id: str = "sensor-01"):
        self.sensor_id = sensor_id
        # Estado inicial "realista"
        self._temp = 25.0
        self._hum = 60.0

    def read(self) -> dict:
        """Retorna uma leitura nova (passeio aleatorio suave)."""
        self._temp = round(self._temp + random.uniform(-0.5, 0.5), 2)
        self._hum = round(self._hum + random.uniform(-1.0, 1.0), 2)
        # Limita a faixas plausiveis
        self._temp = max(15.0, min(40.0, self._temp))
        self._hum = max(20.0, min(95.0, self._hum))
        return {
            "id": self.sensor_id,
            "temperatura": self._temp,
            "umidade": self._hum,
            "ts": int(time.time()),
        }

    def read_json(self) -> bytes:
        """Leitura serializada em JSON (bytes), formato comum em IoT."""
        return json.dumps(self.read(), separators=(",", ":")).encode("utf-8")


if __name__ == "__main__":
    # Teste rapido: imprime 3 leituras
    s = Sensor()
    for _ in range(3):
        print(s.read_json().decode())
        time.sleep(0.2)
