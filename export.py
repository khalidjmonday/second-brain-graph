"""Capture a generated graph as a 4K presentation image with Playwright."""

from pathlib import Path


def export_presentation_slide(
    html_path: Path,
    output_path: Path | None = None,
    *,
    width: int = 3840,
    height: int = 2160,
    settle_seconds: int = 5,
) -> Path:
    """Render local graph HTML in Chromium and save a 4K PNG screenshot."""
    if width < 2 or height < 2 or width % 2 or height % 2 or settle_seconds < 0:
        raise ValueError(
            "Image dimensions must be positive and even; settle time cannot be negative."
        )
    html_path = html_path.expanduser().resolve()
    output_path = (output_path or html_path.with_name("Presentation_Slide.png"))
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "4K slide export needs Playwright. Install it with `pip install playwright` "
            "then run `python -m playwright install chromium`."
        ) from error

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={"width": width // 2, "height": height // 2},
                    device_scale_factor=2,
                )
                page.goto(html_path.as_uri(), wait_until="load", timeout=60_000)
                page.wait_for_function("typeof network !== 'undefined'", timeout=30_000)
                page.wait_for_timeout(settle_seconds * 1000)
                page.evaluate("network.stopSimulation(); network.fit({animation: false})")
                page.screenshot(path=str(output_path), type="png", full_page=True)
            finally:
                browser.close()
    except Exception as error:
        raise RuntimeError(
            "Could not capture the graph. Check the output path and Chromium install "
            f"(`python -m playwright install chromium`): {error}"
        ) from error
    return output_path
