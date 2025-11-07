#!/bin/bash

DOMAIN="volei.ledtech.app"
EMAIL="seu-email@exemplo.com"

echo "=========================================="
echo "Instalando Certbot..."
echo "=========================================="

sudo apt update
sudo apt install -y certbot python3-certbot-nginx

echo ""
echo "=========================================="
echo "Gerando certificado SSL para $DOMAIN"
echo "=========================================="

sudo certbot certonly --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Certificado gerado com sucesso!"
    echo "=========================================="
    echo ""
    echo "Certificados localizados em:"
    echo "  - /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "  - /etc/letsencrypt/live/$DOMAIN/privkey.pem"
    echo ""
    echo "Reiniciando Nginx..."
    sudo systemctl reload nginx
    echo "Nginx reiniciado!"
    echo ""
    echo "Configurando renovação automática..."
    sudo systemctl enable certbot.timer
    sudo systemctl start certbot.timer
    echo ""
    echo "Renovação automática configurada!"
    echo "Para testar a renovação, execute:"
    echo "  sudo certbot renew --dry-run"
else
    echo ""
    echo "=========================================="
    echo "ERRO ao gerar certificado!"
    echo "=========================================="
    echo ""
    echo "Verifique se:"
    echo "  1. O domínio $DOMAIN está apontando para este servidor"
    echo "  2. As portas 80 e 443 estão abertas no firewall"
    echo "  3. O Nginx está rodando e configurado corretamente"
    exit 1
fi
