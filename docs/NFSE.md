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

Confirmar e desfazer são **ações locais**: o valor original do extrato (imutável, o número que
está no PDF), a descrição e a pendência ficam preservados para a restauração. A guarda fiscal pode
recusar confirmação, desfazimento ou descarte quando algum membro já tem emissão ou tentativa que
exige decisão; nesse caso, o grupo não muda. Resolva primeiro o desfecho da nota indicada pelo
sistema e retome a ação somente se o estado resultante permitir. Se a emissão for confirmada, o grupo
continua protegido: não confirme, desfaça nem descarte esse agrupamento.

## Emissão pelo portal: três modos, escolhidos a cada lote

- **Uma por vez**: preenche as três etapas do assistente DPS, para na tela de revisão e fecha o navegador quando a nota sai.
- **Lista inteira**: o mesmo laço, mantendo a janela autenticada de ponta a ponta.
- **Automático**: emite sozinho, depois de uma **auto-revisão** que confere documento, valor e descrição na tela antes de clicar. Usa navegador invisível e lê a alíquota novamente na própria sessão automática.

Nos dois primeiros modos, **a automação preenche e o operador emite**: quem clica em "Emitir NFS-e"
é sempre a pessoa. O modo automático é uma terceira opção escolhida explicitamente a cada lote,
nunca um padrão. Ele exige a auto-seleção válida do certificado da NFS-e antes de iniciar. Pausar,
retomar, pular e parar funcionam durante a espera.

Com a estação do usuário pronta, a assistida de **uma nota** abre o portal no Chrome do PC de quem
pediu, não na tela do servidor; por isso ela também funciona pelo acesso remoto.

- **Uma sessão de navegador para o dia todo**: o login por certificado digital e a conferência da alíquota do Simples acontecem uma vez, não a cada nota.
- **Ninguém chuta se a nota saiu**: a confirmação é lida do portal, não da interface. Se o navegador for fechado no meio da revisão, a nota fica *aguardando confirmação* e o operador marca à mão. Os dois chutes erram em direções opostas (marcar emitida perde uma nota que não existe; marcar pendente reemite no mês seguinte uma nota que já existe).
- **Cancelar uma linha** só registra uma decisão na fila local: não cancela NFS-e na prefeitura nem chama o portal ou a SEFIN. A linha deixa de ser emitível e ocupa a competência; se o extrato for importado novamente, a decisão aparece como duplicidade. Restaurar é uma ação local reversível e reavalia a duplicidade. A aplicação recusa o cancelamento local quando a linha já foi confirmada como duplicata, está emitida, aguarda confirmação no portal, foi absorvida por outra nota (`agrupada`) ou tem uma operação fiscal protegida. Se a nota já existe no Emissor Nacional, trate qualquer cancelamento fiscal pelo procedimento oficial do emissor, fora desta ação.
- **Ação em massa parcial por desenho**: recusas comuns de estado ficam nomeadas e as outras ações permitidas são aplicadas; bloqueio da guarda fiscal compartilhada ou falha de commit reverte o conjunto inteiro. Só entram ações reversíveis por um clique (cancelar/restaurar linha, marcar/desmarcar emissão manual). **Emitir e preencher ficam de fora**, por definição.

## O outro lado da conta: conferência do portal

Um espelho da tela de NFS-e emitidas do Emissor Nacional responde "o que a Receita registra que eu
emiti", contra o "o que eu preciso emitir" vindo do extrato. Daí sai o total do mês, que antes era somado
à mão, e as duas divergências que interessam: **quem pagou e ficou sem nota**, e **que nota saiu sem
pagamento**.

- Filtro e paginação do portal são **querystring**, então a automação monta a URL e navega, o que elimina máscara de data, datepicker e botão que só existe após render assíncrono. O módulo **só lê**: a tela tem botões de cancelar e substituir NFS-e e ele nunca os toca.
- As colunas são lidas pela **classe** do `<td>`, nunca pelo índice, porque uma coluna nova no portal deslocaria tudo em silêncio. A varredura confere a contagem contra o "Total de N registros" da própria tela e **recusa** o resultado se não bater: um total fiscal a menos passa despercebido por parecer plausível.
- **Duas coisas se chamam "competência" e quase nunca são o mesmo mês**: a competência do honorário (mês de referência) e a competência do DPS (mês da emissão). O cliente paga em julho o honorário de junho, e casar os dois campos acusava "pagou e ficou sem nota" para quase todo cliente. A conciliação usa **documento + valor**, com desempate por proximidade de data.
- A consulta é **somente de leitura** e ocorre em segundo plano. Uma sessão autenticada que já esteja aberta, inclusive uma janela visível usada na emissão assistida, é reutilizada; quando não há sessão válida, a abertura é invisível e depende da auto-seleção do certificado.


## Revisão pré-emissão da API nacional (P3-A)

O cartão **Revisão pré-emissão** confere localmente os fatos de uma nota nova antes do preparo da
DPS de produção. Ele mostra os bloqueios e valida uma DPS candidata em memória; não reserva número,
não assina nem envia a DPS e não autoriza a emissão.

- A lista usa somente o veredito de nota emitível calculado pelo servidor. Informe manualmente
  `dCompet`, a data planejada da emissão; ela não é derivada do mês de referência da fila. O pré-voo
  valida a DPS candidata com essa data, e o preparo usa a mesma data em `dhEmi`.
- A resposta mostra tomador, endereço cadastral local, competência mensal, `dCompet`, valor,
  descrição, prestador, município, tributação, NBS, perfil IBS/CBS, retenções, ambiente e versão
  do XSD, além de cada prova e bloqueio.
