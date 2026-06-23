"""
coap_client.py - Cliente CoAP que simula um sensor IoT enviando dados.

A cada intervalo, le o sensor e faz um POST CoAP (sobre UDP) para o servidor.
Mede e imprime o tamanho aproximado da mensagem para comparar com o HTTP.

Rodar (servidor CoAP precisa estar no ar):
    python coap_client.py --n 10 --intervalo 1
"""

import argparse
import asyncio

from aiocoap import Context, Message, POST

from core.sensor import Sensor
from core.tamanhos import tamanho_coap

URI = "coap://127.0.0.1/sensor"


async def main(n: int, intervalo: float):
    sensor = Sensor("sensor-coap")
    protocol = await Context.create_client_context()
    for i in range(n):
        payload = sensor.read_json()
        tam = tamanho_coap(payload)
        req = Message(code=POST, uri=URI, payload=payload)
        resp = await protocol.request(req).response
        print(
            f"[CoAP] envio {i + 1}/{n} | "
            f"msg~{tam}B payload={len(payload)}B | "
            f"resp {resp.code} ({len(resp.payload)}B)"
        )
        if i < n - 1:
            await asyncio.sleep(intervalo)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10, help="numero de envios")
    p.add_argument("--intervalo", type=float, default=1.0, help="segundos entre envios")
    args = p.parse_args()
    asyncio.run(main(args.n, args.intervalo))
