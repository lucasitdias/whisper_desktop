# Validação de Qualidade e Segurança

## 1. Portões automatizados

Todo push e pull request deve passar em Windows e Linux:

1. instalação do perfil CPU em Python 3.11;
2. `ruff check .`;
3. `pytest` com Qt offscreen;
4. download/verificação do FFmpeg;
5. `main.py --self-check`.

Tags `v*` adicionam builds CPU Linux e Windows, autoverificação, instalador offline Inno Setup,
checksums, atalho da Microsoft Store e publicação no GitHub Releases.

### Evidências locais entre 18 e 20/08/2026

- Windows 11 x64, Python 3.11.16 e `ruff check .`: aprovado;
- `pytest`: 36 testes aprovados;
- `uv run --no-sync python main.py --self-check`: aprovado;
- dispositivo detectado: `GPU CUDA: NVIDIA GeForce RTX 5070 Laptop GPU`;
- FFmpeg estático 8.1.2 baixado, SHA-256 verificado e executável validado;
- regressão de build `--windowed`: `stdout`/`stderr` ausentes são substituídos por fluxos graváveis,
  eliminando a falha `'NoneType' object has no attribute 'write'` durante o download do modelo;
- transcrição real de uma amostra de 60 segundos do MP3 do usuário: aprovada em CUDA, com 20
  segmentos e Markdown de 829 caracteres;
- versão 0.2.0 com timestamps por palavra: 60 de 60 segundos processados (100%), 151 palavras,
  confiança média estimada de 88,4%, 14 palavras abaixo de 50% e última fala em 00:59,780;
- cancelamento real durante o carregamento: aprovado sem resultado parcial nem sinal de falha;
- cancelamento real durante a inferência do MP3 longo: aprovado após 15 segmentos, com liberação
  cooperativa da thread e sem resultado parcial;
- build CUDA `--onedir`: 12.119 arquivos e 3.326.602.046 bytes;
- instalador Windows x64 0.2.0: `WhisperTranscriber-Setup-Windows-x64.exe`, 1.798.023.653
  bytes;
- SHA-256 do instalador 0.2.0:
  `09078D4B56A4831ACE5955651A137D2628C0662984949FE78E26C5C2A563D65E`;
- instalação silenciosa por usuário: aprovada com código de saída 0, executável e desinstalador;
- aplicativo instalado `--self-check-output`: aprovado com FFmpeg incorporado e RTX 5070 em CUDA;
- na versão 0.1.1, o executável local não assinado foi bloqueado pelo Smart App Control, mas o
  instalador e o aplicativo instalado foram aceitos. O artefato permanece sem Authenticode por
  falta de certificado de publicação;
- na versão 0.2.0, o Smart App Control bloqueou o novo hash local do instalador e do executável
  antes da inicialização. O código-fonte CUDA e a estrutura completa do pacote foram validados; o
  executável CPU empacotado é validado novamente pelo runner Windows da release. Distribuição sem
  aviso do Smart App Control exige certificado Authenticode público, não disponível neste projeto.
- GitHub Actions `Qualidade` da PR 2 (execução `32446586592`): aprovado em Windows e Linux;
- build final MSIX 0.2.1: 2.149.611.092 bytes, identidade `1.2.1.0` verificada e SHA-256
  `C9EF17B7F8D1C4B08608CC0B8BB7C9186E7BC3B3F841A658188222E71D53D0E3`;
- build final do instalador Windows 0.2.1: 1.798.030.728 bytes e SHA-256
  `60D7CFA1D0098DE0715D108087A00D2CA4CC1CEB15FC7152358910AC99C06655`;
- o Smart App Control local bloqueou o instalador final sem Authenticode antes da execução. Essa
  modalidade só é aprovada em CI limpo; para computadores com a política ativa, o aceite exige o
  MSIX assinado pela Microsoft Store.

## 2. Cobertura comportamental

- resolução e precedência do FFmpeg;
- checksum inválido e extração sem path traversal;
- exportação Unicode, timestamps, vazio e escrita atômica;
- worker CPU, CUDA, falta de VRAM, cancelamento cooperativo, sinais e erros;
- seleção MP3/M4A, thread não bloqueante, botão de cancelamento, estados, editor, prévia, cópia e
  salvamento;
- cobertura integral, confiança por palavra e marcadores de baixa confiança para revisão.

## 3. Controles de segurança

- nenhuma execução por shell ou interpolação de comandos;
- URLs fixas e SHA-256 fixado para binários externos;
- nenhuma extração geral de arquivos compactados;
- caminhos absolutos não entram no Markdown;
- áudio e texto permanecem locais;
- pesos, áudios, binários e ambientes são ignorados pelo Git;
- nenhuma sobrescrita pela GUI sem confirmação;
- dependências de desenvolvimento são travadas por `uv.lock`.

## 4. Aceitação manual

- abrir `uv run main.py` e verificar o tema, textos e High-DPI;
- transcrever um MP3 e um M4A reais fornecidos pelo usuário;
- confirmar que a GUI continua responsiva e mostra progresso/trechos;
- confirmar CUDA na RTX 5070 e executar o artefato CPU para validar fallback;
- editar a fonte, conferir a prévia, copiar e salvar sem sobrescrita silenciosa;
- instalar o Windows pela Microsoft Store após a certificação e executar `--self-check-output`;
- abrir o executável Linux da release e executar `--self-check`;
- instalar o pacote Windows offline da release em máquina sem política de bloqueio e confirmar o
  `--self-check-output`; em máquinas com Smart App Control, usar a versão assinada da Store;
- transcrever um M4A real, pois a regressão local desta versão usou MP3.

O modelo real não é baixado no CI. Essa aceitação permanece opt-in para evitar custo, tráfego e uso
de áudio não autorizado.
