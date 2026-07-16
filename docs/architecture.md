# Arquitetura

O Ninja Narrator separa interface, regras e mecanismo de síntese para evitar que
decisões do XTTS-v2 se espalhem pelo projeto.

```text
GUI / CLI
   │
   ▼
NarrationRequest ──► NarrationService ──► SpeechBackend
                          │                    │
                          │                    └─ XttsBackend
                          ▼
                 GeneratedAudio / Failure
```

- `domain.py`: tipos e validações que não dependem de framework.
- `service.py`: composição dos trabalhos, cancelamento e relatório de falhas.
- `backends/base.py`: contrato para mecanismos locais ou remotos futuros.
- `backends/xtts.py`: integração isolada com o Coqui TTS.
- `gui_app.py`: interface CustomTkinter; nunca carrega o modelo na inicialização.
- `cli.py`: automação de terminal com os mesmos consentimentos da interface.

O modelo é carregado sob demanda. Essa escolha reduz o tempo de abertura da GUI
e permite listar vozes ou editar o texto sem reservar VRAM.
