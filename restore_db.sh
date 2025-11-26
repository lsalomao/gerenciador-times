#!/bin/bash

set -e

echo "==================================="
echo "Restaurar Banco de Dados"
echo "==================================="
echo ""

PROJECT_DIR="/opt/gerenciador-times"

if [ ! -f backup_local.sql ]; then
    echo "Erro: Arquivo backup_local.sql não encontrado!"
    echo "Envie o arquivo com: scp backup_local.sql usuario@servidor:/opt/gerenciador-times/"
    exit 1
fi

cd $PROJECT_DIR

echo "1. Parando aplicação..."
docker-compose stop web

echo ""
echo "2. Limpando banco de dados atual..."
docker-compose exec -T db psql -U volei_user -d volei_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo ""
echo "3. Restaurando backup..."
cat backup_local.sql | docker-compose exec -T db psql -U volei_user -d volei_db

echo ""
echo "4. Reiniciando aplicação..."
docker-compose up -d

echo ""
echo "==================================="
echo "Restauração concluída!"
echo "==================================="
