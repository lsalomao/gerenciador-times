# Gerenciador de Times de Vôlei

Sistema web para gerenciamento de times de vôlei, desenvolvido com Django. Permite cadastro de jogadores, controle de presenças e formação automática de times equilibrados.

## Funcionalidades

- **Cadastro de Jogadores**: Gerencie jogadores com nome, nível de habilidade (1-5) e status ativo/inativo
- **Controle de Presenças**: Registre a presença dos jogadores para cada data de jogo
- **Formação Automática de Times**: Algoritmo inteligente que distribui jogadores em times equilibrados baseado nos níveis
- **Ajustes Manuais**: Edite manualmente a composição dos times após a geração automática
- **Interface Responsiva**: Design moderno com Bootstrap 5

## Tecnologias

- Python 3.11+
- Django 5.0+
- Bootstrap 5
- SQLite (desenvolvimento) / PostgreSQL (produção recomendado)

## Instalação e Execução

### Desenvolvimento Local

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd gerenciador_volei
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute as migrações:
```bash
python manage.py migrate
```

5. Crie um superusuário (opcional):
```bash
python manage.py createsuperuser
```

6. Inicie o servidor de desenvolvimento:
```bash
python manage.py runserver
```

7. Acesse o sistema em: http://localhost:8000

### Deploy com Docker

1. Build da imagem:
```bash
docker build -t gerenciador-volei .
```

2. Execute o container:
```bash
docker run -d -p 8000:8000 \
  -e SECRET_KEY='sua-chave-secreta-aqui' \
  -e DEBUG='False' \
  -e ALLOWED_HOSTS='seu-dominio.com' \
  gerenciador-volei
```

## Uso do Sistema

### 1. Cadastrar Jogadores
- Acesse "Jogadores" no menu
- Clique em "Novo Jogador"
- Preencha nome e nível (1-5)
- Marque como ativo

### 2. Registrar Presenças
- Acesse "Presenças" no menu
- Clique em "Gerenciar Presenças"
- Selecione a data do jogo
- Marque os jogadores presentes
- Salve as alterações

### 3. Gerar Times
- Acesse "Times" no menu
- Clique em "Gerar Times"
- Selecione a data (deve ter pelo menos 10 jogadores confirmados)
- O sistema criará automaticamente times equilibrados

### 4. Ajustar Times (Opcional)
- Na lista de times, clique em "Editar"
- Ajuste manualmente os jogadores titulares e reservas
- Salve as alterações

## Regras de Negócio

- **Mínimo de Jogadores**: 10 jogadores confirmados para gerar times
- **Composição dos Times**: 4 titulares + 1 reserva por time
- **Máximo de Times**: Até 4 times por data
- **Equilíbrio**: Algoritmo distribui jogadores para equilibrar a soma dos níveis entre os times
- **Níveis**: Escala de 1 (iniciante) a 5 (avançado)

## Estrutura do Projeto

```
gerenciador_volei/
├── gerenciador_volei/     # Configurações do projeto
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── volei/                 # App principal
│   ├── models.py          # Modelos: Jogador, Presenca, Time
│   ├── views.py           # Views e lógica de negócio
│   ├── forms.py           # Formulários
│   ├── urls.py            # URLs do app
│   ├── admin.py           # Admin do Django
│   └── templates/         # Templates HTML
├── static/                # Arquivos estáticos
├── Dockerfile             # Configuração Docker
├── requirements.txt       # Dependências Python
└── manage.py              # CLI do Django
```

## Variáveis de Ambiente

Para produção, configure as seguintes variáveis:

- `SECRET_KEY`: Chave secreta do Django (obrigatório em produção)
- `DEBUG`: `False` para produção
- `ALLOWED_HOSTS`: Domínios permitidos (separados por vírgula)

## Licença

Este projeto é de código aberto e está disponível sob a licença MIT.
