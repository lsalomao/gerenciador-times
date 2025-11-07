# Guia de Deploy - Gerenciador de Volei
## Servidor: volei.ledtech.app

Este guia contém todas as instruções para publicar o sistema no servidor com Nginx e SSL.

---

## 📋 Pré-requisitos

- Servidor Ubuntu/Debian com acesso root
- Nginx instalado e configurado
- Python 3.8+ instalado
- Git instalado
- Domínio `volei.ledtech.app` apontando para o IP do servidor

---

## 🚀 Passo a Passo do Deploy

### 1. Preparar o Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Criar diretórios necessários
sudo mkdir -p /var/www/volei.ledtech.app
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/www/certbot
```

### 2. Clonar o Projeto

```bash
# Navegar para o diretório
cd /var/www/volei.ledtech.app

# Clonar o repositório (ajuste a URL conforme necessário)
sudo git clone <URL_DO_REPOSITORIO> .

# Ou fazer upload dos arquivos via SCP/FTP
```

### 3. Configurar Ambiente Python

```bash
# Criar ambiente virtual
sudo python3 -m venv venv

# Ativar ambiente virtual
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/pip install --upgrade pip

# Instalar dependências
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/pip install -r requirements.txt

# Instalar Gunicorn
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/pip install gunicorn
```

### 4. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
sudo cp deploy/.env.example .env

# Editar arquivo .env
sudo nano .env
```

**Conteúdo do arquivo `.env`:**
```env
DEBUG=False
SECRET_KEY=GERE_UMA_CHAVE_SECRETA_FORTE_AQUI
ALLOWED_HOSTS=volei.ledtech.app
DATABASE_URL=sqlite:///db.sqlite3
```

**Para gerar uma SECRET_KEY segura:**
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Preparar o Django

```bash
# Coletar arquivos estáticos
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/python manage.py collectstatic --noinput

# Executar migrações
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/python manage.py migrate

# Criar superusuário (opcional)
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/python manage.py createsuperuser
```

### 6. Configurar Permissões

```bash
# Ajustar proprietário dos arquivos
sudo chown -R www-data:www-data /var/www/volei.ledtech.app

# Ajustar permissões
sudo chmod -R 755 /var/www/volei.ledtech.app
sudo chmod 600 /var/www/volei.ledtech.app/.env
sudo chmod 664 /var/www/volei.ledtech.app/db.sqlite3
```

### 7. Configurar Gunicorn Service

```bash
# Copiar arquivo de serviço
sudo cp /var/www/volei.ledtech.app/deploy/gunicorn.service /etc/systemd/system/volei-gunicorn.service

# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar serviço
sudo systemctl enable volei-gunicorn.service

# Iniciar serviço
sudo systemctl start volei-gunicorn.service

# Verificar status
sudo systemctl status volei-gunicorn.service
```

### 8. Configurar Nginx (Temporário - Sem SSL)

```bash
# Criar configuração temporária sem SSL
sudo nano /etc/nginx/sites-available/volei.ledtech.app
```

**Conteúdo temporário (apenas HTTP):**
```nginx
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
```

```bash
# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/volei.ledtech.app /etc/nginx/sites-enabled/

# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

### 9. Gerar Certificado SSL

```bash
# Editar o script para adicionar seu email
sudo nano /var/www/volei.ledtech.app/deploy/setup-ssl.sh
# Altere a linha: EMAIL="seu-email@exemplo.com"

# Tornar executável
sudo chmod +x /var/www/volei.ledtech.app/deploy/setup-ssl.sh

# Executar script
sudo /var/www/volei.ledtech.app/deploy/setup-ssl.sh
```

### 10. Configurar Nginx com SSL

```bash
# Substituir configuração pelo arquivo completo com SSL
sudo cp /var/www/volei.ledtech.app/deploy/nginx.conf /etc/nginx/sites-available/volei.ledtech.app

# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

---

## 🔍 Verificação e Testes

### Verificar Serviços

