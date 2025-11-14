#!/bin/bash

set -e

echo "==================================="
echo "Deploy - Gerenciador de Times"
echo "Porta: 5006 | HTTPS: Sim"
echo "==================================="
echo ""

if [ "$EUID" -eq 0 ]; then
    echo "Erro: Não execute este script como root"
    exit 1
fi


DOMAIN="volei.ledtech.app"
read -p "Digite o email para SSL (ex: seu@email.com): " EMAIL
read -sp "Digite a senha do banco de dados: " DB_PASSWORD
echo ""

PROJECT_DIR="/opt/gerenciador-times"

echo ""
echo "1. Criando diretório do projeto..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

echo ""
echo "2. Copiando arquivos..."
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

echo ""
echo "3. Configurando variáveis de ambiente..."
if [ ! -f .env ]; then
    cp .env.example .env

    SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

    sed -i "s|DEBUG=.*|DEBUG=False|g" .env
    sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env
    sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1|g" .env
    sed -i "s|DB_PASSWORD=.*|DB_PASSWORD=$DB_PASSWORD|g" .env
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$DB_PASSWORD|g" .env
    sed -i "s|CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN|g" .env

    echo "Arquivo .env configurado!"
else
    echo "Arquivo .env já existe, pulando..."
fi

echo ""
echo "4. Configurando Nginx..."
sudo cp sites-available/volei.ledtech.app /etc/nginx/sites-available/$DOMAIN

if [ ! -f /etc/nginx/sites-enabled/$DOMAIN ]; then
    sudo ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
fi

if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

echo ""
echo "5. Testando configuração do Nginx..."
sudo nginx -t

echo ""
echo "6. Recarregando Nginx..."
sudo systemctl reload nginx

echo ""
echo "7. Iniciando containers Docker (porta 5006)..."
docker-compose down 2>/dev/null || true
docker-compose up -d --build

echo ""
echo "8. Aguardando containers iniciarem..."
sleep 10

echo ""
echo "9. Executando migrações..."
docker-compose exec -T web python manage.py migrate

echo ""
echo "10. Coletando arquivos estáticos..."
docker-compose exec -T web python manage.py collectstatic --noinput

echo ""
echo "11. Copiando arquivos estáticos para Nginx..."
sudo mkdir -p $PROJECT_DIR/staticfiles
sudo mkdir -p $PROJECT_DIR/media
docker cp volei_web:/app/staticfiles/. $PROJECT_DIR/staticfiles/ 2>/dev/null || true
docker cp volei_web:/app/media/. $PROJECT_DIR/media/ 2>/dev/null || true
sudo chown -R www-data:www-data $PROJECT_DIR/staticfiles
sudo chown -R www-data:www-data $PROJECT_DIR/media

echo ""
echo "12. Configurando SSL com Let's Encrypt..."
read -p "Deseja configurar SSL agora? (s/n): " SETUP_SSL

if [ "$SETUP_SSL" = "s" ] || [ "$SETUP_SSL" = "S" ]; then
    if ! command -v certbot &> /dev/null; then
        echo "Instalando Certbot..."
        sudo apt update
        sudo apt install certbot python3-certbot-nginx -y
    fi

    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive
    echo "SSL configurado com sucesso!"
else
    echo "Pulando configuração SSL. Você pode configurar depois com:"
    echo "sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
fi

echo ""
echo "==================================="
echo "Deploy concluído com sucesso!"
echo "==================================="
echo ""
echo "Aplicação rodando em:"
echo "- HTTP: http://$DOMAIN (redireciona para HTTPS)"
echo "- HTTPS: https://$DOMAIN"
echo "- Porta interna: 5006"
echo ""
echo "Próximos passos:"
echo "1. Criar superusuário: docker-compose exec web python manage.py createsuperuser"
echo "2. Acessar: https://$DOMAIN"
echo ""
echo "Comandos úteis:"
echo "- Ver logs: docker-compose logs -f"
echo "- Reiniciar: docker-compose restart"
echo "- Parar: docker-compose down"
echo "- Status: docker-compose ps"
echo ""
