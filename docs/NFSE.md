# NFS-e de honorários

> Pilar de **faturamento do escritório**: emite no **Emissor Nacional** (`nfse.gov.br`) as notas
> de honorários do próprio escritório, partindo do extrato do banco.
> O outro pilar (regularidade fiscal dos clientes) está em [CERTIDOES.md](CERTIDOES.md).

É o único fluxo do sistema que produz **documento fiscal**, e por isso o desenho é
deliberadamente conservador: errar não é rollback, é cancelamento de nota junto à prefeitura.

## Do extrato à fila de notas

- **Dois formatos entram pela mesma porta**, escolhidos pelo **conteúdo** do arquivo e nunca pela extensão: o **CSV de cobranças do Banrisul** e o **PDF do extrato do Banco Inter** (onde os honorários chegam por Pix). Uma seleção pode misturar os dois; dali para baixo o código é o mesmo.
- **A competência tem duas regras, de propósito.** No CSV ela é *derivada* (mês anterior ao vencimento do título, tratando a virada de ano, porque lá a data é de vencimento); no Inter ela vem *escrita* na descrição do Pix e é essa que vale.
- **Leitura do PDF por coordenada de coluna**, não por texto corrido: o extrato do Inter imprime `1.806,00 3.862,63` sem dizer qual é Entrada e qual é Saldo. As colunas são alinhadas à direita em `x` fixo e as coordenadas saem da própria linha de cabeçalho. Nada é *hardcoded* em pixel. Uma palavra só vira valor se parecer dinheiro **e** terminar na borda da coluna.
- **Cada nome vira um cliente**: o banco manda a razão social truncada em 35 caracteres, o cadastro guarda o apelido curto. O casamento é por similaridade, mas só vincula sozinho quando o match é **bom e folgado** em relação ao segundo colocado. Na dúvida, manda para conferência manual em vez de arriscar. Errar aqui emitiria uma nota com o CNPJ de outro cliente. A escolha manual vira **apelido salvo**: no mês seguinte aquele nome já entra resolvido.
- **Tomador pessoa física**: nem todo cliente é empresa. CPF é aceito e memorizado (com validação de dígito verificador), sem virar cadastro de empresa.
- **Trava de duplicidade** por documento + competência + serviço, contando inclusive notas emitidas fora do sistema. Avisa e pede liberação explícita, em vez de bloquear, porque uma alteração contratual e uma baixa da mesma empresa caem no mesmo mês e são duas notas legítimas.
- **Conferência de valor**: se a soma das parcelas do extrato não bate com o valor final, a linha é marcada com divergência (e mantém o valor final do banco).

## Agrupamento: o sistema propõe, o operador confirma

Várias entradas do mesmo tomador no mês, ou um estorno abatendo entradas, viram uma **proposta de
agrupamento**. Enquanto a proposta espera resposta, as notas do grupo ficam **fora da fila**:
emitir a entrada bruta de R$ 2.000,00 com um estorno de R$ 1.784,00 pendurado nela é exatamente
o erro que a proposta evita.

Confirmar é **reversível**: confirmar e desfazer são simétricos e nada é destruído no caminho.
O valor volta do valor original do extrato (imutável, o número que está no PDF) e descrição e
pendência voltam do retrato guardado no momento do agrupamento.

## Emissão: três modos, escolhidos a cada lote

- **Uma por vez**: preenche as três etapas do assistente DPS, para na tela de revisão e fecha o navegador quando a nota sai.
- **Lista inteira**: o mesmo laço, mantendo a janela autenticada de ponta a ponta.
- **Automático**: emite sozinho, depois de uma **auto-revisão** que confere documento, valor e descrição na tela antes de clicar. Usa navegador invisível e lê a alíquota novamente na própria sessão automática.

Nos dois primeiros modos, **a automação preenche e o operador emite**: quem clica em "Emitir NFS-e"
é sempre a pessoa. O modo automático é uma terceira opção escolhida explicitamente a cada lote,
nunca um padrão. Ele exige a auto-seleção válida do certificado da NFS-e antes de iniciar. Pausar,
retomar, pular e parar funcionam durante a espera.

- **Uma sessão de navegador para o dia todo**: o login por certificado digital e a conferência da alíquota do Simples acontecem uma vez, não a cada nota.
- **Ninguém chuta se a nota saiu**: a confirmação é lida do portal, não da interface. Se o navegador for fechado no meio da revisão, a nota fica *aguardando confirmação* e o operador marca à mão. Os dois chutes erram em direções opostas (marcar emitida perde uma nota que não existe; marcar pendente reemite no mês seguinte uma nota que já existe).
- **Ação em massa parcial por desenho**: o que der certo é aplicado e o que não der volta nomeado. Só entram ações reversíveis por um clique (cancelar, restaurar, marcar/desmarcar emitida manualmente). **Emitir e preencher ficam de fora**, por definição.

