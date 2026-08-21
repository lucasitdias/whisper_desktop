# Publicação na Microsoft Store

Este projeto distribui a versão Windows pela Microsoft Store. Esse é o canal
recomendado porque a Microsoft valida e assina o pacote MSIX durante a
certificação. O arquivo MSIX gerado localmente é destinado ao Partner Center e
não deve ser oferecido como instalador direto ao usuário final.

- Página pública: <https://apps.microsoft.com/detail/9PHWS6MM59BG>
- Releases e Linux: <https://github.com/lucasitdias/whisper_desktop/releases/latest>

## Identidade do produto

- Nome na Store: `Whisper Transcriber Desktop`
- Store ID: `9PHWS6MM59BG`
- Package/Identity/Name: `WhisperTranscriber.WhisperTranscriberDesktop`
- Package/Identity/Publisher: `CN=B12A9AED-D3CC-463A-B3E5-ED71178CABF3`
- Package Family Name: `WhisperTranscriber.WhisperTranscriberDesktop_vqjnmqct8h0by`

Esses valores pertencem ao produto reservado no Partner Center. Alterá-los no
manifesto impede a associação do pacote ao aplicativo.

## Gerar o pacote

No Windows x86-64, com o ambiente sincronizado:

```powershell
uv sync --frozen
uv run python build.py --msix
```

Para empacotar novamente uma pasta `dist/WhisperTranscriber` já criada:

```powershell
uv run python build.py --msix-only
```

O build gera `dist/store/WhisperTranscriber-Desktop-<versao>-Windows-x64.msix`.
O pacote é `x64`, usa a identidade reservada e contém o aplicativo PySide6,
Whisper, PyTorch/CUDA e FFmpeg. O modelo `turbo` não é incorporado; ele é
baixado no primeiro uso e mantido no cache local do Whisper.

## Validações antes do envio

```powershell
uv run ruff check .
uv run pytest
uv run main.py --self-check
git diff --check
```

`build.py` também reabre o MSIX e verifica identidade, versão, arquitetura,
manifesto e executável antes de concluir. A versão 0.2.2 gera
`WhisperTranscriber-Desktop-0.2.2-Windows-x64.msix`, com versão MSIX
`1.2.2.0`.

O pacote 0.2.2 possui 2.149.620.732 bytes e SHA-256
`47CAF48B7B39D4CC4152624E42E0270C08CE325C3FC3CF96D6424D36BE26C1BA`.

O Windows App Certification Kit executou os 15 testes estáticos aplicáveis com
resultado `Pass`. O agregador do WACK não encerrou sozinho após os testes; por
isso, a validação definitiva continua sendo a análise automática do Partner
Center.

## Capacidade restrita `runFullTrust`

O manifesto declara `runFullTrust` porque este é um aplicativo desktop Win32
empacotado. A justificativa usada no Partner Center deve explicar:

> Aplicativo desktop local em Python/PySide6. A capacidade é necessária para o
> usuário selecionar e ler arquivos MP3/M4A, executar o FFmpeg empacotado e
> realizar inferência local com Whisper/PyTorch, inclusive CUDA quando
> disponível. O aplicativo não solicita elevação, não instala serviços e não
> envia o áudio para servidores.

## Distribuição segura

- O MSIX local permanece sem certificado público e serve apenas para o envio à
  Store.
- Depois da certificação, a Microsoft assina e distribui o pacote pela página do
  produto.
- O GitHub Releases não deve publicar o executável Windows sem Authenticode.
  Em vez disso, publica um atalho para a Store. Builds Linux podem continuar
  sendo distribuídos diretamente com SHA-256.
- O áudio e a transcrição permanecem locais; apenas o modelo Whisper é baixado
  na primeira utilização.
