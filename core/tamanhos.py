# Funções para calcular o overhead de cada protocolo.
# Usadas pelos clientes, pelo comparar.py e pelo dashboard.


def tamanho_http(payload: bytes) -> int:
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


# CoAP: 4B header fixo + 2B token + option URI-path + 0xFF marker + payload
CABECALHO_FIXO = 4
TOKEN = 2
OPT_URI_PATH = 1 + len("sensor")
MARCADOR_PAYLOAD = 1


def tamanho_coap(payload: bytes) -> int:
    return CABECALHO_FIXO + TOKEN + OPT_URI_PATH + MARCADOR_PAYLOAD + len(payload)


def resumo_por_tamanho(n_payload: int) -> dict:
    return resumo(b"x" * n_payload)


def resumo(payload: bytes) -> dict:
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
