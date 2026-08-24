# Design System da Interface Qt/QSS

> Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

## 1. Objetivos

O design da versão v0.3.0 prioriza leitura prolongada, estados inequívocos e operação segura
durante tarefas demoradas. A interface deve continuar utilizável em High-DPI sem depender de fontes
ou temas externos.

Princípios:

- foco no arquivo, progresso e resultado;
- feedback visível para hover, clique, drag-over, carregamento, cancelamento, sucesso e erro;
- contraste alto e hierarquia tipográfica simples;
- ações destrutivas ou interruptivas visualmente distintas;
- dispositivo real e etapa atual sempre identificáveis;
- nenhum resultado parcial apresentado como concluído.

## 2. Tokens de cor

| Papel | Cor | Uso |
| --- | --- | --- |
| Fundo | `#121214` | Janela principal |
| Painel | `#1E1E24` | Drop zone e áreas agrupadas |
| Entrada | `#18181C` | Editor, prévia, log e barra |
| Borda | `#2C2C35` | Divisores e contornos |
| Primária | `#6366F1` | Ação principal e progresso |
| Hover primário | `#4F46E5` | Botão primário em hover |
| Pressionada | `#4338CA` | Botão primário pressionado |
| Sucesso | `#10B981` | Conclusão e indicadores positivos |
| Texto principal | `#F3F4F6` | Títulos e conteúdo |
| Texto secundário | `#9CA3AF` | Metadados e ajuda |
| Desabilitado | `#4B5563` | Controles indisponíveis |
| Erro | `#EF4444` | Falha e cancelamento |
| Alerta suave | `#FCA5A5` | Texto do botão de cancelar |

O QSS canônico está em `app/ui/styles.py`.

## 3. Tipografia

- interface: Segoe UI, Inter ou sans-serif do sistema;
- log: Consolas, Fira Code ou monospace;
- título do aplicativo: 20 px / peso 700;
- título de seção: 15 px / peso 600;
- corpo e botões: 13 px;
- metadados e dispositivo: 11 px;
- log: 12 px.

Textos longos devem quebrar linha. Nome de arquivo e mensagens técnicas não podem provocar
overflow horizontal da janela.

## 4. Estrutura da janela

1. Cabeçalho com nome, descrição curta e dispositivo detectado.
2. Zona de seleção/drag-and-drop com nome do arquivo.
3. Linha de ações com iniciar, cancelar, copiar e salvar.
4. Status textual e barra de progresso.
5. Log somente leitura com rolagem.
6. Resultado em abas **Markdown** e **Visualização**.

A janela usa layout elástico. O editor e a visualização recebem o espaço vertical excedente.

## 5. Componentes

### Drop zone

- painel `#1E1E24`;
- borda tracejada de 2 px e raio de 8 px;
- drag-over: fundo `#252533` e borda `#6366F1`;
- aceita um único `.mp3` ou `.m4a`, sem distinção de maiúsculas;
- arquivo inválido gera mensagem em pt-BR sem substituir uma seleção válida.

### Botão primário

- fundo índigo, texto branco, raio de 6 px e padding 10/20 px;
- **Iniciar Transcrição** só fica habilitado com arquivo válido e worker inativo.

### Botões secundários

- fundo transparente, borda `#374151` e hover `#2C2C35`;
- copiar/salvar só ficam habilitados quando existe Markdown concluído.

### Botão de cancelamento

- fundo transparente, borda `#EF4444`, texto `#FCA5A5`;
- habilitado somente durante processamento;
- após o clique, fica desabilitado para evitar solicitações repetidas;
- a mensagem informa que a etapa atual será finalizada com segurança.

### Progresso

- trilho `#18181C` e preenchimento índigo;
- estado determinado de preparação durante resolução/download/carregamento, evitando blocos
  animados fragmentados;
- percentual por timestamps durante inferência;
- volta a zero no cancelamento e alcança 100% somente na conclusão.

### Log

- somente leitura, fonte monoespaçada e rolagem vertical;
- exibe verificações, dispositivo, carregamento, segmentos e resultado;
- não deve exibir caminhos absolutos no documento exportado.

### Editor e visualização

- fundo `#18181C`, texto `#F3F4F6`, borda `#2C2C35`, raio de 6 px;
- Markdown é a fonte editável;
- visualização acompanha o conteúdo editado;
- scrollbars com largura 8 px, handle `#2C2C35` e hover `#4B5563`.

