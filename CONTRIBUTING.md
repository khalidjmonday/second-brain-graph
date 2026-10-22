# Contributing

Thanks for taking an interest in Second Brain Graph. The project is designed
to stay local-first, modular, and usable from both the CLI and a fresh clone.

## Local setup

```powershell
python -m pip install -r requirements.txt
python -m compileall -q analytics.py clustering.py exporter.py graph.py main.py parser.py search.py semantic.py visualizer.py
python main.py build .\demo_notes --output .\build\demo.html --json-output .\build\demo.json
```

For parser, graph, and rendering work that does not need model inference, use
`--no-semantic`. The included vault has examples of explicit links, an
unresolved target, and a semantic-only pair.

## Change guidelines

- Keep filesystem traversal and parsing in `parser.py`.
- Keep embedding and cache concerns in `semantic.py`.
- Preserve explicit-link direction and mark semantic suggestions separately.
- Keep generated outputs UTF-8, portable, and free of absolute vault paths.
- Document new CLI options and any change to JSON schema in the README.
- Avoid adding network services or uploading vault content; semantic inference
  is local by design.

GitHub Actions runs a compile and demo smoke build on Python 3.10 through
3.14. Review both the generated HTML and JSON when changing graph or export
behavior.
