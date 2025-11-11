#!/bin/bash

echo "🔧 Atualizando configuração para usar Nginx do sistema..."

# Parar e remover todos os containers
echo "Parando containers..."
docker-compose down --remove-orphans



# Backup do docker-compose.yml antigo
cp docker-compose.yml docker-compose.yml.backup

# Criar novo docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  web:
    build: .
    container_name: volei_web
    restart: always
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    ports:
      - "127.0.0.1:8000:8000"
    env_file:
      - .env
    command: gunicorn --bind 0.0.0.0:8000 --workers 3 gerenciador_volei.wsgi:application
    depends_on:
      - db

  db:
    image: postgres:15-alpine
    container_name: volei_db
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=${DB_NAME:-volei_db}
      - POSTGRES_USER=${DB_USER:-volei_user}
      - POSTGRES_PASSWORD=${DB_PASSWORD:-volei_password}
    ports:
      - "127.0.0.1:5432:5432"

volumes:
  postgres_data:
  static_volume:
  media_volume:
EOF

echo "✅ docker-compose.yml atualizado"

# Atualizar configuração do Nginx
DOMAIN=$(grep "server_name" sites-available/volei | head -1 | awk '{print $2}' | sed 's/;//')

cat > sites-available/volei << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 20M;

    location /static/ {
        alias $(pwd)/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $(pwd)/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
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

echo "✅ Configuração do Nginx atualizada"

# Copiar para sites-available e criar link
cp sites-available/volei /etc/nginx/sites-available/$DOMAIN
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Testar configuração do Nginx
nginx -t

# Criar diretórios
mkdir -p staticfiles media /var/www/certbot

# Iniciar containers
echo "Iniciando containers..."
docker-compose up -d

# Aguardar
sleep 10

# Migrações
echo "Executando migrações..."
docker-compose exec -T web python manage.py migrate

# Coletar estáticos
echo "Coletando arquivos estáticos..."
docker-compose exec -T web python manage.py collectstatic --noinput

# Copiar arquivos estáticos
echo "Copiando arquivos estáticos..."
docker cp volei_web:/app/staticfiles $(pwd)/
docker cp volei_web:/app/media $(pwd)/ 2>/dev/null || mkdir -p $(pwd)/media
chmod -R 755 $(pwd)/staticfiles $(pwd)/media

# Reiniciar Nginx
echo "Reiniciando Nginx..."
systemctl restart nginx

echo ""
echo "✅ Atualização concluída!"
echo "🌐 Acesse: https://$DOMAIN"
echo ""
echo "📝 Criar superusuário: docker-compose exec web python manage.py createsuperuser"
