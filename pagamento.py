"""
pagamento.py — Integração com PagBank
--------------------------------------
Documentação oficial: https://developers.pagbank.com.br
"""

import os
import uuid
import base64
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN    = os.getenv("PAGBANK_TOKEN", "SEU_TOKEN_AQUI")
ENV      = os.getenv("PAGBANK_ENV", "sandbox")
BASE_URL = "https://sandbox.api.pagseguro.com" if ENV == "sandbox" else "https://api.pagseguro.com"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type":  "application/json",
    "accept":        "application/json",
}


# ─── PIX ─────────────────────────────────────────────────────────────────────

def gerar_pix(venda_id: int, valor: float, descricao: str) -> dict:
    valor_centavos = int(round(valor * 100))
    expiracao = (datetime.utcnow() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S-03:00")

    payload = {
        "reference_id": f"venda-{venda_id}-{uuid.uuid4().hex[:8]}",
        "customer": {
            "name": "Cliente Cafeteria",
            "email": "cliente@cafeteria.com",
            "tax_id": "12345678909",
        },
        "items": [{"name": descricao or f"Venda #{venda_id}", "quantity": 1, "unit_amount": valor_centavos}],
        "qr_codes": [{"amount": {"value": valor_centavos}, "expiration_date": expiracao}],
        "notification_urls": [],
    }

    try:
        resp = requests.post(f"{BASE_URL}/orders", json=payload, headers=HEADERS, timeout=15)
        data = resp.json()

        # ── DEBUG ── remove depois que funcionar
        print(f"\n{'='*60}")
        print(f"PAGBANK URL: {BASE_URL}/orders")
        print(f"PAGBANK STATUS: {resp.status_code}")
        print(f"PAGBANK RESPOSTA: {data}")
        print(f"{'='*60}\n")

        if resp.status_code in (200, 201):
            qr = data.get("qr_codes", [{}])[0]
            links = qr.get("links", [])
            png_url = next((l["href"] for l in links if l.get("media") == "image/png"), "")

            qr_base64 = ""
            if png_url:
                try:
                    img = requests.get(png_url, timeout=10)
                    qr_base64 = base64.b64encode(img.content).decode()
                except Exception:
                    pass

            return {
                "ok": True,
                "charge_id": qr.get("id", ""),
                "order_id": data.get("id", ""),
                "qr_code": qr.get("text", ""),
                "qr_code_base64": qr_base64,
                "expiracao": expiracao,
                "status": qr.get("status", "WAITING"),
            }
        return {"ok": False, "erro": _extrair_erro(data), "detalhe": data}

    except requests.exceptions.Timeout:
        return {"ok": False, "erro": "Timeout ao conectar no PagBank"}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# ─── CARTÃO ──────────────────────────────────────────────────────────────────

def pagar_cartao(venda_id: int, valor: float, encrypted_card: str,
                 installments: int = 1, payer_name: str = "Cliente",
                 payer_cpf: str = "00000000000", payer_email: str = "cliente@cafeteria.com",
                 payer_phone: str = "11999999999") -> dict:
    valor_centavos = int(round(valor * 100))

    payload = {
        "reference_id": f"venda-{venda_id}-{uuid.uuid4().hex[:8]}",
        "customer": {
            "name": payer_name, "email": payer_email, "tax_id": payer_cpf,
            "phones": [{"country": "55", "area": payer_phone[:2], "number": payer_phone[2:], "type": "MOBILE"}],
        },
        "items": [{"name": f"Pedido #{venda_id}", "quantity": 1, "unit_amount": valor_centavos}],
        "charges": [{
            "reference_id": f"charge-{venda_id}",
            "description": f"Cafeteria - Pedido #{venda_id}",
            "amount": {"value": valor_centavos, "currency": "BRL"},
            "payment_method": {
                "type": "CREDIT_CARD",
                "installments": installments,
                "capture": True,
                "card": {"encrypted": encrypted_card, "holder": {"name": payer_name}, "store": False},
            },
        }],
    }

    try:
        resp = requests.post(f"{BASE_URL}/orders", json=payload, headers=HEADERS, timeout=15)
        data = resp.json()

        # ── DEBUG ──
        print(f"\n{'='*60}")
        print(f"PAGBANK CARTAO STATUS: {resp.status_code}")
        print(f"PAGBANK CARTAO RESPOSTA: {data}")
        print(f"{'='*60}\n")

        if resp.status_code in (200, 201):
            charge = (data.get("charges") or [{}])[0]
            status = charge.get("status", "")
            return {
                "ok": status in ("PAID", "AUTHORIZED"),
                "charge_id": charge.get("id", ""),
                "order_id": data.get("id", ""),
                "status": status,
                "mensagem": _status_cartao(status),
            }
        return {"ok": False, "erro": _extrair_erro(data), "detalhe": data}

    except requests.exceptions.Timeout:
        return {"ok": False, "erro": "Timeout ao conectar no PagBank"}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# ─── STATUS (polling do Pix) ──────────────────────────────────────────────────

def consultar_status(charge_id: str) -> dict:
    try:
        resp = requests.get(f"{BASE_URL}/charges/{charge_id}", headers=HEADERS, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            status = data.get("status", "")
            return {"ok": True, "charge_id": charge_id, "status": status,
                    "pago": status == "PAID", "mensagem": _status_msg(status)}
        return {"ok": False, "erro": "Cobrança não encontrada"}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# ─── WEBHOOK ─────────────────────────────────────────────────────────────────

def processar_webhook(payload: dict) -> dict:
    charge = (payload.get("charges") or [{}])[0]
    status = charge.get("status", "")
    ref    = charge.get("reference_id", "")

    venda_id = None
    if ref and "-" in ref:
        try:
            venda_id = int(ref.split("-")[1])
        except ValueError:
            pass

    return {
        "evento":    payload.get("type", ""),
        "charge_id": charge.get("id", ""),
        "status":    status,
        "pago":      status == "PAID",
        "venda_id":  venda_id,
    }


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _extrair_erro(data: dict) -> str:
    erros = data.get("error_messages", [])
    if erros:
        return " | ".join(e.get("description", str(e)) for e in erros)
    return data.get("message", data.get("error", "Erro desconhecido no PagBank"))

def _status_msg(s):
    return {"WAITING":"Aguardando pagamento...","PAID":"Pagamento confirmado!",
            "DECLINED":"Recusado","CANCELED":"Cancelado","REFUNDED":"Estornado"}.get(s, s)

def _status_cartao(s):
    return {"PAID":"Cartão aprovado!","AUTHORIZED":"Autorizado!",
            "DECLINED":"Cartão recusado. Tente outro.","CANCELED":"Cancelado"}.get(s, s)
