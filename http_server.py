# Servidor HTTP do experimento — FastAPI na porta 8000.
# Recebe leituras dos sensores via POST e serve o dashboard em /.
#
# Rodar isolado: python http_server.py

import json
import logging
import os
import subprocess
import sys
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core import estado
from core.tamanhos import resumo_por_tamanho, tamanho_http

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

app = FastAPI(title="IoT HTTP Server")

_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC = os.path.join(_DIR, "static")
_ANALISE = os.path.join(_DIR, "capturas", "analise.json")

_ultimas_leituras: dict[str, dict] = {}
_contador = {"posts": 0}


@app.post("/sensor")
async def receber_leitura(request: Request):
    corpo = await request.body()
    dados = await request.json()
    sensor_id = dados.get("id", "desconhecido")
    _ultimas_leituras[sensor_id] = dados
    _contador["posts"] += 1
    logger.info("POST #%d de %s: %s", _contador["posts"], sensor_id, dados)
    estado.gravar(
        "http",
        leitura=dados,
        total_bytes=tamanho_http(corpo),
        payload_bytes=len(corpo),
        contador=_contador["posts"],
    )
    return JSONResponse(status_code=201, content={"status": "ok", "recebido": dados})


@app.get("/sensor/{sensor_id}")
async def consultar_leitura(sensor_id: str):
    if sensor_id not in _ultimas_leituras:
        return JSONResponse(status_code=404, content={"erro": "sem dados"})
    return _ultimas_leituras[sensor_id]


@app.get("/health")
async def health():
    return {"status": "vivo", "posts_recebidos": _contador["posts"]}


@app.get("/api/stats")
async def stats():
    try:
        http_estado = estado.ler("http")
        coap_estado = estado.ler("coap")
        n_payload = 68
        if http_estado and http_estado.get("payload_bytes", 0) > 0:
            n_payload = http_estado["payload_bytes"]
        elif coap_estado and coap_estado.get("payload_bytes", 0) > 0:
            n_payload = coap_estado["payload_bytes"]
        return {
            "http": http_estado,
            "coap": coap_estado,
            "comparacao": resumo_por_tamanho(n_payload),
        }
    except Exception as exc:
        logger.error("erro em /api/stats: %s", exc)
        return JSONResponse(status_code=500, content={"erro": str(exc)})


@app.get("/api/captura")
async def captura_status():
    try:
        with open(_ANALISE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"status": "sem"}


@app.post("/api/captura/run")
async def captura_run():
    atual = await captura_status()
    if atual.get("status") == "capturando":
        if time.time() - atual.get("gerado_em", 0) < 40:
            return {"status": "ja_rodando"}
    subprocess.Popen(
        [sys.executable, "capturar.py", "--existente", "--reiniciar-http"],
        cwd=_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return {"status": "iniciado"}


@app.get("/")
async def dashboard():
    return FileResponse(os.path.join(_STATIC, "dashboard.html"))


if os.path.isdir(_STATIC):
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
