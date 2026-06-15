# Contribuindo para o DevSecurity

Obrigado por interesse em contribuir! Este guia explica como participar do projeto.

---

## Tipos de Contribuição

### Erros Técnicos
- CVEs incorretos ou desatualizados
- Código que não compila ou tem bugs
- Informações factuais incorretas

### Melhorias de Conteúdo
- Explicação mais clara de um conceito
- Exemplos de código adicionais
- Referências para papers ou documentação

### Novos Conteúdos
- CVEs relevantes não documentados
- Ferramentas ou bibliotecas úteis
- Técnicas ou padrões emergentes

---

## Regras de Escrita

### Idioma
- **Texto**: Português brasileiro (PT-BR)
- **Código**: Identificadores em inglês
- **Comentários de código**: Inglês

### Estrutura de Capítulos
Cada capítulo deve seguir:
1. Objetivos de Aprendizado (3-5 itens)
2. Seções técnicas com código
3. Tabelas comparativas quando aplicável
4. CVEs documentados (se relevante)
5. Exercícios (5+)
6. Referências

### Formato
- Mínimo 800 linhas por capítulo
- Código em C++17, JavaScript/TypeScript, Python, Go ou linguagem apropriada
- Sem emojis no conteúdo
- Nomes de arquivo: `NN-slug-do-capitulo.md`

### Código
- Todo código deve ser compilável/executável
- Incluir tanto versão vulnerável quanto corrigida
- Usar bibliotecas maduras (OpenSSL, libsodium, etc.)
- Não implementar criptografia do zero

---

## Como Submeter uma Contribuição

### 1. Fork e Clone
```bash
git clone https://github.com/SEU-USER/DevSecurity.git
cd DevSecurity
```

### 2. Crie uma Branch
```bash
git checkout -b fix/correction-capitulo-03
# ou
git checkout -b feature/new-cve-example
```

### 3. Faça suas Alterações
- Siga as convenções de escrita
- Mantenha o formato existente
- Adicione referências quando citar fontes

### 4. Verifique
- O código compila/executa?
- As linhas estão acima de 800?
- O Markdown renderiza corretamente?

### 5. Submeta o PR
- Título descritivo: `fix(ch03): correction CVE description` ou `feat(ch05): add XSS example`
- Descreva o que foi alterado e por quê
- Link para issue se aplicável

---

## Issues

### Bug Report
```
Título: [Livro X] Descrição curta do problema

**Capítulo**: NN-nome-do-capitulo.md
**Linha(s)**: XXX-YYY
**Descrição**: O que está errado
**Sugestão**: Como corrigir (se souber)
```

### Sugestão de Conteúdo
```
Título: [Livro X] Sugestão de conteúdo

**Capítulo**: NN-nome-do-capitulo.md (ou "Novo capítulo")
**Tipo**: CVE / Ferramenta / Técnica / Referência
**Descrição**: O que adicionar e por quê
**Referências**: Links para fontes
```

---

## Diretrizes por Livro

### Book 1: Security-Driven Development
- Linguagem: C++17
- Foco: Secure coding, threat modeling, compliance

### Book 2: DevSecOps na Prática
- Linguagem: Bash, Python, YAML, Docker, HCL, Go
- Foco: CI/CD, containers, cloud, monitoring

### Book 3: Engenharia e Análise de Malware
- Linguagem: C++17 + Assembly
- Foco: RE, análise estática/dinâmica, debugging

### Book 4: Concorrência e Paralelismo Seguro
- Linguagem: C++17/20
- Foco: Lock-free, deadlocks, side-channels, performance

### Book 5: Criptografia Engenheira em C++
- Linguagem: C++17
- Foco: Constant-time, HSM, TLS, PQC, ZKP

### Book 6: Desenvolvimento Seguro na Web
- Linguagem: JavaScript/TypeScript, Python, Go
- Foco: OWASP Top 10, auth, APIs, XSS, injection

---

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob **CC BY-NC-SA 4.0**, a mesma licença do projeto.

---

## Código de Conduta

- Seja respeitoso e profissional
- Foque no conteúdo técnico
- Críticas construtivas são bem-vindas
- Todo mundo já foi iniciante em algum momento

---

## Perguntas?

Abra uma **Issue** com a标签 `question` ou `discussion`.
