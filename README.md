# Sistema de Avaliação Técnica - Analytics Engineer

Sistema web desenvolvido em Streamlit para gerenciar processos seletivos e avaliar candidatos a vagas de Analytics Engineer, com foco em critérios técnicos específicos da área.

---

## 📋 Para Que Serve

Este sistema foi desenvolvido para **automatizar e padronizar o processo de avaliação técnica** de candidatos a vagas de Analytics Engineer. Ele permite que recrutadores e avaliadores técnicos:

- **Centralizem** todos os processos seletivos em um único lugar
- **Padronizem** critérios de avaliação com pesos e obrigatoriedades definidas
- **Acompanhem** o status de cada candidato em tempo real
- **Documentem** justificativas detalhadas para cada nota atribuída
- **Comparem** candidatos de forma objetiva através de notas ponderadas
- **Mantenham histórico** completo de todas as avaliações realizadas

### Principais Benefícios

✅ **Objetividade**: Sistema de pontuação ponderada elimina vieses subjetivos  
✅ **Rastreabilidade**: Todas as avaliações ficam registradas com data, avaliador e justificativas  
✅ **Eficiência**: Interface intuitiva reduz tempo de avaliação  
✅ **Consistência**: Mesmos critérios aplicados a todos os candidatos  
✅ **Transparência**: Candidatos podem receber feedback estruturado baseado nos critérios

---

## 🎯 Critérios de Avaliação

O sistema avalia candidatos em **três blocos principais** com **18 critérios técnicos**:

### 1. 🔧 Tratamentos (9 critérios - Peso Total: 18)
Avalia a capacidade técnica de manipulação e estruturação de dados:

| Critério | Peso | Obrigatório | Descrição |
|----------|------|-------------|-----------|
| Arquitetura em Camadas | 1 | ❌ | Raw (dados brutos), Staging (tratados) e Golden (modelados) |
| Criação de Dimensões | 2 | ✅ | Calendário, dimensões descritivas e tabelas de apoio |
| Tratamento de Tipagem e Strings | 2 | ✅ | Conversão de tipos, padronização de datas, TRIM, UPPER/LOWER |
| Deduplicação | 2 | ✅ | Tratamento de duplicatas e regras de priorização |
| Padronização de Nomenclatura | 2 | ✅ | snake_case, prefixos fact_/dim_, consistência |
| Normalização de Categorias | 2 | ✅ | Consolidação de valores categóricos |
| Avaliação de Hard-Coding | 2 | ✅ | Evitar regras fixas, preferir tabelas de-para |
| Modelagem de Dados (Star/Snowflake) | 3 | ✅ | Fatos, dimensões, relacionamentos e granularidade |
| Organização do Dashboard | 2 | ✅ | Medidas organizadas, relacionamentos e cardinalidade |

### 2. 📊 Análises (6 critérios - Peso Total: 14)
Avalia a capacidade analítica e de geração de insights:

| Critério | Peso | Obrigatório | Descrição |
|----------|------|-------------|-----------|
| Escolha das Métricas Estratégicas | 3 | ✅ | KPIs relevantes: Receita, CAC, LTV, Conversão, Churn |
| Cálculo Correto das Métricas | 3 | ✅ | Fórmulas corretas respeitando granularidade e contexto |
| Evolução dos Indicadores | 2 | ✅ | Análise temporal, tendências e sazonalidade |
| Segmentação das Métricas | 2 | ✅ | Análise por canal, produto, região ou cliente |
| Storytelling | 2 | ✅ | Narrativa lógica com insights e impactos |
| Relatório Executivo vs Operacional | 2 | ✅ | Separação entre visão estratégica e exploratória |

### 3. 🎨 Visual (4 critérios - Peso Total: 6)
Avalia a qualidade da apresentação visual dos dados:

