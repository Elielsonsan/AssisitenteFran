# ☁️ Guia Definitivo: Hospedagem 100% Gratuita no Google Cloud (Always Free Tier — R$ 0,00/mês)

O Google Cloud oferece **1 máquina virtual gratuita para sempre** (*Always Free*), mesmo após acabar o período de avaliação gratuita. Porém, **o formulário padrão do Google vem com opções pagas pré-selecionadas** (como o disco SSD Equilibrado). Para que a cobrança seja **exatamente `R$ 0,00/mês`**, siga rigorosamente a tabela da Etapa 1.

---

## 📋 Etapa 1: Criando a VM sem Pegadinhas de Cobrança

Acesse **Google Cloud Console** → **Compute Engine** → **Instâncias de VM** → **Criar Instância**.

Altere **exatamente** estes 5 itens (qualquer item diferente disso gera cobrança de centavos por dia):

| Campo no Painel | O que Selecionar (Obrigatório p/ Grátis) | ⚠️ Pegadinha para Evitar |
| :--- | :--- | :--- |
| **1. Região (Region)** | **`us-central1` (Iowa)**, **`us-east1` (Carolina do Sul)** ou **`us-west1` (Oregon)** | **NUNCA** escolha São Paulo (`southamerica-east1`) ou outras regiões fora dessas 3 dos EUA. |
| **2. Série e Tipo de Máquina** | Série **`E2`** → Tipo **`e2-micro`** (2 vCPUs compartilhadas, 1 GB memória) | O padrão vem como `e2-medium` (pago). Mude sempre para **`e2-micro`**. |
| **3. Disco de Inicialização (O PULO DO GATO)** | Clique em **Alterar (Change)** → Sistema: **Ubuntu 22.04 LTS ou 24.04 LTS** → **Tipo de disco de inicialização:** mude para **`Disco permanente padrão` (`Standard persistent disk`)** → Tamanho: **`10 GB` a `30 GB`** | ⚠️ O Google seleciona **`Disco permanente equilibrado` (`Balanced`)** por padrão. Ele cobra ~`R$ 2,50/mês`. Mude **sempre** para **`Disco permanente padrão` (`Standard`)**! |
| **4. Firewall** | Marque ✅ **Permitir tráfego HTTP** e ✅ **Permitir tráfego HTTPS** | Se esquecer de marcar, o site não abre na porta 80 pelo navegador. |
| **5. Rede (Avançado → Rede → Interfaces de rede)** | Nível de serviço de rede (*Network Service Tier*): se disponível, prefira **Standard** (ou mantenha até 1 GB/mês de saída no Premium) | Evite criar IPs Estáticos reservados que fiquem anexados a VMs desligadas. Use o IP Externo **Efêmero (Automático)**. |

> 💡 **Como conferir antes de clicar em Criar:** Na coluna da direita aparece a estimativa mensal. Mesmo que apareça um valor em dólares na estimativa da `e2-micro` + `Standard Persistent Disk`, o Google aplica **100% de desconto automático na fatura** para a primeira `e2-micro` + até `30 GB` de disco `Standard` nessas 3 regiões.

---

## 🛠️ Etapa 2: Preparando o Servidor Linux (1ª vez)

Na lista de **Instâncias de VM**, clique no botão **`SSH`** para abrir o terminal no navegador e execute os blocos abaixo:

### 2.1. Instalar Python, Git, Nginx e utilitários
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx unzip curl
```

### 2.2. Criar Memória Swap de 2 GB (Recomendado para `e2-micro` com 1 GB de RAM)
Como a `e2-micro` tem 1 GB de RAM, criar 2 GB de Swap evita que o servidor trave em picos de acesso:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2.3. Clonar o Projeto do GitHub e criar o Ambiente Virtual (`venv`)
*(Substitua a URL abaixo pelo repositório do seu projeto)*:
```bash
cd ~
git clone https://github.com/Elielsonsan/AssisitenteFran.git assistente-fran
cd ~/assistente-fran

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### 2.4. Criar o arquivo `.env` (Variáveis Secretas e API Keys)
```bash
cat << 'EOF' > ~/assistente-fran/.env
GEMINI_API_KEY=SUA_CHAVE_AQUI
FLASK_SECRET_KEY=uma_chave_secreta_forte_aqui_2026
FLASK_DEBUG=False
EOF
```

