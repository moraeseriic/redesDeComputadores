# Compara o tamanho das mensagens HTTP vs CoAP sem precisar de servidor.
# Rodar: python comparar.py

from core.sensor import Sensor
from core.tamanhos import resumo


def main():
    payload = Sensor("sensor-01").read_json()
    r = resumo(payload)

    print("=" * 56)
    print(" Comparacao de tamanho de mensagem (1 leitura de sensor)")
    print("=" * 56)
    print(f" Payload JSON (igual nos dois):   {len(payload):>4} B")
    print(f" Exemplo: {payload.decode()}")
    print("-" * 56)
    print(f" {'Protocolo':<12}{'Overhead':>12}{'Total':>10}{'Transporte':>14}")
    print(f" {'HTTP/1.1':<12}{r['http_overhead']:>11}B{r['http_total']:>9}B{'TCP':>14}")
    print(f" {'CoAP':<12}{r['coap_overhead']:>11}B{r['coap_total']:>9}B{'UDP':>14}")
    print("-" * 56)
    print(f" CoAP economiza ~{r['economia_pct']:.0f}% do tamanho total por mensagem.")
    print("=" * 56)
    print(" Obs.: HTTP ainda abre conexao TCP (3-way handshake) antes")
    print(" de enviar dados; CoAP envia direto em 1 datagrama UDP.")


if __name__ == "__main__":
    main()
