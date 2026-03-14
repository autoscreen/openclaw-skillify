from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from skillify.models import APISpec

app = typer.Typer(
    name="skillify",
    help="Turn any API surface into OpenClaw/nanobot skills.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def discover(
    source: str = typer.Argument(help="URL, file path, or Python package name"),
    output: str = typer.Option(
        "./skillify-spec.json", "-o", "--output", help="Output spec file path"
    ),
    source_type: str = typer.Option(
        "auto",
        "-t",
        "--source-type",
        help="Source type: auto, openapi, graphql, html, python",
    ),
    model: str = typer.Option(
        None, "-m", "--model", help="LLM model for AI-aided steps"
    ),
) -> None:
    """Discover an API surface and output a spec JSON file."""
    from skillify.discover import discover as _discover

    console.print(f"[bold]Discovering API from:[/bold] {source}")

    spec = asyncio.run(_discover(source, source_type=source_type, model=model))

    # Write spec
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(spec.model_dump_json(indent=2))

    console.print(f"\n[green]Discovered {len(spec.endpoints)} endpoints[/green]")
    if spec.groups:
        console.print(f"[green]Grouped into {len(spec.groups)} skills:[/green]")
        for g in spec.groups:
            console.print(f"  - {g.name} ({len(g.endpoints)} endpoints)")
    console.print(f"\nSpec written to: {out_path}")


@app.command()
def generate(
    spec_path: str = typer.Argument(help="Path to spec JSON file"),
    output_dir: str = typer.Option(
        "./skills", "-o", "--output-dir", help="Output directory"
    ),
    model: str = typer.Option(
        None, "-m", "--model", help="LLM model for generation"
    ),
    preview: bool = typer.Option(
        False, "--preview", help="Dry-run: show what would be generated"
    ),
    install: bool = typer.Option(
        False, "--install", help="Install to ~/.nanobot/workspace/skills/"
    ),
) -> None:
    """Generate OpenClaw skills from a spec JSON file."""
    from skillify.generate import generate as _generate

    spec = APISpec.model_validate_json(Path(spec_path).read_text())
    console.print(
        f"[bold]Generating skills for:[/bold] {spec.api_name} "
        f"({len(spec.groups)} groups)"
    )

    result = asyncio.run(
        _generate(spec, output_dir=output_dir, model=model, dry_run=preview, install=install)
    )

    if preview:
        console.print("\n[bold]Preview — skills that would be generated:[/bold]\n")
        table = Table()
        table.add_column("Skill", style="cyan")
        table.add_column("Endpoints", justify="right")
        table.add_column("References", justify="right")
        table.add_column("Scripts", justify="right")
        for s in result.skills:
            # count endpoints from the group
            group = next(
                (g for g in spec.groups if g.name == s.name), None
            )
            ep_count = len(group.endpoints) if group else "?"
            table.add_row(
                s.name,
                str(ep_count),
                str(len(s.references)),
                str(len(s.scripts)),
            )
        console.print(table)
    else:
        console.print(f"\n[green]Generated {len(result.skills)} skills:[/green]")
        for s in result.skills:
            console.print(f"  - {output_dir}/{s.name}/")
        if install:
            console.print(
                "\n[green]Installed to ~/.nanobot/workspace/skills/[/green]"
            )


@app.command(name="preview")
def preview_cmd(
    spec_path: str = typer.Argument(help="Path to spec JSON file"),
    model: str = typer.Option(None, "-m", "--model", help="LLM model"),
) -> None:
    """Preview what skills would be generated (alias for generate --preview)."""
    from skillify.generate import generate as _generate

    spec = APISpec.model_validate_json(Path(spec_path).read_text())
    result = asyncio.run(
        _generate(spec, dry_run=True, model=model)
    )

    console.print(f"\n[bold]Preview for:[/bold] {spec.api_name}\n")
    table = Table()
    table.add_column("Skill", style="cyan")
    table.add_column("Endpoints", justify="right")
    table.add_column("Has References", justify="center")
    for s in result.skills:
        group = next((g for g in spec.groups if g.name == s.name), None)
        ep_count = len(group.endpoints) if group else "?"
        table.add_row(s.name, str(ep_count), "yes" if s.references else "no")
    console.print(table)


@app.command()
def run(
    source: str = typer.Argument(help="URL, file path, or Python package name"),
    output_dir: str = typer.Option(
        "./skills", "-o", "--output-dir", help="Output directory"
    ),
    source_type: str = typer.Option(
        "auto", "-t", "--source-type", help="Source type"
    ),
    model: str = typer.Option(None, "-m", "--model", help="LLM model"),
    install: bool = typer.Option(
        False, "--install", help="Install to ~/.nanobot/workspace/skills/"
    ),
) -> None:
    """Discover an API and generate skills in one step."""
    from skillify.discover import discover as _discover
    from skillify.generate import generate as _generate

    console.print(f"[bold]Discovering API from:[/bold] {source}")
    spec = asyncio.run(_discover(source, source_type=source_type, model=model))

    console.print(
        f"[green]Found {len(spec.endpoints)} endpoints in {len(spec.groups)} groups[/green]"
    )
    console.print(f"[bold]Generating skills...[/bold]")

    result = asyncio.run(
        _generate(spec, output_dir=output_dir, model=model, install=install)
    )

    console.print(f"\n[green]Generated {len(result.skills)} skills:[/green]")
    for s in result.skills:
        console.print(f"  - {output_dir}/{s.name}/")
    if install:
        console.print("\n[green]Installed to ~/.nanobot/workspace/skills/[/green]")


if __name__ == "__main__":
    app()