### 2.5. Inicializar o Banco de Dados (se houver script de setup)
```bash
cd ~/assistente-fran
./venv/bin/python database_setup.py
```

---

## ⚙️ Etapa 3: Deixar o Site Rodando 24h Sozinho (`Systemd` + `Gunicorn`)

Para que o projeto nunca desligue quando você fechar o SSH (e ligue sozinho se a VM reiniciar), crie um serviço no Linux:

```bash
sudo tee /etc/systemd/system/assistente-fran.service > /dev/null <<EOF
[Unit]
Description=Servidor Gunicorn - Assistente Fran
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER/assistente-fran
Environment="PATH=/home/$USER/assistente-fran/venv/bin"
ExecStart=/home/$USER/assistente-fran/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable assistente-fran
sudo systemctl start assistente-fran
```

*(Nota: se o seu Nginx já estiver apontando para a porta `5000`, use `--bind 127.0.0.1:5000` na linha `ExecStart`).*

---

## 🌐 Etapa 4: Configurar o Nginx (Porta 80 → Gunicorn)

Para que o usuário acesse direto `http://IP_DA_VM/` sem precisar digitar `:5000` ou `:8000`:

```bash
sudo tee /etc/nginx/sites-available/assistente-fran > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/assistente-fran /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
```

Pronto! Basta abrir `http://IP_EXTERNO_DA_VM/` no navegador.

---

## 🔄 Etapa 5: Como Atualizar o Servidor no Futuro (Em 10 Segundos)

Sempre que você fizer alterações no código no seu computador e subir para o GitHub (`git push`), basta abrir o **SSH** da VM e colar este bloco:

### Se a pasta na VM foi criada com `git clone`:
```bash
cd ~/assistente-fran && \
git pull origin main && \
./venv/bin/pip install -r requirements.txt && \
sudo systemctl restart assistente-fran && \
echo "✅ Atualizado com sucesso!"
```

### Se a pasta na VM foi criada sem `git clone` (baixando o `.zip` direto do GitHub e preservando `.env` e o banco):
```bash
cd ~/assistente-fran && \
cp -f .env /tmp/.env.bak 2>/dev/null; \
cp -f educacao_ia.db /tmp/educacao_ia.db.bak 2>/dev/null; \
curl -sL https://github.com/Elielsonsan/AssisitenteFran/archive/refs/heads/main.zip -o /tmp/update.zip && \
rm -rf /tmp/update_extracted && unzip -qo /tmp/update.zip -d /tmp/update_extracted && \
cp -rf /tmp/update_extracted/AssisitenteFran-main/* ~/assistente-fran/ && \
cp -f /tmp/.env.bak ~/assistente-fran/.env 2>/dev/null; \
cp -f /tmp/educacao_ia.db.bak ~/assistente-fran/educacao_ia.db 2>/dev/null; \
./venv/bin/pip install -r requirements.txt && \
sudo systemctl restart assistente-fran && \
echo "✅ Atualizado com sucesso!"
```

---

## 🩺 Etapa 6: Comandos Úteis de Diagnóstico (Quando o site der `502 Bad Gateway` ou erro)

* **Ver se o serviço Python está rodando:**
  ```bash
  sudo systemctl status assistente-fran
  ```
* **Ver os erros em tempo real do Python/Flask (Logs):**
  ```bash
  sudo journalctl -u assistente-fran -n 50 --no-pager
  ```
* **Reiniciar o servidor Python e o Nginx:**
  ```bash
  sudo systemctl restart assistente-fran && sudo systemctl restart nginx
  ```
