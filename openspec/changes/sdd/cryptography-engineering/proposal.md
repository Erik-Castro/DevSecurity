# Proposal: Book 5 — Cryptography Engineering in C++

## Intent
Fill critical gap in PT-BR technical literature: comprehensive cryptography engineering guide in C++17. Book 1 covers "use crypto correctly"; Book 5 covers "build crypto systems correctly". Addresses industry demand for practical crypto engineers, constant-time programming, side-channel mitigation, HSM integration, TLS 1.3 internals, post-quantum migration, and formal verification.

## Scope

### In Scope
- 18-chapter book (~50,000–70,000 lines total)
- PT-BR prose, English code identifiers
- Minimum 800 lines/chapter, target 2,800–3,900 lines
- Structured chapters: Objetivos de Aprendizado → Technical sections → C++17 code → CVE tables → Exercises → References
- 20+ documented CVEs (Lucky13, Minerva, Raccoon, Heartbleed, POODLE, FREAK, ROCA, TPM-FAIL, Hertzbleed, Downfall, Cloudbleed, Debian OpenSSL bug, Android PRNG, etc.)
- Real-world code examples with OpenSSL 3.x, libsodium, BoringSSL, liboqs, Botan, TPM2-TSS
- Coverage: constant-time programming, side-channel attacks, HSM integration, TLS 1.3, PQC migration, advanced key management, modern protocols, hardware security (TPM/enclaves), homomorphic encryption, zero-knowledge proofs, formal verification, testing, compliance

### Out of Scope
- Cryptographic theory (covered in Book 1)
- Language-agnostic crypto (focus is C++17)
- Academic proofs (practical engineering focus)
- Hardware design (software integration only)

## Capabilities

### New Capabilities
- `crypto-engineering-book`: Full 18-chapter book content, structure, and code examples
- `crypto-cve-documentation`: 20+ CVE case studies with analysis and countermeasures
- `crypto-code-examples`: Compilable C++17 code for OpenSSL, libsodium, liboqs, etc.

### Modified Capabilities
None (new book, not modifying existing specs)

## Approach
- Follow established series pattern: chapter files `NN-slug-name.md` in `/home/Projetos/DevSecurity/cryptography/`
- Write chapters incrementally, ensuring each meets 800-line minimum before proceeding
- Use background actors for parallel chapter writing where possible
- Validate line counts after each write, never rewrite (always write new expanded content)
- Index file (INDICE.md) generated after all chapters complete

## Affected Areas
| Area | Impact | Description |
|------|--------|-------------|
| `/home/Projetos/DevSecurity/cryptography/` | New | New book directory with 18 chapter files |
| `openspec/changes/sdd/cryptography-engineering/` | Modified | Proposal, specs, design, tasks, apply-progress, verify-report |
| Series quality gates | Modified | Add Book 5 to completed books count |

## Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Chapter line count below minimum | High | Write new expanded content, never rewrite; verify after each write |
| CVE accuracy | Medium | Cross-reference with NVD, vendor advisories |
| Code compilation errors | Medium | Test all examples against target libraries |
| PT-BR quality | Low | Follow existing book conventions, natural professional tone |

## Rollback Plan
- Delete `/home/Projetos/DevSecurity/cryptography/` directory
- Remove `openspec/changes/sdd/cryptography-engineering/` directory
- No impact on existing books (Books 1–4 remain untouched)

## Dependencies
- OpenSSL 3.x, libsodium, liboqs, Botan, TPM2-TSS libraries for code examples
- NVD database for CVE details
- Existing series conventions (file naming, structure, quality gates)

## Success Criteria
- [ ] 18 chapters written, each ≥800 lines (target 2,800–3,900)
- [ ] 20+ CVEs documented with analysis and countermeasures
- [ ] Total lines ≥50,000
- [ ] All code examples compilable and functional
- [ ] INDICE.md generated with chapter links
- [ ] Quality parity with Books 1–3