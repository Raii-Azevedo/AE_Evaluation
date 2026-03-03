# Sistema de Avaliação Técnica - Analytics Engineer

Sistema web desenvolvido em Streamlit para gerenciar processos seletivos e avaliar candidatos a vagas de Analytics Engineer, com foco em critérios técnicos específicos da área.

## 📋 Visão Geral

Este sistema permite:
- **Criar e gerenciar processos seletivos** (Estágio, Pleno) para diferentes regiões (Brasil, LATAM)
- **Cadastrar candidatos** e vinculá-los a processos específicos
- **Avaliar candidatos** com base em critérios técnicos ponderados
- **Visualizar rankings** e detalhes de avaliações
- **Controlar status** de processos (Aberto/Fechado)

## 🎯 Critérios de Avaliação

O sistema avalia candidatos em três blocos principais:

### 1. Tratamentos (Peso Total: 10)
- Arquitetura em Camadas - Raw/Staging/Golden (Peso 1)
- Criação de Dimensões (Peso 2) 🔴 **Obrigatório**
- Tratamento de Tipagem e Strings (Peso 2) 🔴 **Obrigatório**
- Deduplicação (Peso 2) 🔴 **Obrigatório**
- Modelagem de Dados - Star/Snowflake (Peso 3) 🔴 **Obrigatório**

### 2. Análises (Peso Total: 8)
- Escolha das Métricas Estratégicas (Peso 3) 🔴 **Obrigatório**
- Cálculo Correto das Métricas (Peso 3) 🔴 **Obrigatório**
- Storytelling (Peso 2) 🔴 **Obrigatório**

### 3. Visual (Peso Total: 3)
- Organização dos Visuais (Peso 2) 🔴 **Obrigatório**
- Paleta de Cores e Tipografia (Peso 1) 🔴 **Obrigatório**

### Sistema de Notas
- **Nota Final**: Média ponderada de todos os critérios (0-10)
- **Critérios Obrigatórios**: Nota mínima de 6.0 necessária
- **Classificação**:
  - ✅ **Recomendado**: Nota ≥ 8.0
  - ⚠️ **Avaliar melhor**: Nota entre 6.0 e 7.9
  - ❌ **Não recomendado**: Nota < 6.0
  - 🔴 **Reprovado**: Qualquer critério obrigatório < 6.0

## 🏗️ Arquitetura do Projeto

```
AE_Evaluation/
├── app.py              # Aplicação principal Streamlit
├── processo.py         # Módulo de visualização de processos
├── database.py         # Configuração e inicialização do banco
├── criterios.py        # Definição de critérios de avaliação
├── .gitignore          # Arquivos ignorados pelo Git
└── README.md           # Este arquivo
```

## 🗄️ Estrutura do Banco de Dados

O sistema utiliza **PostgreSQL** com as seguintes tabelas:

### `processos`
- `id` (SERIAL PRIMARY KEY)
- `nome` (TEXT) - Nome do processo seletivo
- `area` (TEXT) - Área da vaga (ex: Analytics Engineer)
- `senioridade` (TEXT) - Nível da vaga (Estágio, Pleno)
- `status` (TEXT) - Status do processo (Aberto, Fechado)
- `local` (TEXT) - Localização (BRASIL, LATAM)
- `data_inicio` (TIMESTAMP) - Data de criação

### `candidatos`
- `id` (SERIAL PRIMARY KEY)
- `nome` (TEXT) - Nome do candidato
- `email` (TEXT UNIQUE) - Email do candidato

### `processos_candidatos`
- `id` (SERIAL PRIMARY KEY)
- `processo_id` (INTEGER FK) - Referência ao processo
- `candidato_id` (INTEGER FK) - Referência ao candidato
- `data_vinculo` (TIMESTAMP) - Data de vinculação
- UNIQUE(processo_id, candidato_id)

### `avaliacoes`
- `id` (SERIAL PRIMARY KEY)
- `processo_id` (INTEGER FK) - Referência ao processo
- `candidato_id` (INTEGER FK) - Referência ao candidato
- `nota_final` (NUMERIC) - Nota final ponderada
- `avaliador` (TEXT) - Nome do avaliador
- `comentario_final` (TEXT) - Comentário geral
- `data` (TIMESTAMP) - Data da avaliação

