# Redes de Computadores — Trabalho II
## Grupo 8 — HTTP vs CoAP para IoT

Aplicação que **simula sensores IoT** enviando leituras de temperatura e umidade por **dois protocolos diferentes** — HTTP e CoAP — para comparar funcionamento, formato de mensagens e custo de overhead de cada um.

---

## Sumário

1. [Estrutura do projeto](#estrutura-do-projeto)
2. [O protocolo HTTP — conceitos e uso no trabalho](#o-protocolo-http)
3. [CoAP — contraponto](#coap)
4. [Comparação direta](#comparação-direta)
5. [Instalação](#instalação)
6. [Como rodar](#como-rodar)
7. [Captura de tráfego](#captura-de-tráfego)
8. [Resultado típico](#resultado-típico)

---

## Estrutura do projeto

```
redesDeComputadores/
├── core/
│   ├── sensor.py       # Sensor virtual (temperatura/umidade)
│   ├── estado.py       # Estado entre processos via JSON (IPC simples)
│   └── tamanhos.py     # Cálculo de overhead HTTP e CoAP (fonte única)
├── static/
│   └── dashboard.html  # Dashboard web em tempo real
├── docs/
│   ├── CONCEITOS.md
│   ├── DEMONSTRACAO.md
│   └── LIMITACOES.md
├── capturas/           # .pcapng gerado pela captura de tráfego
├── http_server.py      # Servidor HTTP (FastAPI, porta 8000 TCP)
├── http_client.py      # Cliente HTTP — simula sensor enviando por HTTP
├── coap_server.py      # Servidor CoAP (aiocoap, RFC 7252, porta 5683 UDP)
├── coap_client.py      # Cliente CoAP — simula sensor enviando por CoAP
├── capturar.py         # Captura e analisa tráfego real (tshark/Wireshark)
├── comparar.py         # Tabela de overhead sem precisar de servidor
├── run_all.py          # Orquestrador — sobe tudo com um único comando
└── requirements.txt
```

---

## O protocolo HTTP

### O que é HTTP

HTTP (*HyperText Transfer Protocol*) é o protocolo de camada de aplicação que serve de base para a web. Ele define um modelo **cliente-servidor** de **requisição e resposta**: o cliente inicia sempre, o servidor responde. É um protocolo **sem estado** (*stateless*) — cada troca de mensagens é independente.

No nosso experimento o **sensor faz papel de cliente** e o **servidor FastAPI faz papel de servidor**, exatamente como um navegador e um servidor web, mas trocando dados de sensores em vez de páginas HTML.

### Transporte: TCP

HTTP/1.1 roda sobre **TCP** (Transmission Control Protocol). Antes de qualquer dado trafegar, o TCP abre uma conexão com o **3-way handshake**:

```
Cliente                  Servidor
  |------ SYN ---------->|    (1) cliente pede conexão
  |<----- SYN-ACK -------|    (2) servidor aceita
  |------ ACK ---------->|    (3) cliente confirma
  |                       |
  |== dados HTTP ========>|    só agora os dados fluem
```

Isso acrescenta **pelo menos uma ida e volta de latência** antes do primeiro byte de dado chegar ao servidor. O cliente HTTP deste projeto usa `keep-alive` (conexão persistente), o que significa que o handshake acontece uma única vez e as requisições subsequentes reutilizam a mesma conexão TCP.

### Estrutura de uma requisição HTTP

Quando o sensor envia uma leitura, o cliente (`http_client.py`) monta e envia esta requisição:

```
POST /sensor HTTP/1.1\r\n
Host: 127.0.0.1:8000\r\n
Content-Type: application/json\r\n
Content-Length: 70\r\n
Accept: */*\r\n
Connection: keep-alive\r\n
\r\n
{"id":"sensor-http","temperatura":25.3,"umidade":61.2,"ts":1719000000}
```

Partes da requisição:

| Parte | Exemplo | Descrição |
|---|---|---|
| **Linha de status** | `POST /sensor HTTP/1.1` | Método + recurso + versão |
| **Host** | `127.0.0.1:8000` | Endereço do servidor |
| **Content-Type** | `application/json` | Formato do corpo |
| **Content-Length** | `70` | Tamanho do corpo em bytes |
| **Corpo (payload)** | `{"id":...}` | Dados do sensor em JSON |

O **método `POST`** foi escolhido porque semanticamente significa "criar um novo recurso" — cada leitura é um novo dado enviado ao servidor, o que combina com a resposta `201 Created`.

### Resposta do servidor

O servidor (`http_server.py`) responde:

```
HTTP/1.1 201 Created\r\n
Content-Type: application/json\r\n
\r\n
{"status":"ok","recebido":{"id":"sensor-http","temperatura":25.3,...}}
```

O código **201 Created** confirma que a leitura foi recebida e registrada.

### Como HTTP é usado para enviar dados (http_client.py)

O cliente usa a biblioteca `httpx` (cliente HTTP assíncrono para Python). A cada ciclo:

1. O sensor gera uma leitura (`core/sensor.py`) — temperatura + umidade + timestamp
2. A leitura é serializada em JSON: `{"id":"sensor-http","temperatura":25.3,...}`
3. O cliente calcula o tamanho total da requisição HTTP (payload + overhead de headers)
4. Envia via `POST http://127.0.0.1:8000/sensor` com `Content-Type: application/json`
5. Registra o status da resposta no log

```python
# trecho de http_client.py
r = await client.post(URL, content=corpo, headers={"Content-Type": "application/json"})
```

Se o servidor estiver indisponível, o cliente tenta até 3 vezes com 1 segundo de intervalo antes de desistir.

### Como HTTP é usado para receber dados (http_server.py)

O servidor usa **FastAPI** (framework web Python moderno, baseado em ASGI/uvicorn). Ele expõe os seguintes endpoints HTTP:

| Método | Endpoint | Função |
|---|---|---|
| `POST` | `/sensor` | Recebe leitura do sensor; retorna `201 Created` |
| `GET` | `/sensor/{id}` | Consulta última leitura de um sensor específico |
| `GET` | `/health` | Verificação de saúde do servidor |
| `GET` | `/api/stats` | Retorna estatísticas ao vivo (HTTP + CoAP + comparação) |
| `GET` | `/api/captura` | Retorna resultado da captura de tráfego (se disponível) |
| `POST` | `/api/captura/run` | Dispara nova captura de tráfego |
| `GET` | `/` | Serve o dashboard HTML em tempo real |

O endpoint central é o `POST /sensor`:

```python
# trecho de http_server.py
@app.post("/sensor")
async def receber_leitura(request: Request):
    corpo = await request.body()       # bytes brutos recebidos
    dados = await request.json()       # parse do JSON
    estado.gravar("http", leitura=dados, total_bytes=tamanho_http(corpo), ...)
    return JSONResponse(status_code=201, content={"status": "ok", "recebido": dados})
```

O servidor lê o corpo bruto (`request.body()`) para medir os bytes reais transmitidos, depois faz parse do JSON para extrair temperatura, umidade e ID.

### Como HTTP é usado para medir overhead (core/tamanhos.py)

A função `tamanho_http()` **calcula o tamanho exato** de uma requisição HTTP a partir do payload, reconstruindo os headers linha a linha:

```python
def tamanho_http(payload: bytes) -> int:
    linha   = "POST /sensor HTTP/1.1\r\n"
    headers = (
        "Host: 127.0.0.1:8000\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "Accept: */*\r\n"
        "Connection: keep-alive\r\n"
        "\r\n"
    )
    return len(linha.encode()) + len(headers.encode()) + len(payload)
```

Para um payload JSON de ~70 bytes, os headers HTTP consomem **~136 bytes adicionais** — quase o dobro do dado útil. Esse valor é exibido no dashboard e comparado com o overhead do CoAP.

### Dashboard e API de estatísticas via HTTP

O próprio **dashboard** (`static/dashboard.html`) é servido via HTTP pelo FastAPI. O navegador acessa `http://127.0.0.1:8000/` e recebe a página HTML. A partir daí, o dashboard faz polling periódico via `fetch()` para `GET /api/stats`, que retorna JSON com:

```json
{
  "http": { "total_bytes": 206, "payload_bytes": 70, "mensagens": 5 },
  "coap": { "total_bytes":  84, "payload_bytes": 70, "mensagens": 5 },
  "comparacao": {
    "payload": 70,
    "http_total": 206,
    "coap_total": 84,
    "http_overhead": 136,
    "coap_overhead": 14,
    "economia_pct": 59.2
  }
}
```

Toda a comunicação entre o dashboard e o back-end é HTTP — seja para receber leituras dos sensores, seja para exibir estatísticas comparativas em tempo real.

---

## CoAP

CoAP (*Constrained Application Protocol*, RFC 7252) é o contraponto: protocolo binário projetado para dispositivos IoT restritos. Roda sobre **UDP** (sem handshake de conexão) e usa um cabeçalho fixo de apenas **4 bytes**.

No experimento, o cliente CoAP envia leituras para `coap://127.0.0.1/sensor` (porta 5683 UDP) com o mesmo payload JSON que o cliente HTTP.

---

## Comparação direta

| Característica | HTTP/1.1 | CoAP |
|---|---|---|
| Transporte | TCP | UDP |
| Handshake | 3-way (SYN/SYN-ACK/ACK) | Nenhum |
| Cabeçalho fixo | ~136 B (texto ASCII) | 4 B (binário) |
| Total por mensagem (~70 B payload) | ~206 B | ~84 B |
| Overhead | ~136 B (~66% do total) | ~14 B (~17% do total) |
| Economia CoAP | — | **~59% menos bytes** |
| Confirmação | HTTP 201 Created | CoAP 2.01 Created |
| Modelo | Req/Resp stateless | Req/Resp + observe |
| Uso típico | Web, APIs REST, dashboards | IoT, LPWAN, microcontroladores |

**Por que HTTP ainda importa em IoT?**
HTTP é onipresente — qualquer linguagem e qualquer servidor suporta nativamente. Para dispositivos com conectividade TCP (como Raspberry Pi ou ESP32 com WiFi) e sem restrição severa de banda, HTTP é perfeitamente viável e simplifica a integração com back-ends web existentes. O CoAP é preferido quando cada byte tem custo (redes LoRa, NB-IoT) ou quando a RAM do dispositivo é contada em kilobytes.

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

## Como rodar

### Um comando — sobe tudo

```bash
python run_all.py
```

Sobe o servidor HTTP (porta 8000 TCP), o servidor CoAP (porta 5683 UDP), os dois clientes sensores e abre o dashboard no navegador automaticamente.

```bash
python run_all.py --intervalo 1      # sensores enviam mais rápido (1 s)
python run_all.py --sem-navegador    # não abre o browser sozinho
```

Dashboard em **http://127.0.0.1:8000/**. Para encerrar: **Ctrl+C**.

### Rodar peças isoladas

```bash
python comparar.py                         # tabela de overhead (sem servidor)
python http_server.py                      # só o servidor HTTP + dashboard
python coap_server.py                      # só o servidor CoAP
python http_client.py --n 10 --intervalo 1 # só o sensor HTTP (10 envios)
python coap_client.py --n 10 --intervalo 1 # só o sensor CoAP (10 envios)
```

---

## Captura de tráfego

Requer Wireshark instalado (com Npcap no Windows).

```bash
python capturar.py
```

Captura 12 segundos de tráfego na interface de loopback, gera `capturas/http_vs_coap.pcapng` e imprime análise comparativa.

Filtros úteis no Wireshark:

```
tcp.port == 8000      → tráfego HTTP
udp.port == 5683      → tráfego CoAP
http.request          → apenas requisições HTTP
coap                  → mensagens CoAP decodificadas
tcp.flags.syn == 1    → handshakes TCP
```

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

Mesmo dado, mesma semântica (`POST` → resposta de "criado"), mas o CoAP transporta a leitura com **uma fração do overhead** e sobre UDP, sem handshake de conexão. É isso que torna o CoAP mais adequado a dispositivos IoT restritos em banda e energia.

---

## Arquitetura

Fluxo idêntico nos dois protocolos (**cliente-servidor / requisição-resposta**):

```
   ┌──────────────┐   POST leitura (JSON)   ┌──────────────┐
   │  cliente     │ ──────────────────────► │  servidor    │
   │  (sensor)    │ ◄────────────────────── │              │
   └──────────────┘   resposta (status)     └──────────────┘
     HTTP  → TCP porta 8000   →  201 Created
     CoAP  → UDP porta 5683   →  2.01 Created
```

```
   navegador ──── GET / ────────────► FastAPI (HTTP)
             ◄─── dashboard.html ────
             ──── GET /api/stats ───► FastAPI (HTTP)
             ◄─── JSON comparação ───
```
