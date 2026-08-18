# Especificação de Arquitetura Técnica

## 1. Visão geral

A aplicação é um monólito desktop standalone. A GUI PySide6 ocupa a thread principal; um
`TranscriberWorker(QThread)` executa FFmpeg, carregamento do modelo e inferência. A comunicação usa
somente sinais/slots Qt.

```text
MainWindow
  ├─ DropZone / editor / prévia
  └─ sinais e slots
       ↓
TranscriberWorker (QThread)
  ├─ FFmpegFinder
  ├─ whisper.load_audio
  ├─ whisper.load_model("turbo")
  └─ MarkdownExporter
```

## 2. Módulos

- `main.py`: bootstrap Qt e `--self-check`.
- `app/core/ffmpeg_finder.py`: resolução, download, SHA-256, extração e PATH.
- `app/core/transcriber.py`: tipos de resultado, progresso, CUDA/CPU e sinais Qt.
- `app/core/exporter.py`: Markdown e escrita UTF-8 atômica.
- `app/ui/main_window.py`: seleção, execução, editor, prévia, cópia e salvamento.
- `app/ui/styles.py`: tokens e folha QSS.
- `build.py`: FFmpeg + PyInstaller no interpretador atual.

## 3. Contratos

`TranscriberWorker` expõe:

- `status_changed(str)`;
- `progress_changed(int)`, usando `-1` para estado indeterminado;
- `segment_decoded(str)`;
- `completed(TranscriptionResult)`;
- `failed(str)`.

`TranscriptionResult` contém nome de origem, duração, texto, segmentos, modelo, idioma, dispositivo
e data com fuso. `MarkdownExporter.render()` é puro e `save()` usa arquivo temporário no mesmo
volume seguido de substituição atômica.

## 4. FFmpeg

Ordem de resolução:

1. `sys._MEIPASS/assets/ffmpeg/<os>/`;
2. `assets/ffmpeg/<os>/` no checkout;
3. `ffmpeg` no `PATH`;
4. cache local verificado;
5. download HTTPS da release mensal fixada, com SHA-256 antes da extração.

Somente o membro `bin/ffmpeg(.exe)` é lido do arquivo; não há `extractall` nem `shell=True`.

## 5. Transcrição e fallback

O áudio é decodificado uma vez com `whisper.load_audio`. A duração deriva da quantidade de amostras.
O modelo usa FP16 em CUDA e FP32 em CPU. A saída incremental do Whisper fornece trechos e timestamps
para o progresso. Em erro de memória CUDA, o cache é liberado e a operação reinicia em CPU.

## 6. Empacotamento

O PyInstaller recebe `--onefile`, `--windowed`, `--add-binary`, `--collect-all whisper` e
`--collect-all torch`. O build deve ser executado separadamente em Windows e Linux; não existe
cross-compilation. As tags `v*` acionam a matriz de release CPU.
