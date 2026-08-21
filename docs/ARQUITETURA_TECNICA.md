# Especificação de Arquitetura Técnica

## 1. Escopo e versão

Esta especificação descreve a implementação entregue na versão **v0.2.1** do Whisper Transcriber
Desktop. O produto é um monólito desktop local para Windows 10/11 x64 e Debian/Ubuntu x86-64.

A thread principal pertence ao Qt. Download, decodificação, carregamento do modelo e inferência
ocorrem em `TranscriberWorker(QThread)`, com comunicação exclusivamente por sinais e slots.

```text
QApplication / MainWindow
  ├── DropZone e seleção de arquivo
  ├── estado dos botões, progresso e log
  ├── editor Markdown e visualização
  └── ações de copiar e salvar
          │ sinais/slots Qt
          ▼
TranscriberWorker (QThread)
  ├── FFmpegFinder
  ├── whisper.load_audio
  ├── whisper.load_model("turbo")
  ├── model.transcribe
  └── TranscriptionResult
          │
          ▼
MarkdownExporter
```

## 2. Estrutura de módulos

```text
whisper_desktop/
├── app/
│   ├── core/
│   │   ├── exporter.py
│   │   ├── ffmpeg_finder.py
│   │   └── transcriber.py
│   └── ui/
│       ├── components.py
│       ├── main_window.py
│       └── styles.py
├── assets/
│   └── ffmpeg/<windows|linux>/
├── installer/WhisperTranscriber.iss
├── packaging/linux/
├── store/
├── tests/
├── build.py
└── main.py
```

Responsabilidades:

- `main.py`: normaliza `stdout`/`stderr` em builds `--windowed`, executa o autodiagnóstico e inicia
  a GUI.
- `app/core/ffmpeg_finder.py`: resolve, valida, baixa e disponibiliza o FFmpeg.
- `app/core/transcriber.py`: detecta o backend, executa o Whisper, calcula métricas e controla o
  cancelamento.
- `app/core/exporter.py`: renderiza o Markdown e faz escrita UTF-8 atômica.
- `app/ui/components.py`: zona de drag-and-drop e componentes reutilizáveis.
- `app/ui/main_window.py`: orquestra seleção, worker, estados, editor, prévia, cópia e salvamento.
- `app/ui/styles.py`: folha QSS canônica do tema escuro.
- `build.py`: PyInstaller, preparação do FFmpeg, autoverificação, Inno Setup e MSIX.
- `.github/workflows/ci.yml`: lint, testes, FFmpeg e autodiagnóstico em Windows/Linux.
- `.github/workflows/release.yml`: builds NVIDIA CUDA/CPU, instalação real, checksums e release.

## 3. Contratos públicos

### 3.1 `TranscriberWorker`

Sinais:

- `status_changed(str)`;
- `progress_changed(int)`, com `-1` para progresso indeterminado;
- `segment_decoded(str)`;
- `completed(object)`, contendo `TranscriptionResult`;
- `failed(str)`;
- `cancelled(str)`.

Métodos relevantes:

- `cancel()`: solicita interrupção cooperativa;
- `detect_device()`: retorna `cuda`, `rocm`, `xpu` ou `cpu`;
- `device_description()`: apresenta backend e nome real do dispositivo;
- `runtime_description()`: identifica o runtime PyTorch incorporado;
- `model_cache_root()`: separa o cache do modelo por aplicação.

### 3.2 Tipos de resultado

`TranscriptionResult` é imutável e contém:

- nome do arquivo de origem, sem caminho absoluto;
- duração total e duração processada;
- texto integral e segmentos;
- modelo, idioma, dispositivo e data com fuso;
- confiança média, quantidade de palavras e palavras abaixo de 50%.

Propriedades calculadas expõem cobertura, fim da última fala e total de palavras de baixa
confiança.

### 3.3 `MarkdownExporter`

- `render(result) -> str`: função pura e testável;
- `save(markdown, path)`: grava em arquivo temporário no mesmo volume, faz `fsync` e substituição
  atômica;
- caminhos absolutos nunca são incluídos no documento.

## 4. Fluxo da transcrição

1. A GUI valida extensão e existência do arquivo.
2. O worker resolve o FFmpeg e o adiciona ao início do `PATH` do processo.
3. `whisper.load_audio()` decodifica o áudio uma única vez em memória.
4. A duração é calculada por amostras divididas por `whisper.audio.SAMPLE_RATE`.
5. O backend é detectado na ordem CUDA/ROCm, XPU e CPU.
6. `whisper.load_model("turbo")` usa o cache próprio do aplicativo.
7. `model.transcribe()` recebe `language="pt"`, `task="transcribe"`, `beam_size=5`, `best_of=5`,
   `condition_on_previous_text=True` e `word_timestamps=True`.
