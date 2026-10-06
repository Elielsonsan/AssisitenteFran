#!/bin/bash
# ==============================================================================
# Script de Instalação e Deploy Automático - Assistente Fran no Google Compute Engine (VM e2-micro)
# ==============================================================================

set -e

echo "=========================================================="
echo "🚀 Iniciando configuração do Assistente Fran no GCP..."
echo "=========================================================="

# 1. Obter diretório atual do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="$(whoami)"

echo "📂 Diretório do projeto: $PROJECT_DIR"
echo "👤 Usuário do sistema: $CURRENT_USER"

# 2. Configurar Memória Swap (2GB) - Indispensável para a VM e2-micro (1GB RAM)
if [ ! -f /swapfile ]; then
    echo "⚙️ Configurando 2GB de Swap para garantir estabilidade de memória..."
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✓ Swap configurado com sucesso!"
else
    echo "✓ Swap já existente."
fi

# 3. Atualizar pacotes do sistema e instalar dependências essenciais
echo "📦 Atualizando repositórios e instalando pacotes..."
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv nginx curl git ufw

# 4. Criar e configurar o ambiente virtual Python
echo "🐍 Configurando ambiente virtual Python..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
fi

"$PROJECT_DIR/venv/bin/pip" install --upgrade pip
echo "📥 Instalando dependências do requirements.txt..."
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# 5. Criar serviço systemd para rodar o Flask com Gunicorn 24/7
echo "⚙️ Configurando serviço de inicialização automática (systemd)..."
SERVICE_FILE="/etc/systemd/system/assistente-fran.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Assistente Fran - Plataforma FLE Flask
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="PORT=5000"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 2 --bind 127.0.0.1:5000 --timeout 120 --access-logfile - --error-logfile - app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable assistente-fran
sudo systemctl restart assistente-fran

# 6. Configurar Nginx como Reverse Proxy (Porta 80 -> Porta 5000)
echo "🌐 Configurando Nginx..."
NGINX_CONF="/etc/nginx/sites-available/assistente-fran"

sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 30M;

    # Servir arquivos estáticos diretamente pelo Nginx para máxima velocidade
    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 120s;
        proxy_read_timeout 120s;
    }
}
EOL

# Ativar o site no Nginx e remover o default antigo se existir
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 7. Configurar Firewall (UFW)
echo "🛡️ Configurando Firewall..."
sudo ufw allow 'Nginx Full' || true
sudo ufw allow 'OpenSSH' || true

# 8. Obter IP Público da VM
PUBLIC_IP=\$(curl -s https://api.ipify.org || echo "SEU_IP_PUBLICO")

echo ""
echo "=========================================================="
echo "🎉 DEPLOY CONCLUÍDO COM SUCESSO!"
echo "=========================================================="
echo "O Assistente Fran já está rodando 24 horas por dia!"
echo ""
echo "🔗 Acesse pelo navegador no endereço:"
echo "   http://$PUBLIC_IP"
echo ""
echo "📌 Comandos úteis para gerenciar o servidor:"
echo "   - Ver status do app:  sudo systemctl status assistente-fran"
echo "   - Reiniciar o app:    sudo systemctl restart assistente-fran"
echo "   - Ver logs em tempo real: sudo journalctl -u assistente-fran -f"
echo "=========================================================="
