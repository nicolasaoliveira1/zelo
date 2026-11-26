# Certidões fiscais

> Pilar de **regularidade fiscal dos clientes**: controle de vencimentos e emissão
> automatizada das certidões Federal, FGTS, Estadual, Municipal e Trabalhista.
> O outro pilar (faturamento do escritório) está em [NFSE.md](NFSE.md).

## Acesso e segurança (login e papéis)

- Login por sessão: **nenhuma tela funciona sem estar autenticado** (negação por padrão; só login, health e estáticos são públicos).
- Três papéis com hierarquia (**leitura** < **operador** < **admin**): leitura só consulta e exporta; operador emite/edita; admin gerencia usuários e vê a auditoria.
- Proteção CSRF em todos os formulários; senhas com hash forte.
- **Trilha de auditoria**: ações sensíveis (login, criação/alteração de usuário, etc.) ficam registradas e são consultáveis em `/admin/auditoria` (admin).
- Gestão de usuários em `/admin/usuarios` (admin). O primeiro administrador é criado por linha de comando (não há auto-cadastro público).
- O login confere usuário e senha **sempre**, mesmo com sessão aberta no navegador; a sessão expira após 12 h sem uso.
- Toda resposta sai com cabeçalhos de segurança (`X-Frame-Options`, `nosniff`, política de referência). Atrás do túnel do Cloudflare, os cookies saem com `Secure` e o IP real do cliente vale para o limite de tentativas e a auditoria.

## Visão geral e operação

- **Visão geral** (`/`): um número por pilar (certidões que pedem atenção, NF-e a manifestar, NFS-e para tratar, certificados A1 que vencem em 30 dias) e a **Central de operações** — pendências e alertas em ordem de gravidade, próximos vencimentos de certificado, a atividade das automações nos últimos 7 dias e o resultado da última execução por tipo. Dado que não carregou aparece como indisponível, nunca como zero.

- Cadastro de empresa com criação automática de 5 certidões.
- Filtros por status e busca por nome em tempo real.
- Status visual de certidões (cor reservada ao estado; o acento verde-petróleo é só para ação):
  - Verde: válida
  - Âmbar: a vencer (limite configurável, global ou por tipo de certidão)
  - Vermelho: vencida
  - Laranja-tijolo: pendente (provável débito), em tom próprio e distinto de vencida
  - Cinza: sem data definida
- Cadastro de nova empresa com seleção de cidade via dropdown (apenas municípios cadastrados) e inscrição mobiliária condicional (Imbé).
- Tela de Empresas com listagem, filtros, edição e remoção com confirmação.
- Toda certidão pendente guarda **o motivo** (positiva, FGTS com impedimento, em processamento no portal, portal não emitiu, marcada à mão, município ou UF mudou…). Mudar a cidade ou a UF da empresa deixa pendentes as certidões que dependem do endereço, para entrarem no próximo lote.
- Consulta de CNPJ **na hora** pela API comercial da CNPJá, com confirmação que mostra o saldo de créditos antes e depois.
- Barra do topo com os pilares no centro e o menu Sistema; navegação sem piscar (fontes pré-carregadas e cache de estáticos).
- Tema claro/escuro com persistência local.

## Automação de emissão

- **Federal**: fluxo assistido melhorado (o gate é hCaptcha invisível Enterprise, inviável sem operador).
  - "Abrir Site" abre o portal da RFB, copia o CNPJ e monitora o download do PDF que o operador baixa.
  - O PDF é classificado ao chegar: positiva vira PENDENTE (arquivo removido); negativa/positiva-com-efeitos-de-negativa grava a validade lida do PDF ("Válida até"), com fallback de 180 dias quando a data não é legível. Assim a Federal entra no ciclo de alertas.
  - Alternativa por **upload**: o operador pode anexar um PDF federal que já tem em mãos (botão "Registrar PDF"), sem reabrir o portal; a mesma classificação/validade é aplicada.
