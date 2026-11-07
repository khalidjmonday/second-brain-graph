export const COLORS = ["#7799c2", "#b77a78", "#367a5b", "#8581a2"];

export const DEMO_NOTES = [
  { id: "Home.md", title: "Home.md", folder: "notes", cluster: "Core ideas", color: COLORS[0], text: "A working index for the knowledge base. Start here to explore the main topics, current questions, and active projects.", links: ["Projects.md", "Data Structures.md", "Machine Learning.md"] },
  { id: "Projects.md", title: "Projects.md", folder: "notes", cluster: "Core ideas", color: COLORS[0], text: "A collection of experiments and project plans. The graph explorer connects notes to make the work and its dependencies easier to navigate.", links: ["Home.md", "Python.md", "Predictive Model Training.md"] },
  { id: "Python.md", title: "Python.md", folder: "notes", cluster: "Programming", color: COLORS[2], text: "Python is a practical language for automation, data processing, and graph analysis. Useful concepts include modules, type hints, and iterators.", links: ["Data Structures.md", "Projects.md"], semanticLinks: ["BFS vs DFS.md"] },
  { id: "Machine Learning.md", title: "Machine Learning.md", folder: "notes", cluster: "Learning systems", color: COLORS[3], text: "Machine learning models find patterns from examples. Embeddings represent text as vectors so notes with related concepts can be discovered.", links: ["Predictive Model Training.md", "Home.md"] },
  { id: "Data Structures.md", title: "Data Structures.md", folder: "notes", cluster: "Programming", color: COLORS[2], text: "Data structures organize information for efficient access. Graphs model relationships using vertices and edges, and support traversal algorithms.", links: ["Python.md", "Home.md"], semanticLinks: ["BFS vs DFS.md"] },
  { id: "Predictive Model Training.md", title: "Predictive Model Training.md", folder: "src", cluster: "Learning systems", color: COLORS[3], text: "Model training adjusts parameters to reduce a loss function. Track the training data, evaluation split, metrics, and reproducible settings.", links: ["Machine Learning.md", "Projects.md"] },
  { id: "BFS vs DFS.md", title: "BFS vs DFS.md", folder: "notes", cluster: "Programming", color: COLORS[2], text: "Breadth-first search explores neighbors level by level. Depth-first search follows one path before backtracking. Both run in O(V + E).", links: ["Data Structures.md"] },
];

export function parseMarkdownFiles(fileList) {
  const files = [...fileList].filter((file) => file.name.toLowerCase().endsWith(".md"));
  const names = new Set(files.map((file) => file.name));
  return Promise.all(files.map(async (file, index) => {
    const text = await file.text();
    const links = [...text.matchAll(/\[\[([^\]]+)\]\]/g)].map((match) => `${match[1].split("|")[0].split("#")[0].trim().replace(/\.md$/i, "")}.md`);
    const title = file.name;
    return {
      id: title,
      title,
      folder: file.webkitRelativePath?.split("/").slice(-2, -1)[0] || "notes",
      cluster: "Imported notes",
      color: COLORS[index % COLORS.length],
      text: text.replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, "").replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (_, target, alias) => alias || target).replace(/^#+\s*/gm, "").trim().slice(0, 360) || "No preview text available.",
      links: links.filter((name) => names.has(name)),
    };
  }));
}
