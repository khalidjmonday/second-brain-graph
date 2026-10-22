# Security and privacy

Second Brain Graph reads Markdown files from a directory selected by the
operator and generates HTML and optional JSON files locally. It does not run a
server or send note text to a semantic-link API. Sentence Transformers may
download model files from Hugging Face on first use; model inference is local.

Generated artifacts contain note titles, vault-relative paths, links, graph
metrics, and similarity scores. Review them before publishing or sharing.
Embedding cache files contain vectors and fingerprints and should be treated
as derived private data from the vault.

To report a vulnerability, open a private GitHub Security Advisory for the
repository owner rather than posting sensitive details in a public issue.
