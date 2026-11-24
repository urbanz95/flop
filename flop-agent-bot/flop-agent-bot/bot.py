#!/usr/bin/env python3
"""
FLOP Testnet Agent Bot
----------------------
Simple 24/7 bot that:
  1. Ensures a keystore exists
  2. Claims faucet daily
  3. Spends test FLOP on inference sessions
  4. Runs continuously with safety limits

Requires: Node 22+, @flop-labs/cli, Python 3.9+
"""

import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.resolve()
STATE_DIR = BASE_DIR / "state"
KEYSTORE_DIR = BASE_DIR / "keystore"
LOG_DIR = BASE_DIR / "logs"

STATE_DIR.mkdir(exist_ok=True)
KEYSTORE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

NETWORK = os.getenv("FLOP_NETWORK", "testnet")          # testnet | devnet
KEYSTORE_PATH = KEYSTORE_DIR / f"agent-{NETWORK}.json"
STATE_FILE = STATE_DIR / f"state-{NETWORK}.json"
PASSWORD_ENV = "FLOP_KEYSTORE_PASSWORD"

# Safety limits (adjust as needed)
MAX_FLOP_PER_SESSION = float(os.getenv("MAX_FLOP_PER_SESSION", "0.5"))
MAX_SESSIONS_PER_DAY = int(os.getenv("MAX_SESSIONS_PER_DAY", "40"))
MIN_BALANCE_TO_SPEND = float(os.getenv("MIN_BALANCE_TO_SPEND", "0.2"))
CLAIM_COOLDOWN_HOURS = 23                               # faucet usually 24h
LOOP_SLEEP_SECONDS = int(os.getenv("LOOP_SLEEP", "90")) # pause between cycles
SESSION_SLEEP_SECONDS = 15

PROMPTS = [
    "Explain what Proof of Useful Inference means in one short paragraph.",
    "Write a short haiku about decentralised AI.",
    "What is the difference between a blockchain validator and a miner?",
    "Give me three practical use cases for autonomous AI agents.",
    "Summarise the benefits of verifiable compute in two sentences.",
    "Describe a simple multi-agent collaboration pattern.",
    "What problems does a compute marketplace solve?",
    "Write a short motivational sentence for builders on testnet.",
]

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str, level: str = "info"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    color = {"info": "cyan", "ok": "green", "warn": "yellow", "err": "red"}.get(level, "white")
    console.print(f"[dim]{ts}[/dim] [{color}]{msg}[/{color}]")
    with open(LOG_DIR / f"bot-{NETWORK}.log", "a") as f:
        f.write(f"{ts} [{level.upper()}] {msg}\n")


def run_cmd(cmd: list[str] | str, env: dict | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=full_env,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "address": None,
        "last_claim": None,
        "sessions_today": 0,
        "last_session_date": None,
        "total_sessions": 0,
        "total_spent_approx": 0.0,
    }


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def ensure_password() -> str:
    pw = os.getenv(PASSWORD_ENV)
    if not pw:
        console.print(f"[red]Environment variable {PASSWORD_ENV} is not set.[/red]")
        console.print("Create a strong password and export it before running the bot:")
        console.print(f'  export {PASSWORD_ENV}="your-strong-password-here"')
        sys.exit(1)
    return pw


def check_cli() -> bool:
    code, out, err = run_cmd(["npx", "--yes", "@flop-labs/cli@0.7.0", "--version"])
    if code != 0:
        log(f"FLOP CLI not available: {err or out}", "err")
        return False
    log(f"FLOP CLI ready: {out or 'ok'}", "ok")
    return True


# ---------------------------------------------------------------------------
# Core actions
# ---------------------------------------------------------------------------

