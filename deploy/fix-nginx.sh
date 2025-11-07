#!/bin/bash

echo "=========================================="
echo "Corrigindo problema do Nginx"
echo "=========================================="
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Por favor, execute como root (sudo)"
    exit 1
fi

echo "1. Procurando referências ao certificado assinatura.crt..."
ARQUIVOS=$(grep -r "assinatura.crt" /etc/nginx/ 2>/dev/null | cut -d: -f1 | sort -u)

if [ -z "$ARQUIVOS" ]; then
    echo "✅ Nenhuma referência encontrada"
    exit 0
fi

echo "Arquivos encontrados:"
echo "$ARQUIVOS"
echo ""

for ARQUIVO in $ARQUIVOS; do
    echo "2. Fazendo backup de $ARQUIVO..."
    cp "$ARQUIVO" "$ARQUIVO.backup-$(date +%Y%m%d-%H%M%S)"
    
    echo "3. Comentando linhas com assinatura.crt em $ARQUIVO..."
    sed -i 's/^\(\s*ssl_certificate.*assinatura\.crt.*\)$/# \1 # COMENTADO AUTOMATICAMENTE/' "$ARQUIVO"
    sed -i 's/^\(\s*ssl_certificate_key.*assinatura\.key.*\)$/# \1 # COMENTADO AUTOMATICAMENTE/' "$ARQUIVO"
    
    echo "✅ Arquivo corrigido: $ARQUIVO"
    echo ""
done

echo "4. Testando configuração do Nginx..."
if nginx -t; then
    echo ""
    echo "✅ Configuração do Nginx corrigida com sucesso!"
    echo ""
    echo "5. Recarregando Nginx..."
    systemctl reload nginx
    echo "✅ Nginx recarregado!"
    echo ""
    echo "=========================================="
    echo "Agora você pode executar o deploy novamente:"
    echo "  cd /opt/gerenciador-times"
    echo "  sudo bash deploy/deploy-from-opt.sh"
    echo "=========================================="
else
    echo ""
    echo "❌ Ainda há erros na configuração do Nginx"
    echo "Verifique manualmente os arquivos:"
    echo "$ARQUIVOS"
fi
