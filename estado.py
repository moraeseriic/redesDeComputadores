"""
estado.py - Estado compartilhado entre os processos via arquivos JSON.

Os servidores HTTP e CoAP rodam em processos separados (memorias separadas),
mas o dashboard (servido pelo FastAPI) precisa mostrar os dados dos dois. A
solucao simples e didatica: cada servidor grava seu ultimo estado num arquivo
JSON; o dashboard le os dois arquivos.

Arquivos gerados (ignorados pelo git): _estado_http.json, _estado_coap.json
"""

import json
import os
import time

_DIR = os.path.dirname(os.path.abspath(__file__))


def _caminho(protocolo: str) -> str:
    return os.path.join(_DIR, f"_estado_{protocolo}.json")


def gravar(protocolo: str, leitura: dict, total_bytes: int, payload_bytes: int, contador: int) -> None:
    """Grava o ultimo estado de um protocolo (chamado a cada POST recebido)."""
    dados = {
        "protocolo": protocolo,
        "leitura": leitura,
        "total_bytes": total_bytes,
        "payload_bytes": payload_bytes,
        "mensagens": contador,
        "atualizado_em": time.time(),
    }
    # Escrita atomica: grava em tmp e renomeia, evita ler arquivo pela metade.
    tmp = _caminho(protocolo) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f)
    os.replace(tmp, _caminho(protocolo))


def ler(protocolo: str) -> dict | None:
    """Le o ultimo estado de um protocolo, ou None se ainda nao houver."""
    try:
        with open(_caminho(protocolo), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def limpar() -> None:
    """Remove os arquivos de estado (util para comecar uma demo limpa)."""
    for proto in ("http", "coap"):
        try:
            os.remove(_caminho(proto))
        except FileNotFoundError:
            pass
