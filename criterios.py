CRITERIOS = {
    "Tratamentos": [
        {
            "criterio": "Arquitetura em Camadas (Raw / Staging / Golden)",
            "descricao": "Raw (dados brutos), Staging (dados tratados e padronizados) e Golden (dados modelados e prontos para consumo analítico).",
            "peso": 1,
            "obrigatorio": False
        },
        {
            "criterio": "Criação de Dimensões",
            "descricao": "Construção de dimensões auxiliares como calendário (ano, mês, trimestre, semana etc.), dimensões descritivas (produto, cliente, canal, status) e tabelas de apoio.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Tratamento de Tipagem e Strings",
            "descricao": "Conversão adequada de tipos de dados, padronização de datas, TRIM, UPPER/LOWER, garantindo integridade nos joins.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Deduplicação",
            "descricao": "Tratamento de registros duplicados evitando explosão de métricas e aplicação de regras de priorização.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Padronização de Nomenclatura",
            "descricao": "Uso de padrão para nomes de tabelas e colunas (snake_case, prefixos fact_/dim_), garantindo consistência.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Normalização de Categorias",
            "descricao": "Consolidação e padronização de valores categóricos (ex: Google Ads, status etc.).",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Avaliação de Hard-Coding",
            "descricao": "Evitar regras fixas excessivas e preferir tabelas de-para para manutenção e governança.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Modelagem de Dados (Star / Snowflake)",
            "descricao": "Estruturação com fatos e dimensões bem definidas, relacionamento correto e granularidade clara.",
            "peso": 3,
            "obrigatorio": True
        },
        {
            "criterio": "Organização do Dashboard (Medidas e Relacionamentos)",
            "descricao": "Medidas organizadas, relacionamentos consistentes e uso adequado de cardinalidade e direção de filtro.",
            "peso": 2,
            "obrigatorio": True
        },
    ],

    "Análises": [
        {
            "criterio": "Escolha das Métricas Estratégicas",
            "descricao": "Definição de KPIs relevantes como Receita, Ticket Médio, CAC, LTV, Conversão e Churn.",
            "peso": 3,
            "obrigatorio": True
        },
        {
            "criterio": "Cálculo Correto das Métricas",
            "descricao": "Implementação correta das fórmulas respeitando granularidade, filtros e contexto.",
            "peso": 3,
            "obrigatorio": True
        },
        {
            "criterio": "Evolução dos Indicadores",
            "descricao": "Apresentação temporal dos KPIs permitindo análise de tendência e sazonalidade.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Segmentação das Métricas",
            "descricao": "Análise por canal, produto, região ou cliente com gráficos adequados.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Storytelling",
            "descricao": "Construção de narrativa lógica com destaque de insights e impactos.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Relatório Executivo vs Operacional",
            "descricao": "Separação clara entre visão estratégica (KPIs principais) e visão exploratória detalhada.",
            "peso": 2,
            "obrigatorio": True
        },
    ],

    "Visual": [
        {
            "criterio": "Organização dos Visuais",
            "descricao": "Layout limpo, alinhamento consistente, espaçamento adequado e hierarquia visual clara.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Filtros e Segmentadores",
            "descricao": "Criação estratégica de filtros (data, canal, produto etc.) facilitando navegação.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Paleta de Cores e Tipografia",
            "descricao": "Uso consistente de cores, contraste adequado e tipografia legível.",
            "peso": 1,
            "obrigatorio": True
        },
        {
            "criterio": "Títulos e Unidades de Medida",
            "descricao": "Títulos claros, unidades visíveis (R$ 10k) e rótulos legíveis.",
            "peso": 1,
            "obrigatorio": True
        },
    ]
}