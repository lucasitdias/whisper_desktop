# Entrega e publicação da v0.3.0

## Estado da versão

A versão pública **v0.3.0** foi concluída e aceita localmente em 24/08/2026. O contador técnico do
pacote MSIX de homologação é `1.3.4.0`. A aplicação gratuita já publicada na Microsoft Store
permanece isolada na versão `1.2.4.0`; a edição Pro deve usar um novo produto reservado no Partner
Center.

Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

## Artefatos locais aceitos

| Bundle de homologação | Bytes | SHA-256 |
| --- | ---: | --- |
| `WhisperTranscriber-Setup-Windows-x64-Offline.zip` | 4.951.754.218 | `20daa4953e12c6373fc1c5bf6ed3775971c1b8d0c79437d1051cb12e4443a304` |
| `WhisperTranscriber-Setup-Windows-x64-CPU-Offline.zip` | 3.373.852.644 | `bb3d2a53cfae631731cb21db7596374748052fe2f33378497d7c0b2c3ac6827d` |

Os ZIPs completos são evidência local e conveniência de transporte. A release do GitHub publica o
launcher `.exe` e suas partes `.bin` separadamente, pois [cada arquivo de uma release precisa ter
menos de 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
O instalador funciona mantendo o launcher e todas as partes de sua variante na mesma pasta.

Os portáteis Windows e os pacotes Linux que ultrapassarem esse limite são publicados em partes
numeradas. Os manifestos `SHA256SUMS-*` sempre registram o hash do arquivo integral antes da
divisão. A reconstrução não modifica o conteúdo:

```powershell
cmd /c copy /b WhisperTranscriber-Windows-x64.zip.part-01+WhisperTranscriber-Windows-x64.zip.part-02 WhisperTranscriber-Windows-x64.zip
```

```bash
cat WhisperTranscriber-Setup-Linux-x64.deb.part-* > WhisperTranscriber-Setup-Linux-x64.deb
```

Depois da reconstrução, o usuário deve conferir o SHA-256 do arquivo integral com o manifesto da
plataforma.

## Sequência de publicação

1. Executar Ruff, pytest, `git diff --check`, autodiagnóstico e varredura de conteúdo publicável.
2. Enviar o commit final em português para `main` e aguardar o CI de Windows/Linux.
3. Criar a tag anotada `v0.3.0` somente após o CI aprovado.
4. Aguardar builds limpos, instalação, autodiagnóstico, desinstalação, checksums e GitHub Release.
5. Baixar novamente os anexos da release e conferir seus hashes.
6. Reservar um produto **separado** para a edição Pro no Partner Center.
7. Atualizar a identidade do manifesto para a nova reserva, manter o desenvolvedor `Lucas Dias`,
   definir o preço brasileiro em **R$ 25,99** e gerar um novo MSIX.
8. Submeter o MSIX Pro, acompanhar a certificação e só marcar a Store como concluída depois que a
   página permitir aquisição e instalação reais.

## Canais e separação comercial

- **Edição gratuita:** produto `9PHWS6MM59BG`, versão instalada `1.2.4.0`, sem receber os recursos
  Pro da v0.3.0.
- **Edição Pro:** novo produto, preço regional de R$ 25,99, versão pública v0.3.0 e identidade ainda
  dependente da reserva no Partner Center.
- **GitHub Release:** código-fonte, instaladores fracionados, portáteis/pacotes fracionados quando
  necessário, avisos de terceiros e checksums.

## Portões que não podem ser ignorados

- não publicar bundles acima de 2 GiB como um único anexo no GitHub;
- não enviar o MSIX Pro usando a identidade da edição gratuita;
- não desativar Smart App Control ou outra proteção do Windows para distribuir um executável;
- não afirmar publicação na Store antes da certificação e aquisição pública;
- não versionar checkpoints, áudios, certificados, chaves, caches ou diretórios de build;
- preservar `LICENSE`, `CITATION.cff` e `docs/THIRD_PARTY_NOTICES.md` nos canais aplicáveis.
