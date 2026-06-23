"""
coap_server.py - Servidor CoAP (Constrained Application Protocol, RFC 7252).

CoAP usa o mesmo modelo requisicao/resposta do HTTP (GET/POST/PUT/DELETE),
mas roda sobre UDP e com mensagens binarias compactas, pensado para
dispositivos IoT com pouca memoria/CPU e redes de baixa largura de banda.

Expoe um recurso /sensor que aceita POST (nova leitura) e GET (ultima
leitura), espelhando a API do servidor HTTP para permitir comparacao justa.

Rodar:
    python coap_server.py
Escuta em UDP porta 5683 (porta padrao do CoAP).
"""

import argparse
import asyncio
import json
import logging

import aiocoap
import aiocoap.resource as resource

from core import estado
from core.tamanhos import tamanho_coap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("coap_server")

_contador = {"posts": 0}


class SensorResource(resource.Resource):
    """Recurso CoAP que guarda a ultima leitura recebida."""

    def __init__(self):
        super().__init__()
        self.ultima_leitura: bytes = b'{"erro":"sem dados"}'

    async def render_get(self, request):
        """GET /sensor -> devolve a ultima leitura."""
        return aiocoap.Message(
            code=aiocoap.CONTENT,  # 2.05 Content (equivalente ao 200 OK)
            payload=self.ultima_leitura,
        )

    async def render_post(self, request):
        """POST /sensor -> armazena nova leitura."""
        self.ultima_leitura = request.payload
        _contador["posts"] += 1
        try:
            dados = json.loads(request.payload.decode())
        except Exception:
            dados = {"raw": request.payload.decode(errors="replace")}
        logger.info("POST #%d: %s", _contador["posts"], dados)
        # Grava no estado compartilhado para o dashboard mostrar.
        estado.gravar(
            "coap",
            leitura=dados,
            total_bytes=tamanho_coap(request.payload),
            payload_bytes=len(request.payload),
            contador=_contador["posts"],
        )
        # Resposta minima: codigo 2.01 Created + eco do payload
        return aiocoap.Message(
            code=aiocoap.CREATED,  # 2.01 Created (equivalente ao 201)
            payload=request.payload,
        )


async def main(host: str, port: int):
    root = resource.Site()
    root.add_resource(["sensor"], SensorResource())
    # .well-known/core: descoberta de recursos, recurso nativo do CoAP
    root.add_resource(
        [".well-known", "core"],
        resource.WKCResource(root.get_resources_as_linkheader),
    )
    await aiocoap.Context.create_server_context(root, bind=(host, port))
    print(f"[CoAP] Servidor escutando em udp://{host}:{port}")
    await asyncio.get_running_loop().create_future()  # roda para sempre


if __name__ == "__main__":
    # Nota: no Windows o aiocoap usa o transporte 'simplesocketserver',
    # que NAO aceita bind em 0.0.0.0 (any-address). Por isso o padrao e
    # 127.0.0.1. Em Linux/Mac pode-se usar 0.0.0.0 para aceitar a LAN.
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5683)
    args = p.parse_args()
    asyncio.run(main(args.host, args.port))
