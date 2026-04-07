import sqlite3

DB_PATH = "cafeteria.db"

def conectar():
    return sqlite3.connect(DB_PATH)

def criar_tabelas():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        nome      TEXT    NOT NULL,
        preco     REAL    NOT NULL,
        estoque   INTEGER NOT NULL DEFAULT 0,
        categoria TEXT    NOT NULL DEFAULT 'Outros',
        emoji     TEXT    NOT NULL DEFAULT '☕'
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS vendas (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        total           REAL    NOT NULL,
        forma_pagamento TEXT    NOT NULL,
        status          TEXT    NOT NULL DEFAULT 'pendente',
        payment_id      TEXT,
        data            TEXT    NOT NULL
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS itens_venda (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id   INTEGER NOT NULL,
        produto_id INTEGER NOT NULL,
        nome       TEXT    NOT NULL,
        preco      REAL    NOT NULL,
        quantidade INTEGER NOT NULL,
        subtotal   REAL    NOT NULL,
        FOREIGN KEY (venda_id) REFERENCES vendas(id)
    )""")

    # Seed inicial de produtos
    c.execute("SELECT COUNT(*) FROM produtos")
    if c.fetchone()[0] == 0:
        seed = [
            ("Café Expresso",     6.50,  100, "Cafés",   "☕"),
            ("Cappuccino",        9.90,   80, "Cafés",   "🫖"),
            ("Latte",            10.90,   60, "Cafés",   "🥛"),
            ("Mocha",            12.90,   50, "Cafés",   "🧋"),
            ("Café com Leite",    7.50,   90, "Cafés",   "☕"),
            ("Chocolate Quente",  9.50,   40, "Bebidas",  "🍫"),
            ("Chá Verde",         6.00,   50, "Bebidas",  "🍵"),
            ("Suco Natural",      8.50,   30, "Bebidas",  "🥤"),
            ("Água Mineral",      3.50,  120, "Bebidas",  "💧"),
            ("Pão de Queijo",     4.50,   60, "Lanches",  "🧀"),
            ("Coxinha",           6.00,   45, "Lanches",  "🍗"),
            ("Misto Quente",      7.00,   35, "Lanches",  "🥪"),
            ("Brownie",           8.00,   25, "Doces",    "🍫"),
            ("Cheesecake",       10.00,   20, "Doces",    "🍰"),
        ]
        c.executemany(
            "INSERT INTO produtos (nome,preco,estoque,categoria,emoji) VALUES (?,?,?,?,?)",
            seed
        )

    # Migrações
    try:
        c.execute("ALTER TABLE vendas ADD COLUMN origem TEXT DEFAULT 'caixa'")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE vendas ADD COLUMN mesa INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    conn.close()
