#!/usr/bin/env python3
"""
E-14 Scraper - Script principal
Orquestador para extracción masiva de formularios E-14 de la Registraduría

Uso:
    python main.py init          # Inicializar DB y cargar tareas
    python main.py run           # Ejecutar el scraping
    python main.py status        # Ver estado actual
    python main.py export        # Exportar resultados
"""
import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import Optional
import asyncpg
import json

import structlog
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from config import settings
from models import init_database
from orchestrator import Orchestrator, run_orchestrator
from worker import E14Worker
from data_loader import load_all_data, SAMPLE_DEPARTAMENTOS

# Configurar logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
console = Console()


async def cmd_init(args):
    """Inicializa la base de datos y carga las tareas iniciales"""
    console.print(Panel.fit(
        "[bold blue]Inicializando E-14 Scraper[/bold blue]",
        subtitle="Configuración inicial"
    ))

    # 1. Inicializar base de datos
    with console.status("[bold green]Creando tablas en la base de datos..."):
        await init_database(settings.database_url)
    console.print("✅ Base de datos inicializada")

    # 2. Cargar datos de departamentos/municipios
    console.print("\n[bold]Cargando estructura de departamentos/municipios...[/bold]")

    if args.sample:
        console.print("[yellow]Usando datos de ejemplo (modo demo)[/yellow]")
        departamentos_data = SAMPLE_DEPARTAMENTOS
    elif args.data_file:
        console.print(f"Cargando desde archivo: {args.data_file}")
        with open(args.data_file, 'r') as f:
            departamentos_data = json.load(f)
    else:
        with console.status("[bold green]Descargando estructura desde Registraduría..."):
            departamentos_data = await load_all_data(use_cache=True)

    # 3. Cargar tareas en la base de datos
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    with console.status("[bold green]Cargando tareas en la cola..."):
        num_tasks = await orchestrator.load_initial_tasks(departamentos_data)

    console.print(f"✅ [bold green]{num_tasks:,}[/bold green] tareas cargadas")

    # Mostrar resumen
    stats = await orchestrator.queue.get_stats()
    await orchestrator.shutdown()

    table = Table(title="Resumen de Inicialización")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    table.add_row("Total de tareas", f"{stats['total']:,}")
    table.add_row("Departamentos", str(len(departamentos_data)))
    table.add_row("Workers configurados", str(settings.num_workers))
    table.add_row("Requests/min por worker", str(settings.requests_per_minute_per_worker))

    console.print(table)

    # Estimación de tiempo
    total_requests = stats['total']
    requests_per_min = settings.num_workers * settings.requests_per_minute_per_worker
    estimated_minutes = total_requests / requests_per_min if requests_per_min > 0 else 0

    console.print(f"\n⏱️  Tiempo estimado: [bold]{estimated_minutes:.0f} minutos[/bold] ({estimated_minutes/60:.1f} horas)")
    console.print("\nEjecuta [bold cyan]python main.py run[/bold cyan] para iniciar el scraping")


async def cmd_run(args):
    """Ejecuta el orquestador y los workers"""
    console.print(Panel.fit(
        "[bold green]Iniciando E-14 Scraper[/bold green]",
        subtitle=f"{settings.num_workers} workers"
    ))

    # Verificar que hay tareas
    pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_size=1,
        max_size=5
    )

    count = await pool.fetchval("SELECT COUNT(*) FROM scraping_tasks WHERE status = 'pending'")
    await pool.close()

    if count == 0:
        console.print("[yellow]⚠️  No hay tareas pendientes. Ejecuta 'python main.py init' primero.[/yellow]")
        return

    console.print(f"📋 Tareas pendientes: [bold]{count:,}[/bold]")
    console.print(f"🔧 Workers: [bold]{settings.num_workers}[/bold]")
    console.print(f"🔑 CAPTCHA solver: [bold]{'Configurado' if settings.captcha_api_key else 'No configurado'}[/bold]")
    console.print(f"🌐 Proxies: [bold]{'Configurados' if settings.use_proxies else 'No configurados'}[/bold]")

    console.print("\n[dim]Presiona Ctrl+C para detener el scraping de forma segura[/dim]\n")

    # Ejecutar
    await run_orchestrator(E14Worker)


