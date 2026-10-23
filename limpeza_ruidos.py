import re
import unicodedata
from pathlib import Path


def normalizar(linha):
    """Minúsculas, sem acento, sem símbolos/emojis: 'Nossos Benefícios: ' -> 'nossos beneficios'."""
    s = unicodedata.normalize("NFKD", linha)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


# Títulos que iniciam um bloco de RUÍDO (tudo abaixo é descartado até aparecer um título útil)
SECOES_RUIDO = [
    "nossos beneficios", "beneficios", "o que voce pode esperar",
    "localizacao e periodo", "candidatura", "sobre a empresa", "quem somos",
    "por que o trabalho", "como sera sua adaptacao", "mentoria e suporte",
    "o que essa vaga significa", "o que vale destacar",
    "por que se juntar", "visao geral do programa", "processo seletivo",
]

# Títulos que (re)iniciam um bloco ÚTIL
SECOES_UTEIS = [
    "sobre a vaga", "sobre a posicao", "o que voce vai fazer", "o que buscamos",
    "diferenciais", "principais responsabilidades", "requisitos",
    "o que e bom ter", "em que voce vai trabalhar", "o que valorizamos",
]


def eh_titulo(linha, padroes):
    if len(linha) > 80:          # título é curto; parágrafo não
        return False
    n = normalizar(linha)
    return any(n.startswith(p) for p in padroes)


def limpar_vaga(texto):
    estado = "util"
    mantidas, removidas = [], []

    for linha in texto.splitlines():
        if eh_titulo(linha, SECOES_RUIDO):
            estado = "ruido"
            removidas.append(linha.strip())
            continue
        if eh_titulo(linha, SECOES_UTEIS):
            estado = "util"
        if estado == "util":
            mantidas.append(linha)

    limpo = "\n".join(mantidas)
    limpo = re.sub(r"https?://\S+|www\.\S+", " ", limpo)        # links
    limpo = re.sub(r"\S+@\S+\.\S+", " ", limpo)                 # e-mails
    limpo = re.sub(r"(?<!\S)#\w+", " ", limpo)                  # hashtags (preserva C#, F#)
    limpo = re.sub(r"(?m)^\s*[-–•]\s+", "", limpo)              # marcadores de lista
    limpo = re.sub(r"[^\w\s\-\+\#\.\,\;\:\(\)\/&%]", " ", limpo)  # emojis e símbolos (preserva C++, C#)
    limpo = re.sub(r"[ \t]+", " ", limpo)
    limpo = re.sub(r"\n\s*\n+", "\n", limpo).strip()
    return limpo, removidas


pasta = Path("data/vagas")
saida = Path("data/vagas_limpas")
saida.mkdir(parents=True, exist_ok=True)

for arquivo in sorted(pasta.glob("vaga*.txt")):
    original = arquivo.read_text(encoding="utf-8")
    limpo, removidas = limpar_vaga(original)
    (saida / arquivo.name).write_text(limpo, encoding="utf-8")
    print(f"{arquivo.name}: {len(original)} -> {len(limpo)} caracteres")
    print("  seções removidas:", removidas)