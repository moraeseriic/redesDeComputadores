# Cliente CoAP — simula um sensor IoT enviando leituras via UDP.
# Rodar: python coap_client.py --n 10 --intervalo 1

import argparse
import asyncio
import logging

from aiocoap import Context, Message, POST
from aiocoap.error import NetworkError, RequestTimedOut

from core.sensor import Sensor
from core.tamanhos import tamanho_coap

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

URI = "coap://127.0.0.1/sensor"
_TENTATIVAS = 3


async def main(n: int, intervalo: float):
    sensor = Sensor("sensor-coap")
    protocol = await Context.create_client_context()
    for i in range(n):
        payload = sensor.read_json()
        tam = tamanho_coap(payload)
        for t in range(1, _TENTATIVAS + 1):
            try:
                req = Message(code=POST, uri=URI, payload=payload)
                resp = await protocol.request(req).response
                logger.info("envio %d/%d | msg~%dB | resp %s", i + 1, n, tam, resp.code)
                break
            except (NetworkError, RequestTimedOut) as exc:
                logger.warning("servidor indisponivel (tentativa %d/%d): %s", t, _TENTATIVAS, exc)
                if t < _TENTATIVAS:
                    await asyncio.sleep(1)
            except Exception as exc:
                logger.error("erro inesperado: %s", exc)
                break
        if i < n - 1:
            await asyncio.sleep(intervalo)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--intervalo", type=float, default=1.0)
    args = p.parse_args()
    asyncio.run(main(args.n, args.intervalo))
