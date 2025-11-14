#!/bin/bash

set -e

echo "==================================="
echo "Atualização - Gerenciador de Times"
echo "==================================="
echo ""

PROJECT_DIR="/opt/gerenciador-times"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Erro: Diretório do projeto não encontrado em $PROJECT_DIR"
    exit 1
fi

cd $PROJECT_DIR

echo "1. Fazendo backup do banco de dados..."
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker-compose exec -T db pg_dump -U volei_user volei_db > $BACKUP_FILE
echo "Backup salvo em: $BACKUP_FILE"

echo ""
echo "2. Atualizando código..."
if [ -d .git ]; then
    git pull
else
    echo "Não é um repositório Git. Copie os arquivos manualmente."
    read -p "Pressione Enter após copiar os arquivos atualizados..."
fi

echo ""
echo "3. Parando containers..."
docker-compose down

echo ""
echo "4. Reconstruindo containers..."
docker-compose up -d --build

echo ""
echo "5. Aguardando containers iniciarem..."
sleep 10

echo ""
echo "6. Executando migrações..."
docker-compose exec -T web python manage.py migrate

echo ""
echo "7. Coletando arquivos estáticos..."
docker-compose exec -T web python manage.py collectstatic --noinput

echo ""
echo "8. Atualizando arquivos estáticos no Nginx..."
docker cp volei_web:/app/staticfiles/. $PROJECT_DIR/staticfiles/
sudo chown -R www-data:www-data $PROJECT_DIR/staticfiles

echo ""
echo "9. Reiniciando Nginx..."
sudo systemctl reload nginx

echo ""
echo "==================================="
echo "Atualização concluída!"
echo "==================================="
echo ""
echo "Verificar logs: docker-compose logs -f"
echo ""
