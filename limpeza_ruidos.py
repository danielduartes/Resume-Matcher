# Em algumas descrições de vagas não há só os requisitos: há também benefícios, apresentação da empresa e outros trechos que viram ruído. Este script limpa as descrições para sobrarem apenas as habilidades necessárias, e deixa um marcador (SECAO_...) no lugar de cada título útil.

import re
import unicodedata
from pathlib import Path

PASTA_PROJETO = Path(__file__).parent

# Deixa uma linha numa forma padrão, com minúsculas, sem acentos e sem símbolos
def normalizar(linha): # recebe a linha do texto
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

# Função que define se uma linha se enquadra como um título ou uma linha de parágrafo normal
def eh_titulo(linha, padroes): # recebe a linha e uma lista de títulos para comparar 
    if len(linha) > 80:  # títulos são curtos; linha longa é parágrafo
        return False
    n = normalizar(linha) # normaliza a escrita da linha
    return any(n.startswith(p) for p in padroes) # testa se a linha começa com algum títula da lista passada nos parâmetros

# Descobre o tipo do título útil (requisito, diferencial, responsabilidade ou outro)
def tipo_da_secao(linha):
    n = normalizar(linha)
    for padrao, tipo in TIPO_DA_SECAO.items():
        if n.startswith(padrao):
            return tipo
    return "OUTRO"

# Diz se é uma linha de formação (curso, ou graduação). Não conta como habilidade
def eh_linha_de_formacao(linha):
    n = normalizar(linha)
    return any(p in n for p in PADROES_FORMACAO)

# Deixa só o que importa da vaga
def limpar_vaga(texto): # recebe a descrição da vaga inteira
    estado = "util"  # trigger: diz se as linhas que estão passando são úteis ou ruído
    mantidas, removidas = [], [] 

    for linha in texto.splitlines(): # percorre linha por linha
        if eh_titulo(linha, SECOES_RUIDO): # se a linha é um título de ruído, ativa o trigger e adiciona o título em 'removidas'
            estado = "ruido"
            removidas.append(linha.strip())
            continue
        if eh_titulo(linha, SECOES_UTEIS): # se a linha é um título útil, adiciona o título em 'mantidas'
            estado = "util"
            mantidas.append("SECAO_" + tipo_da_secao(linha))  # marcador no lugar do título
            continue
        if estado == "util": 
            if eh_linha_de_formacao(linha): # se for uma linha de formação
                removidas.append(linha.strip()[:60])  # adiciona em 'removidas'
            else: # se for uma linha realmente útil
                mantidas.append(linha) # adiciona em 'mantidas'

    limpo = "\n".join(mantidas) # junta todas as linhas mantidas em uma string
    limpo = re.sub(r"https?://\S+|www\.\S+", " ", limpo)                # links
    limpo = re.sub(r"\S+@\S+\.\S+", " ", limpo)                         # e-mails
    limpo = re.sub(r"(?<!\S)#\w+", " ", limpo)                          # hashtags (preserva C#, F#)
    limpo = re.sub(r"(?m)^\s*[-–•]\s+", "", limpo)                      # marcadores de lista
    limpo = re.sub(r"[^\w\s\-\+\#\.\,\;\:\(\)\/&%]", " ", limpo)        # emojis e símbolos (preserva C++, C#)
    limpo = re.sub(r"[ \t]+", " ", limpo)
    limpo = re.sub(r"\n\s*\n+", "\n", limpo).strip()
    return limpo, removidas

# Limpa todas as descrições de vagas e transfere as versões limpas para uma nova pasta
def limpar_todas():
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