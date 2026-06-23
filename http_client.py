"""
http_client.py - Cliente HTTP que simula um sensor IoT enviando dados.

A cada intervalo, le o sensor e faz um POST para o servidor HTTP. Mede e
imprime o tamanho aproximado da requisicao para comparar com o CoAP.

Rodar (servidor HTTP precisa estar no ar):
    python http_client.py --n 10 --intervalo 1
"""

import argparse
import asyncio

import httpx

from sensor import Sensor
from tamanhos import tamanho_http

URL = "http://127.0.0.1:8000/sensor"


async def main(n: int, intervalo: float):
    sensor = Sensor("sensor-http")
    async with httpx.AsyncClient() as client:
        for i in range(n):
            corpo = sensor.read_json()
            tam = tamanho_http(corpo)
            r = await client.post(
                URL,
                content=corpo,
                headers={"Content-Type": "application/json"},
            )
            print(
                f"[HTTP] envio {i + 1}/{n} | "
                f"req~{tam}B corpo={len(corpo)}B | "
                f"resp HTTP {r.status_code} ({len(r.content)}B)"
            )
            if i < n - 1:
                await asyncio.sleep(intervalo)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10, help="numero de envios")
    p.add_argument("--intervalo", type=float, default=1.0, help="segundos entre envios")
    args = p.parse_args()
    asyncio.run(main(args.n, args.intervalo))
