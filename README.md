# Resume Matcher

Ferramenta que compara um currículo com descrições de vaga e mostra, para cada vaga, **quais requisitos técnicos o currículo cobre, quais dá para inferir e quais faltam**, separando o que é obrigatório do que é diferencial.

O foco é o **diagnóstico**, e não uma nota única: cada conclusão vem com o motivo, para quem lê poder conferir.

## Como funciona

```
PDF do currículo → texto
vagas (.txt) → limpeza → extração de habilidades → comparação → relatório por vaga
```

1. **Limpeza das vagas** (`limpeza_ruidos.py`): remove benefícios, apresentação da empresa, linhas de formação (nome de curso não é habilidade) e sujeira de formatação. No lugar de cada título útil, deixa um marcador (`SECAO_REQUISITO`, `SECAO_DIFERENCIAL`, `SECAO_RESPONSABILIDADE`).
2. **Extração de habilidades** (`dicionario_skills.py`): um `PhraseMatcher` do spaCy procura os termos do dicionário (`config/skills.json`) e normaliza as variações (`aprendizado de máquina` = `machine learning`). Siglas curtas (`IA`, `RAG`) só casam com a grafia exata, para o "ia" de "ele ia" não virar a sigla.
3. **Comparação**: cada requisito da vaga cai em um de quatro grupos:
   - **cobertos**: o currículo tem a habilidade escrita;
   - **inferidos**: não está escrito, mas há uma pista quase certa (MySQL implica SQL);
   - **relacionados**: há algo próximo, mas que não prova o requisito (Matplotlib não prova dashboards);
   - **ausentes**: o currículo não menciona.
4. **Relatório** (`relatorios/*.md`): resumo em números, aviso quando a vaga tem poucos requisitos técnicos identificados, e os ausentes ordenados por importância (requisito, diferencial, responsabilidade).

Exemplo de trecho de relatório:

```
**Requisitos identificados:** 25
**Cobertos ou inferidos:** 14 de 25
**Obrigatórios ausentes:** 2 de 14

## Ausentes (o currículo não menciona), dos mais importantes pros menos
- estatística (requisito)
- api (diferencial)
- engenharia de dados (responsabilidade)
```

## Estrutura

```
Resume-Matcher/
├── dicionario_skills.py       # extração, comparação e leitura do dicionário
├── limpeza_ruidos.py          # limpeza das vagas
├── candidatos.py              # fila de termos novos + revisão
├── resume_matcher.ipynb       # notebook principal (diagnóstico, relatórios, avaliação, fila)
├── pdf_to_txt.ipynb           # converte o currículo em PDF para texto
├── config/
│   ├── skills.json            # dicionário: skills, siglas e equivalências
│   ├── gabaritos.json         # gabaritos manuais (grupos treino e teste)
│   ├── candidatos.json        # fila de termos desconhecidos (não versionado)
│   └── ignorados.json         # termos recusados (não versionado)
├── entrada/
│   ├── curriculo/             # PDF e texto do currículo (não versionado)
│   ├── vagas/                 # vagas originais (não versionado)
│   └── vagas_limpas/          # vagas depois da limpeza (não versionado)
└── relatorios/                # relatórios gerados (não versionado)
```

## Como usar

1. Instale as dependências: `pip install spacy pymupdf`
2. Coloque o currículo em PDF em `entrada/curriculo/curriculo.pdf` e rode o `pdf_to_txt.ipynb` para gerar o `curriculo.txt`.
3. Salve cada vaga como `entrada/vagas/vagaN.txt` (só a descrição, sem o menu do site).
4. Rode `python limpeza_ruidos.py`.
5. Abra o `resume_matcher.ipynb` e execute as células em ordem. Os relatórios saem em `relatorios/`.

Depois de editar o `config/skills.json`, reinicie o kernel do notebook: o dicionário e os matchers carregados na memória são os antigos.

## O dicionário cresce com revisão

O vocabulário fica em `config/skills.json`, e não no código. Ao carregar, um validador confere o arquivo e para com uma mensagem clara se, por exemplo, uma equivalência aponta para uma habilidade que não existe.

Para o dicionário crescer sem virar manutenção sem fim:

- `candidatos.py` lê as vagas e guarda numa fila os termos que parecem tecnologia e que o dicionário não conhece, contando em **quantas vagas diferentes** cada um apareceu;
- só vira proposta o que aparece em **2 vagas ou mais**, o que filtra o que é específico de uma empresa;
- `revisar()` pergunta, termo a termo, se você aprova, ignora ou pula. O que for aprovado vai para o `skills.json` depois de passar pelo validador, e o que for ignorado nunca volta.

Nada entra no dicionário sem aprovação humana: a detecção é por heurística e erra.

## Avaliação

Os gabaritos ficam em `config/gabaritos.json`, em dois grupos:

- **treino**: vagas usadas para ampliar o dicionário. O recall delas é alto por construção, e serve de teste de regressão (se cair depois de uma mudança, algo quebrou);
- **teste**: vagas que o dicionário nunca viu. É o grupo que mede se o sistema funciona.

Regra: o gabarito de uma vaga de teste é escrito **antes** de rodar o sistema, e nenhum termo é adicionado ao dicionário com base nela. Quando isso acontece, a vaga passa para o grupo treino.

Linha de base medida nas vagas de teste (antes de ampliar o dicionário com elas): **recall de 43% e 33%, com precisão de 100%**. Ou seja, o sistema quase nunca inventa uma habilidade, mas só enxerga uma parte das que as vagas pedem, e o dicionário precisa crescer.

## Embeddings: o que foi testado

Foi testada a comparação por significado, com `sentence-transformers` (modelo multilíngue, rodando localmente):

- texto inteiro contra texto inteiro: o modelo corta em 128 tokens e lê só o começo, então o ranking não é confiável;
- por trechos: funciona bem para conceitos ("Python para análise de dados"), mas mal para nomes de ferramentas (SQL, Git), em que uma lista de nomes não se parece, em significado, com uma frase sobre a ferramenta, e nenhuma nota de corte separa o que o currículo cobre do que não cobre.

Conclusão: o dicionário é melhor para nomes de ferramentas, e os embeddings só serviriam como apoio, sugerindo trechos para uma pessoa conferir.

## Limitações

- O sistema só reconhece o que está no dicionário, então vagas de áreas novas pedem manutenção.
- A limpeza depende de títulos de seção escritos nas listas. Um título novo deixa o texto passar sem classificação.
- Uma habilidade citada de passagem (por exemplo, "IA" num parágrafo de cultura da empresa) pode ser contada como requisito.
- Soft skills não são avaliadas, de propósito: palavras como "comunicação" aparecem em todo currículo e não provam nada.

## Privacidade

O currículo tem dados pessoais. As pastas `entrada/` e `relatorios/` ficam fora do repositório (`.gitignore`), e as saídas dos notebooks devem ser limpas antes de publicar.