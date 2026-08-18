\# Implementação completa do Whisper Transcriber Desktop



\## Resumo



\- Criar a aplicação desktop em Python 3.11 com PySide6, OpenAI Whisper `turbo`, idioma fixo `pt` e processamento assíncrono por `QThread`.

\- Preservar os documentos em `docs`, corrigir a marcação Markdown quebrada e atualizar as especificações para refletir as decisões aprovadas.

\- Gerenciar dependências com `pyproject.toml`, `.python-version` e `uv.lock`. Usar `openai-whisper==20250625` e PyTorch `2.12.1` com CUDA 13.0 no ambiente de desenvolvimento, compatível com a RTX 5070. O Whisper oficialmente expõe o modelo `turbo`, seus segmentos e timestamps, e exige FFmpeg. \[Whisper oficial](httpsgithub.comopenaiwhisper), \[PyTorch 2.12.1](httpspytorch.orgget-startedprevious-versions), \[uv](httpsdocs.astral.shuvguidesprojects).

\- Criar o repositório privado `lucasitdiaswhisper\_desktop`, com commit e mensagens em português do Brasil. A publicação dependerá de reautenticar o GitHub CLI com `gh auth login`.



\## Arquitetura e interfaces



\- Manter a estrutura prescrita em `appcore`, `appui` e `assets`, acrescentando apenas `tests`, `.githubworkflows`, avisos de terceiros e arquivos de configuração.

\- `main.py`

&#x20; - Inicializar `QApplication`, High-DPI, ícones e tema escuro.

&#x20; - Expor `--self-check` para validar imports, FFmpeg e dispositivo sem abrir a janela nem baixar o modelo.

\- `FFmpegFinder`

&#x20; - Resolver, nesta ordem recurso PyInstaller em `sys.\_MEIPASS`, `assetsffmpegos`, FFmpeg do `PATH` e cache local verificado.

&#x20; - Suportar Windows e Linux x86\_64, validar o executável com `ffmpeg -version` e nunca usar `shell=True`.

&#x20; - Baixar uma compilação estática LGPL da ramificação FFmpeg 8.1, em release imutável da BtbN, validando SHA-256 antes da extração. A linha 8.1 é a estável atual. \[FFmpeg 8.1](httpswww.ffmpeg.orgdownload.html), \[BtbN FFmpeg Builds](httpsgithub.comBtbNFFmpeg-Builds).

\- `TranscriberWorker(QThread)`

&#x20; - Sinais públicos `status\_changed(str)`, `progress\_changed(int)`, `segment\_decoded(str)`, `completed(object)` e `failed(str)`.

&#x20; - Detectar `torch.cuda.is\_available()`, usar CUDA com FP16 ou CPU com FP32.

&#x20; - Decodificar o áudio uma única vez com `whisper.load\_audio`, calcular sua duração e executar `model.transcribe(..., language=pt, task=transcribe)`.

&#x20; - Emitir segmentos e percentual real conforme os timestamps decodificados; usar progresso indeterminado durante downloadcarregamento do modelo.

&#x20; - Em falta de VRAM, liberar o cache CUDA, informar o usuário e reiniciar automaticamente a transcrição em CPU.

&#x20; - Retornar `TranscriptionResult` com texto, segmentos, duração, modelo, idioma, dispositivo, arquivo de origem e data.

\- `MarkdownExporter`

&#x20; - `render(result) - str` para geração pura e testável.

&#x20; - `save(markdown, path)` com UTF-8, escrita atômica e confirmação de sobrescrita na camada de interface.

&#x20; - Gerar metadados, texto integral e timestamps `HHMMSS`, sem registrar caminhos absolutos no documento.



\## Interface e experiência



\- Criar zona de drag-and-drop e seletor aceitando somente um `.mp3` ou `.m4a`, sem distinção de maiúsculas.

\- Aplicar integralmente a paleta, tipografia, estados, botões, barra de progresso e scrollbars do design system.

\- Exibir seleção do arquivo, dispositivo detectado, barra de progresso e log de status em pt-BR.

