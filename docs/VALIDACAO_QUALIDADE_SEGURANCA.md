# Validação de Qualidade e Segurança

## 1. Portões automatizados

Todo push e pull request deve passar em Windows e Linux:

1. instalação do perfil CPU em Python 3.11;
2. `ruff check .`;
3. `pytest` com Qt offscreen;
4. download/verificação do FFmpeg;
5. `main.py --self-check`.

Tags `v*` adicionam build PyInstaller, autoverificação do executável e publicação no GitHub
Releases.

### Evidências locais em 18/08/2026

- Windows 11 x64, Python 3.11.16 e `ruff check .`: aprovado;
- `pytest`: 25 testes aprovados;
- `uv run --no-sync python main.py --self-check`: aprovado;
- dispositivo detectado: `GPU CUDA: NVIDIA GeForce RTX 5070 Laptop GPU`;
- FFmpeg estático 8.1.2 baixado, SHA-256 verificado e executável validado;
- regressão de build `--windowed`: `stdout`/`stderr` ausentes são substituídos por fluxos graváveis,
  eliminando a falha `'NoneType' object has no attribute 'write'` durante o download do modelo;
- transcrição real de uma amostra de 60 segundos do MP3 do usuário: aprovada em CUDA, com 20
  segmentos e Markdown de 829 caracteres;
- build CUDA `--onedir`: 12.119 arquivos e 3.326.602.046 bytes;
- instalador Windows x64: `WhisperTranscriber-Setup-Windows-x64.exe`, 1.798.005.492 bytes;
- SHA-256 do instalador: `049603309072035341EAB7D597294B6296021A4A79A1244FE0A01FB30F8C7C02`;
- instalação silenciosa por usuário: aprovada com código de saída 0, executável e desinstalador;
- aplicativo instalado `--self-check-output`: aprovado com FFmpeg incorporado e RTX 5070 em CUDA;
- o executável local não assinado foi bloqueado pelo Smart App Control, mas o instalador e o
  aplicativo instalado foram aceitos. O artefato permanece sem Authenticode por falta de
  certificado de publicação.
- GitHub Actions `Qualidade` (execução `32103343863`): aprovado em Windows e Linux.

## 2. Cobertura comportamental

- resolução e precedência do FFmpeg;
- checksum inválido e extração sem path traversal;
- exportação Unicode, timestamps, vazio e escrita atômica;
- worker CPU, CUDA, falta de VRAM, sinais e erros;
- seleção MP3/M4A, thread não bloqueante, editor, prévia, cópia e salvamento.

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
- abrir os executáveis Windows/Linux e executar `--self-check`;
- transcrever um M4A real, pois a regressão local desta versão usou MP3.

O modelo real não é baixado no CI. Essa aceitação permanece opt-in para evitar custo, tráfego e uso
de áudio não autorizado.
