Roteiro de Tarefas para Desenvolvimento do Sistema de Gerenciamento de Times de Vôlei
1. Configuração Inicial do Projeto 
 Iniciar projeto Django (django-admin startproject)
 Criar app principal (ex: volei)
 Configurar banco de dados SQLite
 Configurar arquivos estáticos e templates
 Configurar Bootstrap (ou outro framework CSS) para responsividade
2. Modelagem e Migrações
 Implementar models: Jogador, Presenca, Time
 Criar e aplicar migrações iniciais
 Registrar models no admin do Django para facilitar testes
3. Funcionalidades de Jogadores
 Criar views e templates para cadastro, edição e listagem de jogadores
 Implementar validação de nível (1 a 5)
 Adicionar opção de ativar/desativar jogador
4. Gestão de Presenças
 Criar interface para marcar presença dos jogadores em cada data
 Exibir lista de jogadores confirmados para a próxima partida
 Permitir edição de presenças
5. Formação de Times
 Implementar lógica de geração automática de times equilibrados (4 titulares + 1 reserva por time)
 Criar view/template para exibir os times formados
 Permitir que o organizador gere novamente os times, se desejar
6. Ajustes Manuais nos Times
 Criar interface para edição manual dos times (troca de jogadores entre times e reservas)
 Salvar alterações feitas manualmente
7. Gestão de Ausências e Substituições
 Permitir substituição de jogadores ausentes por reservas do mesmo nível
 Atualizar times após substituições
8. Aprimoramento da Interface
 Garantir responsividade das telas (testar em diferentes tamanhos de tela)
 Melhorar usabilidade e navegação entre as páginas
9. Autenticação e Segurança (Opcional para MVP)
 Implementar autenticação básica para o organizador (login/senha)
 Restringir acesso às funções administrativas
10. Testes e Validação
 Testar todas as funcionalidades (cadastro, presença, geração e edição de times)
 Corrigir bugs e ajustar fluxos conforme feedback
11. Preparação para Deploy
 Criar Dockerfile para deploy em produção
 Testar build e execução do container Docker
 Documentar instruções de instalação e uso
12. Documentação
 Atualizar/ajustar o arquivo especificacao.md conforme implementações
 Criar um README.md com instruções de uso e deploy