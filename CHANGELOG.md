# Alterações

## 0.2.0 — 30/10/2026

- Arquivar e restaurar perfis conserva o identificador e a sessão original.
- Falhas ao gravar não alteram a lista, o nome nem a página aberta.
- Configuração validada e gravada por substituição atômica, com testes de erro de escrita.
- Indicadores de carregamento e erro são preservados ao alternar contas.
- Comandos sem perfil selecionado ficam desabilitados; nomes completos aparecem no tooltip.
- Erros na pasta de sessão e em downloads interrompidos recebem aviso.
- Instaladores verificam se a central está aberta antes de modificar o runtime.
- Empacotamentos incluem o novo módulo de persistência e a versão centralizada.
- CI passa a incluir testes de armazenamento e da interface sem login.

Validação local: sete testes de armazenamento, smoke da interface com navegação simulada e proteção de instância ativa passaram. Dois perfis chegaram à tela de QR Code no teste inicial da versão 0.1.0. Login persistente, notificações e chamadas com contas reais ainda dependem de teste do usuário; não há medição comparativa de RAM/CPU. A receita Flatpak continua sem compilação e teste.