\- Manter o botão de transcrição desabilitado sem arquivo ou durante processamento; impedir fechamento inseguro enquanto a thread estiver trabalhando.

\- Apresentar o resultado em abas

&#x20; - “Markdown” fonte editável.

&#x20; - “Visualização” renderização sincronizada do conteúdo editado.

\- Disponibilizar “Copiar Markdown” e “Salvar como”; sugerir `nome-do-audio\_transcricao.md`, acrescentar `.md` quando necessário e nunca salvar automaticamente.

\- Gerar ícones originais PNGICO com documento e onda sonora, usando índigo e esmeralda, incluindo os tamanhos exigidos pelo Windows.



\## Build, documentação e entrega



\- `build.py` deverá

&#x20; - Baixar e verificar o FFmpeg da plataforma.

&#x20; - Chamar PyInstaller pelo mesmo interpretador em execução.

&#x20; - Usar `--onefile`, `--windowed`, ícone da plataforma, `--add-binary`, `--collect-all whisper` e `--collect-all torch`.

&#x20; - Gerar `distWhisperTranscriber.exe` no Windows e `distWhisperTranscriber` no Linux. O modo one-file extrai os recursos para a pasta temporária `\_MEI`, conforme o comportamento oficial do PyInstaller. \[Documentação PyInstaller](httpspyinstaller.orgenstableusage.html).

\- O ambiente local padrão será CUDA e continuará funcionando em CPU quando CUDA não estiver disponível. `torchvision` e `torchaudio` serão omitidos porque não são usados pelo Whisper.

\- Os executáveis publicados pelo CI usarão PyTorch CPU em ambiente isolado e reproduzível, evitando artefatos CUDA de vários gigabytes.

\- Ignorar `.venv`, modelos, áudios, binários FFmpeg baixados, `build`, `dist`, caches e arquivos gerados; versionar `uv.lock`.

\- Atualizar os documentos em `docs` com comandos executáveis, localização real, CUDA atual, fluxo de FFmpeg, builds CPU e critérios de aceite. Preencher `VALIDACAO\_QUALIDADE\_SEGURANCA.md`.

\- Criar

&#x20; - CI em pushes e pull requests com lint, testes e `--self-check` em Windows e Linux.

&#x20; - Release em tags `v`, construindo artefatos CPU WindowsLinux e publicando-os no GitHub Releases.

\- Inicializar `main`, revisar o diff e segredos, executar `git diff --check`, fazer commit em português, criar o repositório privado, push inicial e acompanhar o GitHub Actions até conclusão. Vercel não será usado por não haver implantação web.



\## Testes e critérios de aceite



\- Testes unitários para resolução do FFmpeg, verificação de checksum, extração segura, fallback para PATHcache e plataformas não suportadas.

\- Testes do exportador para Unicode, metadados, duração, timestamps superiores a uma hora, segmentos vazios e escrita atômica.

\- Testes do worker com WhisperTorch simulados CUDA, CPU, falta de VRAM, progresso, segmentos, falhas de download e sinais Qt.

\- Testes `pytest-qt` para seleção, drag-and-drop, estados dos botões, execução não bloqueante, abas, edição, cópia, salvamento e mensagens em pt-BR.

\- CI não baixará o modelo `turbo`; a inferência real será uma aceitação local opt-in com áudio fornecido pelo usuário.

\- Aceite manual final

&#x20; - `uv run main.py` abre corretamente em tema escuro.

&#x20; - MP3 e M4A são transcritos sem congelar a GUI.

&#x20; - A RTX 5070 é identificada como CUDA e o fallback CPU funciona.

&#x20; - O Markdown pode ser editado, visualizado, copiado e salvo.

&#x20; - Os executáveis CPU iniciam e passam em `--self-check` no Windows e Linux.

\- Premissas alvo restrito a WindowsLinux x86\_64; modelo não será incorporado ao executável; documentos permanecerão em `docs`; nenhuma tag inicial será criada automaticamente; o repositório privado permanecerá sem licença própria até decisão posterior, mas incluirá os avisos exigidos pelas dependências.
