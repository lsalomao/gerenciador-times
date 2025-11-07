# 🚀 Deploy Rápido - volei.ledtech.app

## Arquivos já estão em: `/opt/gerenciador-times`

---

## ⚡ Deploy Automático (Recomendado)

Execute apenas **1 comando** no servidor:

```bash
cd /opt/gerenciador-times
sudo bash deploy/deploy-from-opt.sh
```

O script irá:
- ✅ Instalar todas as dependências
- ✅ Copiar arquivos para `/var/www/volei.ledtech.app`
- ✅ Configurar ambiente Python e Django
- ✅ Configurar Gunicorn e Nginx
- ✅ Gerar certificado SSL automaticamente
- ✅ Iniciar o sistema

**Tempo estimado:** 3-5 minutos

---

## 📋 Pré-requisitos

Antes de executar, certifique-se:

1. ✅ Domínio `volei.ledtech.app` aponta para o IP do servidor
2. ✅ Portas 80 e 443 estão abertas no firewall
3. ✅ Você tem acesso root ao servidor

---

## 🔧 Deploy Manual (Passo a Passo)

Se preferir fazer manualmente:

### 1. Instalar dependências
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx
```

### 2. Criar diretórios
```bash
sudo mkdir -p /var/www/volei.ledtech.app
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/www/certbot
```

### 3. Copiar arquivos
```bash
sudo cp -r /opt/gerenciador-times/* /var/www/volei.ledtech.app/
cd /var/www/volei.ledtech.app
```

### 4. Configurar Python
```bash
sudo python3 -m venv venv
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt
```

### 5. Criar arquivo .env
```bash
# Gerar SECRET_KEY usando o Django do ambiente virtual
SECRET_KEY=$(venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Criar arquivo .env
sudo tee .env << EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=volei.ledtech.app
DATABASE_URL=sqlite:///db.sqlite3
EOF
```

### 6. Preparar Django
```bash
sudo venv/bin/python manage.py migrate
sudo venv/bin/python manage.py collectstatic --noinput
```

### 7. Ajustar permissões
```bash
sudo chown -R www-data:www-data /var/www/volei.ledtech.app
sudo chmod -R 755 /var/www/volei.ledtech.app
sudo chmod 600 /var/www/volei.ledtech.app/.env
sudo chmod 664 /var/www/volei.ledtech.app/db.sqlite3
```

### 8. Configurar Gunicorn
```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/volei-gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable volei-gunicorn.service
sudo systemctl start volei-gunicorn.service
sudo systemctl status volei-gunicorn.service
```

### 9. Configurar Nginx (temporário)
```bash
sudo tee /etc/nginx/sites-available/volei.ledtech.app << 'EOF'
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
EOF

sudo ln -sf /etc/nginx/sites-available/volei.ledtech.app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 10. Gerar certificado SSL
```bash
sudo certbot certonly --nginx -d volei.ledtech.app --email SEU_EMAIL@exemplo.com --agree-tos --non-interactive
```

### 11. Configurar Nginx com SSL
```bash
sudo cp /var/www/volei.ledtech.app/deploy/nginx.conf /etc/nginx/sites-available/volei.ledtech.app
sudo nginx -t
sudo systemctl reload nginx
```

### 12. Configurar renovação automática
```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## ✅ Verificação

Após o deploy:

```bash
# Verificar Gunicorn
sudo systemctl status volei-gunicorn.service

# Verificar Nginx
sudo systemctl status nginx

# Ver logs
sudo journalctl -u volei-gunicorn.service -f

# Testar acesso
curl -I https://volei.ledtech.app
```

Acesse: **https://volei.ledtech.app**

---

## 🔄 Atualizar Sistema

Para futuras atualizações:

```bash
cd /opt/gerenciador-times
git pull  # ou copie novos arquivos

sudo cp -r /opt/gerenciador-times/* /var/www/volei.ledtech.app/
cd /var/www/volei.ledtech.app

sudo venv/bin/pip install -r requirements.txt
sudo venv/bin/python manage.py migrate
sudo venv/bin/python manage.py collectstatic --noinput

sudo chown -R www-data:www-data /var/www/volei.ledtech.app
sudo systemctl restart volei-gunicorn.service
```

---

## 🛠️ Comandos Úteis

```bash
# Reiniciar aplicação
sudo systemctl restart volei-gunicorn.service

# Ver logs em tempo real
sudo journalctl -u volei-gunicorn.service -f

# Ver logs do Nginx
sudo tail -f /var/log/nginx/volei.ledtech.app.error.log

# Testar configuração Nginx
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx

# Status dos serviços
sudo systemctl status volei-gunicorn.service
sudo systemctl status nginx
```

---

## ❗ Problemas Comuns

### Erro 502 Bad Gateway
```bash
# Verificar se Gunicorn está rodando
sudo systemctl status volei-gunicorn.service

# Ver logs
sudo journalctl -u volei-gunicorn.service -n 50
```

### Certificado SSL falhou
```bash
# Verificar DNS
nslookup volei.ledtech.app

# Verificar portas
sudo netstat -tlnp | grep -E ':(80|443)'

# Tentar novamente
sudo bash /var/www/volei.ledtech.app/deploy/setup-ssl.sh
```

### Arquivos estáticos não carregam
```bash
sudo venv/bin/python manage.py collectstatic --noinput
sudo chmod -R 755 /var/www/volei.ledtech.app/static/
sudo systemctl reload nginx
```

---

## 🎉 Pronto!

Seu sistema estará disponível em:
### 🌐 https://volei.ledtech.app