| Critério | Peso | Obrigatório | Descrição |
|----------|------|-------------|-----------|
| Organização dos Visuais | 2 | ✅ | Layout limpo, alinhamento e hierarquia visual |
| Filtros e Segmentadores | 2 | ✅ | Filtros estratégicos facilitando navegação |
| Paleta de Cores e Tipografia | 1 | ✅ | Cores consistentes, contraste e legibilidade |
| Títulos e Unidades de Medida | 1 | ✅ | Títulos claros, unidades visíveis e rótulos legíveis |

### 📐 Sistema de Notas

- **Nota Final**: Média ponderada de todos os critérios (0-10)
- **Escala**: 0.0 a 10.0 (incrementos de 0.5)
- **Critérios Obrigatórios**: Nota mínima de 6.0 necessária (16 de 18 critérios)
- **Classificação Automática**:
  - 🟢 **Recomendado**: Nota ≥ 8.0
  - 🟡 **Avaliar melhor**: Nota entre 6.0 e 7.9
  - 🔴 **Não recomendado**: Nota < 6.0
  - ⚪ **Pendente**: Sem avaliação

---

## 🔑 Pontos-Chave de Funcionamento

### 1. 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT APP                        │
│                      (app.py)                           │
├─────────────────────────────────────────────────────────┤
│  Views:                                                 │
│  • Home          → Lista processos                      │
│  • Processo      → Gerencia candidatos                  │
│  • Avaliar       → Formulário de avaliação              │
│  • Detalhe       → Visualiza avaliação completa         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              DATABASE LAYER (database.py)               │
│  • get_connection() → Conexão PostgreSQL                │
│  • init_db()        → Criação de tabelas                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   POSTGRESQL DATABASE                   │
│  Tabelas:                                               │
│  • processos              • avaliacoes                  │
│  • candidatos             • avaliacoes_criterios        │
│  • processos_candidatos                                 │
└─────────────────────────────────────────────────────────┘
```

### 2. 🔄 Fluxo de Trabalho

```
1. CRIAR PROCESSO
   ↓
2. ADICIONAR CANDIDATOS
   ↓
3. AVALIAR CANDIDATOS
   │  ├─ Preencher notas (0-10)
   │  ├─ Justificar cada critério
   │  ├─ Validar obrigatórios (≥6.0)
   │  └─ Calcular nota final ponderada
   ↓
4. VISUALIZAR RESULTADOS
   │  ├─ Ranking de candidatos
   │  ├─ Detalhes da avaliação
   │  └─ Histórico completo
   ↓
5. FECHAR PROCESSO
```

### 3. 💾 Modelo de Dados

**Relacionamentos:**
```
processos (1) ──┬── (N) processos_candidatos (N) ── (1) candidatos
                │
                └── (N) avaliacoes ──── (N) avaliacoes_criterios
                         │
                         └── (N) candidatos
```

**Integridade Referencial:**
- `ON DELETE CASCADE`: Ao deletar processo, remove candidatos vinculados e avaliações
- `UNIQUE(processo_id, candidato_id)`: Impede duplicação de vínculo
- `UNIQUE(email)`: Garante unicidade de candidatos

### 4. 🎯 Cálculo da Nota Final

```python
# Fórmula da Nota Ponderada
nota_final = Σ(nota_criterio × peso_criterio) / Σ(pesos)

