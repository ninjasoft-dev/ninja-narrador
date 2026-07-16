# Como contribuir

Obrigado por ajudar o Ninja Narrator. Correções, documentação, novos testes e
backends de síntese são bem-vindos.

## Preparação

1. Crie um fork e uma branch curta para a mudança.
2. Use Python 3.10 ou 3.11.
3. Instale `requirements-dev.txt` em um ambiente virtual.
4. Não adicione vozes, pesos de modelos, credenciais ou dados pessoais.

Antes do pull request, execute:

```powershell
python -m ruff check ninja_narrator tests interface.py
python -m pytest
```

Prefira mudanças pequenas, com motivação clara e testes proporcionais ao risco.
Comentários e docstrings do projeto são escritos em português brasileiro.

## Segurança e ética

Contribuições que facilitem fraude, personificação sem consentimento ou remoção
de salvaguardas não serão aceitas. Todo backend novo deve documentar sua licença
e as restrições aplicáveis aos pesos e às saídas.