8. A saída incremental é convertida em trechos e progresso por timestamp.
9. Segmentos e probabilidades por palavra são normalizados em tipos imutáveis.
10. A GUI recebe o resultado completo e renderiza o Markdown.

GPU usa FP16. CPU usa FP32. Em erro de memória do acelerador, o cache correspondente é liberado,
o coletor é executado e a transcrição reinicia automaticamente em CPU.

## 5. Cancelamento e ciclo de vida

O cancelamento combina `threading.Event` e `QThread.requestInterruption()`. Pontos seguros existem
antes/depois de validação, FFmpeg, decodificação, carregamento, inferência e emissão do resultado.
Durante a inferência, `_WhisperOutputStream.write()` verifica a solicitação a cada saída incremental.

Não são usados `QThread.terminate()` nem resultados parciais. A interface:

- desabilita nova transcrição enquanto o worker está ativo;
- habilita somente o botão de cancelamento;
- impede fechamento inseguro da janela;
- restaura os controles após conclusão, falha ou cancelamento.

## 6. Resolução segura do FFmpeg

Ordem efetiva:

1. `sys._MEIPASS/assets/ffmpeg/<os>/` em PyInstaller;
2. `assets/ffmpeg/<os>/` no checkout;
3. executável encontrado no `PATH`;
4. cache local previamente validado;
5. download HTTPS do artefato fixado.

A versão fixada é `8.1.2-34-g9b6c8969e0`, release BtbN
`autobuild-2026-07-31-14-10`, variante LGPL. O SHA-256 é verificado antes da extração. Somente o
membro esperado `bin/ffmpeg(.exe)` é extraído; não há `extractall` nem `shell=True`. O binário é
validado executando `ffmpeg -version` com timeout.

## 7. Backends de processamento

PyTorch distribui CPU, CUDA, ROCm e XPU em wheels distintas. O detector só escolhe um backend
quando a API correspondente está disponível e funcional.

- CUDA: GPU NVIDIA, API `torch.cuda`.
- ROCm: GPU AMD no Linux, identificada por `torch.version.hip`; o nome de dispositivo continua
  `cuda` por compatibilidade PyTorch.
- XPU: GPU Intel, API `torch.xpu`.
- CPU: fallback universal.

Os anexos v0.2.1 incluem um runtime NVIDIA CUDA 13 e runtimes CPU. O código suporta ROCm/XPU, mas
esses runtimes não estão incorporados nos instaladores publicados.

## 8. Interface e exportação

A `MainWindow` mantém uma única fonte Markdown editável. A visualização é derivada dessa fonte,
evitando divergência entre conteúdo copiado, salvo e exibido. A confirmação de sobrescrita pertence
à camada de interface; persistência e formatação permanecem no núcleo.

O arquivo sugerido segue `<nome-do-audio>_transcricao.md`. A exportação inclui:

- data, arquivo, duração, modelo, idioma e processamento;
- cobertura, duração processada, última fala e confiança;
- texto integral;
- lista de segmentos com timestamps `HH:MM:SS`;
- lista opcional de palavras com confiança inferior a 50%.

## 9. Empacotamento e distribuição

O PyInstaller recebe `--windowed`, ícone próprio, FFmpeg via `--add-binary` e coleta completa de
`whisper` e `torch`.

| Artefato | Modo | Runtime |
| --- | --- | --- |
| Windows NVIDIA | `--onedir` dentro do Inno Setup | PyTorch CUDA 13 |
| Windows CPU instalável | `--onedir` dentro do Inno Setup | PyTorch CPU |
| Windows portátil | `--onefile` | PyTorch CPU |
| Linux portátil | `--onefile` | PyTorch CPU |
| Linux DEB | portátil instalado em `/opt` | PyTorch CPU |
| Microsoft Store | `--onedir` dentro de MSIX | PyTorch CUDA 13 |

Não há cross-compilation: cada pacote é construído no sistema operacional alvo. O MSIX local é
destinado ao Partner Center. A assinatura confiável do canal Store é aplicada pela Microsoft após
certificação. Os instaladores Inno Setup da release não possuem Authenticode e podem ser bloqueados
por Smart App Control.

## 10. Autodiagnóstico

`main.py --self-check` valida imports, FFmpeg, dispositivo e runtime sem abrir a janela ou baixar o
modelo. `--self-check-output <arquivo>` grava o mesmo resultado em JSON e é usado em executáveis
`--windowed`, instaladores e CI.

## 11. Portões de qualidade

- Ruff;
- 55 testes `pytest`/`pytest-qt`;
- `git diff --check`;
- autodiagnóstico Windows/Linux;
- instalação, execução e desinstalação reais dos instaladores Windows;
- instalação, execução e remoção reais do DEB;
- SHA-256 publicado e validado novamente após a release.
