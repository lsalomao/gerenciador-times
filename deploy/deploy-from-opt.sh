#!/bin/bash

set -e

echo "=========================================="
echo "Script de Deploy - Gerenciador de Volei"
echo "volei.ledtech.app"
echo "=========================================="
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Por favor, execute como root (sudo)"
    exit 1
fi

SOURCE_DIR="/opt/gerenciador-times"
APP_DIR="/var/www/volei.ledtech.app"
DOMAIN="volei.ledtech.app"

read -p "Digite seu email para o certificado SSL: " EMAIL

if [ -z "$EMAIL" ]; then
    echo "Email é obrigatório!"
    exit 1
fi

echo ""
echo "1. Instalando dependências do sistema..."
apt update
apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

echo ""
echo "2. Criando diretórios e copiando arquivos..."
mkdir -p $APP_DIR
mkdir -p /var/log/gunicorn
mkdir -p /var/www/certbot

echo "Copiando arquivos de $SOURCE_DIR para $APP_DIR..."
cp -r $SOURCE_DIR/* $APP_DIR/

echo ""
echo "3. Configurando ambiente Python..."
cd $APP_DIR
python3 -m venv venv
$APP_DIR/venv/bin/pip install --upgrade pip
$APP_DIR/venv/bin/pip install -r requirements.txt

echo ""
echo "4. Configurando variáveis de ambiente..."
if [ ! -f "$APP_DIR/.env" ]; then
    SECRET_KEY=$($APP_DIR/venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    cat > $APP_DIR/.env << EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$DOMAIN
DATABASE_URL=sqlite:///db.sqlite3
EOF
    echo "✅ Arquivo .env criado com SECRET_KEY gerada automaticamente"
else
    echo "⚠️  Arquivo .env já existe, pulando..."
fi

echo ""
echo "5. Preparando Django..."
$APP_DIR/venv/bin/python manage.py migrate
$APP_DIR/venv/bin/python manage.py collectstatic --noinput

echo ""
echo "6. Ajustando permissões..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR
chmod 600 $APP_DIR/.env
if [ -f "$APP_DIR/db.sqlite3" ]; then
    chmod 664 $APP_DIR/db.sqlite3
fi

echo ""
echo "7. Configurando Gunicorn service..."
cp $APP_DIR/deploy/gunicorn.service /etc/systemd/system/volei-gunicorn.service
systemctl daemon-reload
systemctl enable volei-gunicorn.service
systemctl start volei-gunicorn.service

sleep 2
if systemctl is-active --quiet volei-gunicorn.service; then
    echo "✅ Gunicorn iniciado com sucesso"
else
    echo "❌ Erro ao iniciar Gunicorn. Verificando logs..."
    journalctl -u volei-gunicorn.service -n 20
    exit 1
fi

echo ""
echo "8. Configurando Nginx (temporário sem SSL)..."
cat > /etc/nginx/sites-available/$DOMAIN << 'EOF'
server {
    listen 80;
    server_name volei.ledtech.app;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /static/ {
        alias /var/www/volei.ledtech.app/static/;
    }

    location /media/ {
        alias /var/www/volei.ledtech.app/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

if nginx -t; then
    systemctl reload nginx
    echo "✅ Nginx configurado e recarregado"
else
    echo "❌ Erro na configuração do Nginx"
    exit 1
fi

echo ""
echo "9. Gerando certificado SSL..."
certbot certonly --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

if [ $? -eq 0 ]; then
    echo ""
    echo "10. Configurando Nginx com SSL..."
    cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/$DOMAIN
    
    if nginx -t; then
        systemctl reload nginx
        echo "✅ Nginx com SSL configurado"
    else
        echo "❌ Erro na configuração do Nginx com SSL"
        exit 1
    fi
    
    echo ""
    echo "11. Configurando renovação automática do SSL..."
    systemctl enable certbot.timer
    systemctl start certbot.timer
    
    echo ""
    echo "=========================================="
    echo "✅ DEPLOY CONCLUÍDO COM SUCESSO!"
    echo "=========================================="
    echo ""
    echo "🌐 Seu sistema está disponível em:"
    echo "   https://$DOMAIN"
    echo ""
    echo "📊 Status dos serviços:"
    systemctl status volei-gunicorn.service --no-pager -l
    echo ""
    echo "📝 Comandos úteis:"
    echo "   Ver logs:     sudo journalctl -u volei-gunicorn.service -f"
    echo "   Reiniciar:    sudo systemctl restart volei-gunicorn.service"
    echo "   Status:       sudo systemctl status volei-gunicorn.service"
    echo "   Logs Nginx:   sudo tail -f /var/log/nginx/volei.ledtech.app.error.log"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "⚠️  ERRO ao gerar certificado SSL"
    echo "=========================================="
    echo ""
    echo "O sistema está rodando em HTTP (sem SSL)"
    echo "🌐 Acesse: http://$DOMAIN"
    echo ""
    echo "Para configurar SSL manualmente:"
    echo "  1. Verifique se o domínio aponta para este servidor"
    echo "  2. Verifique se as portas 80 e 443 estão abertas"
    echo "  3. Execute: sudo bash $APP_DIR/deploy/setup-ssl.sh"
    echo ""
fi
