#!/bin/bash

DOMAIN="volei.ledtech.app"
SSL_DIR="/etc/ssl/volei"

echo "=========================================="
echo "Configuração de Certificado SSL Próprio"
echo "=========================================="
echo ""
echo "Escolha uma opção:"
echo "1) Gerar certificado autoassinado (para testes)"
echo "2) Usar certificados existentes (.crt e .key)"
echo ""
read -p "Opção [1-2]: " OPCAO

case $OPCAO in
    1)
        echo ""
        echo "Gerando certificado autoassinado..."
        
        # Criar diretório
        mkdir -p $SSL_DIR
        
        # Gerar certificado autoassinado válido por 365 dias
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout $SSL_DIR/privkey.pem \
            -out $SSL_DIR/fullchain.pem \
            -subj "/C=BR/ST=Estado/L=Cidade/O=Organizacao/CN=$DOMAIN"
        
        if [ $? -eq 0 ]; then
            echo "✅ Certificado autoassinado gerado com sucesso!"
            echo ""
            echo "Arquivos criados:"
            echo "  - $SSL_DIR/fullchain.pem"
            echo "  - $SSL_DIR/privkey.pem"
        else
            echo "❌ Erro ao gerar certificado"
            exit 1
        fi
        ;;
        
    2)
        echo ""
        echo "Usando certificados existentes..."
        echo ""
        read -p "Caminho completo do arquivo .crt (certificado): " CRT_FILE
        read -p "Caminho completo do arquivo .key (chave privada): " KEY_FILE
        
        if [ ! -f "$CRT_FILE" ]; then
            echo "❌ Arquivo $CRT_FILE não encontrado!"
            exit 1
        fi
        
        if [ ! -f "$KEY_FILE" ]; then
            echo "❌ Arquivo $KEY_FILE não encontrado!"
            exit 1
        fi
        
        # Criar diretório
        mkdir -p $SSL_DIR
        
        # Copiar certificados
        cp "$CRT_FILE" $SSL_DIR/fullchain.pem
        cp "$KEY_FILE" $SSL_DIR/privkey.pem
        
        echo "✅ Certificados copiados com sucesso!"
        echo ""
        echo "Arquivos configurados:"
        echo "  - $SSL_DIR/fullchain.pem"
        echo "  - $SSL_DIR/privkey.pem"
        ;;
        
    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

# Ajustar permissões
chmod 644 $SSL_DIR/fullchain.pem
chmod 600 $SSL_DIR/privkey.pem
chown root:root $SSL_DIR/*.pem

echo ""
echo "=========================================="
echo "Configurando Nginx com SSL..."
echo "=========================================="

# Criar configuração Nginx com SSL
cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate $SSL_DIR/fullchain.pem;
    ssl_certificate_key $SSL_DIR/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 10M;

    access_log /var/log/nginx/$DOMAIN.access.log;
    error_log /var/log/nginx/$DOMAIN.error.log;

    location /static/ {
        alias /var/www/$DOMAIN/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/$DOMAIN/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Ativar site
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/

# Testar configuração
echo ""
echo "Testando configuração do Nginx..."
if nginx -t; then
    echo ""
    echo "Recarregando Nginx..."
    systemctl reload nginx
    echo ""
    echo "=========================================="
    echo "✅ SSL CONFIGURADO COM SUCESSO!"
    echo "=========================================="
    echo ""
    echo "🌐 Acesse: https://$DOMAIN"
    echo ""
    if [ "$OPCAO" = "1" ]; then
        echo "⚠️  ATENÇÃO: Certificado autoassinado!"
        echo "   O navegador mostrará aviso de segurança."
        echo "   Isso é normal para certificados autoassinados."
        echo ""
    fi
else
    echo ""
    echo "❌ Erro na configuração do Nginx"
    echo "Verifique os erros acima"
    exit 1
fi
