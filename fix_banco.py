import sqlite3

conn = sqlite3.connect('cafeteria.db')
try:
    conn.execute("ALTER TABLE vendas ADD COLUMN origem TEXT DEFAULT 'caixa'")
    conn.commit()
    print("Coluna origem adicionada com sucesso!")
except Exception as e:
    print("Aviso:", e)
conn.close()