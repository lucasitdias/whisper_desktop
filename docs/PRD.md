# Documento de Requisitos de Produto (PRD)

## 1. Visão do produto

O **Whisper Transcriber Desktop** oferece transcrição local de MP3/M4A para Markdown, priorizando
privacidade, simplicidade e responsividade. O público inclui usuários de reuniões, aulas, notas de
voz e entrevistas em Português do Brasil.

## 2. Escopo funcional

| ID | Requisito | Critério de aceite |
| --- | --- | --- |
| RF01 | Seleção de áudio | Aceitar um `.mp3` ou `.m4a` por diálogo ou drag-and-drop. |
| RF02 | Modelo e idioma | Usar Whisper `turbo`, tarefa `transcribe` e `language="pt"`. |
| RF03 | GPU/CPU | Usar CUDA quando disponível; informar e usar CPU caso contrário. |
| RF04 | Primeiro uso | Baixar FFmpeg/modelo quando ausentes, com indicação visual. |
| RF05 | Assincronismo | Executar a carga pesada em `QThread`. |
| RF06 | Progresso | Exibir etapa, percentual por timestamp e trechos decodificados. |
| RF07 | Markdown | Produzir metadados, texto integral e timestamps. |
| RF08 | Resultado | Permitir editar, visualizar, copiar e salvar como `.md`. |
| RF09 | Segurança de saída | Não sobrescrever sem confirmação e gravar de forma atômica. |
| RF10 | Cancelamento | Permitir interromper com segurança, sem salvar resultado parcial. |
| RF11 | Integridade | Exibir duração processada, cobertura, última fala e confiança estimada. |

## 3. Requisitos não funcionais

- Interface e mensagens inteiramente em pt-BR, com tema escuro e suporte High-DPI.
- Arquivos de áudio nunca são enviados a serviços externos.
- Windows 10/11 x64 e Linux x86_64 são os alvos suportados.
- O executável portátil usa `--onefile --windowed`; o instalador Windows usa `--onedir` e Inno
  Setup. Ambos incluem FFmpeg, enquanto o modelo permanece no cache do usuário.
- Python 3.11, `uv`, PySide6, `openai-whisper==20250625`, PyTorch 2.12.1 e PyInstaller 6.
- O build de desenvolvimento suporta CUDA 13.0; releases usam CPU para portabilidade.

## 4. Saída Markdown

```markdown
# Transcrição de Áudio - reunião

- **Data da Transcrição:** 2026-08-18 10:30:00 -03
- **Arquivo de Origem:** `reunião.m4a`
- **Duração do Áudio:** 00:42:17
- **Modelo Utilizado:** Whisper `turbo` (809M parâmetros)
- **Idioma Configurado:** Português do Brasil (`pt`)
- **Processamento:** GPU (CUDA)

---

## 📝 Transcrição Completa

Texto completo.

---

## ⏱️ Transcrição com Marcadores Temporais (Timestamps)

- **[00:00:00 -> 00:00:05]** Primeiro trecho.
```

O caminho absoluto do áudio não deve aparecer na exportação.

## 5. Fora do escopo inicial

- gravação de microfone, processamento em lote, diarização e tradução;
- formatos diferentes de MP3/M4A;
- macOS, ARM e instaladores Linux nativos;
- incorporação dos pesos do modelo no executável.
