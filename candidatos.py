import json
import re
from pathlib import Path

from dicionario_skills import SKILLS, SIGLAS, CAMINHO, validar

ARQ_CANDIDATOS = Path("config/candidatos.json")
ARQ_IGNORADOS = Path("config/ignorados.json")   # termos que você recusou (nunca mais voltam)

GATILHOS = re.compile(
    r"(?:conhecimentos?|experiência|familiaridade|noções|domínio)(?:\s+\w+)?\s+(?:em|com|de|sobre)\s+([^;:\n]+)",
    re.I,
)


SUFIXOS_VERBAIS = re.compile(r"-(se|me|te|lhe|lhes|nos|vos|o|a|os|as|lo|la|los|las)$", re.I)

IGNORAR_SIGLAS = {"pcd", "lgbtqia", "esg", "ltda", "sa", "cnpj", "cpf", "rh", "ti"}


def _ler(caminho, padrao):
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else padrao


def _salvar(caminho, dados):
    caminho.parent.mkdir(exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def termos_conhecidos():
    """Nomes e variantes que o dicionário já tem (em minúsculas)."""
    conhecidos = set()
    for grupo in (SKILLS, SIGLAS):
        for nome, variantes in grupo.items():
            conhecidos.add(nome.lower())
            conhecidos.update(v.lower() for v in variantes)
    return conhecidos


def candidatos_da_linha(linha):
    """Acha termos que parecem tecnologia numa linha (heurística: vai errar, por isso existe a aprovação)."""
    achados = set()

    for tok in re.findall(r"[A-Za-z][\w.+#/\-]*", linha):
        tok = tok.strip(".,;:")                     # tira só pontuação das pontas (mantém o '/' e o '.')
        if len(tok) < 2 or SUFIXOS_VERBAIS.search(tok):
            continue
        # termo com '/': cada lado é um candidato (javascript/typescript -> dois)
        partes = [tok] if tok.lower() in ("ci/cd",) else tok.split("/")
        for p in partes:
            p = p.strip(".,;:-")
            if len(p) < 2:
                continue
            if p.lower().rstrip("+") in IGNORAR_SIGLAS:
                continue
            tem_pista = any(c in p[1:] for c in ".+#") or re.search(r"[a-z][A-Z]", p)
            if tem_pista or (p.isupper() and 2 <= len(p) <= 6):
                achados.add(p.lower())

    for m in GATILHOS.finditer(linha):
        for chunk in re.split(r",|\s+e\s+|\s+ou\s+", m.group(1)):
            chunk = chunk.strip(" .;")
            if chunk[:1].isupper() and 1 <= len(chunk.split()) <= 2:
                achados.add(chunk.lower())

    return achados


def atualizar_fila(nome_vaga, texto):
    """Soma à fila os termos desconhecidos do texto de uma vaga. Rodar duas vezes na mesma vaga não duplica."""
    conhecidos = termos_conhecidos()
    ignorados = set(_ler(ARQ_IGNORADOS, []))
    fila = _ler(ARQ_CANDIDATOS, {})

    for linha in texto.splitlines():
        for termo in candidatos_da_linha(linha):
            if termo in conhecidos or termo in ignorados:
                continue
            item = fila.setdefault(termo, {"vagas": [], "exemplo": linha.strip()[:100]})
            if nome_vaga not in item["vagas"]:
                item["vagas"].append(nome_vaga)

    _salvar(ARQ_CANDIDATOS, fila)
    return fila


def propostas(minimo=2):
    """Candidatos que apareceram em pelo menos 'minimo' vagas diferentes, do mais frequente pro menos."""
    fila = _ler(ARQ_CANDIDATOS, {})
    lista = [(t, d) for t, d in fila.items() if len(d["vagas"]) >= minimo]
    return sorted(lista, key=lambda x: len(x[1]["vagas"]), reverse=True)


def revisar(minimo=2):
    fila = _ler(ARQ_CANDIDATOS, {})
    ignorados = _ler(ARQ_IGNORADOS, [])
    dados = json.loads(CAMINHO.read_text(encoding="utf-8"))

    for termo, d in propostas(minimo):
        print(f"\n{termo}  ({len(d['vagas'])} vagas: {', '.join(d['vagas'])})")
        print(f"  ex.: {d['exemplo']}")
        r = input("  [a]provar / [i]gnorar / [p]ular? ").strip().lower()

        if r == "i":
            ignorados.append(termo)
            fila.pop(termo, None)
        elif r == "a":
            nome = input(f"  nome padronizado [{termo}]: ").strip().lower() or termo
            extra = input("  outras formas de escrever (separadas por vírgula): ")
            variantes = [termo] + [v.strip().lower() for v in extra.split(",") if v.strip()]
            sigla = input("  é sigla curta (só casa em MAIÚSCULAS)? [s/n] ").strip().lower() == "s"
            secao = "siglas" if sigla else "skills"
            if sigla:
                variantes = [v.upper() for v in variantes]
            lista = dados[secao].setdefault(nome, [])
            lista.extend(v for v in variantes if v not in lista)
            fila.pop(termo, None)

    validar(dados)   # se algo estiver errado, para aqui e não salva nada
    CAMINHO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    _salvar(ARQ_CANDIDATOS, fila)
    _salvar(ARQ_IGNORADOS, ignorados)