# Dicionário de habilidades e funções de extração e comparação.
# O NER do spaCy não reconhece habilidades técnicas, então usamos um PhraseMatcher que procura
# os termos listados em config/skills.json (skills, siglas e equivalências).

import json
from pathlib import Path
from spacy.matcher import PhraseMatcher

CAMINHO = Path(__file__).parent / "config" / "skills.json"
PRIORIDADE = ["REQUISITO", "DIFERENCIAL", "RESPONSABILIDADE", "OUTRO"]


def validar(dados):
    """Confere o JSON e levanta erro listando tudo o que estiver errado."""
    nomes = set(dados["skills"]) | set(dados["siglas"])
    problemas = []

    for secao in ("skills", "siglas"):
        for nome, variantes in dados[secao].items():
            if not variantes:
                problemas.append(f"{secao}: '{nome}' está sem variantes")

    for requisito, regra in dados["equivalencias"].items():
        if requisito not in nomes:
            problemas.append(f"equivalência '{requisito}' não existe em skills/siglas")
        for pista in regra["premissas"]:
            if pista not in nomes:
                problemas.append(f"'{requisito}': a pista '{pista}' não existe em skills/siglas")
        if regra["tipo"] not in ("inferido", "relacionado"):
            problemas.append(f"'{requisito}': tipo '{regra['tipo']}' inválido")

    if problemas:
        raise ValueError("Problemas no skills.json:\n- " + "\n- ".join(problemas))


def carregar_dados(caminho=CAMINHO):
    """Lê o JSON, valida e devolve (SKILLS, SIGLAS, SE_TEM_ENTAO_TEM)."""
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    validar(dados)
    return dados["skills"], dados["siglas"], dados["equivalencias"]


SKILLS, SIGLAS, SE_TEM_ENTAO_TEM = carregar_dados()


def construir_matchers(nlp):
    """
    Prepara os dois matchers que vão procurar habilidades nos textos (não lê nenhum texto).
    - matcher_skills: compara em minúsculas (Python = python = PYTHON)
    - matcher_siglas: exige a grafia exata, para não confundir "ia" (verbo) com "IA" (sigla)
    """
    matcher_skills = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher_siglas = PhraseMatcher(nlp.vocab)
    for skill, variantes in SKILLS.items():
        matcher_skills.add(skill, [nlp.make_doc(v) for v in variantes])  # nome padronizado + todas as formas de escrever
    for skill, variantes in SIGLAS.items():
        matcher_siglas.add(skill, [nlp.make_doc(v) for v in variantes])
    return matcher_skills, matcher_siglas


def extrair_habilidades(texto, nlp, matcher_skills, matcher_siglas):
    """Acha as habilidades do dicionário num texto. Devolve {nome padronizado: [trechos como estavam escritos]}."""
    doc = nlp(texto)  # divide o texto em tokens
    achadas = {}
    for matcher in (matcher_skills, matcher_siglas):  # um passe com cada matcher
        for match_id, inicio, fim in matcher(doc):
            skill = nlp.vocab.strings[match_id]  # código interno -> nome da habilidade
            achadas.setdefault(skill, []).append(doc[inicio:fim].text)  # cria a lista na primeira vez e guarda o trecho
    return achadas


def classificar(skills_vaga, skills_cv):
    """
    Compara os requisitos de UMA vaga com as habilidades do currículo (os dois são conjuntos de nomes).
    Devolve quatro listas: cobertos, inferidos, relacionados e ausentes.
    """
    resultado = {"cobertos": [], "inferidos": [], "relacionados": [], "ausentes": []}
    for skill in sorted(skills_vaga):  # cada requisito da vaga
        if skill in skills_cv:
            resultado["cobertos"].append(skill)  # o currículo tem a skill escrita
            continue
        regra = SE_TEM_ENTAO_TEM.get(skill)  # regra com as skills do currículo que valem como este requisito (None se não houver)
        achadas = [p for p in regra["premissas"] if p in skills_cv] if regra else []  # pistas da regra que o currículo tem
        if achadas:
            chave = "inferidos" if regra["tipo"] == "inferido" else "relacionados"
            resultado[chave].append((skill, achadas, regra["motivo"]))  # requisito, pistas achadas e explicação
        else:
            resultado["ausentes"].append(skill)  # sem a skill escrita e sem nenhuma pista
    return resultado


def extrair_com_secao(texto, nlp, matcher_skills, matcher_siglas):
    """Devolve {habilidade: seção mais forte onde ela apareceu}, lendo os marcadores SECAO_ deixados pela limpeza."""
    secao = "OUTRO"
    resultado = {}
    for linha in texto.splitlines():
        l = linha.strip()
        if l.startswith("SECAO_") and " " not in l:
            secao = l.replace("SECAO_", "")
            continue
        for skill in extrair_habilidades(l, nlp, matcher_skills, matcher_siglas):
            atual = resultado.get(skill)
            if atual is None or PRIORIDADE.index(secao) < PRIORIDADE.index(atual):
                resultado[skill] = secao
    return resultado