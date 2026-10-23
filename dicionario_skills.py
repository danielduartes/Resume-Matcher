# O NER do spaCy não consegue identificar bem o que são as skills em um currículo ou os requisitos em uma vaga. Para corrigir isso, criamos um arquivo para mostramos ao nosso NER siglas e palavras que são classificadas como skills. 

import spacy
from spacy.matcher import PhraseMatcher
from pathlib import Path

# Dicionário de skills => "nome padronizado": "lista com formas em que a palavra pode ser escrita"
SKILLS = {
    "python": ["python"],
    "sql": ["sql"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "git": ["git", "versionamento de código", "controle de versão"],
    "postgresql": ["postgresql", "postgres"],
    "linux": ["linux"],
    "rust": ["rust"],
    "javascript": ["javascript"],
    "typescript": ["typescript"],
    "nix": ["nix"],
    "linguagens funcionais": ["haskell", "ocaml", "lisp", "clojure", "scheme", "f#"],
    "machine learning": ["machine learning", "aprendizado de máquina", "aprendizado de maquina"],
    "inteligência artificial": ["inteligência artificial", "inteligencia artificial"],
    "ia generativa": ["ia generativa", "inteligência artificial generativa"],
    "estatística": ["estatística", "estatistica", "estatísticos", "estatísticas"],
    "análise exploratória": ["análise exploratória", "análises exploratórias", "analise exploratoria"],
    "análise de dados": ["análise de dados", "análises de dados"],
    "ciência de dados": ["ciência de dados", "ciencia de dados", "data science"],
    "engenharia de dados": ["engenharia de dados", "data engineering"],
    "regressão": ["regressão", "regressao"],
    "classificação": ["classificação", "classificacao"],
    "árvores de decisão": ["árvores de decisão", "árvore de decisão", "arvores de decisao"],
    "overfitting": ["overfitting"],
    "dashboards": ["dashboard", "dashboards"],
    "business intelligence": ["business intelligence"],
    "quality assurance": ["quality assurance"],
    "web crawling": ["web crawling", "rastreamento da web"],
    "mineração de dados": ["mineração de dados", "mineracao de dados", "data mining"],
    "banco de dados": ["banco de dados", "bancos de dados"],
    "devops": ["devops"],
    "front-end": ["front-end", "frontend"],
    "back-end": ["back-end", "backend"],
    "mysql": ["mysql"],
    "matplotlib": ["matplotlib"],
    "seaborn": ["seaborn"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"]
}

# Algumas palavras conseguem ser abreviadas então criamos um dicionário que possuem apenas essas palavras.
SIGLAS = {
    "machine learning": ["ML"],
    "inteligência artificial": ["IA", "AI"],
    "llm": ["LLM", "LLMs"],
    "rag": ["RAG"],
    "etl": ["ETL"],
    "api": ["API", "APIs"],
    "business intelligence": ["BI"],
    "quality assurance": ["QA"],
}

# 
INFERENCIAS = {
    "sql": {
        "premissas": ["mysql", "postgresql"],
        "tipo": "inferido",
        "motivo": "MySQL e PostgreSQL são bancos de dados SQL",
    },
    "numpy": {
        "premissas": ["pandas", "scikit-learn"],
        "tipo": "inferido",
        "motivo": "Pandas e Scikit-learn são construídos sobre NumPy",
    },
    "análise exploratória": {
        "premissas": ["análise de dados"],
        "tipo": "inferido",
        "motivo": "análise de dados com Python envolve análise exploratória",
    },
    "overfitting": {
        "premissas": ["machine learning"],
        "tipo": "inferido",
        "motivo": "conceito básico de qualquer trabalho com Machine Learning",
    },
    "dashboards": {
        "premissas": ["matplotlib", "seaborn"],
        "tipo": "relacionado",
        "motivo": "o currículo tem visualização de dados, mas não ferramentas de dashboard/BI",
    },
}

# Função que ensina aos matchers as possíveis skills que podem aparecer
def construir_matchers(nlp): # recebe como parâmetro o objeto do spaCy que foi criado
    # O 'PhraseMatcher' recebe uma lista de termos e ao receber um texto retorna a posição de cada palavra que aparece tanto na lista quanto no texto.
    # Foram criados dois, um para comparar o texto em letras minúsculas caso palavras sejam escritas com letra maiúscula e poderia fazer o matcher não reconhecer, e outro que lê normalmente para encontrar siglas que geralmente são escritas sempre em letras maiúsculas.
    matcher_skills = PhraseMatcher(nlp.vocab, attr="LOWER")  # ignora as maiúsculas
    matcher_siglas = PhraseMatcher(nlp.vocab)                # respeita as maiúsculas
    for skill, variantes in SKILLS.items(): 
        matcher_skills.add(skill, [nlp.make_doc(v) for v in variantes]) # registra no matcher as skills do dicionário e todas as suas formas possíveis de escrita
    for skill, variantes in SIGLAS.items(): 
        matcher_siglas.add(skill, [nlp.make_doc(v) for v in variantes]) # registra no matcher as siglas do dicionário e suas formas de escrita
    return matcher_skills, matcher_siglas # retorna os dois matchers

# Função utilizada para identificar as skills ou requisitos de um texto
def extrair_habilidades(texto, nlp, matcher_skills, matcher__siglas): # recebe o texto a ser analisado, o objeto dos spaCy e os matchers criados anteriormente 
    doc = nlp(texto) # o NLP recebe o texto (vaga ou currículo) e divide ele em tokens, retornando um Doc
    achadas = {}   # dicionário que vai armazenar as skills ou requisitos identificados {"nome padronizado": "forma que foi escrita"}
    for matcher in (matcher_skills, matcher__siglas): # percorre o texto duas vezes, com o matcher de skills e com o de siglas
        for match_id, inicio, fim in matcher(doc):# procura no texto todos os padrões encontrados e retorna uma lista de ocorrências
            skill = nlp.vocab.strings[match_id] # converte o 'match_id' (código interno das string) em sua forma textual
            achadas.setdefault(skill, []).append(doc[inicio:fim].text)
    return achadas


def classificar(skills_vaga, skills_cv):
    resultado = {"cobertos": [], "inferidos": [], "relacionados": [], "ausentes": []}
    for skill in sorted(skills_vaga):
        if skill in skills_cv:
            resultado["cobertos"].append(skill)
            continue
        regra = INFERENCIAS.get(skill)
        achadas = [p for p in regra["premissas"] if p in skills_cv] if regra else []
        if achadas:
            chave = "inferidos" if regra["tipo"] == "inferido" else "relacionados"
            resultado[chave].append((skill, achadas, regra["motivo"]))
        else:
            resultado["ausentes"].append(skill)
    return resultado