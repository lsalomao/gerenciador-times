#!/bin/bash

set -e

echo "=========================================="
echo "🚀 Deploy Rápido - Gerenciador de Vôlei"
echo "=========================================="
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "❌ Execute como root: sudo ./deploy-rapido.sh"
    exit 1
fi

read -p "📧 Digite seu email para SSL: " EMAIL
if [ -z "$EMAIL" ]; then
    echo "❌ Email é obrigatório!"
    exit 1
fi

read -p "🌐 Digite o domínio (ex: volei.ledtech.app): " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo "❌ Domínio é obrigatório!"
    exit 1
fi

APP_DIR=$(pwd)

echo ""
echo "📦 1/9 - Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    apt install docker-compose -y
    rm get-docker.sh
else
    echo "✅ Docker já instalado"
fi

echo ""
echo "📁 2/9 - Criando diretórios..."
mkdir -p staticfiles media /var/www/certbot
chmod -R 755 staticfiles media

echo ""
echo "🔐 3/9 - Configurando .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env

    SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || openssl rand -hex 50)
    SECRET_KEY=$(echo "$SECRET_KEY" | sed 's/[\/&]/\\&/g')

    sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env
    sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN|g" .env
    sed -i "s|CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN|g" .env

    DB_PASSWORD=$(openssl rand -hex 32)
    sed -i "s|DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|g" .env
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$DB_PASSWORD|g" .env

    chmod 600 .env
    echo "✅ Arquivo .env criado com senhas geradas automaticamente"
else
    echo "⚠️  Arquivo .env já existe, mantendo configurações"
fi

echo ""
echo "🔧 4/9 - Configurando Nginx do sistema..."
sed -i "s|volei\.ledtech\.app|$DOMAIN|g" sites-available/volei
cp sites-available/volei /etc/nginx/sites-available/$DOMAIN
ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

echo ""
echo "🏗️  5/9 - Construindo containers..."
docker-compose build

echo ""
echo "🚀 6/9 - Iniciando containers..."
docker-compose up -d

echo ""
echo "⏳ Aguardando banco de dados iniciar..."
sleep 10

echo ""
echo "📊 7/9 - Executando migrações..."
docker-compose exec -T web python manage.py migrate

echo ""
echo "📦 8/9 - Coletando arquivos estáticos..."
docker-compose exec -T web python manage.py collectstatic --noinput

echo ""
echo "🔗 Copiando arquivos estáticos para acesso do Nginx..."
docker cp volei_web:/app/staticfiles $APP_DIR/
docker cp volei_web:/app/media $APP_DIR/ 2>/dev/null || mkdir -p $APP_DIR/media
chmod -R 755 $APP_DIR/staticfiles $APP_DIR/media

echo ""
echo "🔒 9/9 - Configurando SSL com Certbot..."
certbot certonly --nginx \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email \
  -d $DOMAIN \
  -d www.$DOMAIN

echo ""
echo "🔄 Reiniciando Nginx..."
systemctl restart nginx

echo ""
echo "=========================================="
echo "✅ Deploy concluído com sucesso!"
echo "=========================================="
echo ""
echo "🌐 Acesse: https://$DOMAIN"
echo ""
echo "📝 Próximos passos:"
echo "1. Criar superusuário: docker-compose exec web python manage.py createsuperuser"
echo "2. Acessar admin: https://$DOMAIN/admin"
echo ""
echo "📊 Ver logs: docker-compose logs -f"
echo "🔄 Reiniciar: docker-compose restart"
echo "🛑 Parar: docker-compose down"
echo ""
