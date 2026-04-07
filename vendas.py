from banco import conectar
from datetime import datetime, date
import calendar

# ─────────────────────────────────────────────────────────────────────────────
# REGISTRAR / CONFIRMAR / CANCELAR
# ─────────────────────────────────────────────────────────────────────────────

def registrar_venda(itens: list, forma_pagamento: str, origem: str = "caixa"):
    conn = conectar()
    c = conn.cursor()
    total = 0.0
    itens_completos = []

    for item in itens:
        c.execute("SELECT id,nome,preco,estoque FROM produtos WHERE id=?", (item["produto_id"],))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"ok": False, "erro": f"Produto ID {item['produto_id']} não encontrado"}
        pid, nome, preco, estoque = row
        if estoque < item["quantidade"]:
            conn.close()
            return {"ok": False, "erro": f"Estoque insuficiente para '{nome}'"}
        subtotal = preco * item["quantidade"]
        total += subtotal
        itens_completos.append((pid, nome, preco, item["quantidade"], subtotal))

    c.execute(
        "INSERT INTO vendas (total,forma_pagamento,status,data,origem) VALUES (?,?,?,?,?)",
        (total, forma_pagamento, "pendente", datetime.now().isoformat(), origem)
    )
    venda_id = c.lastrowid

    for pid, nome, preco, qtd, sub in itens_completos:
        c.execute(
            "INSERT INTO itens_venda (venda_id,produto_id,nome,preco,quantidade,subtotal) VALUES (?,?,?,?,?,?)",
            (venda_id, pid, nome, preco, qtd, sub)
        )
        c.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?", (qtd, pid))

    conn.commit()
    conn.close()
    return {"ok": True, "venda_id": venda_id, "total": total}


def confirmar_venda(venda_id: int, payment_id: str):
    conn = conectar()
    c = conn.cursor()
    c.execute("UPDATE vendas SET status='concluida', payment_id=? WHERE id=?", (payment_id, venda_id))
    conn.commit()
    conn.close()


def marcar_pago(venda_id: int, payment_id: str):
    """Salva o payment_id mas mantém status pendente — pedido fica na cozinha."""
    conn = conectar()
    c = conn.cursor()
    c.execute("UPDATE vendas SET payment_id=? WHERE id=?", (payment_id, venda_id))
    conn.commit()
    conn.close()


def cancelar_venda(venda_id: int):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT produto_id, quantidade FROM itens_venda WHERE venda_id=?", (venda_id,))
    itens = c.fetchall()
    for pid, qtd in itens:
        c.execute("UPDATE produtos SET estoque=estoque+? WHERE id=?", (qtd, pid))
    c.execute("UPDATE vendas SET status='cancelada' WHERE id=?", (venda_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# LISTAGENS
# ─────────────────────────────────────────────────────────────────────────────

def listar_vendas(data_filtro: str = None, status_filtro: str = None, limit: int = 500):
    conn = conectar()
    c = conn.cursor()
    query = "SELECT id,total,forma_pagamento,status,payment_id,data,origem FROM vendas WHERE 1=1"
    params = []

    if data_filtro:
        query += " AND date(data) = ?"
        params.append(data_filtro)
    else:
        query += " AND date(data) = ?"
        params.append(date.today().isoformat())

    if status_filtro:
        query += " AND status = ?"
        params.append(status_filtro)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [{"id":r[0],"total":r[1],"forma_pagamento":r[2],"status":r[3],
             "payment_id":r[4],"data":r[5],"origem":r[6] if len(r)>6 else "caixa"} for r in rows]


def listar_vendas_todas(data_inicio: str = None, data_fim: str = None):
    conn = conectar()
    c = conn.cursor()
    query = "SELECT id,total,forma_pagamento,status,payment_id,data,origem FROM vendas WHERE status='concluida'"
    params = []
    if data_inicio:
        query += " AND date(data) >= ?"
        params.append(data_inicio)
    if data_fim:
        query += " AND date(data) <= ?"
        params.append(data_fim)
    query += " ORDER BY data DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [{"id":r[0],"total":r[1],"forma_pagamento":r[2],"status":r[3],
             "payment_id":r[4],"data":r[5],"origem":r[6] if len(r)>6 else "caixa"} for r in rows]


