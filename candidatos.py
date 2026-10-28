# Arquivo responsável pelo crescimento contínuo do conhecimento do sistema em questão à tecnologias. Fazendo com que o arquivo 'skills.json' guarde novas habilidades que o sistema não reconheceu apenas com o 'dicionario_skills.py'.

# Nenhum item entra sem a validação do usuário.

import json
import re
from pathlib import Path

from dicionario_skills import SKILLS, SIGLAS, CAMINHO, validar

PASTA_CONFIG = Path(__file__).parent / "config" # 
ARQ_CANDIDATOS = PASTA_CONFIG / "candidatos.json" # fila de tecnologias novas que podem ser adicionadas ou ignoradas
ARQ_IGNORADOS = Path("config/ignorados.json")   # termos novos que foram ignorados são adicionados no 'ignorados.json'

# Regras de filtro para decidir quais termos da descrição da vaga virarão candidatos
GATILHOS = re.compile(r"(?:conhecimentos?|experiência|familiaridade|noções|domínio)(?:\s+\w+)?\s+(?:em|com|de|sobre)\s+([^;:\n]+)",re.I,)

SUFIXOS_VERBAIS = re.compile(r"-(se|me|te|lhe|lhes|nos|vos|o|a|os|as|lo|la|los|las)$", re.I)

IGNORAR_SIGLAS = {"pcd", "lgbtqia", "esg", "ltda", "sa", "cnpj", "cpf", "rh", "ti"}

# Lê o arquivo JSON e retorna o conteúdo como dicionário ou lista de Python  
def _ler(caminho, padrao):
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else padrao # 