```bash
# Status do Gunicorn
sudo systemctl status volei-gunicorn.service

# Status do Nginx
sudo systemctl status nginx

# Logs do Gunicorn
sudo tail -f /var/log/gunicorn/volei.error.log
sudo tail -f /var/log/gunicorn/volei.access.log

# Logs do Nginx
sudo tail -f /var/log/nginx/volei.ledtech.app.error.log
sudo tail -f /var/log/nginx/volei.ledtech.app.access.log
```

### Testar Aplicação

1. Acesse: `https://volei.ledtech.app`
2. Verifique se o certificado SSL está válido
3. Teste todas as funcionalidades do sistema

---

## 🔄 Atualizações Futuras

Para atualizar o sistema:

```bash
# Navegar para o diretório
cd /var/www/volei.ledtech.app

# Fazer backup do banco de dados
sudo cp db.sqlite3 db.sqlite3.backup

# Atualizar código (git pull ou upload de arquivos)
sudo git pull

# Ativar ambiente virtual e instalar dependências
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/pip install -r requirements.txt

# Executar migrações
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/python manage.py migrate

# Coletar arquivos estáticos
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/python manage.py collectstatic --noinput

# Reiniciar Gunicorn
sudo systemctl restart volei-gunicorn.service
```

---

## 🛠️ Comandos Úteis

```bash
# Reiniciar Gunicorn
sudo systemctl restart volei-gunicorn.service

# Reiniciar Nginx
sudo systemctl restart nginx

# Ver logs em tempo real
sudo journalctl -u volei-gunicorn.service -f

# Testar renovação SSL
sudo certbot renew --dry-run

# Renovar certificado manualmente
sudo certbot renew
```

---

## 🔒 Segurança

### Firewall (UFW)

```bash
# Habilitar firewall
sudo ufw enable

# Permitir SSH
sudo ufw allow 22/tcp

# Permitir HTTP e HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Verificar status
sudo ufw status
```

### Backup Automático

Crie um script de backup:

```bash
sudo nano /usr/local/bin/backup-volei.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/volei"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco de dados
cp /var/www/volei.ledtech.app/db.sqlite3 $BACKUP_DIR/db_$DATE.sqlite3

# Manter apenas últimos 7 dias
find $BACKUP_DIR -name "db_*.sqlite3" -mtime +7 -delete
```

```bash
# Tornar executável
sudo chmod +x /usr/local/bin/backup-volei.sh

# Adicionar ao crontab (backup diário às 2h)
sudo crontab -e
# Adicionar linha:
0 2 * * * /usr/local/bin/backup-volei.sh
```

---

## ❗ Troubleshooting

### Erro 502 Bad Gateway

```bash
# Verificar se Gunicorn está rodando
sudo systemctl status volei-gunicorn.service

# Verificar logs
sudo journalctl -u volei-gunicorn.service -n 50
```

### Erro de Permissão

```bash
# Ajustar permissões
sudo chown -R www-data:www-data /var/www/volei.ledtech.app
sudo chmod 664 /var/www/volei.ledtech.app/db.sqlite3
```

### Arquivos Estáticos não Carregam

```bash
# Coletar novamente
sudo -u www-data /var/www/volei.ledtech.app/venv/bin/python manage.py collectstatic --noinput

# Verificar permissões
sudo chmod -R 755 /var/www/volei.ledtech.app/static/
```

### Certificado SSL não Renova

```bash
# Verificar timer do certbot
sudo systemctl status certbot.timer

# Testar renovação
sudo certbot renew --dry-run

# Forçar renovação
sudo certbot renew --force-renewal
```

---

## 📞 Suporte

Para problemas ou dúvidas:
- Verifique os logs do sistema
- Consulte a documentação do Django: https://docs.djangoproject.com/
- Documentação do Nginx: https://nginx.org/en/docs/
- Documentação do Certbot: https://certbot.eff.org/

---

**Deploy realizado com sucesso! 🎉**
