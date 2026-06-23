"""
capturar.py - Captura e analise de trafego (item 3 da entrega).

Dois modos:
  - padrao:        sobe servidores + sensores, captura e analisa (uso isolado)
        python capturar.py
  - --existente:   captura o trafego que JA esta fluindo (usado pelo run_all.py
                   e pelo botao do dashboard, com os servidores ja no ar)
        python capturar.py --existente

Em ambos: salva capturas/http_vs_coap.pcapng, grava capturas/analise.json
(consumido pelo dashboard) e imprime um resumo no terminal.

Requisitos: Wireshark instalado com Npcap (suporte a captura em loopback).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

DIR = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SAIDA_DIR = os.path.join(DIR, "capturas")
PCAP = os.path.join(SAIDA_DIR, "http_vs_coap.pcapng")
ANALISE = os.path.join(SAIDA_DIR, "analise.json")
FILTRO_CAPTURA = "tcp port 8000 or udp port 5683"
DURACAO = 12  # segundos de captura (autostop do tshark)


# --------------------------------------------------------------------------- #
# Localizacao de ferramentas
# --------------------------------------------------------------------------- #
def achar_tshark() -> str | None:
    """Localiza o tshark no PATH ou nos caminhos padrao do Windows (ou None)."""
    from shutil import which

    p = which("tshark")
    if p:
        return p
    for c in (r"C:\Program Files\Wireshark\tshark.exe",
              r"C:\Program Files (x86)\Wireshark\tshark.exe"):
        if os.path.isfile(c):
            return c
    return None


def achar_loopback(tshark: str) -> str | None:
    """Acha a interface de loopback via 'tshark -D' casando pelo nome."""
    out = subprocess.run([tshark, "-D"], capture_output=True, text=True).stdout
    for linha in out.splitlines():
        m = re.match(r"^\s*\d+\.\s+(\S+)\s+\((.*)\)", linha)
        if m and "loopback" in m.group(2).lower():
            return m.group(1)
    return None


def _escrever_status(estado: dict) -> None:
    os.makedirs(SAIDA_DIR, exist_ok=True)
    tmp = ANALISE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False)
    os.replace(tmp, ANALISE)


# --------------------------------------------------------------------------- #
# Captura + analise
# --------------------------------------------------------------------------- #
def analisar(tshark: str) -> dict:
    """Le o .pcapng, calcula metricas honestas e devolve um dicionario."""
    def tsh(*args):
        return subprocess.run([tshark, "-r", PCAP, *args],
                              capture_output=True, text=True).stdout.strip()

    def linhas(s):
        return [x for x in s.splitlines() if x.strip()]

    def conta_bytes(filtro):
        out = linhas(tsh("-Y", filtro, "-T", "fields", "-e", "frame.len"))
        return len(out), sum(int(x) for x in out)

    pk_http, by_http = conta_bytes("tcp.port==8000")
    pk_coap, by_coap = conta_bytes("udp.port==5683")
    n_syn = len(linhas(tsh("-Y", "tcp.flags.syn==1", "-T", "fields", "-e", "frame.number")))
    req_http = len(linhas(tsh("-Y", "http.request", "-T", "fields", "-e", "frame.number")))
    req_coap = len(linhas(tsh("-Y", "coap.code==2", "-T", "fields", "-e", "frame.number")))
    coap_dg = linhas(tsh("-Y", "coap.code==2", "-T", "fields", "-e", "frame.len"))

    return {
        "status": "pronto",
        "gerado_em": time.time(),
        "pcap": os.path.relpath(PCAP, DIR).replace("\\", "/"),
        "http": {
            "pacotes": pk_http,
            "bytes": by_http,
            "requisicoes": req_http,
            "bytes_por_req": round(by_http / req_http) if req_http else None,
        },
        "coap": {
            "pacotes": pk_coap,
            "bytes": by_coap,
            "requisicoes": req_coap,
            "bytes_por_req": round(by_coap / req_coap) if req_coap else None,
        },
        "razao_bytes": round(by_http / by_coap, 1) if by_coap else None,
        "syn_tcp": n_syn,
        "coap_datagrama_bytes": int(coap_dg[0]) if coap_dg else None,
    }


def imprimir(a: dict) -> None:
    print("\n" + "=" * 60)
    print(" ANALISE DO TRAFEGO CAPTURADO")
    print("=" * 60)
    print(f"   {'':12}{'pacotes':>10}{'bytes':>10}{'req':>6}{'B/req':>9}")
    h, c = a["http"], a["coap"]
    print(f"   {'HTTP (TCP)':12}{h['pacotes']:>10}{h['bytes']:>10}{h['requisicoes']:>6}{h['bytes_por_req'] or '-':>9}")
    print(f"   {'CoAP (UDP)':12}{c['pacotes']:>10}{c['bytes']:>10}{c['requisicoes']:>6}{c['bytes_por_req'] or '-':>9}")
    if a["razao_bytes"]:
        print(f"   -> HTTP transmitiu ~{a['razao_bytes']}x mais bytes que o CoAP.")
    print(f"   Handshake TCP: {a['syn_tcp']} SYN  |  CoAP/UDP: 0 (sem conexao)")
    if a["coap_datagrama_bytes"]:
        print(f"   CoAP: 1 requisicao = 1 datagrama de {a['coap_datagrama_bytes']} B no fio")
    print(f"   Arquivo: {a['pcap']}")
    print("=" * 60)


def capturar(com_infra: bool) -> int:
    """Executa a captura. Se com_infra=True, sobe servidores+sensores antes.

    Devolve codigo de saida (0 = ok).
    """
    tshark = achar_tshark()
    if not tshark:
        _escrever_status({"status": "indisponivel", "gerado_em": time.time(),
                          "msg": "tshark/Wireshark nao encontrado"})
        print("[erro] tshark nao encontrado. Instale o Wireshark (com Npcap).")
        return 1
    loop = achar_loopback(tshark)
    if not loop:
        _escrever_status({"status": "indisponivel", "gerado_em": time.time(),
                          "msg": "interface de loopback nao encontrada (Npcap)"})
        print("[erro] interface de loopback nao encontrada (reinstale o Npcap).")
        return 1

    os.makedirs(SAIDA_DIR, exist_ok=True)
    _escrever_status({"status": "capturando", "gerado_em": time.time()})

    infra = []
    try:
        if com_infra:
            import estado as _estado
            _estado.limpar()
            print("[1/3] subindo servidores HTTP e CoAP...")
            infra.append(subprocess.Popen([PY, "http_server.py"], cwd=DIR,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            infra.append(subprocess.Popen([PY, "coap_server.py"], cwd=DIR,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            time.sleep(3)

        print(f"[+] capturando {DURACAO}s na loopback ({loop})...")
        cap = subprocess.Popen(
            [tshark, "-i", loop, "-f", FILTRO_CAPTURA, "-a", f"duration:{DURACAO}", "-w", PCAP],
            cwd=DIR, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        time.sleep(2)

        if com_infra:
            print("[2/3] disparando sensores (rajada)...")
            subprocess.run([PY, "http_client.py", "--n", "6", "--intervalo", "0.4"],
                           cwd=DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([PY, "coap_client.py", "--n", "6", "--intervalo", "0.4"],
                           cwd=DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        _, err = cap.communicate(timeout=DURACAO + 10)
        if not os.path.isfile(PCAP):
            _escrever_status({"status": "erro", "gerado_em": time.time(),
                              "msg": "tshark nao gerou o arquivo (permissao/Npcap?)"})
            print("[erro] tshark falhou:\n" + (err or ""))
            return 1
    finally:
        for s in infra:
            if s.poll() is None:
                s.terminate()
        for s in infra:
            try:
                s.wait(timeout=5)
            except Exception:
                s.kill()

    a = analisar(tshark)
    _escrever_status(a)
    imprimir(a)
    return 0


def main():
    p = argparse.ArgumentParser(description="Captura e analisa trafego HTTP vs CoAP.")
    p.add_argument("--existente", action="store_true",
                   help="captura o trafego ja em andamento (nao sobe servidores)")
    args = p.parse_args()
    sys.exit(capturar(com_infra=not args.existente))


if __name__ == "__main__":
    main()