- O pré-voo mostra o perfil IBS/CBS configurado e exige ISSQN tributável sem retenção. A prova
  estrutural monta uma DPS candidata com número sintético e a valida contra o XSD de produção
  versionado. Uma revisão local apta não reserva número, não assina nem envia a DPS.
- Para `cIndOp 100301`, o pré-voo reaproveita o endereço já importado no cadastro local. Se o cadastro
  não tiver logradouro, número, bairro, CEP ou município IBGE, a revisão bloqueia; ela não consulta
  Receita, portal ou API para completar o dado automaticamente.
- A ação lê somente o banco e o XSD versionado. Monta a DPS candidata em memória com número
  sintético para validar a estrutura, mas não assina nem reserva número. Não consulta ADN/SEFIN/portal,
  não altera a nota e não oferece botão de envio.

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

## Emissão pela API nacional em produção

A emissão por API é um fluxo separado do portal Selenium. Há três modos: **uma nota**, escolhida pelo operador; **assistido**, que apresenta uma nota por vez e pede confirmação antes de cada envio; e **automático**, que exige autorização explícita para um escopo fechado e é processado pelo servidor.

Em qualquer modo, a **preparação** revalida o pré-voo, reserva um número, monta e assina a DPS localmente e grava uma tentativa durável. Preparar não envia nada à SEFIN. O POST só começa após a confirmação de envio da nota ou, no automático, após a autorização do lote. Se uma edição aceita mudar os fatos usados na DPS depois do preparo, prepare outra DPS: o envio da tentativa desatualizada é recusado.

No modo automático, o operador escolhe uma competência ou a última importação como escopo e informa `dCompet` no formato `AAAA-MM-DD`. A autorização congela a lista de notas aptas naquele momento e a data; notas importadas depois não entram nesse lote. `dCompet` é a data planejada para emissão, não a competência mensal do honorário, e também define a data usada em `dhEmi`. Bloqueios do pré-voo precisam ser resolvidos antes da autorização. O servidor mantém o progresso mesmo que a aba feche e interrompe o lote no primeiro desfecho que pede decisão. Se o lote ficar parado após reinício do servidor, retome ou encerre essa autorização antes de criar outra.

A falha de um motor não aciona o outro. O fluxo de produção não troca para Selenium e o ensaio restrito não envia para produção.

A tentativa conserva o XML da DPS assinada antes do envio. O [manual oficial da API do Emissor
Público Nacional](https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/documentacao-atual/manual-contribuintes-emissor-publico-api-sistema-nacional-nfs-e-v1-2-out2025.pdf),
seção 1.3.2, descreve que `POST /nfse` recebe a DPS e retorna o XML da NFS-e gerada com ela.
No sucesso, o serviço confere o identificador informado pela SEFIN, a estrutura mínima do XML e se a
chave retornada corresponde ao `Id` da NFS-e; então persiste o XML integral e a chave na mesma
tentativa `EmissaoDpsNfse` e atualiza o espelho na mesma transação. O parser recusa XML
descompactado acima de 20 MiB. No MySQL, os XMLs da tentativa usam `LONGTEXT`; no SQLite usam
`TEXT`. Para a persistência funcionar em todo o limite aceito, o MySQL precisa de
`max_allowed_packet` de pelo menos `128M`; a aplicação bloqueia a consulta à SEFIN ou o envio fiscal
quando o limite global ou o da conexão estiver abaixo disso.
A aplicação compara com a DPS enviada o identificador, o ambiente, tipo e documento do prestador e
do tomador, a competência e o valor do serviço, além de conferir a coerência entre a chave retornada
e o `Id` da NFS-e. Essa comparação é parcial: não cobre todos os campos da DPS incorporada, e a
aplicação não verifica localmente a assinatura do XML da NFS-e recebida.

Se a SEFIN confirmar a emissão, mas a nota da fila já estiver emitida por outro caminho ou não estiver
mais disponível, a prova validada fica preservada na tentativa em `conflito_vinculo`, sem reescrever
a nota ou o espelho conhecido. Só quando a emissão estiver confirmada pela fonte oficial, a linha
local estiver marcada como emitida e a prova estiver completa, use **Reconciliar vínculo**: a ação
registra a prova no espelho sem novo acesso à SEFIN nem alteração da linha. Se a linha não estiver
disponível, a emissão não puder ser confirmada ou os fatos da prova divergirem, mantenha a tentativa
pendente para análise e não prepare nem envie outra DPS. Respostas conflitantes são preservadas
separadamente da prova já conhecida.

Timeout ou resposta inconclusiva deixa a tentativa em `desfecho_desconhecido`; `enviando` também
exige recuperação antes de outra ação. Use **Reconsultar resultado** na mesma tentativa: a consulta
usa o identificador já enviado, não faz outro POST e não reserva outro número. Se a reconsulta ainda
não comprovar o resultado ou encontrar divergência, mantenha o bloqueio e encaminhe a conferência;
não repita o envio. A interface mostra o estado e a disponibilidade dos XMLs, não seu conteúdo bruto.

A API não usa o Emissor Nacional via Selenium como fallback. Pré-voo, assinatura, envio, consulta e
reconciliação têm ações separadas; o ambiente de produção é fixado no serviço, e a tela não aceita
URL ou ambiente fiscal definidos pelo pedido HTTP.

## Limitações atuais

- O vínculo automático nome→CNPJ cobre a maior parte do extrato, mas não tudo; o restante exige uma escolha do operador, que fica memorizada para os meses seguintes.
- A leitura do PDF do Inter é acoplada ao layout atual do extrato; mudança de layout do banco exige revisão das colunas.
- A conferência do portal soma apenas as notas com código de nota gerada; outros códigos são contados à parte e mostrados, nunca somados nem descartados por adivinhação.
