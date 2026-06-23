"""
coap_client.py - Cliente CoAP que simula um sensor IoT enviando dados.

A cada intervalo, le o sensor e faz um POST CoAP (sobre UDP) para o servidor.
Mede e imprime o tamanho aproximado da mensagem para comparar com o HTTP.

Rodar (servidor CoAP precisa estar no ar):
    python coap_client.py --n 10 --intervalo 1
"""

import argparse
import asyncio
import logging

from aiocoap import Context, Message, POST
from aiocoap.error import NetworkError, RequestTimedOut

from core.sensor import Sensor
from core.tamanhos import tamanho_coap

logging.basicConfig(level=logging.INFO, format="%(asctime)s [coap_client] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("coap_client")

URI = "coap://127.0.0.1/sensor"
_TENTATIVAS = 3


async def main(n: int, intervalo: float):
    sensor = Sensor("sensor-coap")
    protocol = await Context.create_client_context()
    for i in range(n):
        payload = sensor.read_json()
        tam = tamanho_coap(payload)
        for tentativa in range(1, _TENTATIVAS + 1):
            try:
                req = Message(code=POST, uri=URI, payload=payload)
                resp = await protocol.request(req).response
                logger.info(
                    "envio %d/%d | msg~%dB payload=%dB | resp %s (%dB)",
                    i + 1, n, tam, len(payload), resp.code, len(resp.payload),
                )
                break
            except (NetworkError, RequestTimedOut) as exc:
                logger.warning("envio %d/%d | servidor indisponivel (tentativa %d/%d): %s", i + 1, n, tentativa, _TENTATIVAS, exc)
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