# Grava os dados da fila no JSON 
def _salvar(caminho, dados):
    caminho.parent.mkdir(exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

# Monta uma lista de tudo que o dicionário já conhece em minúsculas
def termos_conhecidos():
    conhecidos = set() # cria o conjunto vazio
    for grupo in (SKILLS, SIGLAS): # roda o bloco duas vezes, com o dicionário de skills e de siglas
        for nome, variantes in grupo.items(): 
            conhecidos.add(nome.lower()) # adiciona o nome padronizado no conjunto
            conhecidos.update(v.lower() for v in variantes) # adiciona todas as variantes também
    return conhecidos 

# Descobre numa linha da descrição da vaga quais termos parecem tecnologia
def candidatos_da_linha(linha):
    achados = set() # conjunto vazio com as tecnologias encontradas

    # Regra 1: O que tem "cara" de tecnologia
    for tok in re.findall(r"[A-Za-z][\w.+#/\-]*", linha): # acha as palavras da linha, cada uma começa com uma letra e pode ter um símbolo, letras ou números depois  
        tok = tok.strip(".,;:") # tira só a pontuação das pontas (mantém o '/' e o '.')
        if len(tok) < 2 or SUFIXOS_VERBAIS.search(tok):
            continue
        partes = [tok] if tok.lower() in ("ci/cd",) else tok.split("/") # se tem '/' cada lado vira um candidato, a única exceção é "ci/cd". ex.: "javascript/typescript"

        # Limpa de novo e pula as siglas da lista de ignorados
        for p in partes: 
            p = p.strip(".,;:-")
            if len(p) < 2:
                continue
            if p.lower().rstrip("+") in IGNORAR_SIGLAS:
                continue
            # O termo é candidato se tiver '.', '+' ou '#' no meio ('node.js', 'c++'), ou uma maiúscula e depois uma minúscula ('FastAPI') ou se for uma sigla em maiúscula de 2 a 6 letras ('AWS')
            tem_pista = any(c in p[1:] for c in ".+#") or re.search(r"[a-z][A-Z]", p)
            if tem_pista or (p.isupper() and 2 <= len(p) <= 6):
                achados.add(p.lower())

    # Regra 2: O que vem depois de "conhecimento em"
    for m in GATILHOS.finditer(linha):
        for chunk in re.split(r",|\s+e\s+|\s+ou\s+", m.group(1)):
            chunk = chunk.strip(" .;")
            if chunk[:1].isupper() and 1 <= len(chunk.split()) <= 2:
                achados.add(chunk.lower())

    return achados

# Atualiza a fila de candidatos com os termos de uma vaga. Pra cada termo que parece tecnologia e que o dicionário não conhece, ela anota em quais vagas ela apareceu
def atualizar_fila(nome_vaga, texto):
    conhecidos = termos_conhecidos() # todos os termos conhecidos
    ignorados = set(_ler(ARQ_IGNORADOS, [])) # os termos recusados anteriormente 
    fila = _ler(ARQ_CANDIDATOS, {}) # o que já estava gravado   

    for linha in texto.splitlines(): # percorre a vaga linha por linha
        for termo in candidatos_da_linha(linha): # percorre cada possível tecnologia encontrada
            if termo in conhecidos or termo in ignorados: # se o termo já estiver em algum dicionário, é pulado
                continue
            item = fila.setdefault(termo, {"vagas": [], "exemplo": linha.strip()[:100]}) # retorna o registro do termo da fila
            if nome_vaga not in item["vagas"]: 
                item["vagas"].append(nome_vaga) # se o nome da vaga não estiver na lista, ela é adicionada

    _salvar(ARQ_CANDIDATOS, fila) # grava a fila no arquivo
    return fila # retorna a fila

# Lista os candidatos que apareceram pelo menos em duas vagas diferentes, dos mais pros menos frequentes
def propostas(minimo=2):
    fila = _ler(ARQ_CANDIDATOS, {}) # lê a fila do 'candidatos.json'
    lista = [(t, d) for t, d in fila.items() if len(d["vagas"]) >= minimo] # monta a lista filtrada
    return sorted(lista, key=lambda x: len(x[1]["vagas"]), reverse=True) # ordena e retorna

# Etapa que o usuário irá validar os candidatos, definir se elas são realmente tecnologias ou não
def revisar(minimo=2):
    # Leitura dos três arquivos
    fila = _ler(ARQ_CANDIDATOS, {}) 
    ignorados = _ler(ARQ_IGNORADOS, [])
    dados = json.loads(CAMINHO.read_text(encoding="utf-8"))

    for termo, d in propostas(minimo): # percorre as propostas
        print(f"\n{termo}  ({len(d['vagas'])} vagas: {', '.join(d['vagas'])})") # mostra em quais vagas apareceu
        print(f"  ex.: {d['exemplo']}") # linha de exemplo
        r = input("  [a]provar / [i]gnorar / [p]ular? ").strip().lower() # resposta do usuário

        if r == "i": # se responder 'i' (ignorado): 
            ignorados.append(termo) # adiciona na lista de ignorados
            fila.pop(termo, None) # tira da fila
        elif r == "a": # se responder 'a' (aprovado): 
            nome = input(f"  nome padronizado [{termo}]: ").strip().lower() or termo # pergunta o nome padronizado
            extra = input("  outras formas de escrever (separadas por vírgula): ") # outras formas de escrever
            variantes = [termo] + [v.strip().lower() for v in extra.split(",") if v.strip()]
            sigla = input("  é sigla curta (só casa em MAIÚSCULAS)? [s/n] ").strip().lower() == "s" # pergunta se é sigla
            secao = "siglas" if sigla else "skills"
            if sigla: # se sim:
                variantes = [v.upper() for v in variantes] # vai pra seção de siglas e as variantes viram maiúsculas, se não: vai pra seção de skills
            lista = dados[secao].setdefault(nome, []) # pega a lista de variantes desse nome no dicionário
            lista.extend(v for v in variantes if v not in lista) # acrescenta as variantes que ainda não estão lá
            fila.pop(termo, None) # tira da fila

    validar(dados)   # se algo estiver errado, para aqui e não salva nada
    CAMINHO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    _salvar(ARQ_CANDIDATOS, fila)
    _salvar(ARQ_IGNORADOS, ignorados)