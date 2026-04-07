"""
resetar_produtos.py
===================
Apaga APENAS os produtos do banco e recria com o cardápio novo.
As vendas históricas NÃO são apagadas.

Como usar: python resetar_produtos.py
"""
import sqlite3

DB_PATH = "cafeteria.db"

print("\n" + "="*50)
print("  RESETAR PRODUTOS — Cafeteria Grão")
print("="*50)
print("\n  ⚠️  Isso vai APAGAR todos os produtos atuais")
print("  e recarregar o cardápio novo.")
print("  As vendas históricas serão mantidas.\n")
print("  Continuar? (s/n): ", end="")
resp = input().strip().lower()
if resp != "s":
    print("  Cancelado.\n")
    exit()

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Apaga só os produtos
c.execute("DELETE FROM produtos")
print("\n  ✓ Produtos antigos removidos.")

# Insere o cardápio novo
seed = [
    # ── BEBIDAS ──────────────────────────────────────────────────────
    ("Café Coado",                   10.90, 100, "Bebidas",  "☕"),
    ("Café Espresso",                 5.90, 100, "Bebidas",  "☕"),
    ("Duplo",                         9.90,  80, "Bebidas",  "☕"),
    ("Cappuccino Italiano",          13.90,  80, "Bebidas",  "🫖"),
    ("Cappuccino",                   16.90,  80, "Bebidas",  "🫖"),
    ("Mocha Quente",                 12.90,  60, "Bebidas",  "🍫"),
    ("Soda Italiana",                16.90,  50, "Bebidas",  "🥤"),
    ("Café Gelado",                  16.90,  50, "Bebidas",  "☕"),
    ("Chá Gelado",                    9.90,  40, "Bebidas",  "🍵"),
    ("Milk Shake",                   16.90,  40, "Bebidas",  "🥛"),
    ("Chocolate Quente P",            9.90,  60, "Bebidas",  "🍫"),
    ("Chocolate Quente G",           13.90,  60, "Bebidas",  "🍫"),
    ("Suco de Polpa (Água)",          9.90,  40, "Bebidas",  "🥤"),
    ("Suco de Polpa (Leite)",        10.90,  40, "Bebidas",  "🥤"),
    ("Refrigerante",                  8.00,  80, "Bebidas",  "🥤"),
    ("Água Sem Gás",                  5.00, 100, "Bebidas",  "💧"),
    ("Água Com Gás",                  5.50,  80, "Bebidas",  "💧"),
    ("Budweiser 330ml",              12.90,  40, "Bebidas",  "🍺"),
    ("Heineken 330ml",               13.90,  40, "Bebidas",  "🍺"),
    ("Império Ultra 275ml",          11.90,  40, "Bebidas",  "🍺"),
    # ── DOCES ────────────────────────────────────────────────────────
    ("Fatias de Tortas",             19.90,  20, "Doces",    "🎂"),
    ("Fatia de Bolo",                 6.90,  30, "Doces",    "🍰"),
    ("Cookies",                       8.00,  30, "Doces",    "🍪"),
    ("Tortinha",                      9.90,  20, "Doces",    "🥧"),
    ("Kit Kate",                      6.00,  30, "Doces",    "🍫"),
    ("Chokito",                       6.00,  30, "Doces",    "🍫"),
    ("Bis",                           6.00,  30, "Doces",    "🍫"),
    ("Snickers",                      6.00,  30, "Doces",    "🍫"),
    ("Pirulito Pop",                  1.00,  50, "Doces",    "🍭"),
    # ── MASSAS ───────────────────────────────────────────────────────
    ("Lasanha",                      24.90,  20, "Massas",   "🍝"),
    ("Kit com 3 Panquecas",          22.90,  20, "Massas",   "🥞"),
    ("Escondidinho",                 24.90,  20, "Massas",   "🍲"),
    # ── SALGADOS ─────────────────────────────────────────────────────
    ("Coxinha",                      13.90,  40, "Salgados", "🍗"),
    ("Croissant",                    13.90,  30, "Salgados", "🥐"),
    ("Empada",                       13.90,  30, "Salgados", "🥧"),
    ("Enrolado de Salsicha",         13.90,  30, "Salgados", "🌭"),
    ("Fatia de Torta de Frango",      0.00,  20, "Salgados", "🥧"),
    ("Folhados",                     13.90,  30, "Salgados", "🥐"),
    ("Guiche",                       11.90,  30, "Salgados", "🥪"),
    ("Pão de Queijo Mineiro (unid)",  2.90,  60, "Salgados", "🧀"),
    ("Pão de Queijo do Reino (unid)", 3.90,  40, "Salgados", "🧀"),
]

c.executemany(
    "INSERT INTO produtos (nome,preco,estoque,categoria,emoji) VALUES (?,?,?,?,?)",
    seed
)
conn.commit()
conn.close()

print(f"  ✓ {len(seed)} produtos do cardápio novo carregados!")
print("\n  ✅ Pronto! Reinicie o sistema (INICIAR.bat).\n")