- **FGTS**:
  - Emissão individual com geração de PDF via Chrome DevTools.
  - Emissão em lote com pausa, retomada, parada e resumo final.
  - Detecção de PDF positiva no lote: arquivo removido e certidão marcada como PENDENTE automaticamente.
  - **Contrato adaptativo**: a tela observável fixa CNPJ, Consultar, Certificado e Visualizar antes da automação. Com contrato ativo, os seletores do snapshot são a única fonte; sem contrato, o mapa legado continua valendo.
- **Estadual RS**:
  - Unitário mantido manual para evitar consumo indevido de solver.
  - Lote com ALTCHA automático via API 2captcha.
  - Processo robusto: só avança para o próximo CNPJ após baixar, estabilizar, mover e classificar o arquivo.
  - **Contrato adaptativo**: a sessão por certificado chega à tela do formulário e observa CNPJ, host do ALTCHA e Enviar sem preencher nem submeter. Só o CNPJ pode autoajustar; mudança em ALTCHA ou Enviar bloqueia para revisão. Sem contrato, o fluxo legado permanece.
- **Municipal**: automação orientada por dados, com URL, seletores e steps de cada cidade guardados na tabela Município.
  - Tramandaí: fluxo condicional com detecção de link NEGATIVA na página final; suporte a lote.
  - Gravataí: classificação de status via conteúdo do PDF (positiva/negativa), com tratamento automático de pendência quando positiva.
  - Imbé: resolução automática de captcha de imagem via 2captcha; emissão de geral e mobiliário separadamente; suporte a lote por subtipo.
  - Portais **IPM Atende.Net** (Gravataí, Osório, Novo Hamburgo): a emissão individual usa **undetected-chromedriver** com um perfil persistente dedicado para não ser bloqueada pelo score anti-bot do portal (tela "validação automática de segurança / baixa pontuação"). A detecção é automática pela URL (`*.atende.net`), então qualquer novo município com esse domínio entra no fluxo sem mudança de código. O captcha em si continua resolvido manualmente pelo operador. Falhas de pré-condição (driver indisponível ou perfil em uso) retornam mensagem acionável (HTTP 409) sem cair para o navegador comum.
  - **Contrato adaptativo por município/variante**: a configuração existente é traduzida para um snapshot em memória sem sobrescrever o cadastro. O dry-run continua sendo a referência até toda a variante ter contrato ativo; município sem adaptador ou sem contrato não recebe proteção parcial.
- **Trabalhista (CNDT/TST)**:
  - Unitário mantido assistido/manual para evitar consumo indevido de solver (o operador resolve o captcha).
  - Lote com captcha de imagem resolvido automaticamente via 2captcha; disponível também na emissão proativa do agendador.
  - Classificação do PDF: positiva vira PENDENTE (arquivo removido); negativa/positiva-com-efeitos-de-negativa grava validade de 180 dias.
  - **Contrato adaptativo (piloto)**: os seletores do CNDT deixaram de ser constante de código e passam a vir de uma **versão aprovada** da estrutura do portal, guardada em banco. Antes de preencher qualquer campo, a automação observa a tela e compara com a versão ativa: se nada mudou, segue; se um campo de entrada mudou de endereço de forma inequívoca, ajusta sozinha; se mudou a rota, o captcha ou o botão de emitir, **para antes de gastar captcha** e abre um incidente para revisão humana. Enquanto não houver versão ativa, o fluxo antigo continua valendo sem alteração.

## Verificação preventiva dos municípios