## O outro lado da conta: conferência do portal

Um espelho da tela de NFS-e emitidas do Emissor Nacional responde "o que a Receita registra que eu
emiti", contra o "o que eu preciso emitir" vindo do extrato. Daí sai o total do mês, que antes era somado
à mão, e as duas divergências que interessam: **quem pagou e ficou sem nota**, e **que nota saiu sem
pagamento**.

- Filtro e paginação do portal são **querystring**, então a automação monta a URL e navega, o que elimina máscara de data, datepicker e botão que só existe após render assíncrono. O módulo **só lê**: a tela tem botões de cancelar e substituir NFS-e e ele nunca os toca.
- As colunas são lidas pela **classe** do `<td>`, nunca pelo índice, porque uma coluna nova no portal deslocaria tudo em silêncio. A varredura confere a contagem contra o "Total de N registros" da própria tela e **recusa** o resultado se não bater: um total fiscal a menos passa despercebido por parecer plausível.
- **Duas coisas se chamam "competência" e quase nunca são o mesmo mês**: a competência do honorário (mês de referência) e a competência do DPS (mês da emissão). O cliente paga em julho o honorário de junho, e casar os dois campos acusava "pagou e ficou sem nota" para quase todo cliente. A conciliação usa **documento + valor**, com desempate por proximidade de data.
- A consulta é **somente de leitura** e ocorre em segundo plano. Uma sessão autenticada que já esteja aberta, inclusive uma janela visível usada na emissão assistida, é reutilizada; quando não há sessão válida, a abertura é invisível e depende da auto-seleção do certificado.

## Como usar

Acesse `/nfse` e siga os passos da página:

1. **Importar** o extrato do banco (CSV do Banrisul e/ou PDF do Inter, um ou vários de uma vez).
2. **Resolver** o que ficou pendente: vínculo empresa→CNPJ, descrição do serviço e propostas de agrupamento.
3. **Abrir o portal** e conferir a alíquota (uma vez por sessão).
4. **Escolher o modo** e emitir. Nos modos assistidos, o sistema para na tela de revisão de cada nota. **O clique em emitir é seu**.

## Revisão pré-emissão da API nacional (P3-A)

O cartão **Revisão pré-emissão** é um pré-voo local para uma nota nova. Ele existe para conferir
os fatos e deixar os bloqueios visíveis antes de a API de produção ser liberada; não é uma emissão
simulada nem uma autorização.

- A lista usa somente o veredito de nota emitível calculado pelo servidor. Informe manualmente
  `dCompet`, que no perfil atual corresponde ao dia planejado da emissão, normalmente no fim do mês;
  o campo começa vazio e não é derivado do mês de referência da fila. O montador futuro usará a data
  efetiva de `dhEmi` para manter essa regra no XML.
- A resposta mostra tomador, endereço cadastral local, competência mensal, `dCompet`, valor,
  descrição, prestador, município, tributação, NBS, perfil IBS/CBS, retenções, ambiente e versão
  do XSD, além de cada prova e bloqueio.
- O perfil decidido para a API informa IBS/CBS (`CST 200`, `cClassTrib 200052`, `cIndOp 100301`,
  sem tratamento especial) e ISSQN tributável sem retenção. A prova estrutural da DPS continua
  bloqueada até resolver os demais campos obrigatórios do grupo IBS/CBS e a compatibilidade do XSD;
  uma revisão local apta ainda não autoriza emissão.
- Para `cIndOp 100301`, o pré-voo reaproveita o endereço já importado no cadastro local. Se o cadastro
  não tiver logradouro, número, bairro, CEP ou município IBGE, a revisão bloqueia; ela não consulta
  Receita, portal ou API para completar o dado automaticamente.
- A ação lê somente o banco e o XSD versionado. Não monta XML final, não assina, não reserva
  número, não consulta ADN/SEFIN/portal, não altera a nota e não oferece botão de envio.

### Estado de prontidão

O pré-voo local está pronto para conferência com dados sintéticos e o builder
offline já monta a DPS nova em memória com `IBSCBS` completo para o perfil
decidido. A emissão real ainda depende da compatibilidade estrutural do XSD,
contador, assinatura, transporte e recuperação. A montagem local não envia,
reserva número nem substitui a revisão humana.

## Ensaio restrito da API nacional (P2)

