# FLOP Testnet Agent Bot

Bot simples 24/7 para farmar a testnet da FLOP Network como **Agent**.

O que faz:
1. Gera uma keystore (só uma vez)
2. Pede faucet todos os dias
3. Gasta o saldo em inference sessions
4. Corre em loop com limites de segurança

> **Aviso**: A testnet está em fase *unscored opening*. O gasto só conta para airdrop quando a fase scored for anunciada oficialmente. Usa wallet dedicada. Nunca partilhes a password ou o ficheiro da keystore.

---

## Requisitos

- Ubuntu 22.04 / 24.04 (Oracle Free Tier funciona perfeitamente)
- Node 22+
- Python 3.9+

---

## Instalação rápida (Oracle Cloud / VPS)

### 1. Criar a instância na Oracle

1. Vai a [cloud.oracle.com](https://cloud.oracle.com) e cria conta Free Tier
2. Cria uma **Compute Instance**:
   - Image: **Ubuntu 22.04** ou **24.04**
   - Shape: **VM.Standard.A1.Flex** (Ampere) – 2 OCPU + 12 GB RAM (grátis)
   - Ou AMD se preferires
3. Adiciona a tua SSH key
4. Abre a porta 22 (SSH) no Security List

### 2. Ligar à máquina

```bash
ssh ubuntu@IP_DA_INSTANCIA
```

### 3. Clonar o repositório

```bash
sudo apt update && sudo apt install -y git curl
git clone https://github.com/TEU_USER/flop-agent-bot.git
cd flop-agent-bot
```

### 4. Setup

```bash
chmod +x setup.sh
./setup.sh
```

### 5. Configurar password

```bash
nano .env
```

Muda a linha:
```
FLOP_KEYSTORE_PASSWORD=change-me-to-a-strong-password
```
para uma password forte (guarda-a num sítio seguro).

### 6. Correr o bot

**Opção A – Direto (simples)**

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python bot.py
```

Para deixar a correr em background com `tmux`:

```bash
sudo apt install -y tmux
tmux new -s flop
# dentro do tmux:
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python bot.py
# Ctrl+B depois D para sair
```

**Opção B – Docker (recomendado para 24/7)**

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Faz logout/login ou:
newgrp docker

# Correr
docker compose up -d --build

# Ver logs
docker compose logs -f
```

---

## Comandos úteis

```bash
# Ver estado
cat state/state-testnet.json

# Ver logs
tail -f logs/bot-testnet.log

# Parar (Docker)
docker compose down

# Reiniciar
docker compose restart
```

---

## Configuração (.env)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `FLOP_KEYSTORE_PASSWORD` | — | **Obrigatório**. Password da keystore |
| `FLOP_NETWORK` | `testnet` | `testnet` ou `devnet` |
| `MAX_FLOP_PER_SESSION` | `0.5` | Máximo de FLOP por inference |
| `MAX_SESSIONS_PER_DAY` | `40` | Limite diário de sessions |
| `MIN_BALANCE_TO_SPEND` | `0.2` | Só gasta se tiver pelo menos isto |
| `LOOP_SLEEP` | `90` | Segundos entre ciclos |

---

## Segurança

- A keystore fica em `./keystore/` com permissões 600
- A password **nunca** é escrita em disco pelo bot (só via env)
- Não commits o ficheiro `.env` nem a pasta `keystore/`
- Usa sempre uma wallet dedicada à testnet

---

## Notas importantes

- A testnet está **live** mas ainda em fase unscored.
- O faucet pode estar instável nos primeiros dias.
- Se o CLI mudar de sintaxe, o bot pode precisar de ajuste (é normal em testnet early).
- Devnet **não conta** para airdrop.

---

## Estrutura

```
flop-agent-bot/
├── bot.py              # Bot principal
├── setup.sh            # Instalação automática
├── requirements.txt
├── networks.json
├── Dockerfile
├── docker-compose.yml
├── .env                # (criado no setup – não commits)
├── keystore/           # keystore gerada (não commits)
├── state/              # estado do bot
└── logs/               # logs
```

---

Feito para correr 24/7 na Oracle Free Tier.
Qualquer dúvida, abre uma issue ou fala comigo.
