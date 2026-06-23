# Servidor CoAP do experimento — aiocoap na porta 5683 (UDP).
# Espelha a API do servidor HTTP para comparação justa entre os protocolos.
#
# Rodar isolado: python coap_server.py
# Nota Windows: aiocoap não aceita 0.0.0.0 no Windows, usa 127.0.0.1.

import argparse
import asyncio
import json
import logging

import aiocoap
import aiocoap.resource as resource

from core import estado
from core.tamanhos import tamanho_coap

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

_contador = {"posts": 0}


class SensorResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.ultima_leitura: bytes = b'{"erro":"sem dados"}'

    async def render_get(self, request):
        return aiocoap.Message(code=aiocoap.CONTENT, payload=self.ultima_leitura)

    async def render_post(self, request):
        self.ultima_leitura = request.payload
        _contador["posts"] += 1
        try:
            dados = json.loads(request.payload.decode())
        except Exception:
            dados = {"raw": request.payload.decode(errors="replace")}
        logger.info("POST #%d: %s", _contador["posts"], dados)
        estado.gravar(
            "coap",
            leitura=dados,
            total_bytes=tamanho_coap(request.payload),
            payload_bytes=len(request.payload),
            contador=_contador["posts"],
        )
        return aiocoap.Message(code=aiocoap.CREATED, payload=request.payload)


async def main(host: str, port: int):
    root = resource.Site()
    root.add_resource(["sensor"], SensorResource())
    root.add_resource(
        [".well-known", "core"],
        resource.WKCResource(root.get_resources_as_linkheader),
    )
    await aiocoap.Context.create_server_context(root, bind=(host, port))
    logger.info("CoAP escutando em udp://%s:%d", host, port)
    await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5683)
    args = p.parse_args()
    asyncio.run(main(args.host, args.port))
