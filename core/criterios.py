CRITERIOS_POR_AREA = {
    "Analytics Engineer": {
        "Tratamentos": [
            {"criterio": "Arquitetura em Camadas (Raw / Staging / Golden)", "peso": 1, "obrigatorio": False},
            {"criterio": "Criação de Dimensões", "peso": 2, "obrigatorio": True},
            {"criterio": "Tratamento de Tipagem e Strings", "peso": 2, "obrigatorio": True},
            {"criterio": "Deduplicação", "peso": 2, "obrigatorio": True},
            {"criterio": "Padronização de Nomenclatura", "peso": 2, "obrigatorio": True},
            {"criterio": "Normalização de Categorias", "peso": 2, "obrigatorio": True},
            {"criterio": "Avaliação de Hard-Coding", "peso": 2, "obrigatorio": True},
            {"criterio": "Modelagem de Dados (Star / Snowflake)", "peso": 3, "obrigatorio": True},
            {"criterio": "Organização do Dashboard (Medidas e Relacionamentos)", "peso": 2, "obrigatorio": True},
        ],
        "Análises": [
            {"criterio": "Escolha das Métricas Estratégicas", "peso": 3, "obrigatorio": True},
            {"criterio": "Cálculo Correto das Métricas", "peso": 3, "obrigatorio": True},
            {"criterio": "Evolução dos Indicadores", "peso": 2, "obrigatorio": True},
            {"criterio": "Segmentação das Métricas", "peso": 2, "obrigatorio": True},
            {"criterio": "Storytelling", "peso": 2, "obrigatorio": True},
            {"criterio": "Relatório Executivo vs Operacional", "peso": 2, "obrigatorio": True},
        ],
        "Visual": [
            {"criterio": "Organização dos Visuais", "peso": 2, "obrigatorio": True},
            {"criterio": "Filtros e Segmentadores", "peso": 2, "obrigatorio": True},
            {"criterio": "Paleta de Cores e Tipografia", "peso": 1, "obrigatorio": True},
            {"criterio": "Títulos e Unidades de Medida", "peso": 1, "obrigatorio": True},
        ],
    }
}


def get_criterios_por_area(area):
    return CRITERIOS_POR_AREA.get(area or "Analytics Engineer", CRITERIOS_POR_AREA["Analytics Engineer"])


def get_areas_disponiveis():
    return list(CRITERIOS_POR_AREA.keys())