## 6. Matriz de estados

| Estado | Iniciar | Cancelar | Copiar/Salvar | Progresso |
| --- | --- | --- | --- | --- |
| Sem arquivo | Desabilitado | Desabilitado | Desabilitado | 0% |
| Arquivo válido | Habilitado | Desabilitado | Habilitado somente se houver resultado concluído | 0% |
| Preparando modelo | Desabilitado | Habilitado | Desabilitado | Indeterminado |
| Transcrevendo | Desabilitado | Habilitado | Desabilitado | 20–95% |
| Cancelando | Desabilitado | Desabilitado | Desabilitado | Etapa atual |
| Concluído | Habilitado | Desabilitado | Habilitado | 100% |
| Falha/cancelado | Habilitado se houver arquivo | Desabilitado | Desabilitado | 0% |

## 7. Mensagens e acessibilidade

- todo texto operacional é pt-BR;
- mensagens devem dizer ação, estado e próximo passo;
- erro técnico conhecido recebe tradução amigável;
- não depender somente de cor: estado também aparece em texto e habilitação do controle;
- foco e navegação de teclado seguem o comportamento nativo Qt;
- fechamento durante trabalho ativo solicita confirmação e prioriza cancelamento seguro.

## 8. Ícone

Marca original com documento e onda sonora, sem texto, usando índigo `#6366F1`, esmeralda
`#10B981` e transparência. `assets/icon.png` tem 256×256; `assets/icon.ico` contém 16, 32, 48 e
256 px.

## 9. Gravação e revisão v0.3.0

- O cartão superior reúne microfone, formato, `Gravar`, `Pausar/Retomar`, `Parar`, cronômetro e
  nível. Vermelho é reservado à captura ativa/ação de parada; roxo continua sendo a ação principal
  da transcrição.
- O medidor vai de 0 a 100% e não promete volume calibrado. A interface traduz `<5%` em sinal baixo
  e `>=98%` em possível clipping.
- Controles incompatíveis ficam desabilitados por estado, sem desaparecer ou mudar de posição.
- `Pausar` muda para `Retomar`; o cronômetro representa somente amostras gravadas.
- **Ativando o microfone** separa a abertura física do estado **Gravando**, evitando que a pessoa
  fale antes de o primeiro bloco estar realmente disponível.
- **Modelo de transcrição**, contexto, prioridade e revisão seletiva valem igualmente para arquivo
  importado e gravação; cada modelo e prioridade oferecem uma explicação ao passar o mouse.
- **Maior fidelidade** marca e bloqueia a revisão seletiva enquanto estiver ativa, tornando o custo
  adicional explícito; **Equilibrada** permanece padrão e **Velocidade** prioriza menor latência.
- Parar nunca inicia o modelo. **Salvar áudio como...** e **Iniciar transcrição** são decisões
  separadas, preservando responsividade e previsibilidade.
- Links `audio://seek/<segundos>` da visualização posicionam o player sem abrir URL externa.
- O monitor permanece visível durante e depois da transcrição: tempo, CPU/RAM do aplicativo e,
  quando o backend é NVIDIA, GPU total e VRAM informadas pelo driver.
- O conteúdo rola verticalmente, ocupa a largura disponível até 1480 px e evita campos esticados
  em telas ultrawide. A janela mínima é 820 x 640; o tamanho inicial é 1240 x 860.
- Tipografia usa 11 pt como base, 10 pt apenas para texto secundário e 18 pt no título, respeitando
  escala High-DPI do Qt.
- O resultado fica em um `QSplitter` vertical. A alça redimensiona o painel e **Expandir
  resultado** oculta apenas a área superior; **Restaurar** ou `Esc` recuperam o divisor anterior.
- Texto, aba, rolagem, edição e reprodução não são reconstruídos durante a expansão.
- As larguras obrigatórias de validação são 820, 900, 1240 e 1536 px, sem rolagem horizontal.
- O catálogo começa por **Offline** ou **Requer download**. Cada item informa parâmetros, VRAM,
  velocidade, fidelidade, tamanho e disponibilidade; o botão de download aparece só quando útil.
- `large-v3` permanece a primeira escolha de máxima fidelidade, mas seu rótulo informa **Requer
  download**; `medium` e `turbo` continuam utilizáveis sem rede desde a instalação.
