# 🚀 Deploy do Gerenciador de Vôlei na VPS

Guia completo para fazer deploy do sistema na VPS usando Docker.

## 📋 Pré-requisitos na VPS

- Ubuntu 20.04+ ou Debian 11+
- Docker e Docker Compose instalados
- Domínio apontando para o IP da VPS (volei.ledtech.app)
- Portas 80 e 443 abertas no firewall

## 🔧 Instalação do Docker (se necessário)

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose -y

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER
```

## 📦 Preparação do Projeto

### 1. Clonar/Enviar o projeto para a VPS

```bash
# Opção 1: Via Git
cd /opt
sudo git clone <seu-repositorio> gerenciador-volei
cd gerenciador-volei

# Opção 2: Via SCP/SFTP
# Envie os arquivos para /opt/gerenciador-volei
```

### 2. Configurar variáveis de ambiente

```bash
# Copiar o arquivo de exemplo
cp .env.example .env

# Editar com suas configurações
nano .env
```

**Configurações importantes no .env:**

```env
DEBUG=False
SECRET_KEY=sua-chave-secreta-super-forte-aqui-gere-uma-nova
ALLOWED_HOSTS=volei.ledtech.app,www.volei.ledtech.app

# Banco de dados PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=volei_db
DB_USER=volei_user
DB_PASSWORD=senha-forte-do-banco
DB_HOST=db
DB_PORT=5432

# Configurações do PostgreSQL
POSTGRES_DB=volei_db
POSTGRES_USER=volei_user
POSTGRES_PASSWORD=senha-forte-do-banco

# CSRF
CSRF_TRUSTED_ORIGINS=https://volei.ledtech.app,https://www.volei.ledtech.app
```

**⚠️ IMPORTANTE:** Gere uma nova SECRET_KEY:

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Criar diretórios necessários

```bash
sudo mkdir -p certbot/conf certbot/www
sudo chmod -R 755 certbot
```

## 🚀 Deploy

### 1. Build e iniciar containers

```bash
# Build das imagens
sudo docker-compose build

# Iniciar containers
sudo docker-compose up -d
```

### 2. Executar migrações do banco

```bash
sudo docker-compose exec web python manage.py migrate
```

### 3. Criar superusuário

```bash
sudo docker-compose exec web python manage.py createsuperuser
```

### 4. Coletar arquivos estáticos

```bash
sudo docker-compose exec web python manage.py collectstatic --noinput
```

### 5. Configurar SSL com Let's Encrypt

```bash
# Obter certificado SSL
sudo docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email seu-email@exemplo.com \
  --agree-tos \
  --no-eff-email \
  -d volei.ledtech.app \
  -d www.volei.ledtech.app

# Reiniciar nginx para aplicar SSL
sudo docker-compose restart nginx
```

## 🔍 Verificação

### Verificar status dos containers

```bash
sudo docker-compose ps
```

Todos devem estar com status "Up".

### Verificar logs

```bash
# Logs de todos os containers
sudo docker-compose logs -f

# Logs específicos
sudo docker-compose logs -f web
sudo docker-compose logs -f nginx
sudo docker-compose logs -f db
```

### Testar o site

Acesse: https://volei.ledtech.app

## 🔄 Atualizações

Para atualizar o sistema:

```bash
# Parar containers
sudo docker-compose down

# Atualizar código (se usando git)
sudo git pull

# Rebuild e reiniciar
sudo docker-compose build
sudo docker-compose up -d

# Executar migrações
sudo docker-compose exec web python manage.py migrate

# Coletar estáticos
sudo docker-compose exec web python manage.py collectstatic --noinput
```

## 🛠️ Comandos Úteis

```bash
# Ver logs em tempo real
sudo docker-compose logs -f

# Reiniciar um serviço específico
sudo docker-compose restart web

# Parar todos os containers
sudo docker-compose down

# Parar e remover volumes (CUIDADO: apaga banco de dados)
sudo docker-compose down -v

# Acessar shell do Django
sudo docker-compose exec web python manage.py shell

# Acessar bash do container
sudo docker-compose exec web bash

# Backup do banco de dados
sudo docker-compose exec db pg_dump -U volei_user volei_db > backup.sql

# Restaurar banco de dados
sudo docker-compose exec -T db psql -U volei_user volei_db < backup.sql
```

## 🔒 Segurança

### Firewall (UFW)

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Permissões

```bash
# Ajustar permissões dos arquivos
sudo chown -R $USER:$USER /opt/gerenciador-volei
sudo chmod 600 .env
```

## 🐛 Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados
sudo docker-compose logs web

# Verificar configurações
sudo docker-compose config
```

### Erro de permissão no banco

```bash
# Recriar banco
sudo docker-compose down
sudo docker volume rm gerenciador-volei_postgres_data
sudo docker-compose up -d
sudo docker-compose exec web python manage.py migrate
```

### SSL não funciona

```bash
# Verificar certificados
sudo docker-compose exec nginx ls -la /etc/letsencrypt/live/volei.ledtech.app/

# Renovar certificado manualmente
sudo docker-compose run --rm certbot renew
```

### Arquivos estáticos não carregam

```bash
# Recoletar estáticos
sudo docker-compose exec web python manage.py collectstatic --noinput --clear

# Verificar permissões
sudo docker-compose exec web ls -la /app/staticfiles/
```

## 📊 Monitoramento

### Ver uso de recursos

```bash
sudo docker stats
```

### Ver espaço em disco

```bash
sudo docker system df
```

### Limpar recursos não utilizados

```bash
sudo docker system prune -a
```

## 🔄 Backup Automático

Criar script de backup em `/opt/backup-volei.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/volei"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco
docker-compose -f /opt/gerenciador-volei/docker-compose.yml exec -T db \
  pg_dump -U volei_user volei_db > $BACKUP_DIR/db_$DATE.sql

# Backup dos arquivos
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/gerenciador-volei/media

# Manter apenas últimos 7 dias
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

Adicionar ao crontab:

```bash
sudo crontab -e
# Adicionar linha:
0 2 * * * /opt/backup-volei.sh
```

## 📞 Suporte

Em caso de problemas, verifique:
1. Logs dos containers
2. Configurações do .env
3. Permissões de arquivos
4. Status dos serviços
5. Conectividade de rede

---

**Desenvolvido para volei.ledtech.app** 🏐
