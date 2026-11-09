"""Launch the graph builder after choosing a Markdown folder in a native dialog."""

from pathlib import Path

from main import main as run_cli


def main() -> int:
    """Select a folder, then build its graph and presentation image."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except ImportError as error:
        print(f"Could not load the folder picker: {error}")
        return 2

    try:
        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askdirectory(title="Select the project folder to map")
        root.destroy()
    except tk.TclError as error:
        print(f"Could not open the folder picker: {error}")
        return 2

    if not selected:
        return 0

    folder = Path(selected).resolve()
    html_path = folder / "graph.html"
    status = run_cli(["build", str(folder), "--output", str(html_path)])
    if status == 0:
        slide_path = folder / "Presentation_Slide.png"
        presentation_line = (
            f"\n\nPresentation image:\n{slide_path}"
            if slide_path.is_file()
            else "\n\nInstall Playwright and Chromium to export a slide image."
        )
        messagebox.showinfo(
            "Second Brain Graph",
            f"Your graph is ready:\n{html_path}{presentation_line}",
        )
    else:
        messagebox.showerror(
            "Second Brain Graph", "Graph generation failed. See the console for details."
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
