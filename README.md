# Redes de Computadores — Trabalho II
## Grupo 8 — HTTP vs CoAP para IoT

Aplicação que **simula sensores IoT** enviando leituras de temperatura e
umidade por **dois protocolos diferentes** — HTTP e CoAP — para comparar
funcionamento, formato das mensagens e leveza de cada um.

> Documentos complementares (conceitos, limitações e roteiro da demonstração)
> estão em [`docs/`](docs/):
> - [`docs/CONCEITOS.md`](docs/CONCEITOS.md) — explicação teórica ligada à prática
> - [`docs/LIMITACOES.md`](docs/LIMITACOES.md) — limitações do experimento
> - [`docs/DEMONSTRACAO.md`](docs/DEMONSTRACAO.md) — passo a passo + captura no Wireshark

---

## Estrutura do projeto

```
redesDeComputadores/
├── core/                   # Módulos compartilhados entre servidores e clientes
│   ├── sensor.py           #   Sensor virtual (temperatura/umidade)
│   ├── estado.py           #   Estado entre processos via JSON (IPC simples)
│   └── tamanhos.py         #   Cálculo de overhead HTTP e CoAP (fonte única)
├── static/
│   └── dashboard.html      # Dashboard web em tempo real
├── http_server.py          # Servidor HTTP (FastAPI, porta 8000)
├── http_client.py          # Cliente HTTP — simula sensor enviando por HTTP
├── coap_server.py          # Servidor CoAP (aiocoap, RFC 7252, porta 5683 UDP)
├── coap_client.py          # Cliente CoAP — simula sensor enviando por CoAP
├── capturar.py             # Captura e analisa tráfego real (Wireshark/tshark)
├── comparar.py             # Tabela de overhead sem precisar de servidor
├── run_all.py              # Orquestrador — sobe tudo com um único comando
└── requirements.txt        # Dependências Python
```

| Arquivo/Pasta | Papel |
|---|---|
| `run_all.py` | **Sobe tudo com um comando** (2 servidores + 2 sensores + dashboard). |
| `core/sensor.py` | Gera leituras simuladas (temperatura/umidade) em JSON. Compartilhado pelos dois clientes. |
| `core/tamanhos.py` | Fórmulas de overhead de cada protocolo — **fonte única** usada por todo o projeto. |
| `core/estado.py` | Estado compartilhado entre os processos via arquivos JSON (IPC simples). |
| `http_server.py` | Servidor **HTTP** (FastAPI) — recebe leituras via `POST /sensor`, serve o dashboard. |
| `coap_server.py` | Servidor **CoAP** (aiocoap, RFC 7252) — recebe leituras via `POST /sensor` sobre UDP. |
| `http_client.py` | Cliente com retry — simula o sensor enviando por **HTTP**. |
| `coap_client.py` | Cliente com retry — simula o sensor enviando por **CoAP**. |
| `comparar.py` | Imprime a tabela de tamanho/overhead HTTP vs CoAP (sem precisar de servidor). |
| `capturar.py` | **Captura e analisa o tráfego real** com tshark (Wireshark) e salva `.pcapng`. |
| `static/dashboard.html` | **Dashboard web** em tempo real (servido pelo FastAPI em `/`). |

Arquitetura (idêntica nos dois protocolos, **cliente-servidor / requisição-resposta**):

```
   ┌──────────────┐   POST leitura (JSON)   ┌──────────────┐
   │  cliente     │ ──────────────────────► │  servidor    │
   │  (sensor)    │ ◄────────────────────── │              │
   └──────────────┘   resposta (status)     └──────────────┘
     HTTP  → TCP porta 8000
     CoAP  → UDP porta 5683
```

---

## Instalação

Requer **Python 3.10+** (testado no 3.12).

```bash
# 1. criar ambiente virtual
python -m venv .venv

# 2. ativar
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1
#   Linux/Mac:
source .venv/bin/activate

# 3. instalar dependências
pip install -r requirements.txt
```

---

## Como rodar — **um comando**

> Roteiro completo da demonstração em [`docs/DEMONSTRACAO.md`](docs/DEMONSTRACAO.md).

**Um único comando** sobe os dois servidores (HTTP e CoAP), os dois sensores
e abre o dashboard no navegador:

```bash
python run_all.py
```

> Na primeira execução, o `run_all.py` **instala as dependências sozinho**
> (a partir do `requirements.txt`) caso ainda não estejam presentes — não é
> obrigatório criar a venv antes. Usar venv continua sendo recomendado para
> não misturar pacotes com o Python do sistema.

O `run_all.py` ainda **dispara automaticamente uma captura de tráfego** (se o
Wireshark/tshark estiver instalado): em ~12s o painel **"Captura de tráfego"**
no próprio dashboard mostra quantos bytes/pacotes cada protocolo gastou, o
handshake TCP e a razão HTTP/CoAP — tudo a partir de um `.pcapng` real. Há
também o botão **"Recapturar"** na página. Sem Wireshark, o resto funciona
normalmente e a captura fica desabilitada.

Depois é só ver o dashboard que abriu em **http://127.0.0.1:8000/** — leituras
dos dois protocolos lado a lado, contadores e comparação de bytes ao vivo.
Para encerrar tudo, pressione **Ctrl+C** no terminal.

Opções:
```bash
python run_all.py --intervalo 1      # sensores enviam mais rápido (1s)
python run_all.py --sem-navegador    # não abre o browser sozinho
```

### Captura de tráfego (item 3 da entrega)

Com o Wireshark instalado (com Npcap), **um comando** captura o tráfego real
dos dois protocolos na interface de loopback, salva o `.pcapng` e imprime a
análise comparativa:

```bash
python capturar.py
```

Gera `capturas/http_vs_coap.pcapng` (abra no Wireshark) e mostra, no terminal,
a hierarquia de protocolos, o handshake TCP e quantos bytes cada protocolo
gastou para entregar as mesmas leituras. Passo a passo manual (interfaces,
filtros) em [`docs/DEMONSTRACAO.md`](docs/DEMONSTRACAO.md).

### Rodar peças isoladas (opcional)

```bash
python comparar.py                              # só a tabela de tamanho (sem servidor)
python http_server.py                           # só o servidor HTTP (+ dashboard em /)
python coap_server.py                           # só o servidor CoAP
python http_client.py --n 10 --intervalo 1      # só o sensor HTTP
python coap_client.py --n 10 --intervalo 1      # só o sensor CoAP
```
Clientes aceitam `--n` (quantos envios) e `--intervalo` (segundos entre envios).

---

## Resultado típico

```
========================================================
 Comparacao de tamanho de mensagem (1 leitura de sensor)
========================================================
 Payload JSON (igual nos dois):     70 B
 Protocolo       Overhead     Total    Transporte
 HTTP/1.1            136B      206B           TCP
 CoAP                 14B       84B           UDP
 CoAP economiza ~59% do tamanho total por mensagem.
========================================================
```

Mesmo dado, mesma semântica (POST → resposta de "criado"), mas o CoAP
transporta a leitura com **uma fração do overhead** e sobre UDP, sem
handshake de conexão. É isso que torna o CoAP mais adequado a dispositivos
IoT restritos. Detalhes em [`docs/CONCEITOS.md`](docs/CONCEITOS.md).
