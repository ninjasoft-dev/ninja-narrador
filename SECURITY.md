# Política de segurança

## Versões suportadas

Correções de segurança são aplicadas à versão mais recente da branch `main`.

Desde a versão 1.0.2, o backend usa o fork mantido `coqui-tts`. Instale versões
novas em um ambiente virtual limpo para evitar resíduos incompatíveis do pacote
histórico `TTS`. Não carregue checkpoints ou modelos obtidos de fontes não
confiáveis; o fluxo padrão utiliza o identificador público do XTTS-v2.

## Limitações conhecidas da auditoria

A resolução completa de dependências ainda informa dois identificadores
upstream sem correção aplicável a este ambiente:

- `CVE-2025-3000` descreve corrupção de memória em `torch.jit.script` no
  PyTorch 2.6. O projeto exige PyTorch 2.11 e não utiliza JIT.
- `PYSEC-2026-3447` trata de normalização Unicode ao criar `sdist` no macOS.
  O build usa Setuptools 83 ou superior em ambiente isolado; Setuptools 81
  aparece apenas como restrição transitiva do runtime PyTorch 2.11.

Esses alertas não são suprimidos por configuração do projeto. Devem ser
reavaliados quando PyTorch ou os bancos de vulnerabilidade forem atualizados.

## Relato responsável

Não publique detalhes exploráveis em uma issue aberta. Use o recurso privado
**Report a vulnerability** na aba Security do repositório.

Inclua impacto, versão afetada, passos mínimos para reprodução e uma sugestão de
mitigação, quando houver. Evite anexar vozes, credenciais ou outros dados
pessoais ao relato.
