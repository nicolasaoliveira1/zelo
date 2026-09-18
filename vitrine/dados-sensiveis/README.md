# Barreira de dados sensíveis

Um hook de pre-commit que recusa documento fiscal real antes que ele entre no
histórico do git.

## Por que existe

Este repositório nasceu público. Em algum momento entraram nele, sem ninguém
perceber: documento de cliente numa fixture de teste, CNPJ real dentro de uma
asserção de função pura, um extrato bancário de verdade em `tests/fixtures/` e
números internos da operação no corpo de um pull request.

Todos foram trocados depois. **Trocar não resolve** — o commit anterior continua
lá, acessível por SHA, e um repositório público é raspado por robô no mesmo dia.
A única correção que funciona é uma barreira que roda **antes** do commit.

## O que ele procura

- **CNPJ e CPF com dígito verificador válido** que não estejam na lista de
  documentos sintéticos declarada no próprio arquivo. A lista é a única porta de
  entrada: documento de teste tem de ser inventado, e inventado com DV correto,
  senão o teste não exercita a validação de verdade.
- **Chave de acesso de NF-e** (44 dígitos) cujo CNPJ do emitente, nas posições
  6 a 20, não seja sintético.

## O que ele não tenta fazer

Adivinhar se `PADARIA CENTRAL` é nome real. Nome de cliente não tem forma
reconhecível, e um verificador que chuta vira ruído que a equipe aprende a
ignorar — o que é pior do que não ter verificador. Para nome, a regra continua
sendo humana: ler o diff antes de commitar.

## Três decisões que parecem detalhe e não são

**Lê o índice, não a árvore de trabalho.** O que vai no commit é o índice. Um
verificador que lê o arquivo em disco aprova bytes que não são os que serão
gravados — basta editar depois do `git add`.

**Lista negativa de extensões, nunca positiva.** Uma lista de extensões
*permitidas* deixa passar todo formato de texto que o repositório ganhar depois:
`.env.example`, `.toml`, `.ini`, `.cfg`, `.bat`, `.sql`, um `Dockerfile` sem
extensão. A pergunta certa é "isto é binário?", e quem responde é a decodificação.

**Decodifica em modo estrito.** Com `errors="ignore"` todo binário vira texto e o
verificador gasta tempo procurando CNPJ dentro de PNG. O byte NUL é o segundo
teste: arquivo de texto não tem, e há binário que decodifica como latin-1 por
acidente.

## A armadilha que já quebrou o hook

O hook é `sh` POSIX (dash), não bash: `read -d` não existe ali. A primeira versão
usava, errava silenciosamente, saía `0` e **falhava aberto** — pior do que não
existir. Por isso o shell script é mínimo e todo o trabalho está no Python, que
usa só a biblioteca padrão e roda em qualquer `python3`.

## Uso

```bash
# uma vez por clone
git config core.hooksPath .githooks

# manual, sobre arquivos específicos ou sobre tudo que está versionado
python3 verificar_dados_sensiveis.py [caminho ...]

# o que o hook roda: apenas os blobs em índice
python3 verificar_dados_sensiveis.py --staged
```

Sai `1` se achar algo. No projeto real ele roda também no CI, para que uma
branch que nasceu antes do `core.hooksPath` não passe direto.

## Testes

```bash
python3 -m pytest test_verificar_dados_sensiveis.py -q
```
