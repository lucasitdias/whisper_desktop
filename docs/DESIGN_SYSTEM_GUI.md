# Design System da Interface Qt/QSS

## 1. Objetivos

O design da versão v0.2.1 prioriza leitura prolongada, estados inequívocos e operação segura
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
- estado indeterminado durante resolução/download/carregamento;
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