- **Dry-run por município**: percorre o fluxo real do portal até a fronteira da emissão e reporta qual passo/seletor deixou de resolver. O passo que gera o PDF é apenas localizado, **nunca clicado**: nenhuma certidão é emitida e nenhum download acontece.
- Honesto sobre o que não deu para ver: passos que dependeriam do clique de emissão são reportados como não verificados, em vez de contados como aprovados. Portal com captcha vira "parcial" (não gasta crédito de solver).
- **Roda sozinho todo dia**, em horário deslocado do lote de emissão, e dispara alerta quando um município passa a falhar.
- **Painel em `/diagnostico/municipios`** com o estado de cada município e botão para rodar o dry-run sob demanda.
- **Passo `recaptcha`** no fluxo municipal: lê a chave do reCAPTCHA v2 na página, resolve no 2captcha e entrega o token ao callback do widget. O dry-run nunca executa esse passo, porque é pago.
- **Estação do operador**: com as estações ligadas, a emissão individual roda no PC de quem pediu, não na tela do servidor. A estação fala com o servidor só pela API (HTTPS pelo domínio), com token próprio ligado ao usuário; recebe a tarefa, roda o mesmo núcleo de emissão num SQLite local descartável e devolve o PDF, que o servidor confere antes de promover. Instala-se pelo próprio Zelo (menu do avatar › **Instalar neste PC**), com checagem do PC e ícone na bandeja. Pelo acesso remoto, nada abre navegador no servidor.
- Grafia das cidades padronizada (acento e caixa) com fonte única de canonicalização. O casamento no backend segue normalizado, então acento não quebra nada.

## Gestão de arquivos

- Detecta PDF novo/alterado na pasta Downloads.
- Move e renomeia para a pasta final da empresa.
- Salva caminho do arquivo no banco.
- Visualização de PDF com token assinado e expirável.
- **Arquivos da empresa pelo navegador**: "Abrir pasta" abre um painel lateral só de leitura, preso à pasta da empresa (caminho absoluto, `..` e link para fora respondem 404), com cada download registrado na auditoria. Funciona de qualquer PC e pelo domínio.
- Download automático no Chrome (incluindo fluxos em modo anônimo), reduzindo necessidade de interação manual no diálogo de salvar.

## Emissão proativa (agendador)

- Agendador embutido (sem serviço externo) que roda **uma vez por dia**, na hora configurada no painel.
- Todo dia tira uma "foto" das contagens (para o gráfico de evolução) e, quando ligado, **enfileira e emite automaticamente** as certidões vencidas/a vencer, reaproveitando os mesmos lotes da operação manual.
- Fila durável: o que ficou pendente sobrevive a reinício do sistema e pode ser retentado por item.
- Liga/desliga e hora ficam na tela de **Configurações**.

## Notificações por e-mail

- **Digest periódico** (semanal por padrão, ou diário) com o resumo da carteira: quantas a vencer, vencidas e pendentes.
- **Alertas** de falha recorrente de automação e de **saldo baixo do 2captcha** antes de um lote parar no meio.
- Anti-spam durável (não repete o mesmo alerta dentro da janela, mesmo após reiniciar) e envio que nunca derruba a automação se o e-mail falhar.
- Destinatários e cadência configuráveis no painel; credenciais SMTP só por variável de ambiente.

## Exportação e relatórios

- **Exportar carteira (Excel):** botão na tela de Certidões baixa uma planilha `.xlsx` **respeitando os filtros ativos** (status, tipo, estado, cidade). Sai exatamente o que está na tela.
- **Dossiê (PDF) por empresa:** um único PDF com capa + as certidões **válidas** concatenadas, pronto para licitação/cliente (papel operador). PDF ausente/corrompido é pulado com aviso.
- **Produtividade:** página `/produtividade` com emissões/dia, taxa de sucesso por tipo, tempo médio de lote (30/90 dias) e a lista de empresas que falharam, com o motivo legível e o que fazer; exportação em Excel.
- **Relatórios:** página `/relatorios` com indicadores e distribuição por status/tipo, pendências detalhadas com rankings por tipo e município, as últimas 100 certidões emitidas, o gráfico de evolução por status.


## Limitações atuais

- Automações dependem da estabilidade dos portais públicos; mudanças de HTML nos sites podem exigir ajuste de seletores.
- Captchas fora do lote RS, Municipal (Imbé) e Trabalhista continuam majoritariamente manuais.
- A Federal permanece assistida por limitação do portal (hCaptcha invisível Enterprise), não por escolha de escopo.
- Ainda não existe cobertura completa de testes automatizados para os fluxos Selenium; a verificação deles é feita por um roteiro manual.
