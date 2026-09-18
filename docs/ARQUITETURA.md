# Arquitetura

Como o Zelo é organizado por dentro, o que ele registra enquanto roda e como é
verificado. O código-fonte vive em repositório privado; o que está aqui é a
descrição da estrutura, não instruções de instalação.

## Estrutura do projeto

```text
.
  config.py
  run.py                     # Entrypoint; aborta o boot se faltar dependência crítica
  requirements.txt
  migrations/                # Alembic
app/
  __init__.py                # Inicialização Flask (factory create_app)
  routes/                    # Rotas por domínio, todas no blueprint 'main'
    __init__.py              #   core: bp, hooks, dashboard, /api/pendencias, /health, /diagnostico*
    empresas.py              #   rotas de empresa
    certidoes.py             #   /certidao/* (baixar delega a emissao_service)
    lotes.py                 #   factory de rotas de lote + fluxos do agendador
    relatorios.py            #   /relatorios, /configuracoes, exportação
    nfse.py                  #   /nfse/* (importação, resolução, sessão e lote assistido)
    manifestador.py          #   /manifestador/* (cofre, chaves, eventos e lote)
    contratos_portais.py     #   contratos adaptativos dos portais e incidentes
  auth.py                    # Login/papéis (deny-by-default) + painéis admin
  cli.py                     # Comandos CLI de administração
  models.py                  # Modelos do banco
  captcha_solver.py          # Integração 2captcha (ALTCHA e captcha de imagem)
  file_manager.py            # Detecção/movimentação de PDFs
  errors.py                  # Taxonomia de erros + mensagens acionáveis
  utils.py                   # Utilitários compartilhados (inclui validação de CPF/CNPJ)
  automation/                # Pacote de automação
    sites.py                 #   URLs, seletores e validades padrão
    driver.py                #   WebDriver Chrome/undetected-chromedriver
    cert_policy.py           #   Núcleo da auto-seleção de certificado (RS e NFSe)
    cert_store.py            #   Leitura dos certificados A1 e casamento por CNPJ
    steps.py                 #   Steps municipais data-driven
    pdf.py                   #   Leitura/classificação de PDF
    emissao.py               #   Emissão por tipo (FGTS/Estadual RS/Municipal/Trabalhista)
    captcha_img.py           #   Núcleo de captcha de imagem
    trabalhista.py           #   Fluxo CNDT/TST
    nfse.py                  #   Emissor Nacional de NFS-e (login, etapas do DPS, detectores)
    nfse_emitidas.py         #   Leitura da tela de NFS-e emitidas do portal
    nfse_recon.py            #   Reconhecimento adaptativo do portal da NFS-e
    trabalhista_recon.py     #   Reconhecimento adaptativo do portal trabalhista
    capture.py               #   Screenshot + HTML na falha Selenium
    batch_state.py           #   Estado e locks compartilhados dos lotes
  services/                  # Camada de serviços (motor de lotes, agendador, notificações,
                             #   exportação, observabilidade, importação e emissão de NFS-e,
                             #   manifestação de NF-e, circuit breaker por portal e saúde
                             #   dos portais)
  schemas/                   # Validação de entrada das rotas
  static/                    # CSS, imagens e JS por página (ES modules, sem bundler)
  templates/                 # Jinja2
```

A lógica mora nos serviços; as rotas são finas e ficam com o envelope HTTP.
Lote nenhum tem controle próprio: os seis fluxos passam pelo mesmo motor, e o
estado compartilhado fica em um único lugar.

## Observabilidade e diagnóstico

