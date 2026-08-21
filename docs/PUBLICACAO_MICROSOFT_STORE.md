# Publicação na Microsoft Store

## 1. Objetivo do canal

A Microsoft Store é o canal recomendado para Windows quando a máquina exige aplicativo assinado.
O projeto gera um MSIX destinado ao Partner Center; esse MSIX local não deve ser oferecido como
instalador direto. A Microsoft valida e assina o pacote aceito antes de distribuí-lo.

- Produto: **Whisper Transcriber Desktop**
- Store ID: `9PHWS6MM59BG`
- Página: <https://apps.microsoft.com/detail/9PHWS6MM59BG>
- Downloads alternativos: <https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.2.1>

A existência do link não substitui a confirmação no Partner Center. Aquisição, disponibilidade
regional e instalação pela Store devem ser validadas depois que a submissão estiver publicada.

## 2. Identidade reservada

| Campo | Valor |
| --- | --- |
| Nome na Store | `Whisper Transcriber Desktop` |
| Package/Identity/Name | `WhisperTranscriber.WhisperTranscriberDesktop` |
| Package/Identity/Publisher | `CN=B12A9AED-D3CC-463A-B3E5-ED71178CABF3` |
| Package Family Name | `WhisperTranscriber.WhisperTranscriberDesktop_vqjnmqct8h0by` |
| Arquitetura | `x64` |
| Família de dispositivo | `Windows.Desktop` |

Esses valores pertencem ao produto reservado. Alterá-los quebra a associação do pacote com o
aplicativo no Partner Center.

## 3. Conteúdo e capacidades

O MSIX contém:

- executável PyInstaller `--onedir`;
- PySide6;
- OpenAI Whisper;
- PyTorch CUDA 13 e fallback CPU;
- FFmpeg estático validado;
- ícones exigidos pelo manifesto.

O modelo `turbo` não é incorporado. Ele é baixado no primeiro uso e mantido no cache local da
aplicação.

O manifesto declara `runFullTrust` porque é um aplicativo desktop Win32 empacotado. Justificativa:

> Aplicativo desktop local em Python/PySide6. A capacidade é necessária para o usuário selecionar
> e ler arquivos MP3/M4A, executar o FFmpeg empacotado e realizar inferência local com
> Whisper/PyTorch, inclusive CUDA quando disponível. O aplicativo não solicita elevação, não
> instala serviços e não envia o áudio para servidores.

## 4. Gerar o pacote

Requisitos: Windows x64, ambiente CUDA sincronizado e Windows SDK/MakeAppx.

```powershell
uv sync --frozen
uv run ruff check .
uv run python -m pytest
uv run main.py --self-check
uv run python build.py --msix
```

Para reempacotar `dist/WhisperTranscriber` existente:

```powershell
uv run python build.py --msix-only
```

Saída:

```text
dist/store/WhisperTranscriber-Desktop-0.2.1-Windows-x64.msix
```

## 5. Versionamento

- versão pública do aplicativo: `0.2.1`;
- versão técnica do MSIX atual: `1.2.4.0`.

A versão técnica é um contador monotônico independente da tag pública. Ela foi avançada para
substituir pacotes de rascunho anteriores e não representa uma release `0.2.4`.

Evidência do candidato enviado:

- tamanho: 2.149.611.092 bytes;
- SHA-256: `199DF03410371E8C22D74B75EA49AC9278D59B2504AC63FCBBF3ADCD64ADB3F9`;
- identidade, versão, arquitetura, manifesto e executável verificados por `build.py`;
- 15 testes estáticos aplicáveis do Windows App Certification Kit com resultado `Pass`.

A certificação definitiva pertence ao Partner Center, mesmo quando o WACK local é aprovado.

## 6. Checklist antes do envio

- [ ] `main` limpa e sincronizada;
- [ ] versão pública e técnica revisadas;
- [ ] 55 testes e lint aprovados;
- [ ] FFmpeg e runtime CUDA presentes no autodiagnóstico;
- [ ] identidade do manifesto igual à reservada;
- [ ] arquitetura restrita a Windows Desktop x64;
- [ ] assets visuais e descrições preenchidos;
- [ ] política de privacidade e informações de teste preenchidas;
- [ ] pacote anterior incorreto removido do rascunho;
- [ ] MSIX final salvo e submetido;
- [ ] Partner Center sem erro de validação;
- [ ] página pública permitindo aquisição;
- [ ] instalação pela Store testada em Windows compatível;
- [ ] primeira transcrição e download do modelo testados.

## 7. Relação com os downloads GitHub

A release v0.2.1 oferece instaladores offline NVIDIA CUDA/CPU, portáteis e Linux. Eles foram
instalados e autoverificados em CI, mas os executáveis Windows diretos não têm Authenticode.

Em computadores com Smart App Control:

- não desative a proteção;
- prefira a versão assinada distribuída pela Microsoft Store;
- trate `WinError 4551` como bloqueio de política, não como falha do motor de transcrição.

O arquivo `Instalar-WhisperTranscriber-Windows.url` da release apenas abre a página do produto; não
contorna certificação, disponibilidade regional ou políticas da Microsoft.

## 8. Pós-publicação

Depois da aprovação:

1. abrir a página sem sessão administrativa;
2. confirmar nome, ícones, versão e disponibilidade regional;
3. instalar pela Store em Windows x64;
4. executar `WhisperTranscriber.exe --self-check-output self-check.json` quando aplicável;
5. abrir a GUI e conferir o dispositivo;
6. transcrever MP3 e M4A autorizados;
7. validar atualização/desinstalação pelo canal Store;
8. registrar a evidência em `VALIDACAO_QUALIDADE_SEGURANCA.md`.
