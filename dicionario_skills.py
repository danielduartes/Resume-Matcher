# Carrega os dicionários, monta os matchers, acha habilidades num texto, compara vaga com currículo e descobre de qual seção cada habilidade veio

import json
from pathlib import Path
from spacy.matcher import PhraseMatcher

CAMINHO = Path(__file__).parent / "config" / "skills.json" # pasta onde está o dicionário com as skills
PRIORIDADE = ["REQUISITO", "DIFERENCIAL", "RESPONSABILIDADE", "OUTRO"] # ordem de prioridade das seções de uma vaga

# Confere o 'skills.json' antes do uso, caso haja algum erro de digitação no JSON, parando com uma mensagem clara casso tenha erro
def validar(dados): 
    nomes = set(dados["skills"]) | set(dados["siglas"]) # lista com todas as habilidades 
    problemas = [] # lista que armazena as mensagens de erro 

    for secao in ("skills", "siglas"): # percorre a seção de skills e siglas 
        for nome, variantes in dados[secao].items():
            if not variantes: # se uma habilidade tem a lista de variantes vazia:
                problemas.append(f"{secao}: '{nome}' está sem variantes") # anota o erro. Uma habilidade sem variantes nunca seria encontrada no texto 

    # Conferir que cada regra de equivalência aponta para coisas que existem no dicionário
    for requisito, regra in dados["equivalencias"].items(): # percorre cada regra da seçao 'equivalencias'
        if requisito not in nomes: # conferindo se o requisito existe como uma skill
            problemas.append(f"equivalência '{requisito}' não existe em skills/siglas") # se não, anota o problema na lista de problemas
        for pista in regra["premissas"]: # percorre a pista de cada regra
            if pista not in nomes: # confere se a pista está registrada como uma skill
                problemas.append(f"'{requisito}': a pista '{pista}' não existe em skills/siglas") # se não, anota o problema na lista de problemas
        if regra["tipo"] not in ("inferido", "relacionado"): # confere se o tipo da regra é um dos que a função 'classificar' reconhece
            problemas.append(f"'{requisito}': tipo '{regra['tipo']}' inválido") # caso esteja escrito errado, anota o problema

    if problemas: # verifica se foi detectado algum problema vendo se a lista tem itens
        raise ValueError("Problemas no skills.json:\n- " + "\n- ".join(problemas)) 

# Função que faz o carregamento dos três dicionários: skills, siglas e equivalências
def carregar_dados(caminho=CAMINHO):
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    validar(dados)
    return dados["skills"], dados["siglas"], dados["equivalencias"]


SKILLS, SIGLAS, SE_TEM_ENTAO_TEM = carregar_dados()


# Função que ensina aos matchers as possíveis skills que podem aparecer
def construir_matchers(nlp): # recebe como parâmetro o objeto do spaCy que foi criado
    # O 'PhraseMatcher' recebe uma lista de termos e ao receber um texto retorna a posição de cada palavra que aparece tanto na lista quanto no texto.
    # Foram criados dois, um para comparar o texto em letras minúsculas caso palavras sejam escritas com letra maiúscula e poderia fazer o matcher não reconhecer, e outro que lê normalmente para encontrar siglas que geralmente são escritas sempre em letras maiúsculas.
    matcher_skills = PhraseMatcher(nlp.vocab, attr="LOWER") # ignora as maiúsculas 
    matcher_siglas = PhraseMatcher(nlp.vocab) # respeita as maiúsculas
    for skill, variantes in SKILLS.items(): # 
        matcher_skills.add(skill, [nlp.make_doc(v) for v in variantes]) # registra no matcher as skills do dicionário e todas as suas formas possíveis de escrita
    for skill, variantes in SIGLAS.items():
        matcher_siglas.add(skill, [nlp.make_doc(v) for v in variantes]) # registra no matcher as siglas do dicionário e suas formas de escrita
    return matcher_skills, matcher_siglas # retorna os dois matchers


# Função utilizada para identificar as skills ou requisitos de um texto
def extrair_habilidades(texto, nlp, matcher_skills, matcher_siglas): # recebe o texto a ser analisado, o objeto dos spaCy e os matchers criados anteriormente
    doc = nlp(texto)  # o NLP recebe o texto (vaga ou currículo) e divide ele em tokens, retornando um Doc
    achadas = {} # # dicionário que vai armazenar as skills ou requisitos identificados {"nome padronizado": "forma que foi escrita"}
    for matcher in (matcher_skills, matcher_siglas):  # percorre o texto duas vezes, com o matcher de skills e com o de siglas
        for match_id, inicio, fim in matcher(doc): # procura no texto todos os padrões encontrados e retorna uma lista de ocorrências
            skill = nlp.vocab.strings[match_id]  # converte o 'match_id' (código interno da string) em sua forma textual
            achadas.setdefault(skill, []).append(doc[inicio:fim].text)  # quando uma skill for lida pela primeira vez, ela será inserida no 'achadas'
    return achadas

# Compara os requisitos de uma vaga com as skills de um currículo e classifica o requisito como coberto, inferido, relacionado ou ausente
def classificar(skills_vaga, skills_cv): # recebe as requisitos da vaga e as skills do currículo
    resultado = {"cobertos": [], "inferidos": [], "relacionados": [], "ausentes": []} 
    for skill in sorted(skills_vaga):  # percorre cada requisito da vaga
        if skill in skills_cv:
            resultado["cobertos"].append(skill)  # se o requisito estiver no currículo, vai para 'coberto'
            continue
        regra = SE_TEM_ENTAO_TEM.get(skill) # procura se existe uma regra de equivalência para o requisito, retorna a regra ou None
        achadas = [p for p in regra["premissas"] if p in skills_cv] if regra else [] # procura quais pistas da regra o currículo tem
        if achadas: # se tiver pista:
            chave = "inferidos" if regra["tipo"] == "inferido" else "relacionados" # escolhe a lista de destino dependendo do tipo da regra
            resultado[chave].append((skill, achadas, regra["motivo"]))  # adiciona na lista escolhida
        else:
            resultado["ausentes"].append(skill)  # nenhuma pista foi encontrada
    return resultado


# Função que descobre de qual seção da vaga veio cada skill (requisito, diferencial, responsabilidade ou outro)
def extrair_com_secao(texto, nlp, matcher_skills, matcher_siglas): # recebe a descrição da vaga já limpa, o objeto do spaCy e os dois matchers 
    secao = "OUTRO" # variável que armazena o nome da seção em que a skill foi encontrada. Começa como "OUTRO" para habilidades que apareçam antes de qualquer marcador
    resultado = {} 
    for linha in texto.splitlines(): # percorre linha por linha
        l = linha.strip() 
        if l.startswith("SECAO_") and " " not in l: # reconhece a linha como marcador
            secao = l.replace("SECAO_", "")
            continue
        for skill in extrair_habilidades(l, nlp, matcher_skills, matcher_siglas): # percorre cada skill da linha    
            atual = resultado.get(skill) # vê qual seção essa habilidade já tem registrada. Se for a primeira vez, o .get() vira None
            # Decidindo se registra ou não
            if atual is None or PRIORIDADE.index(secao) < PRIORIDADE.index(atual): # registra se a habilidade ainda não tem uma seção registrada ou se a seção de agora é mais forte que a registrada 
                resultado[skill] = secao
    return resultado