def buscar_venda(venda_id: int):
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT id,total,forma_pagamento,status,payment_id,data,origem FROM vendas WHERE id=?", (venda_id,))
    v = c.fetchone()
    if not v:
        conn.close()
        return None
    c.execute("SELECT nome,preco,quantidade,subtotal FROM itens_venda WHERE venda_id=?", (venda_id,))
    itens = [{"nome":i[0],"preco":i[1],"quantidade":i[2],"subtotal":i[3]} for i in c.fetchall()]
    conn.close()
    return {"id":v[0],"total":v[1],"forma_pagamento":v[2],"status":v[3],
            "payment_id":v[4],"data":v[5],"origem":v[6] if len(v)>6 else "caixa","itens":itens}


# ─────────────────────────────────────────────────────────────────────────────
# COZINHA — só pedidos de HOJE com status pendente ou preparando
# ─────────────────────────────────────────────────────────────────────────────

def listar_pedidos_cozinha():
    conn = conectar()
    c = conn.cursor()
    hoje = date.today().isoformat()
    c.execute("""
        SELECT v.id, v.status, v.data, v.origem,
               GROUP_CONCAT(iv.nome || '|' || iv.quantidade, ';;') as itens_str
        FROM vendas v
        JOIN itens_venda iv ON iv.venda_id = v.id
        WHERE v.status IN ('pendente','preparando')
          AND date(v.data) = ?
        GROUP BY v.id
        ORDER BY v.id ASC
    """, (hoje,))
    rows = c.fetchall()
    conn.close()

    pedidos = []
    for r in rows:
        itens = []
        if r[4]:
            for item_str in r[4].split(';;'):
                parts = item_str.split('|')
                if len(parts) == 2:
                    itens.append({"nome": parts[0], "quantidade": int(parts[1])})
        pedidos.append({
            "id": r[0], "status": r[1], "data": r[2],
            "origem": r[3] if r[3] else "caixa", "itens": itens
        })
    return pedidos


def atualizar_status_pedido(venda_id: int, novo_status: str):
    conn = conectar()
    c = conn.cursor()
    c.execute("UPDATE vendas SET status=? WHERE id=?", (novo_status, venda_id))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def resumo_dashboard(data_filtro: str = None):
    conn = conectar()
    c = conn.cursor()

    if not data_filtro:
        data_filtro = date.today().isoformat()

    c.execute("SELECT COALESCE(SUM(total),0) FROM vendas WHERE status='concluida' AND date(data)=?", (data_filtro,))
    total_hoje = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vendas WHERE status='concluida' AND date(data)=?", (data_filtro,))
    qtd_hoje = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(total),0) FROM vendas WHERE status='concluida'")
    total_geral = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vendas WHERE status='concluida'")
    qtd_geral = c.fetchone()[0]
    c.execute("""
        SELECT iv.nome, SUM(iv.quantidade) as qtd
        FROM itens_venda iv JOIN vendas v ON v.id=iv.venda_id
        WHERE v.status='concluida' AND date(v.data)=?
        GROUP BY iv.nome ORDER BY qtd DESC LIMIT 5
    """, (data_filtro,))
    mais_vendidos = [{"nome":r[0],"quantidade":r[1]} for r in c.fetchall()]
    c.execute("""
        SELECT forma_pagamento, COUNT(*) as qtd, SUM(total) as total
        FROM vendas WHERE status='concluida' AND date(data)=?
        GROUP BY forma_pagamento
    """, (data_filtro,))
    por_pagamento = [{"forma":r[0],"qtd":r[1],"total":r[2]} for r in c.fetchall()]
    conn.close()
    return {
        "data": data_filtro, "total_vendas": total_hoje,
        "qtd_vendas": qtd_hoje, "total_geral": total_geral,
        "qtd_geral": qtd_geral, "mais_vendidos": mais_vendidos,
        "por_pagamento": por_pagamento
    }


# ─────────────────────────────────────────────────────────────────────────────
# RELATÓRIOS — por período / mês / ano
# ─────────────────────────────────────────────────────────────────────────────

