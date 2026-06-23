"""
comparar.py - Comparacao direta do tamanho das mensagens HTTP vs CoAP.

Nao precisa de servidor: usa o mesmo payload JSON do sensor e calcula o
overhead de cada protocolo, imprimindo uma tabela. Util para a parte
"leveza de protocolo" do trabalho.

    python comparar.py
"""

from core.sensor import Sensor
from core.tamanhos import resumo


def main():
    sensor = Sensor("sensor-01")
    payload = sensor.read_json()

    r = resumo(payload)
    http_total = r["http_total"]
    coap_total = r["coap_total"]
    http_overhead = r["http_overhead"]
    coap_overhead = r["coap_overhead"]
    economia = r["economia_pct"]

    print("=" * 56)
    print(" Comparacao de tamanho de mensagem (1 leitura de sensor)")
    print("=" * 56)
    print(f" Payload JSON (igual nos dois):   {len(payload):>4} B")
    print(f" Exemplo de payload: {payload.decode()}")
    print("-" * 56)
    print(f" {'Protocolo':<12}{'Overhead':>12}{'Total':>10}{'Transporte':>14}")
    print(f" {'HTTP/1.1':<12}{http_overhead:>11}B{http_total:>9}B{'TCP':>14}")
    print(f" {'CoAP':<12}{coap_overhead:>11}B{coap_total:>9}B{'UDP':>14}")
    print("-" * 56)
    print(f" CoAP economiza ~{economia:.0f}% do tamanho total por mensagem.")
    print("=" * 56)
    print(" Obs.: HTTP ainda abre conexao TCP (3-way handshake) antes de")
    print(" enviar dados; CoAP envia direto em 1 datagrama UDP. A diferenca")
    print(" real em rede e maior do que so o tamanho da mensagem.")


if __name__ == "__main__":
    main()
