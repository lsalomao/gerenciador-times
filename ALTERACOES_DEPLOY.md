# 📝 Resumo das Alterações para Deploy na VPS

## ✅ Arquivos Criados/Modificados

### Novos Arquivos:
1. **docker-compose.yml** - Orquestração de containers (Django, PostgreSQL, Nginx, Certbot)
2. **.env.example** - Template de variáveis de ambiente
3. **.dockerignore** - Otimização do build Docker
4. **sites-available/volei** - Configuração correta do Nginx para o projeto
5. **DEPLOY_VPS.md** - Documentação completa de deploy
6. **deploy-rapido.sh** - Script automatizado de deploy

### Arquivos Modificados:
1. **requirements.txt** - Adicionadas dependências de produção:
   - whitenoise (servir arquivos estáticos)
   - psycopg2-binary (PostgreSQL)
   - python-dotenv (variáveis de ambiente)

2. **gerenciador_volei/settings.py** - Configurações de produção:
   - Suporte a PostgreSQL via variáveis de ambiente
   - WhiteNoise middleware para arquivos estáticos
   - CSRF_TRUSTED_ORIGINS configurável
   - Configurações de segurança para produção (SSL, HSTS, etc)
   - Suporte a arquivos de media

## 🚀 Como Fazer Deploy

### Opção 1: Deploy Automatizado (Recomendado)

```bash
# Na VPS, como root:
sudo chmod +x deploy-rapido.sh
sudo ./deploy-rapido.sh
```

O script irá:
- Instalar Docker (se necessário)
- Configurar variáveis de ambiente automaticamente
- Gerar senhas seguras
- Construir e iniciar containers
- Configurar SSL com Let's Encrypt
- Executar migrações

### Opção 2: Deploy Manual

Siga o guia completo em **DEPLOY_VPS.md**

## 🔧 Configurações Importantes

### Antes do Deploy:

1. **Domínio**: Aponte `volei.ledtech.app` para o IP da VPS
2. **Firewall**: Libere portas 80, 443 e 22
3. **Email**: Tenha um email válido para certificado SSL

### Após o Deploy:

```bash
# Criar superusuário
docker-compose exec web python manage.py createsuperuser

# Ver logs
docker-compose logs -f

# Reiniciar serviços
docker-compose restart
```

## 📊 Estrutura dos Containers

- **web**: Django + Gunicorn (porta 8000)
- **db**: PostgreSQL 15 (porta 5432)
- **nginx**: Proxy reverso (portas 80/443)
- **certbot**: Renovação automática de SSL

## 🔒 Segurança

✅ SSL/TLS automático com Let's Encrypt
✅ Senhas geradas automaticamente
✅ DEBUG=False em produção
✅ HSTS habilitado
✅ Cookies seguros
✅ CSRF protection

## 📝 Variáveis de Ambiente (.env)

```env
DEBUG=False
SECRET_KEY=<gerada automaticamente>
ALLOWED_HOSTS=volei.ledtech.app,www.volei.ledtech.app
DB_ENGINE=django.db.backends.postgresql
DB_NAME=volei_db
DB_USER=volei_user
DB_PASSWORD=<gerada automaticamente>
DB_HOST=db
DB_PORT=5432
CSRF_TRUSTED_ORIGINS=https://volei.ledtech.app,https://www.volei.ledtech.app
```

## 🎯 Próximos Passos

1. Enviar código para VPS (git clone ou scp)
2. Executar `deploy-rapido.sh`
3. Criar superusuário
4. Acessar https://volei.ledtech.app
5. Configurar backup automático (opcional)

## 🐛 Troubleshooting

Ver **DEPLOY_VPS.md** seção "Troubleshooting" para:
- Problemas com containers
- Erros de SSL
- Arquivos estáticos não carregam
- Problemas de permissão

---

**Status**: ✅ Pronto para deploy na VPS
