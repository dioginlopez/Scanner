# Scanner facial para FC26

Sistema local em Python que usa webcam para analisar proporções faciais e gerar **sugestões iniciais** de sliders (0-100) para criação de rosto no FC26.

> Observação importante: este projeto **não integra oficialmente** com o jogo. Ele gera recomendações para você ajustar manualmente no editor facial do FC26.

## O que este projeto faz

- Captura seu rosto em tempo real pela webcam no navegador
- Exibe uma interface web responsiva para acompanhar a leitura
- Extrai métricas faciais com MediaPipe Face Mesh
- Converte métricas em sugestões de sliders para FC26
- Exporta relatório em `JSON` e `Markdown` em `output/`

## Requisitos

- Windows com webcam
- Python 3.10+

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Como usar

A interface principal é uma aplicação web local. Execute:

```powershell
python main.py
```

O navegador será aberto em `http://127.0.0.1:5000`. Permita o acesso à webcam, configure a câmera e a quantidade de amostras, clique em **INICIAR ESCANEAMENTO** e aguarde a consolidação. O painel mostra os sliders sugeridos, as métricas normalizadas e os arquivos gerados. O botão **COPIAR VALORES** copia os sliders para a área de transferência.

Para publicar no Render, conecte este repositório e use o `render.yaml` incluído. Ele instala as dependências e inicia o serviço com Gunicorn. No Render, a câmera continua sendo acessada pelo navegador do usuário; o servidor recebe os frames para análise.

## Organização

- `front/index.html`: tela principal da aplicação
- `front/styles.css`: estilos da interface
- `front/app.js`: câmera, progresso e comunicação com a API
- `back/app.py`: servidor Flask e endpoints de análise
- `src/fc26_face_scanner/`: MediaPipe, geometria, métricas e mapeamento dos sliders

Para usar o fluxo de terminal:

```powershell
python -m src.fc26_face_scanner.cli --samples 45 --camera-index 0
```

Parâmetros úteis:

- `--samples`: quantidade de amostras válidas (mais amostras = mais estabilidade)
- `--camera-index`: índice da webcam
- `--output-dir`: pasta de saída
- `--no-preview`: roda sem janela da câmera

Exemplo:

```powershell
python -m src.fc26_face_scanner.cli --samples 60 --camera-index 0 --output-dir output
```

## Saída gerada

Depois de rodar, o sistema cria:

- `output/fc26_face_report_YYYYMMDD_HHMMSS.json`
- `output/fc26_face_report_YYYYMMDD_HHMMSS.md`

No relatório, use os valores de `sliders_fc26_0a100` como base no editor facial do jogo.

## Teste rápido

```powershell
pytest -q
```

## Dicas para melhor resultado

- Use luz frontal uniforme
- Mantenha o rosto centralizado
- Evite inclinar demais a cabeça durante a captura
- Faça ajuste fino manual no FC26 após importar os valores