def generate_keystore(password: str) -> str | None:
    """Generate a new sr25519 keystore if it does not exist. Returns address."""
    if KEYSTORE_PATH.exists():
        log(f"Keystore already exists: {KEYSTORE_PATH}", "info")
        return inspect_address(password)

    log("Generating new keystore...", "info")
    cmd = [
        "npx", "--yes", "@flop-labs/cli@0.7.0",
        "--offline", "keys", "generate",
        "--type", "sr25519",
        "--name", f"flop-agent-{NETWORK}",
        "--out", str(KEYSTORE_PATH),
        "--password-env", PASSWORD_ENV,
    ]
    code, out, err = run_cmd(cmd, env={PASSWORD_ENV: password})
    if code != 0:
        log(f"Failed to generate keystore: {err or out}", "err")
        return None

    # Restrict permissions
    try:
        os.chmod(KEYSTORE_PATH, 0o600)
    except Exception:
        pass

    address = inspect_address(password)
    if address:
        log(f"Keystore created. Address: {address}", "ok")
    return address


def inspect_address(password: str) -> str | None:
    cmd = [
        "npx", "--yes", "@flop-labs/cli@0.7.0",
        "--offline", "keys", "inspect",
        str(KEYSTORE_PATH), "--json",
    ]
    code, out, err = run_cmd(cmd, env={PASSWORD_ENV: password})
    if code != 0:
        log(f"Failed to inspect keystore: {err or out}", "err")
        return None
    try:
        data = json.loads(out)
        # Different CLI versions may nest the address differently
        address = (
            data.get("address")
            or data.get("ss58Address")
            or data.get("publicKey")
            or (data.get("account") or {}).get("address")
        )
        if address:
            return address
        # Fallback: search for SS58-looking string
        match = re.search(r"5[a-zA-Z0-9]{47}", out)
        if match:
            return match.group(0)
    except Exception as e:
        log(f"Could not parse address: {e}", "warn")
    log(f"Raw inspect output: {out}", "warn")
    return None


def claim_faucet(address: str) -> bool:
    log(f"Requesting faucet for {address}...", "info")
    cmd = [
        "npx", "--yes", "@flop-labs/cli@0.7.0",
        "--network", NETWORK,
        "faucet", "request", address,
    ]
    code, out, err = run_cmd(cmd, timeout=90)
    combined = (out + "\n" + err).lower()
    if code == 0 or "success" in combined or "funded" in combined or "granted" in combined:
        log("Faucet claim submitted successfully", "ok")
        return True
    if "cooldown" in combined or "already" in combined or "wait" in combined or "24" in combined:
        log("Faucet still in cooldown (normal)", "warn")
        return False
    log(f"Faucet response: {out or err}", "warn")
    return False


def get_balance(address: str) -> float | None:
    cmd = [
        "npx", "--yes", "@flop-labs/cli@0.7.0",
        "--network", NETWORK,
        "balance", address,
    ]
    code, out, err = run_cmd(cmd)
    if code != 0:
        log(f"Balance check failed: {err or out}", "warn")
        return None
    # Try to extract a number
    match = re.search(r"([\d.]+)\s*FLOP", out, re.IGNORECASE)
    if match:
        return float(match.group(1))
    # Sometimes just a raw number
    match = re.search(r"([\d.]+)", out)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    log(f"Could not parse balance from: {out}", "warn")
    return None


def run_inference(password: str, max_flop: float) -> bool:
    prompt = random.choice(PROMPTS)
    log(f"Starting inference session (max {max_flop} FLOP)...", "info")
    cmd = [
        "npx", "--yes", "@flop-labs/cli@0.7.0",
        "--network", NETWORK,
        "--keystore", str(KEYSTORE_PATH),
        "--password-env", PASSWORD_ENV,
        "chat",
        "--max-flop", str(max_flop),
        prompt,
    ]
    code, out, err = run_cmd(cmd, env={PASSWORD_ENV: password}, timeout=180)
    if code == 0:
        log("Inference session completed", "ok")
        if out:
            # Show a short snippet
            snippet = out[:200].replace("\n", " ")
            log(f"Response snippet: {snippet}...", "info")
        return True
    log(f"Inference failed: {err or out}", "warn")
    return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def print_banner(state: dict):
    table = Table(title="FLOP Agent Bot", show_header=False, box=None)
    table.add_column(style="cyan")
    table.add_column()
    table.add_row("Network", NETWORK)
    table.add_row("Address", state.get("address") or "—")
    table.add_row("Sessions today", str(state.get("sessions_today", 0)))
    table.add_row("Total sessions", str(state.get("total_sessions", 0)))
    table.add_row("Keystore", str(KEYSTORE_PATH))
    console.print(Panel(table, border_style="green"))


