# Em algumas descrições de vagas não há só os requisitos: há também benefícios, apresentação da empresa
# e outros trechos que viram ruído. Este script limpa as descrições para sobrarem só as habilidades
# necessárias, e deixa um marcador (SECAO_...) no lugar de cada título útil.

import re
import unicodedata
from pathlib import Path

PASTA_PROJETO = Path(__file__).parent


def normalizar(linha):
    """Minúsculas, sem acento e sem símbolos, para comparar com as listas de títulos."""
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
    "informacoes adicionais", "alguns dos nossos beneficios",
]

# Títulos úteis e o tipo de cada seção (vira um marcador no texto limpo)
TIPO_DA_SECAO = {
    "requisitos": "REQUISITO",
    "o que buscamos": "REQUISITO",
    "diferenciais": "DIFERENCIAL",
    "responsabilidades": "RESPONSABILIDADE",
    "principais responsabilidades": "RESPONSABILIDADE",
    "o que voce vai fazer": "RESPONSABILIDADE",
    "em que voce vai trabalhar": "RESPONSABILIDADE",
    "sobre a vaga": "OUTRO",
    "sobre a posicao": "OUTRO",
    "o que e bom ter": "OUTRO",
    "o que valorizamos": "OUTRO",
}
SECOES_UTEIS = list(TIPO_DA_SECAO)

# Linhas que falam de formação (nome de curso não é habilidade)
PADROES_FORMACAO = ["cursando", "formacao superior", "graduacao", "bacharelado", "estudante de", "matricula ativa"]


def eh_titulo(linha, padroes):
    """Diz se a linha é um título de uma das listas ('SECOES_RUIDO' ou 'SECOES_UTEIS')."""
    if len(linha) > 80:  # títulos são curtos; linha longa é parágrafo
        return False
    n = normalizar(linha)
    return any(n.startswith(p) for p in padroes)


def tipo_da_secao(linha):
    """Tipo do título útil (REQUISITO, DIFERENCIAL, RESPONSABILIDADE ou OUTRO)."""
    n = normalizar(linha)
    for padrao, tipo in TIPO_DA_SECAO.items():
        if n.startswith(padrao):
            return tipo
    return "OUTRO"


def eh_linha_de_formacao(linha):
    """Diz se a linha fala de formação (curso, graduação), que não conta como habilidade."""
    n = normalizar(linha)
    return any(p in n for p in PADROES_FORMACAO)


def limpar_vaga(texto):
    """Devolve (texto limpo, lista do que foi removido) de uma descrição de vaga."""
    estado = "util"  # interruptor: diz se as linhas que estão passando são úteis ou ruído
    mantidas, removidas = [], []

    for linha in texto.splitlines():
        if eh_titulo(linha, SECOES_RUIDO):
            estado = "ruido"
            removidas.append(linha.strip())
            continue
        if eh_titulo(linha, SECOES_UTEIS):
            estado = "util"
            mantidas.append("SECAO_" + tipo_da_secao(linha))  # marcador no lugar do título
            continue
        if estado == "util":
            if eh_linha_de_formacao(linha):
                removidas.append(linha.strip()[:60])  # fica anotada para auditoria
            else:
                mantidas.append(linha)

    limpo = "\n".join(mantidas)
    limpo = re.sub(r"https?://\S+|www\.\S+", " ", limpo)                # links
    limpo = re.sub(r"\S+@\S+\.\S+", " ", limpo)                         # e-mails
    limpo = re.sub(r"(?<!\S)#\w+", " ", limpo)                          # hashtags (preserva C#, F#)
    limpo = re.sub(r"(?m)^\s*[-–•]\s+", "", limpo)                      # marcadores de lista
    limpo = re.sub(r"[^\w\s\-\+\#\.\,\;\:\(\)\/&%]", " ", limpo)        # emojis e símbolos (preserva C++, C#)
    limpo = re.sub(r"[ \t]+", " ", limpo)
    limpo = re.sub(r"\n\s*\n+", "\n", limpo).strip()
    return limpo, removidas


def limpar_todas():
    """Limpa todas as vagas de entrada/vagas e salva o resultado em entrada/vagas_limpas."""
    pasta = PASTA_PROJETO / "entrada" / "vagas"
    saida = PASTA_PROJETO / "entrada" / "vagas_limpas"
    saida.mkdir(parents=True, exist_ok=True)

    for arquivo in sorted(pasta.glob("vaga*.txt")):
        original = arquivo.read_text(encoding="utf-8")
        limpo, removidas = limpar_vaga(original)
        (saida / arquivo.name).write_text(limpo, encoding="utf-8")
        print(f"{arquivo.name}: {len(original)} -> {len(limpo)} caracteres")
        print("  seções removidas:", removidas)
    print("Salvo em:", saida.resolve())


if __name__ == "__main__":  # só roda quando o arquivo é executado direto, e não quando é importado
    limpar_todas()