# Publicação na Microsoft Store

> Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

## Atualização v0.3.0

O manifesto passa a declarar `<DeviceCapability Name="microphone" />` porque a aplicação só acessa
o microfone depois de o usuário clicar em **Gravar**. A certificação deve validar permissão negada,
ausência de dispositivo, gravação/pausa/parada e política de privacidade. O envio ao Partner Center
foi autorizado pelo responsável pelo produto em 23/08/2026.

### Estratégia de produtos aprovada

- **Whisper Transcriber Desktop (gratuito):** manter o produto atual e a versão instalada
  `1.2.4.0`, sem receber a v0.3.0.
- **Whisper Transcriber Desktop Pro (pago):** produto separado `9NJN8VV2N833`, configurado por
  **R$ 26,95**, com a implementação v0.3.0 aceita localmente em 24/08/2026.
- Ambos devem exibir **Lucas Dias** como desenvolvedor público.

O candidato local anterior usou a identidade gratuita exclusivamente para testar a atualização
nesta máquina e não pode ser enviado. O build atual usa a identidade oficial do produto Pro; essa
separação preserva a edição gratuita em `1.2.4.0`.

## 1. Objetivo do canal

A Microsoft Store é o canal recomendado para Windows quando a máquina exige aplicativo assinado.
O projeto gera um MSIX destinado ao Partner Center; esse MSIX local não deve ser oferecido como
instalador direto. A Microsoft valida e assina o pacote aceito antes de distribuí-lo.

- Produto gratuito: **Whisper Transcriber Desktop**
- Produto pago: **Whisper Transcriber Desktop Pro**
- Desenvolvedor público: **Lucas Dias**
- Store ID gratuito: `9PHWS6MM59BG`
- Store ID Pro: `9NJN8VV2N833`
- Página Pro: <https://apps.microsoft.com/detail/9NJN8VV2N833>
- Downloads da v0.3.0: <https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.3.0>

A existência do link não substitui a confirmação no Partner Center. Aquisição, disponibilidade
regional e instalação pela Store devem ser validadas depois que a submissão estiver publicada.

## 2. Identidade reservada da edição gratuita

| Campo | Valor |
| --- | --- |
| Nome na Store | `Whisper Transcriber Desktop` |
| Package/Identity/Name | `WhisperTranscriber.WhisperTranscriberDesktop` |
| Package/Identity/Publisher | `CN=B12A9AED-D3CC-463A-B3E5-ED71178CABF3` |
| Package Family Name | `WhisperTranscriber.WhisperTranscriberDesktop_vqjnmqct8h0by` |
| Arquitetura | `x64` |
| Família de dispositivo | `Windows.Desktop` |

Esses valores pertencem ao produto gratuito. Alterá-los quebra a associação do pacote com esse
aplicativo no Partner Center. A edição Pro precisa receber os valores da sua nova reserva antes do
build final; nenhum identificador deve ser inventado ou reutilizado.

## 2.1 Identidade reservada da edição Pro

| Campo | Valor |
| --- | --- |
| Nome na Store | `Whisper Transcriber Desktop Pro` |
| Store ID | `9NJN8VV2N833` |
| Package/Identity/Name | `WhisperTranscriberDesktop.WhisperTranscriberDeskto` |
| Package/Identity/Publisher | `CN=8D30778F-07F5-435C-A526-6B1646073081` |
| Package Family Name | `WhisperTranscriberDesktop.WhisperTranscriberDeskto_69ska0htfra0e` |
| PublisherDisplayName esperado | `Lucas Dias` |

O Partner Center ainda exibia o nome cadastral incorreto durante a preparação. O chamado Microsoft
`2608240040002130` solicita a correção para `Lucas Dias`; o pacote não deve ser submetido antes de
esse valor aparecer na identidade do produto.

## 3. Conteúdo e capacidades

O MSIX contém:

- executável PyInstaller `--onedir`;
- PySide6;
- OpenAI Whisper;
- PyTorch CUDA 13 e fallback CPU;
- FFmpeg estático validado;
- ícones exigidos pelo manifesto.

Os modelos `medium` e `turbo` são incorporados e funcionam sem rede. `tiny`, `base`, `small` e
`large-v3` são baixados somente após ação explícita, validados por SHA-256 e então usados localmente.
Áudios e transcrições nunca são enviados durante esse download.

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
dist/store/WhisperTranscriber-Desktop-0.3.0-Windows-x64.msix
```

## 5. Versionamento

- versão pública final do aplicativo: `0.3.0`;
- versão técnica do MSIX local de aceite: `1.3.4.0`;
- versão técnica instalada anteriormente: `1.2.4.0`.

A versão técnica é um contador monotônico independente da tag pública. Ela foi avançada para
substituir pacotes de rascunho anteriores e não representa uma release `0.2.4`.

Evidência do candidato local anterior, ainda com `large-v3` incorporado (não enviado):

- tamanho: 7.896.794.378 bytes;
- SHA-256: `8ecd815dcdea63f9e80b0b16caf1bf815a52c80cbf951437352b5a8200b7519c`;
- identidade, versão, arquitetura, manifesto e executável verificados por `build.py`;
- instalação local registrada pelo Windows com versão `1.3.4.0` e status `Ok`;
- resultado do Windows App Certification Kit registrado no relatório final de validação junto dos
  artefatos.

A certificação definitiva pertence ao Partner Center, mesmo quando o WACK local é aprovado.

## 6. Checklist antes do envio

- [ ] `main` limpa e sincronizada após a publicação no GitHub;
- [ ] versão pública e técnica revisadas;
- [x] 131 testes e lint aprovados localmente;
- [x] FFmpeg e runtime CUDA presentes no autodiagnóstico;
- [x] identidade do manifesto igual à edição gratuita somente para o teste local;
- [x] novo produto Pro reservado e identidade copiada para o manifesto;
- [x] preço brasileiro de R$ 26,95 configurado no produto Pro;
- [x] arquitetura restrita a Windows Desktop x64;
- [ ] assets visuais e descrições preenchidos;
- [x] política de privacidade preenchida;
- [ ] pacote anterior incorreto removido do rascunho;
- [ ] MSIX final salvo e submetido;
- [ ] Partner Center sem erro de validação;
- [ ] página pública permitindo aquisição;
- [ ] instalação pela Store testada em Windows compatível;
- [x] inferência offline de `medium` e `turbo` testada em GPU e CPU;
- [x] novo fluxo de download explícito/cache de `large-v3` revalidado no candidato reduzido;
- [x] download explícito, cancelamento e cache de `tiny`, `base` e `small` testados.

## 7. Relação com os downloads GitHub

A release v0.3.0 oferece instaladores offline NVIDIA CUDA/CPU, portáteis e Linux. O pipeline instala
e autoverifica os pacotes antes de publicar, mas os executáveis Windows diretos não têm
Authenticode.

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