O cartão **Ensaio restrito** serve para reproduzir uma nota histórica já emitida usando a API
oficial, sem transformar o ensaio em emissão de produção. Ele só lista notas que o servidor
reconhece como `emitida` e vinculadas a um espelho oficial.

- **Preparar ensaio** lê a referência, monta a DPS, valida o esquema, verifica a assinatura e
  compara os fatos fiscais localmente. Essa ação não faz escrita fiscal remota.
- **Enviar ao ambiente de testes** é uma ação separada e pede confirmação no modal. O ambiente
  restrito pode gerar uma NFS-e de teste, mas ela é **sem validade jurídica** e não altera a nota
  histórica de origem.
- Divergência fiscal bloqueadora deixa o envio desabilitado. Um resultado `indefinido` ou um envio
  ainda em andamento oferece somente **Reconsultar resultado**, sem novo envio automático.
- **Verificar acesso** mostra três serviços independentes, cada um em Produção e Produção restrita:
  Parametrização Municipal (`GET /parametrizacao/{codigoMunicipio}/convenio` no ADN), SEFIN
  (`HEAD /dps/{id}`, somente leitura) e ADN de contribuintes (`GET /DFe/0` com `lote=false`). A
  Parametrização Municipal não é o teste direto da SEFIN. No ADN, um `404` acompanhado do envelope
  oficial que informa ausência de documento confirma o acesso; um `404` genérico continua sendo
  tratado como resposta inválida. O diagnóstico nunca usa `POST /nfse`.
- O campo **Ambiente de leitura do ADN** controla somente a verificação e a sincronização do
  histórico: **Produção** lê documentos reais já distribuídos; **Produção restrita** lê o ambiente
  de testes. Os endpoints não são intercambiáveis. Essa escolha nunca autoriza emissão.
- A conferência read-only segue a sequência **portal → ADN → comparação**: o portal é consultado
  no intervalo escolhido, o ADN é sincronizado para o mesmo recorte e as observações das duas
  fontes são comparadas. Uma fonte inconclusiva não é convertida em igualdade.
- Na conferência sombra, a tela separa o tamanho persistido de cada retrato no período das
  contagens da execução: `ADN: 0` pode significar que o cursor não encontrou NSU novo, mesmo
  havendo observações ADN já gravadas e comparadas.
- Quando o ADN chegar ao fim do cursor e devolver o envelope contratual
  `NENHUM_DOCUMENTO_LOCALIZADO` — inclusive com HTTP 400/404 — a sincronização termina normalmente,
  preservando o último NSU confirmado. O manual recomenda aguardar pelo menos uma hora antes de
  consultar novamente.
- O ensaio P2 ignora essa escolha de leitura e usa sempre **Produção restrita** para preparar e
  enviar a DPS de teste. A produção não é um destino possível para o ensaio.
- Antes de consultar o identificador ou enviar a DPS, o sistema consulta novamente a
  **Parametrização Municipal da Produção restrita**. Convênio inativo, credencial não autorizada,
  indisponibilidade ou rejeição mantêm o ensaio em `preparado`, registram uma orientação e fazem
  zero POST. Um resultado de Parametrização Municipal em Produção e o teste direto da SEFIN não
  substituem essa barreira.

Antes de uma UAT, o administrador deve escolher uma série exclusiva do ambiente restrito e o
operador deve confirmar a nota histórica e os fatos mostrados na comparação. A UAT é manual,
explicitamente autorizada e nunca deve usar produção, série de produção ou dados de teste
misturados com a operação fiscal diária.

A série não é fornecida automaticamente pela SEFIN: ela identifica a sequência de DPS mantida
pelo contribuinte ou pela aplicação emissora. Em **Configurações da nota → Acesso à API nacional**,
consulte primeiro o campo **Série da DPS** no PDF ou XML de uma NFS-e recente e informe outro
número, exclusivo para o ensaio. O Zelo aceita de 1 a 5 algarismos, no intervalo de `0` a `79999`;
`80000–89999` é a faixa reservada à transcrição manual e valores maiores não pertencem ao leiaute
oficial. Se houver outra integração que gere DPS, confirme com quem a administra quais séries ela
utiliza antes de escolher; depois do primeiro uso, mantenha a série configurada para preservar a
sequência do contador.

## Limitações atuais

- O vínculo automático nome→CNPJ cobre a maior parte do extrato, mas não tudo; o restante exige uma escolha do operador, que fica memorizada para os meses seguintes.
- A leitura do PDF do Inter é acoplada ao layout atual do extrato; mudança de layout do banco exige revisão das colunas.
- A conferência do portal soma apenas as notas com código de nota gerada; outros códigos são contados à parte e mostrados, nunca somados nem descartados por adivinhação.
