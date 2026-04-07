from banco import conectar

def listar_produtos():
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT id,nome,preco,estoque,categoria,emoji FROM produtos ORDER BY categoria,nome")
    rows = c.fetchall()
    conn.close()
    return [{"id":r[0],"nome":r[1],"preco":r[2],"estoque":r[3],"categoria":r[4],"emoji":r[5]} for r in rows]

def cadastrar_produto(nome, preco, qtd, categoria="Outros", emoji="☕"):
    conn = conectar()
    c = conn.cursor()
    c.execute("INSERT INTO produtos (nome,preco,estoque,categoria,emoji) VALUES (?,?,?,?,?)",
              (nome, preco, qtd, categoria, emoji))
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid

def atualizar_produto(produto_id: int, campos: dict):
    if not campos:
        return False
    conn = conectar()
    c = conn.cursor()
    set_sql = ", ".join(f"{k}=?" for k in campos)
    vals = list(campos.values()) + [produto_id]
    c.execute(f"UPDATE produtos SET {set_sql} WHERE id=?", vals)
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    return ok

def deletar_produto(produto_id: int):
    conn = conectar()
    c = conn.cursor()
    c.execute("DELETE FROM produtos WHERE id=?", (produto_id,))
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    return ok

def reduzir_estoque(produto_id: int, quantidade: int) -> bool:
    conn = conectar()
    c = conn.cursor()
    c.execute("SELECT estoque FROM produtos WHERE id=?", (produto_id,))
    row = c.fetchone()
    if not row or row[0] < quantidade:
        conn.close()
        return False
    c.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?", (quantidade, produto_id))
    conn.commit()
    conn.close()
    return True