### `avaliacoes_criterios`
- `id` (SERIAL PRIMARY KEY)
- `avaliacao_id` (INTEGER FK) - Referência à avaliação
- `bloco` (TEXT) - Nome do bloco (Tratamentos, Análises, Visual)
- `criterio` (TEXT) - Nome do critério específico
- `nota` (NUMERIC) - Nota atribuída (0-10)
- `justificativa` (TEXT) - Justificativa da nota

## 🚀 Instalação e Configuração

### Pré-requisitos
- Python 3.8+
- PostgreSQL
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
pip install streamlit pandas psycopg2-binary
```

5. **Configure a conexão com o banco de dados**

Edite o arquivo [`database.py`](database.py:7) e configure a string de conexão PostgreSQL:
```python
def get_connection():
    return psycopg2.connect(
        "postgresql://usuario:senha@host:porta/database"
    )
```

Ou configure via variável de ambiente:
```bash
export DATABASE_URL="postgresql://usuario:senha@host:porta/database"
```

6. **Execute a aplicação**
```bash
streamlit run app.py
```

A aplicação estará disponível em `http://localhost:8501`

## 📱 Funcionalidades Principais

### 🏠 Tela Inicial
- Visualização de todos os processos seletivos
- Criação de novos processos
- Acesso rápido aos processos existentes

### 📂 Gestão de Processos
- Adicionar candidatos ao processo
- Buscar candidatos por nome ou email
- Filtrar candidatos por status (Todos, Pendentes, Avaliados)
- Visualizar ranking de candidatos
- Fechar/Reabrir processos

### 📝 Avaliação de Candidatos
- Interface intuitiva com sliders (0-10, step 0.5)
- Campos de justificativa para cada critério
- Cálculo automático da nota final ponderada
- Validação de critérios obrigatórios
- Comentário final geral

### 📊 Visualização de Resultados
- Detalhamento completo de avaliações
- Histórico de avaliações por candidato
- Notas por bloco e critério
- Justificativas detalhadas

## 🎨 Interface

O sistema possui uma interface moderna com:
- **Gradiente de fundo** em tons de azul, roxo e rosa
- **Cards com efeito glassmorphism** e hover animado
- **Código de cores para status**:
  - 🟢 Verde: Recomendado (≥ 8.0)
  - 🟡 Amarelo: Avaliar melhor (6.0-7.9)
  - 🔴 Vermelho: Não recomendado (< 6.0)
  - ⚪ Cinza: Pendente (sem avaliação)

## 📄 Arquivos Principais

### [`app.py`](app.py:1)
Aplicação principal com 4 views:
- **home**: Lista de processos
- **processo**: Detalhes do processo e candidatos
- **avaliar**: Formulário de avaliação
- **detalhe_avaliacao**: Visualização de avaliação completa

### [`database.py`](database.py:1)
- Função [`get_connection()`](database.py:5): Retorna conexão PostgreSQL
- Função [`init_db()`](database.py:11): Cria estrutura de tabelas

### [`criterios.py`](criterios.py:1)
Dicionário com critérios de avaliação alternativos (não utilizado na versão atual do [`app.py`](app.py:1))

### [`processo.py`](processo.py:1)
Módulo alternativo para visualização de processos com foco em ranking

## 🔒 Segurança

- Emails de candidatos são únicos no sistema
- Relacionamento processo-candidato é único (não permite duplicatas)
- Processos fechados impedem novas avaliações
- Cascade delete configurado para manter integridade referencial

## 🛠️ Tecnologias Utilizadas

- **[Streamlit](https://streamlit.io/)**: Framework web para Python
- **[PostgreSQL](https://www.postgresql.org/)**: Banco de dados relacional
- **[psycopg2](https://www.psycopg.org/)**: Adaptador PostgreSQL para Python
- **[Pandas](https://pandas.pydata.org/)**: Manipulação de dados (usado em [`processo.py`](processo.py:1))

## 📝 Notas de Desenvolvimento

- O sistema usa `st.session_state` para gerenciar navegação entre views
- Conexão com banco é mantida durante toda a sessão
- Validação de critérios obrigatórios ocorre em tempo real
- Sistema suporta múltiplas avaliações por candidato

## 🤝 Contribuindo

Para contribuir com o projeto:
1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📧 Contato

Para dúvidas ou sugestões sobre o sistema, entre em contato com a equipe de desenvolvimento.

---

**Desenvolvido para otimizar o processo de avaliação técnica de candidatos a Analytics Engineer** 🚀