def relatorio_periodo(data_inicio: str, data_fim: str):
    """Relatório dia a dia entre duas datas"""
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        SELECT date(data) as dia,
               COUNT(*) as qtd,
               SUM(total) as total,
               SUM(CASE WHEN forma_pagamento='pix' THEN total ELSE 0 END) as total_pix,
               SUM(CASE WHEN forma_pagamento='dinheiro' THEN total ELSE 0 END) as total_dinheiro,
               SUM(CASE WHEN forma_pagamento LIKE 'cartao%' THEN total ELSE 0 END) as total_cartao
        FROM vendas
        WHERE status='concluida' AND date(data) BETWEEN ? AND ?
        GROUP BY dia ORDER BY dia DESC
    """, (data_inicio, data_fim))
    rows = c.fetchall()
    conn.close()
    return [{"data":r[0],"qtd":r[1],"total":r[2],"pix":r[3],"dinheiro":r[4],"cartao":r[5]} for r in rows]


def relatorio_mensal(ano: int, mes: int):
    """Relatório completo de um mês"""
    data_inicio = f"{ano:04d}-{mes:02d}-01"
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    data_fim = f"{ano:04d}-{mes:02d}-{ultimo_dia:02d}"
    dias = relatorio_periodo(data_inicio, data_fim)

    conn = conectar()
    c = conn.cursor()
    c.execute("""
        SELECT iv.nome, SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as receita
        FROM itens_venda iv JOIN vendas v ON v.id=iv.venda_id
        WHERE v.status='concluida'
          AND strftime('%Y-%m', v.data) = ?
        GROUP BY iv.nome ORDER BY qtd DESC LIMIT 10
    """, (f"{ano:04d}-{mes:02d}",))
    top_produtos = [{"nome":r[0],"qtd":r[1],"receita":r[2]} for r in c.fetchall()]

    c.execute("""
        SELECT forma_pagamento, COUNT(*) as qtd, SUM(total) as total
        FROM vendas
        WHERE status='concluida' AND strftime('%Y-%m', data) = ?
        GROUP BY forma_pagamento
    """, (f"{ano:04d}-{mes:02d}",))
    por_pagamento = [{"forma":r[0],"qtd":r[1],"total":r[2]} for r in c.fetchall()]
    conn.close()

    total_mes = sum(d["total"] or 0 for d in dias)
    qtd_mes = sum(d["qtd"] or 0 for d in dias)
    return {
        "ano": ano, "mes": mes,
        "total": total_mes, "qtd": qtd_mes,
        "dias": dias, "top_produtos": top_produtos, "por_pagamento": por_pagamento
    }


def relatorio_anual(ano: int):
    """Resumo mês a mês de um ano"""
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        SELECT strftime('%Y-%m', data) as mes,
               COUNT(*) as qtd,
               SUM(total) as total,
               SUM(CASE WHEN forma_pagamento='pix' THEN total ELSE 0 END) as total_pix,
               SUM(CASE WHEN forma_pagamento='dinheiro' THEN total ELSE 0 END) as total_dinheiro,
               SUM(CASE WHEN forma_pagamento LIKE 'cartao%' THEN total ELSE 0 END) as total_cartao
        FROM vendas
        WHERE status='concluida' AND strftime('%Y', data) = ?
        GROUP BY mes ORDER BY mes ASC
    """, (str(ano),))
    rows = c.fetchall()
    conn.close()
    meses = [{"mes":r[0],"qtd":r[1],"total":r[2],"pix":r[3],"dinheiro":r[4],"cartao":r[5]} for r in rows]
    total_ano = sum(m["total"] or 0 for m in meses)
    qtd_ano = sum(m["qtd"] or 0 for m in meses)
    return {"ano": ano, "total": total_ano, "qtd": qtd_ano, "meses": meses}


def resumo_por_dia(data: str = None):
    """Resumo de um dia com detalhamento por hora e produtos"""
    if not data:
        data = date.today().isoformat()
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        SELECT strftime('%H', data) as hora, COUNT(*) as qtd, SUM(total) as total
        FROM vendas WHERE status='concluida' AND date(data) = ?
        GROUP BY hora ORDER BY hora ASC
    """, (data,))
    por_hora = [{"hora":r[0],"qtd":r[1],"total":r[2]} for r in c.fetchall()]
    c.execute("""
        SELECT iv.nome, SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as receita
        FROM itens_venda iv JOIN vendas v ON v.id=iv.venda_id
        WHERE v.status='concluida' AND date(v.data) = ?
        GROUP BY iv.nome ORDER BY qtd DESC
    """, (data,))
    produtos = [{"nome":r[0],"qtd":r[1],"receita":r[2]} for r in c.fetchall()]
    conn.close()
    return {"data": data, "por_hora": por_hora, "produtos": produtos}
