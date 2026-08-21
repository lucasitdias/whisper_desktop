# Whisper Transcriber Desktop

Aplicativo desktop local para transcrever arquivos `.mp3` e `.m4a` em português usando o
OpenAI Whisper `turbo`. A interface PySide6 permanece responsiva durante o processamento e gera
Markdown editável com metadados, texto integral e timestamps.

## Downloads

| Plataforma | Download | Observação |
| --- | --- | --- |
| Windows 10/11 x64 | [Instalar pela Microsoft Store](https://apps.microsoft.com/detail/9PHWS6MM59BG) | Canal recomendado: pacote MSIX validado e assinado pela Microsoft após a certificação. |
| Linux x86-64 | [Baixar a release mais recente](https://github.com/lucasitdias/whisper_desktop/releases/latest) | Use o arquivo `WhisperTranscriber-Linux-x64` e confira `SHA256SUMS.txt`. |
| Código-fonte | [Releases do projeto](https://github.com/lucasitdias/whisper_desktop/releases) | Cada release oferece arquivos `.zip` e `.tar.gz` gerados pelo GitHub. |

A release também inclui `Instalar-WhisperTranscriber-Windows.url`, que abre a página oficial do
produto na Microsoft Store. Enquanto a primeira certificação não for concluída, a página pode não
permitir a aquisição. O MSIX enviado ao Partner Center não é distribuído diretamente porque só a
Microsoft pode devolvê-lo com a assinatura confiável necessária para instalação segura.

## Recursos

- seleção de um MP3 ou M4A por diálogo ou arrastar e soltar;
- processamento em `QThread`, sem bloquear a interface;
- cancelamento cooperativo, sem encerrar a thread à força nem salvar resultado parcial;
- CUDA/FP16 quando disponível e fallback automático para CPU/FP32, inclusive por falta de VRAM;
- resolução e verificação automática do FFmpeg 8.1.2;
- progresso por timestamps e exibição incremental dos trechos decodificados;
- editor Markdown, visualização sincronizada, cópia e salvamento atômico;
- duração processada, cobertura, última fala e confiança estimada por palavra;
- mensagens em português do Brasil e tema escuro com suporte High-DPI.

## Como a integridade é indicada

Cobertura de 100% significa que o Whisper percorreu toda a duração do áudio decodificado. A tela e
o Markdown também apresentam a última fala detectada, a confiança média estimada e as palavras com
confiança inferior a 50%.

Esses indicadores comprovam o processamento integral, mas não garantem fidelidade palavra por
palavra. Ruído, vozes sobrepostas, sotaques, nomes próprios e gravações ruins podem gerar erros.
Conteúdo crítico deve ser revisado ouvindo o áudio nos timestamps indicados.

## Executar pelo código-fonte

Requisitos:

- Windows 10/11 x64 ou Linux x86-64;
- Python 3.11 e [`uv`](https://docs.astral.sh/uv/);
- conexão no primeiro uso para baixar o modelo `turbo`;
- aproximadamente 15 GB livres para ambiente, cache e builds.

```powershell
uv sync --frozen
uv run main.py
```

O ambiente de desenvolvimento usa PyTorch 2.12.1 com CUDA 13.0. Sem GPU ou driver compatível, a
aplicação continua funcionando em CPU. O áudio e a transcrição permanecem no computador.

Autoverificação sem abrir a interface nem baixar o modelo:

```powershell
uv run main.py --self-check
```

Em um aplicativo empacotado sem console:

```powershell
WhisperTranscriber.exe --self-check-output self-check.json
```

## Testes

```powershell
uv run ruff check .
uv run python -m pytest
git diff --check
```

O CI executa lint, testes e autoverificação em Windows e Linux sem baixar o modelo. A inferência
real é uma aceitação local opcional com áudio autorizado pelo usuário.

## Builds

Executável portátil da plataforma atual:

```powershell
uv run build.py
```

Pacote Windows para envio à Microsoft Store:

```powershell
uv run build.py --msix
```

Instalador Windows Inno Setup para testes internos:

```powershell
uv run build.py --installer
```

O instalador Inno Setup e o executável Windows produzidos localmente não possuem Authenticode e
podem ser bloqueados pelo Smart App Control. Eles não devem ser publicados como alternativa ao
pacote assinado da Store, e a proteção do Windows não deve ser desativada.

## Estrutura

```text
whisper_desktop/
├── .github/workflows/       # qualidade e release por tag
├── app/
│   ├── core/                # FFmpeg, Whisper e exportação
│   └── ui/                  # janela, componentes e tema QSS
├── assets/                  # ícones e FFmpeg por plataforma
├── docs/                    # especificações, validação e publicação
├── installer/               # instalador interno Inno Setup
├── requirements/            # perfil CPU usado no CI
├── store/                   # manifesto MSIX e atalho oficial da Store
├── tests/                   # suíte automatizada
├── build.py
├── main.py
├── pyproject.toml
└── uv.lock
```

## Documentação

- [Documento de requisitos](docs/PRD.md)
- [Arquitetura técnica](docs/ARQUITETURA_TECNICA.md)
- [Design system](docs/DESIGN_SYSTEM_GUI.md)
- [Preparação do ambiente](docs/MEMORANDO_PREPARACAO_AMBIENTE.md)
- [Validação de qualidade e segurança](docs/VALIDACAO_QUALIDADE_SEGURANCA.md)
- [Publicação na Microsoft Store](docs/PUBLICACAO_MICROSOFT_STORE.md)
- [Avisos de terceiros](docs/THIRD_PARTY_NOTICES.md)
