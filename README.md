<div align="center">
  <img src="ninja_narrator/assets/ninjasoft-logo.png" alt="NinjaSoft" width="240">
  <h1>Ninja Narrator</h1>
  <p>Narração local com clonagem de voz por IA, interface desktop e automação por CLI.</p>

  [![Quality](https://github.com/ninjasoft-dev/ninja-narrator/actions/workflows/quality.yml/badge.svg)](https://github.com/ninjasoft-dev/ninja-narrator/actions/workflows/quality.yml)
  [![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![License: MIT](https://img.shields.io/badge/code-MIT-55D6A3.svg)](LICENSE)
  [![Model: CPML](https://img.shields.io/badge/XTTS--v2-uso%20não%20comercial-9D72EF.svg)](THIRD_PARTY_NOTICES.md)
</div>

![Interface do Ninja Narrator](docs/assets/ninja-narrator-escuro.png)

O Ninja Narrator transforma textos em arquivos WAV usando amostras de uma voz
autorizada. A síntese roda no próprio computador com o XTTS-v2; textos e vozes
não são enviados a uma API externa.

## Destaques

- interface clara e escura no padrão visual da NinjaSoft;
- texto digitado ou importado de TXT;
- uma voz, combinação de amostras ou comparação entre vozes;
- velocidade e duração final configuráveis;
- carregamento do modelo somente quando a geração começa;
- execução em segundo plano, cancelamento, log e reprodução do resultado;
- CLI para lotes e automações;
- arquitetura preparada para novos backends de síntese;
- consentimento de voz e licença do modelo confirmados explicitamente.

## Requisitos

| Recurso | Mínimo funcional | Recomendado |
|---|---:|---:|
| Sistema | Windows 10/11 ou Linux 64 bits | Windows 11 64 bits |
| Python | 3.10 ou 3.11 | 3.11 |
| RAM | 16 GB | 32 GB |
| Armazenamento livre | 10 GB | 20 GB |
| GPU | CPU é aceita, mas lenta | NVIDIA RTX com 8 GB+ de VRAM |

O caminho CUDA deste repositório requer uma GPU NVIDIA e drivers compatíveis.
Foi validado em uma **GeForce RTX 5070 Ti com 16 GB**, PyTorch 2.7.1 e CUDA
12.8. Outras GPUs podem exigir uma combinação diferente de PyTorch/CUDA. Em CPU,
o projeto funciona, mas uma narração pode levar muito mais tempo.

## Instalação no Windows

Clone o repositório e execute o instalador para NVIDIA/CUDA:

```powershell
git clone https://github.com/ninjasoft-dev/ninja-narrator.git
cd ninja-narrator
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Para instalar sem CUDA:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Cpu
```

Abra a interface:

```powershell
.\.venv\Scripts\python.exe .\interface.py
```

Na primeira geração, o Coqui TTS baixa os pesos do XTTS-v2. Esse processo exige
internet e pode levar alguns minutos; as execuções seguintes usam o cache local.

## Preparar uma voz

1. Obtenha autorização expressa da pessoa cuja voz será usada.
2. Grave de 6 a 15 segundos de fala limpa, sem música, eco ou outras pessoas.
3. Prefira WAV mono e nomeie o arquivo de forma reconhecível.
4. Coloque uma ou mais amostras em `reference_audio/`.

O repositório não inclui vozes demonstrativas. Amostras de voz são dados
biométricos e permanecem ignoradas pelo Git.

## Modos de referência

- **Uma voz:** usa somente a amostra selecionada.
- **Combinar amostras:** envia todas as amostras ao XTTS-v2 para formar o contexto.
- **Comparar vozes:** cria um WAV separado para cada amostra da biblioteca.

## Uso pela CLI

Liste as vozes disponíveis:

```powershell
.\.venv\Scripts\python.exe -m ninja_narrator --list-voices
```

Gere uma narração:

```powershell
.\.venv\Scripts\python.exe -m ninja_narrator `
  --text "Uma demonstração de narração local." `
  --name demonstracao `
  --mode single `
  --reference minha-voz.wav `
  --tenho-autorizacao-da-voz `
  --aceito-licenca-modelo
```

Os dois últimos argumentos são obrigatórios para síntese. O projeto não aceita
termos em nome da pessoa usuária.

## Configuração

Copie `config.example.toml` para `config.toml` para personalizar caminhos,
dispositivo e valores padrão. O arquivo local não é versionado. Também é possível
usar variáveis como `NINJA_NARRATOR_REFERENCE_DIR`, `NINJA_NARRATOR_OUTPUT_DIR`,
`NINJA_NARRATOR_DEVICE` e `NINJA_NARRATOR_MODEL`.

A estrutura interna e os pontos de extensão estão em
[docs/architecture.md](docs/architecture.md).

## Licenças e uso responsável

O **código do Ninja Narrator** é open source sob a [licença MIT](LICENSE). Isso
permite estudar, modificar e trocar o backend do projeto.

O **XTTS-v2 não usa a licença MIT**. Seus pesos e os resultados gerados por eles
estão sujeitos à Coqui Public Model License 1.0.0, que restringe esse modelo a
uso não comercial. Leia a
[licença oficial do XTTS-v2](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt)
e os [avisos de terceiros](THIRD_PARTY_NOTICES.md).

Não use clonagem de voz para personificação, fraude, desinformação, assédio ou
qualquer finalidade sem consentimento. Quem executa ou modifica o software é
responsável pelas vozes, pelos modelos e pelas saídas que utiliza.

## Desenvolvimento

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check ninja_narrator tests interface.py
.\.venv\Scripts\python.exe -m pytest --cov=ninja_narrator
```

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir um pull request e
[SECURITY.md](SECURITY.md) para relatos responsáveis.

---

Desenvolvido pela **NinjaSoft** como projeto open source de IA aplicada.
