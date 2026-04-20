import asyncio
import typer
import uvicorn
from rich.console import Console

from crawlforge.config.settings import get_settings
from crawlforge.cli.wizard import run_wizard

app = typer.Typer(
    help="CrawlForge: Professional web scraping system.",
    rich_markup_mode="rich",
)
console = Console()

@app.command()
def server(
    port: int = typer.Option(8000, help="Port to run the API server on"),
    host: str = typer.Option("0.0.0.0", help="Host to run the API server on"),
    reload: bool = typer.Option(True, help="Enable auto-reload for development"),
):
    """Start the CrawlForge API server."""
    console.print(f"[bold green]Starting CrawlForge Server on {host}:{port}...[/bold green]")
    uvicorn.run(
        "crawlforge.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )

@app.command()
def ui():
    """Start the interactive configuration wizard."""
    asyncio.run(run_wizard())

@app.command()
def info():
    """Display system and environment information."""
    settings = get_settings()
    console.print(f"[bold blue]app_name:[/bold blue] {settings.app_name}")
    console.print(f"[bold blue]env:[/bold blue] {settings.app_env}")
    console.print(f"[bold blue]workers:[/bold blue] {settings.queue_num_workers}")
    console.print(f"[bold blue]browser:[/bold blue] {settings.crawl4ai_browser_type}")

def main():
    app()

if __name__ == "__main__":
    main()