- Logs com **saída dupla**: console legível para humano (hora, nível, domínio, evento, campos-chave e `req_id`, com cor por nível) e arquivo JSON rotativo com o registro cru.
- `request_id` por requisição HTTP e `execution_id` por execução de lote; as respostas HTTP incluem o header `X-Request-Id` para correlacionar logs e requisições.
- Taxonomia de erros (`TIMEOUT`, `CAPTCHA`, `PORTAL`, `SELECTOR`, `NETWORK_PATH`, `PERMISSION`, `DB`, `UNKNOWN`) traduzida em **mensagens acionáveis** (título + causa + ação) que chegam ao usuário no toast e carregam `error_type`/`acao` no JSON.
- **Pré-checagens (preflight)** antes de emitir ou abrir lote: valida rede, perfil do Chrome e solver, falhando cedo com mensagem clara em vez de quebrar no meio do Selenium.
- **Detector de padrões recorrentes**: o mesmo erro repetido no mesmo alvo abre um alerta com hipótese (provável seletor quebrado ou portal fora).
- **Painel de diagnóstico**: últimos erros e avisos, com histórico persistido em banco e retenção configurável, mais os alertas de recorrência.
- **Painel de municípios**: estado da automação de cada município, com dry-run sob demanda.
- **Contratos dos portais** (perfil admin): estrutura aprovada de cada portal com contrato adaptativo, incidentes abertos e histórico de versões. "Verificar agora" só observa a tela do portal — não preenche, não resolve captcha e não emite. Ativar uma versão muda o que a automação obedece e por isso pede confirmação; se houver emissão em curso no mesmo portal, a ação é recusada (HTTP 423) em vez de atrapalhar o lote.
- Um job diário do agendador faz a mesma observação sozinho, deslocado algumas horas da emissão, para a mudança de layout aparecer antes da primeira emissão do dia. Roda mesmo com a renovação automática desligada, porque não emite nem consome captcha.
- **Saúde composta dos portais** (admin): `estado` informa apenas se o portal respondeu ao ping ou ao último dry-run; `contrato_estado` informa `compativel`, `autoajustado`, `bloqueado` ou `desconhecido`; `pronto_para_automatizar` combina essas dimensões com o circuit breaker. O health check da aplicação é separado e cobre somente a infraestrutura.
- Retry com limite e backoff em pontos recuperáveis, como timeout de carregamento e leitura de caminho de rede.
- **Health check** dedicado: retorna `ok` ou `degraded` com detalhes de banco de dados, caminho de rede (incluindo leitura e escrita), perfil do Chrome e configuração do solver.

## Testes e CI

Dois jobs paralelos no GitHub Actions, com papéis distintos:

- **`testes-sqlite`** — lint (`ruff`) e a suíte inteira em SQLite. É o gate rápido, roda em todo PR e em push na `main`.
- **`testes-mysql`** — a suíte inteira contra **MySQL 8.0** em service container, com `utf8mb4`/`utf8mb4_0900_ai_ci`, quando há alteração de backend, banco ou testes, mais uma execução noturna e manual. O job também valida a **migração idempotente** (`upgrade → downgrade → upgrade`).

A paridade não é zelo excessivo. Cinco divergências entre os dois bancos já
custaram caro, e **todas passam no gate rápido**: o tipo enum nativo diverge
(por isso status é `String`); o `DATETIME` do MySQL arredonda para o segundo; a
largura de `VARCHAR` o SQLite ignora e o MySQL impõe; o InnoDB recusa derrubar
índice usado por chave estrangeira, quebrando o `downgrade`; e o SQLite não
impõe integridade referencial, enquanto o InnoDB impõe.

No frontend, o JavaScript é verificado por checagem de sintaxe, tipos via JSDoc
com `checkJs` e testes em `node:test` com `jsdom`. Os testes JS usam dados
sintéticos e não acessam portais, certificados, Selenium nem serviços externos.

### A guarda do banco da suíte

O harness de testes cria um banco descartável por worker. Antes de criar o
schema, limpar dados ou destruí-lo, ele compara a URL real do engine com o
destino autorizado e confere uma sentinela que ele mesmo gravou. Isso cobre o
caso em que um lançador importou a aplicação antes do harness: a coleta falha
antes do primeiro DDL ou `DELETE`, e a mensagem mostra encontrado e esperado,
com as senhas mascaradas.

O opt-in para MySQL só aceita o banco de teste declarado ou o banco do worker
com o sufixo numerado. Um nome diferente falha antes de qualquer
`CREATE DATABASE` ou `DROP DATABASE`.

Rede de saída e criação de Chrome ficam **bloqueadas por padrão**. Um teste que
precise atravessar uma dessas fronteiras declara isso em si mesmo, por marcador
explícito, e continua usando dados sintéticos quando o transporte não é o objeto
da verificação.

### A barreira de dados sensíveis

Um hook de pre-commit recusa CNPJ, CPF e chave de acesso de NF-e com dígito
verificador válido que não estejam na lista de documentos sintéticos. Roda
também no CI, para que uma branch antiga não passe direto. O módulo está
publicado inteiro em [`vitrine/dados-sensiveis/`](../vitrine/dados-sensiveis/).

### O que os testes não cobrem

Os fluxos Selenium não são exercitados pelos testes automatizados — o navegador
é substituído por mocks. Para eles existe um roteiro de verificação manual. A
varredura recursiva de pastas do manifestador roda no navegador e também não tem
cobertura automatizada; o lado servidor está coberto.
