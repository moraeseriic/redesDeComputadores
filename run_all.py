"""
run_all.py - Sobe TUDO com um unico comando.

Inicia, em processos separados:
  1. servidor HTTP (FastAPI, tambem serve o dashboard)
  2. servidor CoAP (aiocoap)
  3. cliente/sensor HTTP (envios continuos)
  4. cliente/sensor CoAP (envios continuos)

Depois abre o dashboard no navegador. Encerre tudo com Ctrl+C.

    python run_all.py
    python run_all.py --intervalo 1      # mais rapido
    python run_all.py --sem-navegador    # nao abrir o browser
"""

import argparse
import importlib.util
import os
import signal
import subprocess
import sys
import time
import webbrowser

DIR = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable  # mesmo Python/venv que rodou este script
URL = "http://127.0.0.1:8000/"


def garantir_dependencias():
    """Se faltar alguma dependencia neste Python, instala via requirements.txt.

    Assim 'python run_all.py' funciona mesmo sem ter ativado a venv antes.
    """
    necessarios = ("fastapi", "uvicorn", "httpx", "aiocoap")
    faltando = [m for m in necessarios if importlib.util.find_spec(m) is None]
    if not faltando:
        return
    print(f"[deps] faltando: {', '.join(faltando)} -> instalando...")
    req = os.path.join(DIR, "requirements.txt")
    subprocess.check_call([PY, "-m", "pip", "install", "-q", "-r", req])
    print("[deps] instalado.\n")


garantir_dependencias()
import estado  # importado depois de garantir deps


def lancar(args_lista):
    """Inicia um processo filho rodando 'python <args_lista>'."""
    return subprocess.Popen([PY, *args_lista], cwd=DIR)


def main():
    p = argparse.ArgumentParser(description="Sobe servidores + sensores HTTP e CoAP.")
    p.add_argument("--intervalo", type=float, default=2.0, help="segundos entre envios dos sensores")
    p.add_argument("--n", type=int, default=1_000_000, help="numero de envios por sensor")
    p.add_argument("--sem-navegador", action="store_true", help="nao abrir o dashboard no browser")
    args = p.parse_args()

    estado.limpar()  # comeca a demo do zero

    procs = []
    print("== Subindo HTTP vs CoAP IoT ==")

    print(" [1/4] servidor HTTP  (FastAPI :8000) ...")
    procs.append(lancar(["http_server.py"]))

    print(" [2/4] servidor CoAP  (aiocoap :5683) ...")
    procs.append(lancar(["coap_server.py"]))

    # da um tempo para os servidores subirem antes dos clientes
    time.sleep(3)

    print(" [3/4] sensor HTTP    (envios a cada %.0fs) ..." % args.intervalo)
    procs.append(lancar(["http_client.py", "--n", str(args.n), "--intervalo", str(args.intervalo)]))

    print(" [4/4] sensor CoAP    (envios a cada %.0fs) ..." % args.intervalo)
    procs.append(lancar(["coap_client.py", "--n", str(args.n), "--intervalo", str(args.intervalo)]))

    # Dispara uma captura de trafego em background (se o Wireshark/tshark
    # existir). NAO entra em 'procs': e curta e sai sozinha; o watchdog abaixo
    # nao deve derrubar tudo quando ela terminar. O resultado aparece no
    # painel do dashboard quando concluir.
    import capturar
    captura_proc = None
    if capturar.achar_tshark():
        print(" [+]  captura de tráfego iniciada (resultado aparece no dashboard)")
        captura_proc = lancar(["capturar.py", "--existente"])
    else:
        print(" [i]  Wireshark/tshark não encontrado — captura desabilitada")

    print(f"\n  Dashboard: {URL}")
    print("  Encerrar tudo: Ctrl+C\n")

    if not args.sem_navegador:
        time.sleep(1)
        try:
            webbrowser.open(URL)
        except Exception:
            pass

    try:
        # espera ate Ctrl+C (ou ate algum processo morrer)
        while True:
            time.sleep(0.5)
            if any(pr.poll() is not None for pr in procs):
                print("\n[!] Um dos processos encerrou. Derrubando o resto...")
                break
    except KeyboardInterrupt:
        print("\n[*] Ctrl+C recebido. Encerrando...")
    finally:
        if captura_proc is not None and captura_proc.poll() is None:
            try:
                captura_proc.terminate()
            except Exception:
                pass
        for pr in procs:
            if pr.poll() is None:
                try:
                    if os.name == "nt":
                        pr.send_signal(signal.CTRL_BREAK_EVENT)
                    pr.terminate()
                except Exception:
                    pass
        # garante encerramento
        for pr in procs:
            try:
                pr.wait(timeout=5)
            except Exception:
                pr.kill()
        print("[*] Tudo encerrado.")


if __name__ == "__main__":
    main()
