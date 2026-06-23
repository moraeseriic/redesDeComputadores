"""
tamanhos.py - Fonte unica de verdade para o calculo de overhead dos protocolos.

Centraliza as funcoes que estimam o tamanho (em bytes) de uma mensagem HTTP
e de uma mensagem CoAP carregando o mesmo payload. Usado pelos clientes, pelo
script de comparacao e pelo dashboard, para que todos mostrem os mesmos numeros.
"""

# --- HTTP/1.1 (texto, sobre TCP) ---------------------------------------------

def tamanho_http(payload: bytes) -> int:
    """Tamanho estimado de um POST HTTP/1.1 (linha + headers + corpo)."""
    linha = "POST /sensor HTTP/1.1\r\n"
    headers = (
        "Host: 127.0.0.1:8000\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "Accept: */*\r\n"
        "Connection: keep-alive\r\n"
        "\r\n"
    )
    return len(linha.encode()) + len(headers.encode()) + len(payload)


# --- CoAP (binario, sobre UDP) -----------------------------------------------
CABECALHO_FIXO = 4          # versao, tipo, token len, codigo, message-id
TOKEN = 2                   # tamanho de token usado por padrao
OPT_URI_PATH = 1 + len("sensor")   # option header + nome do recurso
MARCADOR_PAYLOAD = 1        # byte 0xFF que separa header/options do payload


def tamanho_coap(payload: bytes) -> int:
    """Tamanho estimado de uma mensagem CoAP (binaria e compacta)."""
    return CABECALHO_FIXO + TOKEN + OPT_URI_PATH + MARCADOR_PAYLOAD + len(payload)


def resumo_por_tamanho(n_payload: int) -> dict:
    """Igual a resumo(), mas a partir do tamanho do payload (em bytes)."""
    return resumo(b"x" * n_payload)


def resumo(payload: bytes) -> dict:
    """Devolve um dicionario com os numeros usados no dashboard/comparacao."""
    http_total = tamanho_http(payload)
    coap_total = tamanho_coap(payload)
    p = len(payload)
    return {
        "payload": p,
        "http_total": http_total,
        "coap_total": coap_total,
        "http_overhead": http_total - p,
        "coap_overhead": coap_total - p,
        "economia_pct": round(100 * (http_total - coap_total) / http_total, 1),
    }
