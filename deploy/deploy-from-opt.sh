#!/bin/bash

set -e

APP_NAME="volei"
DOMAIN="volei.ledtech.app"
SOURCE_DIR="/opt/gerenciador-times"
APP_DIR="/var/www/$DOMAIN"
GUNICORN_SERVICE="volei-gunicorn.service"

echo "=========================================="
echo "Script de Deploy - Gerenciador de Volei"
echo "$DOMAIN"
echo "=========================================="
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "Por favor, execute como root (sudo)"
    exit 1
fi

read -p "Digite seu email para o certificado SSL: " EMAIL

if [ -z "$EMAIL" ]; then
    echo "Email é obrigatório!"
    exit 1
fi

log() { echo ""; echo "$1"; }
fail() { echo "❌ $1"; exit 1; }

log "1. Instalando dependências do sistema..."
apt update
apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

log "2. Criando diretórios e copiando arquivos..."
mkdir -p "$APP_DIR"
mkdir -p /var/log/gunicorn
mkdir -p /var/www/certbot

if [ -d "$SOURCE_DIR" ]; then
    echo "Copiando arquivos de $SOURCE_DIR para $APP_DIR..."
    cp -r "$SOURCE_DIR"/* "$APP_DIR"/ || fail "Falha ao copiar arquivos"
else
    echo "⚠️  Diretorio $SOURCE_DIR não encontrado. Pulando cópia."
fi

log "3. Configurando ambiente Python..."
cd "$APP_DIR" || fail "Diretório $APP_DIR não existe"
python3 -m venv venv
"$APP_DIR/venv/bin/pip" install --upgrade pip
if [ -f requirements.txt ]; then
    "$APP_DIR/venv/bin/pip" install -r requirements.txt
else
    echo "⚠️  requirements.txt não encontrado, pulando instalação de dependências Python"
fi

log "4. Configurando variáveis de ambiente..."
if [ ! -f "$APP_DIR/.env" ]; then
    SECRET_KEY=$("$APP_DIR/venv/bin/python" - <<PY
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
)
    cat > "$APP_DIR/.env" <<EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$DOMAIN
DATABASE_URL=sqlite:///db.sqlite3
EOF
    echo "✅ Arquivo .env criado com SECRET_KEY gerada automaticamente"
else
    echo "⚠️  Arquivo .env já existe, pulando..."
fi

log "5. Preparando Django..."
if [ -f manage.py ]; then
    "$APP_DIR/venv/bin/python" manage.py migrate --noinput
    "$APP_DIR/venv/bin/python" manage.py collectstatic --noinput
else
    echo "⚠️  manage.py não encontrado, pulando migrate/collectstatic"
fi

log "6. Ajustando permissões..."
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"
if [ -f "$APP_DIR/.env" ]; then
    chmod 600 "$APP_DIR/.env"
fi
if [ -f "$APP_DIR/db.sqlite3" ]; then
    chmod 664 "$APP_DIR/db.sqlite3"
fi

log "Preparando diretório de logs do Gunicorn..."
mkdir -p /var/log/gunicorn
chown -R www-data:www-data /var/log/gunicorn
chmod -R 755 /var/log/gunicorn

log "7. Configurando Gunicorn service..."
if [ -f "$APP_DIR/deploy/gunicorn.service" ]; then
    cp "$APP_DIR/deploy/gunicorn.service" /etc/systemd/system/"$GUNICORN_SERVICE"
    systemctl daemon-reload
    systemctl enable "$GUNICORN_SERVICE"
    systemctl start "$GUNICORN_SERVICE"
else
    echo "⚠️  $APP_DIR/deploy/gunicorn.service não encontrado. Certifique-se de criar o serviço manualmente."
fi

sleep 2
if systemctl is-active --quiet "$GUNICORN_SERVICE"; then
    echo "✅ Gunicorn iniciado com sucesso"
else
    echo "❌ Erro ao iniciar Gunicorn. Verificando logs..."
    journalctl -u "$GUNICORN_SERVICE" -n 20 || true
    fail "Falha ao iniciar Gunicorn"
fi

log "8. Configurando Nginx (temporário sem SSL)..."

# Remove link simbólico se já existir
rm -f /etc/nginx/sites-enabled/"$DOMAIN"

cat > /etc/nginx/sites-available/"$DOMAIN" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /static/ {
        alias $APP_DIR/static/;
    }

    location /media/ {
        alias $APP_DIR/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/"$DOMAIN" /etc/nginx/sites-enabled/

echo "Testando configuração do Nginx..."
if nginx -t 2>&1 | grep -q -i "successful"; then
    systemctl reload nginx
    echo "✅ Nginx configurado e recarregado"
else
    echo "⚠️  Aviso: Há problemas na configuração do Nginx"
    echo "Continuando mesmo assim..."
fi

log "9. Configurando SSL..."
echo ""
echo "Escolha o tipo de certificado SSL:"
echo "1) Let's Encrypt (gratuito, automático)"
echo "2) Certificado próprio (autoassinado ou existente)"
echo ""
read -p "Opção [1-2]: " SSL_OPTION

case "$SSL_OPTION" in
    1)
        log "Gerando certificado Let's Encrypt..."
        if certbot certonly --nginx -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive; then
            log "10. Aplicando configuração Nginx com SSL (se existir deploy/nginx.conf será usado)..."
            if [ -f "$APP_DIR/deploy/nginx.conf" ]; then
                cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/"$DOMAIN"
            else
                echo "⚠️  $APP_DIR/deploy/nginx.conf não encontrado. Certbot deve ter atualizado a configuração automaticamente."
            fi

            if nginx -t 2>&1 | grep -q -i "successful"; then
                systemctl reload nginx
                echo "✅ Nginx com SSL configurado"
            else
                echo "⚠️ Aviso: Problemas na configuração do Nginx após SSL"
            fi

            log "11. Configurando renovação automática do SSL..."
            systemctl enable certbot.timer || true
            systemctl start certbot.timer || true

            echo ""
            echo "=========================================="
            echo "✅ DEPLOY CONCLUÍDO COM SUCESSO!"
            echo "=========================================="
            echo ""
            echo "🌐 Seu sistema está disponível em:"
            echo "   https://$DOMAIN"
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
            echo "  sudo bash $APP_DIR/deploy/setup-ssl.sh"
            echo ""
        fi
        ;;
    2)
        log "Configurando certificado próprio (script custom)..."
        if [ -f "$APP_DIR/deploy/setup-ssl-custom.sh" ]; then
            bash "$APP_DIR/deploy/setup-ssl-custom.sh"
            if [ $? -eq 0 ]; then
                echo ""
                echo "=========================================="
                echo "✅ DEPLOY CONCLUÍDO COM SUCESSO!"
                echo "=========================================="
                echo ""
                echo "🌐 Seu sistema está disponível em:"
                echo "   https://$DOMAIN"
                echo ""
            else
                fail "Erro ao configurar SSL próprio"
            fi
        else
            fail "Script $APP_DIR/deploy/setup-ssl-custom.sh não encontrado"
        fi
        ;;
    *)
        echo ""
        echo "Opção inválida. Continuando sem SSL..."
        echo ""
        echo "=========================================="
        echo "⚠️  SISTEMA RODANDO SEM SSL"
        echo "=========================================="
        echo ""
        echo "🌐 Acesse: http://$DOMAIN"
        echo ""
        echo "Para configurar SSL depois:"
        echo "  Let's Encrypt: sudo bash $APP_DIR/deploy/setup-ssl.sh"
        echo "  Próprio:       sudo bash $APP_DIR/deploy/setup-ssl-custom.sh"
        echo ""
        ;;
esac

echo ""
echo "📊 Status dos serviços:"
systemctl status "$GUNICORN_SERVICE" --no-pager -l || true
echo ""
echo "📝 Comandos úteis:"
echo "   Ver logs:     sudo journalctl -u $GUNICORN_SERVICE -f"
echo "   Reiniciar:    sudo systemctl restart $GUNICORN_SERVICE"
echo "   Status:       sudo systemctl status $GUNICORN_SERVICE"
echo "   Logs Nginx:   sudo tail -f /var/log/nginx/$DOMAIN.error.log"
echo ""
