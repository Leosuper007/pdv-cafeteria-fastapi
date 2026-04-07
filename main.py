from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import banco, estoque, vendas, pagamento
from datetime import date

app = FastAPI(title="Café PDV API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

banco.criar_tabelas()

# ─── MODELS ───────────────────────────────────────────────────────────────────

class ProdutoIn(BaseModel):
    nome: str
    preco: float
    estoque: int
    categoria: str = "Outros"
    emoji: str = "☕"

class ProdutoUpdate(BaseModel):
    nome: Optional[str] = None
    preco: Optional[float] = None
    estoque: Optional[int] = None
    categoria: Optional[str] = None
    emoji: Optional[str] = None

class ItemVenda(BaseModel):
    produto_id: int
    quantidade: int

class VendaIn(BaseModel):
    itens: List[ItemVenda]
    forma_pagamento: str
    origem: str = "caixa"   # caixa | totem

class PixReq(BaseModel):
    venda_id: int
    valor: float
    descricao: str = ""

class CartaoReq(BaseModel):
    venda_id: int
    valor: float
    token: str
    installments: int = 1
    payment_method_id: str = "visa"
    payer_email: str = "cliente@cafeteria.com"

# ─── PRODUTOS ────────────────────────────────────────────────────────────────

@app.get("/produtos")
def get_produtos():
    return estoque.listar_produtos()

@app.post("/produtos", status_code=201)
def post_produto(p: ProdutoIn):
    pid = estoque.cadastrar_produto(p.nome, p.preco, p.estoque, p.categoria, p.emoji)
    return {"id": pid, "mensagem": "Produto cadastrado"}

@app.put("/produtos/{pid}")
def put_produto(pid: int, p: ProdutoUpdate):
    ok = estoque.atualizar_produto(pid, p.dict(exclude_none=True))
    if not ok:
        raise HTTPException(404, "Produto não encontrado")
    return {"mensagem": "Atualizado"}

@app.delete("/produtos/{pid}")
def del_produto(pid: int):
    ok = estoque.deletar_produto(pid)
    if not ok:
        raise HTTPException(404, "Produto não encontrado")
    return {"mensagem": "Removido"}

# ─── VENDAS ──────────────────────────────────────────────────────────────────

@app.post("/vendas")
def post_venda(v: VendaIn):
    itens = [i.dict() for i in v.itens]
    resultado = vendas.registrar_venda(itens, v.forma_pagamento, v.origem)
    if not resultado["ok"]:
        raise HTTPException(400, resultado["erro"])
    return resultado

@app.get("/vendas")
def get_vendas(
    data: Optional[str] = Query(None, description="YYYY-MM-DD"),
    status: Optional[str] = Query(None),
    todas: bool = Query(False, description="Se true, ignora filtro de data")
):
    if todas:
        return vendas.listar_vendas_todas()
    return vendas.listar_vendas(data_filtro=data, status_filtro=status)

@app.get("/vendas/{vid}")
def get_venda(vid: int):
    v = vendas.buscar_venda(vid)
    if not v:
        raise HTTPException(404, "Venda não encontrada")
    return v

@app.patch("/vendas/{vid}/confirmar")
def patch_confirmar(vid: int, payment_id: str = ""):
    vendas.confirmar_venda(vid, payment_id)
    return {"mensagem": "Confirmada"}

@app.patch("/vendas/{vid}/pago")
def patch_pago(vid: int, payment_id: str = ""):
    """Registra pagamento e mantém status pendente — cozinha verá o pedido."""
    vendas.marcar_pago(vid, payment_id)
    return {"mensagem": "Pagamento registrado"}

@app.patch("/vendas/{vid}/cancelar")
def patch_cancelar(vid: int):
    vendas.cancelar_venda(vid)
    return {"mensagem": "Cancelada"}

# ─── COZINHA ─────────────────────────────────────────────────────────────────

@app.get("/cozinha/pedidos")
def get_pedidos_cozinha():
    return vendas.listar_pedidos_cozinha()

@app.patch("/cozinha/pedidos/{vid}")
def patch_pedido_cozinha(vid: int, body: dict):
    status = body.get("status", "")
    if status not in ("pendente", "preparando", "pronto", "concluida"):
        raise HTTPException(400, "Status inválido")
    vendas.atualizar_status_pedido(vid, status)
    return {"mensagem": f"Status atualizado para {status}"}

@app.patch("/cozinha/pedidos/{vid}/status")
def patch_status_pedido(vid: int, status: str = Query(...)):
    if status not in ("pendente", "preparando", "pronto", "concluida"):
        raise HTTPException(400, "Status inválido")
    vendas.atualizar_status_pedido(vid, status)
    return {"mensagem": f"Status atualizado para {status}"}

# ─── PAGAMENTOS ──────────────────────────────────────────────────────────────

@app.post("/pagamentos/pix")
def post_pix(req: PixReq):
    r = pagamento.gerar_pix(req.venda_id, req.valor, req.descricao)
    if not r["ok"]:
        raise HTTPException(400, r["erro"])
    return r

@app.post("/pagamentos/cartao")
def post_cartao(req: CartaoReq):
    r = pagamento.pagar_cartao(
        req.venda_id, req.valor, req.token,
        req.installments, req.payment_method_id, req.payer_email
    )
    if not r["ok"]:
        raise HTTPException(400, r["erro"])
    return r

@app.get("/pagamentos/status/{charge_id}")
def get_status(charge_id: str):
    return pagamento.consultar_status(charge_id)

@app.post("/webhook/pagbank")
async def webhook_pagbank(payload: dict):
    resultado = pagamento.processar_webhook(payload)
    if resultado["pago"] and resultado["venda_id"]:
        vendas.confirmar_venda(resultado["venda_id"], resultado["charge_id"])
    return {"ok": True}

# ─── DASHBOARD E RELATÓRIOS ──────────────────────────────────────────────────

@app.get("/dashboard")
def get_dashboard(data: Optional[str] = Query(None)):
    return vendas.resumo_dashboard(data_filtro=data)

@app.get("/relatorios/periodo")
def get_relatorio_periodo(
    inicio: str = Query(..., description="YYYY-MM-DD"),
    fim: str = Query(..., description="YYYY-MM-DD")
):
    return vendas.relatorio_periodo(inicio, fim)

@app.get("/relatorios/mensal")
def get_relatorio_mensal(
    ano: int = Query(..., description="Ex: 2026"),
    mes: int = Query(..., description="1-12")
):
    if not (1 <= mes <= 12):
        raise HTTPException(400, "Mês deve ser entre 1 e 12")
    return vendas.relatorio_mensal(ano, mes)

@app.get("/relatorios/anual")
def get_relatorio_anual(ano: int = Query(..., description="Ex: 2026")):
    return vendas.relatorio_anual(ano)

@app.get("/relatorios/dia")
def get_resumo_dia(data: Optional[str] = Query(None, description="YYYY-MM-DD")):
    return vendas.resumo_por_dia(data)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    import uvicorn

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=8000,
        reload=False,
        workers=1,
        access_log=False,
        use_colors=False,
        log_config=None,
        loop="asyncio"
    )

    server = uvicorn.Server(config)
    server.run()