def main():
    console.print(Panel.fit(
        "[bold green]FLOP Testnet Agent Bot[/bold green]\n"
        "Claim faucet → Spend on inference → Repeat 24/7",
        border_style="green",
    ))

    password = ensure_password()

    if not check_cli():
        console.print("[red]Install Node 22+ and try again.[/red]")
        sys.exit(1)

    state = load_state()

    # Ensure keystore
    if not state.get("address"):
        address = generate_keystore(password)
        if not address:
            log("Could not create or read keystore. Exiting.", "err")
            sys.exit(1)
        state["address"] = address
        save_state(state)
    else:
        # Verify we can still read it
        addr = inspect_address(password)
        if addr and addr != state["address"]:
            log(f"Address mismatch, updating to {addr}", "warn")
            state["address"] = addr
            save_state(state)

    print_banner(state)
    address = state["address"]
    log(f"Bot started for address {address}", "ok")
    log(f"Explorer: https://testnet.flopscan.io/ (search the address)", "info")

    while True:
        try:
            # Reset daily counter
            today = today_utc()
            if state.get("last_session_date") != today:
                state["sessions_today"] = 0
                state["last_session_date"] = today
                save_state(state)
                log("New UTC day – session counter reset", "info")

            # 1. Claim faucet if needed
            last_claim = state.get("last_claim")
            should_claim = True
            if last_claim:
                try:
                    last_dt = datetime.fromisoformat(last_claim)
                    hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                    if hours < CLAIM_COOLDOWN_HOURS:
                        should_claim = False
                except Exception:
                    pass

            if should_claim:
                if claim_faucet(address):
                    state["last_claim"] = datetime.now(timezone.utc).isoformat()
                    save_state(state)
                time.sleep(8)  # give the chain a moment

            # 2. Check balance
            balance = get_balance(address)
            if balance is not None:
                log(f"Current balance: {balance:.4f} FLOP", "info")
            else:
                log("Could not read balance, will try spend anyway", "warn")
                balance = 1.0  # optimistic

            # 3. Spend if we have enough and under daily limit
            if state["sessions_today"] >= MAX_SESSIONS_PER_DAY:
                log(f"Daily session limit reached ({MAX_SESSIONS_PER_DAY}). Sleeping...", "warn")
                time.sleep(LOOP_SLEEP_SECONDS * 3)
                continue

            if balance is not None and balance < MIN_BALANCE_TO_SPEND:
                log(f"Balance too low ({balance:.4f} < {MIN_BALANCE_TO_SPEND}). Waiting for faucet...", "warn")
                time.sleep(LOOP_SLEEP_SECONDS * 2)
                continue

            # Run one or more sessions
            sessions_this_cycle = 0
            while (
                state["sessions_today"] < MAX_SESSIONS_PER_DAY
                and sessions_this_cycle < 3
            ):
                success = run_inference(password, MAX_FLOP_PER_SESSION)
                if success:
                    state["sessions_today"] += 1
                    state["total_sessions"] += 1
                    state["total_spent_approx"] = state.get("total_spent_approx", 0) + MAX_FLOP_PER_SESSION
                    save_state(state)
                    sessions_this_cycle += 1
                    log(f"Sessions today: {state['sessions_today']}/{MAX_SESSIONS_PER_DAY}", "ok")
                else:
                    break
                time.sleep(SESSION_SLEEP_SECONDS)

            log(f"Cycle done. Sleeping {LOOP_SLEEP_SECONDS}s...", "info")
            time.sleep(LOOP_SLEEP_SECONDS)

        except KeyboardInterrupt:
            log("Stopped by user", "warn")
            break
        except Exception as e:
            log(f"Unexpected error: {e}", "err")
            time.sleep(60)


if __name__ == "__main__":
    main()
