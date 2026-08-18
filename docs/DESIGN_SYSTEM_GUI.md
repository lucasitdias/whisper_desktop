# Design System da Interface Qt/QSS

## Princípios

- foco no conteúdo e poucos elementos decorativos;
- feedback visível para hover, clique, drag-over, carregamento, sucesso e erro;
- alto contraste adequado para leitura prolongada;
- fontes nativas e layout compatível com High-DPI.

## Tokens

| Papel | Cor |
| --- | --- |
| Fundo | `#121214` |
| Painel | `#1E1E24` |
| Entrada | `#18181C` |
| Borda | `#2C2C35` |
| Primária | `#6366F1` |
| Hover | `#4F46E5` |
| Pressionada | `#4338CA` |
| Sucesso/progresso | `#10B981` |
| Texto principal | `#F3F4F6` |
| Texto secundário | `#9CA3AF` |
| Desabilitado | `#4B5563` |
| Erro | `#EF4444` |

## Tipografia

- interface: Segoe UI, Inter ou sans-serif do sistema;
- logs: Consolas, Fira Code ou monospace;
- título: 20 px / 700;
- seção: 15 px / 600;
- corpo: 13 px;
- metadados: 11 px;
- logs: 12 px.

## Componentes

- Drop zone: painel `#1E1E24`, borda tracejada de 2 px e raio de 8 px; drag-over usa
  `#252533` e borda `#6366F1`.
- Botão primário: fundo índigo, texto branco, raio 6 px e padding 10/20 px.
- Botões secundários: fundo transparente, borda `#374151` e hover `#2C2C35`.
- Barra de progresso: trilho `#18181C`, preenchimento índigo e estado indeterminado no download.
- Editor/prévia: fundo `#18181C`, texto `#F3F4F6`, borda `#2C2C35` e raio 6 px.
- Scrollbar: largura 8 px, handle `#2C2C35`, hover `#4B5563`.

O QSS canônico está em `app/ui/styles.py`.

## Ícone

Marca original combinando documento e onda sonora, sem texto, com índigo `#6366F1`, esmeralda
`#10B981` e fundo transparente. `icon.png` tem 256×256; `icon.ico` contém 16, 32, 48 e 256 px.
