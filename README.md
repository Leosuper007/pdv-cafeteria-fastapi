# ☕ Café PDV — Sistema Completo

## Arquitetura

```
cafe-pdv/
├── backend/          ← Python + FastAPI
│   ├── main.py       ← API REST (porta 8000)
│   ├── banco.py      ← SQLite + seed de produtos
│   ├── estoque.py    ← CRUD de produtos
│   ├── vendas.py     ← Registro e histórico de vendas
│   ├── pagamento.py  ← Mercado Pago (Pix + Cartão)
│   └── requirements.txt
│
└── frontend/
    └── index.html    ← React-like SPA (abre direto no navegador)
```

---

## 1. Configurar Backend

```bash
cd backend
pip install -r requirements.txt
```

### Configurar Mercado Pago

1. Crie uma conta em https://www.mercadopago.com.br/developers
2. Vá em **Credenciais** e copie seu **Access Token**
   - Sandbox (testes): começa com `TEST-`
   - Produção: começa com `APP_USR-`
3. Defina a variável de ambiente:

```bash
# Linux/Mac
export MP_ACCESS_TOKEN="TEST-xxxxxxxxxxxxxxxxxxxx"

# Windows
set MP_ACCESS_TOKEN=TEST-xxxxxxxxxxxxxxxxxxxx

# Ou crie um arquivo .env na pasta backend:
echo "MP_ACCESS_TOKEN=TEST-xxxx" > .env
```

### Iniciar servidor

```bash
cd backend
python main.py
# API disponível em http://localhost:8000
# Docs automáticas em http://localhost:8000/docs
```

---

## 2. Abrir Frontend

Abra o arquivo `frontend/index.html` direto no navegador.  
Não precisa de npm, Vite ou nada — é um único arquivo HTML.

---

## 3. Como funciona cada pagamento

### 💵 Dinheiro
- Registra a venda e confirma imediatamente.

### 📱 Pix
1. Venda é registrada com status `pendente`
2. API chama Mercado Pago → gera QR Code + código copia-cola
3. Frontend exibe o QR Code para o cliente escanear
4. A cada 5 segundos consulta o status no Mercado Pago
5. Quando `approved` → confirma a venda automaticamente

### 💳 Cartão (Produção)
Para cartão em produção, integre o **MercadoPago.js** no frontend:

```html
<!-- Adicione no <head> do index.html -->
<script src="https://sdk.mercadopago.com/js/v2"></script>

<script>
  const mp = new MercadoPago('SUA_PUBLIC_KEY');
  const cardForm = mp.cardForm({
    amount: String(total),
    form: { id: "form-checkout", ... },
    callbacks: {
      onFormMounted: (error) => { ... },
      onSubmit: async (event) => {
        event.preventDefault();
        const { token, installments, paymentMethodId } = mp.cardForm().getCardFormData();
        // Envie token para o backend /pagamentos/cartao
      }
    }
  });
</script>
```

> ⚠️ NUNCA envie dados brutos do cartão ao servidor.  
> Sempre tokenize no frontend com MercadoPago.js.

---

## 4. Endpoints da API

| Método | Rota                          | Descrição               |
|--------|-------------------------------|-------------------------|
| GET    | /produtos                     | Listar produtos         |
| POST   | /produtos                     | Cadastrar produto       |
| PUT    | /produtos/{id}                | Atualizar produto       |
| DELETE | /produtos/{id}                | Remover produto         |
| POST   | /vendas                       | Registrar venda         |
| GET    | /vendas                       | Histórico de vendas     |
| PATCH  | /vendas/{id}/confirmar        | Confirmar pagamento     |
| PATCH  | /vendas/{id}/cancelar         | Cancelar venda          |
| POST   | /pagamentos/pix               | Gerar QR Code Pix       |
| POST   | /pagamentos/cartao            | Processar cartão        |
| GET    | /pagamentos/status/{id}       | Status do pagamento     |
| GET    | /dashboard                    | Resumo de vendas        |
| GET    | /docs                         | Swagger UI automático   |