async def cmd_status(args):
    """Muestra el estado actual del scraping"""
    pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_size=1,
        max_size=5
    )

    try:
        # Estadísticas generales
        stats = await pool.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'retry') as retry,
                COUNT(DISTINCT worker_id) FILTER (WHERE status = 'in_progress') as active_workers
            FROM scraping_tasks
        """)

        total = stats['total'] or 1
        completed = stats['completed'] or 0
        percent = (completed / total) * 100

        # Tabla principal
        table = Table(title="📊 Estado del Scraping E-14")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        table.add_column("Porcentaje", style="yellow")

        table.add_row("Total tareas", f"{stats['total']:,}", "100%")
        table.add_row("Completadas", f"{stats['completed']:,}", f"{percent:.1f}%")
        table.add_row("Pendientes", f"{stats['pending']:,}", f"{(stats['pending']/total*100):.1f}%")
        table.add_row("En progreso", f"{stats['in_progress']:,}", f"{(stats['in_progress']/total*100):.1f}%")
        table.add_row("Fallidas", f"{stats['failed']:,}", f"{(stats['failed']/total*100):.1f}%")
        table.add_row("En reintento", f"{stats['retry']:,}", f"{(stats['retry']/total*100):.1f}%")
        table.add_row("Workers activos", str(stats['active_workers']), "-")

        console.print(table)

        # Progreso por departamento
        if args.detailed:
            dept_stats = await pool.fetch("""
                SELECT
                    departamento_nombre,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed
                FROM scraping_tasks
                GROUP BY departamento_id, departamento_nombre
                ORDER BY departamento_nombre
            """)

            dept_table = Table(title="Progreso por Departamento")
            dept_table.add_column("Departamento", style="cyan")
            dept_table.add_column("Total", style="white")
            dept_table.add_column("Completadas", style="green")
            dept_table.add_column("Progreso", style="yellow")

            for row in dept_stats:
                pct = (row['completed'] / row['total'] * 100) if row['total'] > 0 else 0
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                dept_table.add_row(
                    row['departamento_nombre'],
                    str(row['total']),
                    str(row['completed']),
                    f"{bar} {pct:.0f}%"
                )

            console.print(dept_table)

        # Workers activos
        workers = await pool.fetch("""
            SELECT worker_id, tasks_completed, tasks_failed, last_activity
            FROM worker_sessions
            WHERE is_active = TRUE
            ORDER BY worker_id
        """)

        if workers:
            worker_table = Table(title="Workers Activos")
            worker_table.add_column("Worker", style="cyan")
            worker_table.add_column("Completadas", style="green")
            worker_table.add_column("Fallidas", style="red")
            worker_table.add_column("Última actividad", style="dim")

            for w in workers:
                worker_table.add_row(
                    w['worker_id'],
                    str(w['tasks_completed']),
                    str(w['tasks_failed']),
                    w['last_activity'].strftime("%H:%M:%S") if w['last_activity'] else "-"
                )

            console.print(worker_table)

    finally:
        await pool.close()


async def cmd_export(args):
    """Exporta los resultados a un archivo"""
    console.print(Panel.fit("[bold blue]Exportando resultados[/bold blue]"))

    pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_size=1,
        max_size=5
    )

    try:
        output_file = args.output or f"e14_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with console.status(f"[bold green]Exportando a {output_file}..."):
            results = await pool.fetch("""
                SELECT
                    t.departamento_nombre,
                    t.municipio_nombre,
                    t.zona_nombre,
                    t.puesto_nombre,
                    t.corporacion,
                    t.e14_url,
                    r.votos_por_partido,
                    r.total_votos,
                    r.raw_data
                FROM scraping_tasks t
                LEFT JOIN e14_results r ON t.id = r.task_id
                WHERE t.status = 'completed'
                ORDER BY t.departamento_nombre, t.municipio_nombre
            """)

            data = []
            for row in results:
                data.append({
                    'departamento': row['departamento_nombre'],
                    'municipio': row['municipio_nombre'],
                    'zona': row['zona_nombre'],
                    'puesto': row['puesto_nombre'],
                    'corporacion': row['corporacion'],
                    'e14_url': row['e14_url'],
                    'votos_por_partido': row['votos_por_partido'],
                    'total_votos': row['total_votos'],
                    'raw_data': row['raw_data']
                })

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        console.print(f"✅ Exportados [bold]{len(data):,}[/bold] registros a [bold cyan]{output_file}[/bold cyan]")

    finally:
        await pool.close()


async def cmd_reset(args):
    """Reinicia las tareas fallidas o todas las tareas"""
    pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
        min_size=1,
        max_size=5
    )

    try:
        if args.all:
            if not args.force:
                console.print("[yellow]⚠️  Esto reiniciará TODAS las tareas. Usa --force para confirmar.[/yellow]")
                return

            result = await pool.execute("""
                UPDATE scraping_tasks
                SET status = 'pending', attempts = 0, worker_id = NULL, last_error = NULL
            """)
            console.print(f"✅ Todas las tareas reiniciadas")
        else:
            result = await pool.execute("""
                UPDATE scraping_tasks
                SET status = 'pending', worker_id = NULL
                WHERE status IN ('failed', 'retry')
            """)
            console.print(f"✅ Tareas fallidas reiniciadas")

    finally:
        await pool.close()


def main():
    parser = argparse.ArgumentParser(
        description="E-14 Scraper - Extracción masiva de formularios electorales",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Comando init
    init_parser = subparsers.add_parser('init', help='Inicializar base de datos y tareas')
    init_parser.add_argument('--sample', action='store_true', help='Usar datos de ejemplo (demo)')
    init_parser.add_argument('--data-file', type=str, help='Archivo JSON con datos de departamentos')

    # Comando run
    run_parser = subparsers.add_parser('run', help='Ejecutar el scraping')
    run_parser.add_argument('--workers', type=int, help='Número de workers (override config)')

    # Comando status
    status_parser = subparsers.add_parser('status', help='Ver estado actual')
    status_parser.add_argument('--detailed', '-d', action='store_true', help='Mostrar detalles por departamento')

    # Comando export
    export_parser = subparsers.add_parser('export', help='Exportar resultados')
    export_parser.add_argument('--output', '-o', type=str, help='Archivo de salida')

    # Comando reset
    reset_parser = subparsers.add_parser('reset', help='Reiniciar tareas')
    reset_parser.add_argument('--all', action='store_true', help='Reiniciar todas las tareas')
    reset_parser.add_argument('--force', action='store_true', help='Confirmar reinicio total')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Ejecutar comando
    commands = {
        'init': cmd_init,
        'run': cmd_run,
        'status': cmd_status,
        'export': cmd_export,
        'reset': cmd_reset,
    }

    try:
        asyncio.run(commands[args.command](args))
    except KeyboardInterrupt:
        console.print("\n[yellow]Operación cancelada por el usuario[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("Error fatal")
        sys.exit(1)


if __name__ == "__main__":
    main()
