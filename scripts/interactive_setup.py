import asyncio
import sys
from pathlib import Path
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from crawlforge.config.settings import get_settings
from crawlforge.core.engine import CrawlerEngine
from crawlforge.core.session import SessionHandler
from crawlforge.exporters.markdown import MarkdownExporter
from crawlforge.exporters.html import HtmlExporter
from crawlforge.exporters.text import TextExporter
from crawlforge.exporters.pdf import PdfExporter
from crawlforge.models.enums import ExtractionStrategy, OutputFormat, JobPriority
from crawlforge.models.schemas import CrawlJob

console = Console()

async def main():
    console.print(Panel.report(
        "[bold blue]CrawlForge Interactive Setup[/bold blue]\n"
        "Configure e execute seu crawl com facilidade.",
        title="Forge Wizard",
        expand=False
    ))

    # 1. Target URL
    url = await questionary.text(
        "Qual a URL alvo?",
        validate=lambda text: True if text.startswith("http") else "A URL deve começar com http/https"
    ).ask_async()

    # 2. Strategy
    strategy_str = await questionary.select(
        "Qual estratégia de extração?",
        choices=[
            "Full Page (Markdown)",
            "HTML Only",
            "CSS Selectors (JSON)",
            "Deep Crawl (Exploração Recursiva)"
        ],
        default="Full Page (Markdown)"
    ).ask_async()

    strategy_map = {
        "Full Page (Markdown)": ExtractionStrategy.FULL,
        "HTML Only": ExtractionStrategy.HTML,
        "CSS Selectors (JSON)": ExtractionStrategy.CSS,
        "Deep Crawl (Exploração Recursiva)": ExtractionStrategy.DEEP_CRAWL
    }
    strategy = strategy_map[strategy_str]

    # 3. Output Format
    format_str = await questionary.select(
        "Em qual formato deseja exportar?",
        choices=["Markdown", "HTML", "Plain Text", "PDF"],
        default="Markdown"
    ).ask_async()

    format_map = {
        "Markdown": OutputFormat.MARKDOWN,
        "HTML": OutputFormat.HTML,
        "Plain Text": OutputFormat.TEXT,
        "PDF": OutputFormat.PDF
    }
    output_format = format_map[format_str]

    # 4. Deep Crawl Specifics
    depth = 0
    max_pages = 50
    if strategy == ExtractionStrategy.DEEP_CRAWL:
        depth = int(await questionary.text("Profundidade máxima (0-5)?", default="1").ask_async())
        max_pages = int(await questionary.text("Número máximo de URLs (1-500)?", default="50").ask_async())

    # 5. Robots.txt
    respect_robots = await questionary.confirm("Respeitar robots.txt?", default=True).ask_async()

    # 6. Anti-bot
    use_magic = await questionary.confirm("Usar Magic Mode (Anti-bot avançado)?", default=False).ask_async()

    # 7. Workers
    num_workers = int(await questionary.text("Quantos workers paralelos?", default="3").ask_async())

    # Setup environment
    settings = get_settings()
    settings.queue_num_workers = num_workers
    
    await SessionHandler.global_start(settings)
    engine = CrawlerEngine(settings)
    
    exporters = {
        OutputFormat.MARKDOWN: MarkdownExporter(),
        OutputFormat.HTML: HtmlExporter(),
        OutputFormat.TEXT: TextExporter(),
        OutputFormat.PDF: PdfExporter()
    }
    exporter = exporters[output_format]

    job = CrawlJob(
        url=url,
        strategy=strategy,
        output_format=output_format,
        depth=depth,
        max_pages=max_pages,
        respect_robots=respect_robots,
        use_magic=use_magic
    )

    console.print(f"\n[bold green]Iniciando crawl job {job.id}...[/bold green]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Crawling {url}...", total=None)
        result = await engine.execute(job)

    if result.success:
        path = await exporter.export(result.content, job)
        console.print(f"\n[bold green]✨ Sucesso![/bold green] Arquivo salvo em: [cyan]{path}[/cyan]")
    else:
        console.print(f"\n[bold red]❌ Falha:[/bold red] {result.error_message}")

    await SessionHandler.global_cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Crawl cancelado pelo usuário.[/yellow]")
        sys.exit(0)
