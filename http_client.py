"""
http_client.py - Cliente HTTP que simula um sensor IoT enviando dados.

A cada intervalo, le o sensor e faz um POST para o servidor HTTP. Mede e
imprime o tamanho aproximado da requisicao para comparar com o CoAP.

Rodar (servidor HTTP precisa estar no ar):
    python http_client.py --n 10 --intervalo 1
"""

import argparse
import asyncio
import logging

import httpx

from core.sensor import Sensor
from core.tamanhos import tamanho_http

logging.basicConfig(level=logging.INFO, format="%(asctime)s [http_client] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("http_client")

URL = "http://127.0.0.1:8000/sensor"
_TENTATIVAS = 3  # retenta N vezes antes de desistir do envio


async def main(n: int, intervalo: float):
    sensor = Sensor("sensor-http")
    async with httpx.AsyncClient(timeout=5.0) as client:
        for i in range(n):
            corpo = sensor.read_json()
            tam = tamanho_http(corpo)
            for tentativa in range(1, _TENTATIVAS + 1):
                try:
                    r = await client.post(
                        URL,
                        content=corpo,
                        headers={"Content-Type": "application/json"},
                    )
                    logger.info(
                        "envio %d/%d | req~%dB corpo=%dB | resp HTTP %d (%dB)",
                        i + 1, n, tam, len(corpo), r.status_code, len(r.content),
                    )
                    break
                except httpx.ConnectError:
                    logger.warning("envio %d/%d | servidor indisponivel (tentativa %d/%d)", i + 1, n, tentativa, _TENTATIVAS)
                    if tentativa < _TENTATIVAS:
                        await asyncio.sleep(1)
                except Exception as exc:
                    logger.error("envio %d/%d | erro inesperado: %s", i + 1, n, exc)
                    break
            if i < n - 1:
                await asyncio.sleep(intervalo)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10, help="numero de envios")
    p.add_argument("--intervalo", type=float, default=1.0, help="segundos entre envios")
    args = p.parse_args()
    asyncio.run(main(args.n, args.intervalo))