# Exemplo:
# Tratamentos: (8×1 + 7×2 + 9×2 + 8×2 + 7×2 + 8×2 + 9×2 + 8×3 + 7×2) = 142
# Análises:    (9×3 + 8×3 + 7×2 + 8×2 + 9×2 + 8×2) = 108
# Visual:      (8×2 + 7×2 + 9×1 + 8×1) = 47
# Total:       (142 + 108 + 47) / (18 + 14 + 6) = 297 / 38 = 7.82
```

### 5. 🔐 Controle de Acesso e Status

- **Processo Aberto**: Permite adicionar candidatos e criar avaliações
- **Processo Fechado**: Modo somente leitura, impede novas avaliações
- **Session State**: Gerencia navegação e estado da aplicação
- **Validação em Tempo Real**: Critérios obrigatórios validados durante preenchimento

### 6. 🔍 Funcionalidades de Busca e Filtro

- **Busca por texto**: Nome ou email do candidato
- **Filtro por status**: Todos / Pendentes / Avaliados
- **Ordenação automática**: Candidatos pendentes aparecem primeiro
- **Indicadores visuais**: Cores diferentes para cada faixa de nota

---

## 🗄️ Estrutura do Banco de Dados

### Tabela: `processos`
```sql
CREATE TABLE processos (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    area TEXT,                    -- Ex: "Analytics Engineer"
    tipo TEXT,                    -- Ex: "Ampla Concorrência"
    senioridade TEXT,             -- Ex: "Pleno", "Estágio"
    status TEXT,                  -- "Aberto" ou "Fechado"
    local TEXT,                   -- "BRASIL" ou "LATAM"
    data_inicio TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `candidatos`
```sql
CREATE TABLE candidatos (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT UNIQUE             -- Email único no sistema
);
```

### Tabela: `processos_candidatos`
```sql
CREATE TABLE processos_candidatos (
    id SERIAL PRIMARY KEY,
    processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
    candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
    data_vinculo TIMESTAMP DEFAULT NOW(),
    UNIQUE(processo_id, candidato_id)  -- Impede duplicação
);
```

### Tabela: `avaliacoes`
```sql
CREATE TABLE avaliacoes (
    id SERIAL PRIMARY KEY,
    processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
    candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
    nota_final NUMERIC,           -- Nota ponderada final
    avaliador TEXT,               -- Nome do avaliador
    comentario_final TEXT,        -- Comentário geral
    data TIMESTAMP DEFAULT NOW()
);
```

### Tabela: `avaliacoes_criterios`
```sql
CREATE TABLE avaliacoes_criterios (
    id SERIAL PRIMARY KEY,
    avaliacao_id INTEGER REFERENCES avaliacoes(id) ON DELETE CASCADE,
    bloco TEXT,                   -- "Tratamentos", "Análises", "Visual"
    criterio TEXT,                -- Nome do critério específico
    nota NUMERIC,                 -- Nota de 0 a 10
    justificativa TEXT            -- Justificativa detalhada
);
```

---

## 🚀 Instalação e Configuração

### Pré-requisitos
- Python 3.8 ou superior
- PostgreSQL 12 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

1. **Clone o repositório**
```bash
git clone <url-do-repositorio>
cd AE_Evaluation
```

2. **Crie um ambiente virtual**
```bash
python -m venv venv
```

3. **Ative o ambiente virtual**
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. **Instale as dependências**
```bash
pip install -r requirements.txt
```

5. **Configure a variável de ambiente do banco de dados**

Windows (CMD):
```bash
set DATABASE_URL=postgresql://usuario:senha@localhost:5432/nome_database
```

Windows (PowerShell):
```powershell
$env:DATABASE_URL="postgresql://usuario:senha@localhost:5432/nome_database"
```

Linux/Mac:
```bash
export DATABASE_URL="postgresql://usuario:senha@localhost:5432/nome_database"
```

6. **Execute a aplicação**
```bash
streamlit run app.py
```

A aplicação estará disponível em `http://localhost:8501`

---

## 📱 Funcionalidades Detalhadas

### 🏠 Tela Inicial (Home)
- **Criar Processo**: Formulário expansível com todos os campos necessários
- **Listar Processos**: Cards com informações resumidas e botão de acesso
- **Informações Exibidas**: Nome, área, tipo, senioridade, local e status

### 📂 Gestão de Processos
- **Adicionar Candidatos**: Formulário com nome e email (valida duplicatas)
- **Busca Inteligente**: Filtra por nome ou email em tempo real
- **Filtros de Status**: Visualiza todos, apenas pendentes ou apenas avaliados
- **Ordenação Automática**: Pendentes aparecem primeiro para priorização
- **Indicadores Visuais**: Cards coloridos conforme nota final
- **Fechar Processo**: Bloqueia novas avaliações mantendo histórico

### 📝 Avaliação de Candidatos
- **Interface Intuitiva**: Sliders de 0 a 10 com incrementos de 0.5
- **Descrições Detalhadas**: Cada critério possui descrição explicativa
- **Indicação de Peso**: Peso de cada critério visível durante avaliação
- **Marcação de Obrigatórios**: Critérios obrigatórios claramente identificados
- **Justificativas**: Campo de texto para documentar cada nota
- **Cálculo em Tempo Real**: Nota final atualiza conforme preenchimento
- **Validação Automática**: Sistema valida critérios obrigatórios
- **Comentário Final**: Campo para observações gerais sobre o candidato

### 📊 Visualização de Resultados
- **Nota Final Destacada**: Métrica principal em destaque
- **Informações do Avaliador**: Nome e data da avaliação
- **Detalhamento por Bloco**: Notas organizadas por categoria
- **Justificativas Completas**: Todas as justificativas registradas
- **Histórico Preservado**: Múltiplas avaliações por candidato mantidas

---

## 🎨 Interface e Design

### Paleta de Cores
- **Fundo**: Gradiente azul → roxo → rosa (`#0B1E3D` → `#3A1C71` → `#D4145A`)
- **Cards**: Glassmorphism com backdrop blur e bordas translúcidas
- **Status**:
  - 🟢 Verde (`#22c55e`): Recomendado (≥ 8.0)
  - 🟡 Amarelo (`#facc15`): Avaliar melhor (6.0-7.9)
  - 🔴 Vermelho (`#ef4444`): Não recomendado (< 6.0)
  - ⚪ Cinza (`#9ca3af`): Pendente

### Efeitos Visuais
- **Hover nos Cards**: Elevação com `translateY(-6px)` e sombra expandida
- **Botões**: Gradiente azul-rosa com hover animado
- **Inputs**: Fundo translúcido com bordas suaves
- **Transições**: Animações suaves de 0.25s

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Versão | Propósito |
|------------|--------|-----------|
| **Python** | 3.8+ | Linguagem principal |
| **Streamlit** | Latest | Framework web interativo |
| **PostgreSQL** | 12+ | Banco de dados relacional |
| **psycopg2-binary** | Latest | Driver PostgreSQL para Python |
| **Pandas** | Latest | Manipulação de dados (módulo processo.py) |

### Dependências Adicionais (requirements.txt)
```
streamlit
pandas
psycopg2-binary
streamlit-authenticator
bcrypt
PyYAML
```

---

## 📂 Estrutura de Arquivos

```
AE_Evaluation/
│
├── app.py                    # ⭐ Aplicação principal Streamlit
│   ├── View: home           # Lista de processos
│   ├── View: processo       # Gestão de candidatos
│   ├── View: avaliar        # Formulário de avaliação
│   └── View: detalhe        # Detalhes da avaliação
│
├── database.py              # 💾 Camada de banco de dados
│   ├── get_connection()    # Conexão PostgreSQL
│   └── init_db()           # Inicialização de tabelas
│
├── processo.py              # 📊 Módulo alternativo (ranking)
├── criterios.py             # 📋 Definições de critérios (não usado)
│
├── requirements.txt         # 📦 Dependências Python
├── .gitignore              # 🚫 Arquivos ignorados
└── README.md               # 📖 Esta documentação
```

---

## 🔒 Segurança e Integridade

### Validações Implementadas
✅ Email único por candidato  
✅ Vínculo único processo-candidato  
✅ Validação de critérios obrigatórios (≥ 6.0)  
✅ Processos fechados bloqueiam novas avaliações  
✅ Cascade delete mantém integridade referencial  

### Boas Práticas
✅ Uso de prepared statements (proteção contra SQL injection)  
✅ Validação de dados no frontend  
✅ Session state para gerenciamento de estado  
✅ Timestamps automáticos para auditoria  

---

## 📊 Possíveis Melhorias

### 🔐 Segurança e Autenticação
- [ ] **Sistema de Login**: Implementar autenticação com `streamlit-authenticator`
- [ ] **Controle de Permissões**: Diferentes níveis de acesso (Admin, Avaliador, Visualizador)
- [ ] **Auditoria Completa**: Log de todas as ações (quem criou, editou, deletou)
- [ ] **Criptografia de Dados Sensíveis**: Proteger informações pessoais dos candidatos
- [ ] **Sessões Seguras**: Timeout automático e gerenciamento de sessões
- [ ] **Variáveis de Ambiente**: Migrar credenciais para arquivo `.env`

### 📊 Funcionalidades de Análise
- [ ] **Dashboard Analítico**: Gráficos de desempenho por processo
- [ ] **Comparação de Candidatos**: Visualização lado a lado de avaliações
- [ ] **Estatísticas Gerais**: Média de notas, taxa de aprovação, tempo médio
- [ ] **Exportação de Relatórios**: PDF, Excel com avaliações completas
- [ ] **Gráficos de Radar**: Visualização das competências por candidato
- [ ] **Análise de Tendências**: Evolução das notas ao longo do tempo
- [ ] **Benchmarking**: Comparação com médias históricas

### 🎯 Melhorias na Avaliação
- [ ] **Avaliação Colaborativa**: Múltiplos avaliadores por candidato
- [ ] **Pesos Customizáveis**: Permitir ajustar pesos por processo
- [ ] **Critérios Dinâmicos**: Adicionar/remover critérios por processo
- [ ] **Templates de Avaliação**: Salvar estruturas para reutilização
- [ ] **Comentários por Bloco**: Além de comentário final
- [ ] **Anexos**: Upload de arquivos (portfólio, testes técnicos)
- [ ] **Avaliação Cega**: Ocultar nome do candidato durante avaliação

### 🔄 Gestão de Processos
- [ ] **Workflow Completo**: Etapas (Triagem → Técnica → Cultural → Final)
- [ ] **Notificações**: Email automático para candidatos e avaliadores
- [ ] **Agendamento**: Integração com calendário para entrevistas
- [ ] **Status Customizáveis**: Além de Aberto/Fechado (Em Andamento, Pausado, etc.)
- [ ] **Clonagem de Processos**: Duplicar estrutura de processos anteriores
- [ ] **Arquivamento**: Arquivar processos antigos sem deletar
- [ ] **Tags e Categorias**: Organização adicional de processos

### 💾 Banco de Dados e Performance
- [ ] **Connection Pooling**: Otimizar conexões com PostgreSQL
- [ ] **Índices**: Adicionar índices em campos frequentemente consultados
- [ ] **Paginação**: Implementar para listas grandes de candidatos
- [ ] **Cache**: Usar `@st.cache_data` para queries repetitivas
- [ ] **Backup Automático**: Rotina de backup do banco de dados
- [ ] **Migrations**: Sistema de versionamento de schema (Alembic)
- [ ] **Soft Delete**: Marcar como deletado ao invés de remover

### 🎨 Interface e UX
- [ ] **Modo Escuro/Claro**: Toggle entre temas
- [ ] **Responsividade Mobile**: Otimizar para dispositivos móveis
- [ ] **Atalhos de Teclado**: Navegação rápida
- [ ] **Feedback Visual**: Loading spinners, toasts de sucesso/erro
- [ ] **Validação em Tempo Real**: Feedback imediato em formulários
- [ ] **Tour Guiado**: Onboarding para novos usuários
- [ ] **Internacionalização**: Suporte a múltiplos idiomas (PT/EN/ES)

### 📱 Integrações
- [ ] **API REST**: Expor funcionalidades via API
- [ ] **Integração com ATS**: Greenhouse, Lever, BambooHR
- [ ] **Slack/Teams**: Notificações em tempo real
- [ ] **Google Calendar**: Agendamento de entrevistas
- [ ] **LinkedIn**: Importar dados de candidatos
- [ ] **Zapier/Make**: Automações personalizadas
- [ ] **Webhooks**: Eventos customizados

### 🧪 Qualidade e Testes
- [ ] **Testes Unitários**: Pytest para funções críticas
- [ ] **Testes de Integração**: Validar fluxos completos
- [ ] **CI/CD**: Pipeline automatizado (GitHub Actions)
- [ ] **Linting**: Black, Flake8, MyPy
- [ ] **Documentação de Código**: Docstrings completas
- [ ] **Logs Estruturados**: Sistema de logging robusto
- [ ] **Monitoramento**: Sentry para tracking de erros

### 📈 Escalabilidade
- [ ] **Containerização**: Docker e Docker Compose
- [ ] **Deploy em Cloud**: AWS, GCP ou Azure
- [ ] **Load Balancing**: Suporte a múltiplas instâncias
- [ ] **CDN**: Para assets estáticos
- [ ] **Redis**: Cache distribuído
- [ ] **Microserviços**: Separar funcionalidades críticas
- [ ] **Kubernetes**: Orquestração de containers

### 🤖 Inteligência Artificial
- [ ] **Análise de Currículo**: NLP para extração automática de dados
- [ ] **Sugestão de Notas**: IA sugere notas baseadas em histórico
- [ ] **Detecção de Viés**: Alertas sobre possíveis vieses na avaliação
- [ ] **Matching Automático**: Score de fit candidato-vaga
- [ ] **Chatbot**: Assistente para dúvidas sobre critérios
- [ ] **Análise de Sentimento**: Avaliar comentários e justificativas

### 📋 Compliance e Governança
- [ ] **LGPD/GDPR**: Conformidade com leis de proteção de dados
- [ ] **Termo de Consentimento**: Aceite de candidatos
- [ ] **Anonimização**: Opção de anonimizar dados após processo
- [ ] **Retenção de Dados**: Política de exclusão automática
- [ ] **Auditoria Completa**: Trilha de todas as alterações
- [ ] **Relatórios de Compliance**: Documentação para auditorias

---

## 🤝 Contribuindo

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

### Padrões de Código
- Use **snake_case** para variáveis e funções
- Use **PascalCase** para classes
- Docstrings em todas as funções públicas
- Máximo de 100 caracteres por linha
- Type hints quando possível

---

## 📝 Notas de Desenvolvimento

### Session State
O sistema usa `st.session_state` para gerenciar:
- `view`: View atual (home, processo, avaliar, detalhe_avaliacao)
- `processo_id`: ID do processo selecionado
- `candidato_id`: ID do candidato sendo avaliado
- `avaliacao_id`: ID da avaliação sendo visualizada
- Notas e justificativas durante avaliação

### Conexão com Banco
- Conexão estabelecida no início da aplicação
- Mantida durante toda a sessão
- Usa variável de ambiente `DATABASE_URL`
- Prepared statements para segurança

### Validações
- Critérios obrigatórios validados em tempo real
- Email único verificado antes de inserção
- Vínculo processo-candidato único (ON CONFLICT DO NOTHING)
- Processos fechados impedem novas avaliações

---

## 📧 Suporte

Para dúvidas, sugestões ou reportar problemas:
- Abra uma issue no repositório
- Entre em contato com a equipe de desenvolvimento

---

## 📄 Licença

Este projeto é proprietário e destinado ao uso interno da organização.

---

**Desenvolvido para otimizar e padronizar o processo de avaliação técnica de candidatos a Analytics Engineer** 🚀

*Última atualização: Março 2026*
