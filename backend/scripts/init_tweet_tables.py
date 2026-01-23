#!/usr/bin/env python3
"""
Initialize tweet storage tables.
Run this script to create the new tables for storing tweets and analysis data.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect
from config import Config
from models.database import (
    Base, ApiCall, Tweet, AnalysisSnapshot,
    PndAxisMetric, ForecastSnapshot, CampaignStrategy
)


def main():
    """Initialize tweet storage tables."""
    print("=" * 60)
    print("CASTOR ELECCIONES - Inicializando tablas de tweets")
    print("=" * 60)

    # Get database URL
    db_url = Config.DATABASE_URL
    print(f"\nDatabase: {db_url}")

    # Create engine
    if db_url.startswith("sqlite"):
        # Create data directory if needed
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)

        # Adjust path for SQLite
        db_path = db_url.replace("sqlite:///./", "")
        full_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
        db_url = f"sqlite:///{full_db_path}"

        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        print(f"SQLite database: {full_db_path}")
    else:
        engine = create_engine(db_url)

    # Check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"\nTablas existentes: {existing_tables}")

    # New tables to create
    new_tables = [
        "api_calls",
        "tweets",
        "analysis_snapshots",
        "pnd_axis_metrics",
        "forecast_snapshots",
        "campaign_strategies"
    ]

    tables_to_create = [t for t in new_tables if t not in existing_tables]

    if not tables_to_create:
        print("\n✅ Todas las tablas ya existen!")
    else:
        print(f"\nCreando tablas: {tables_to_create}")

        # Create only new tables
        Base.metadata.create_all(bind=engine, tables=[
            ApiCall.__table__,
            Tweet.__table__,
            AnalysisSnapshot.__table__,
            PndAxisMetric.__table__,
            ForecastSnapshot.__table__,
            CampaignStrategy.__table__
        ])

        print("\n✅ Tablas creadas exitosamente!")

    # Verify tables
    inspector = inspect(engine)
    final_tables = inspector.get_table_names()
    print(f"\nTablas finales: {final_tables}")

    # Show table structure
    print("\n" + "=" * 60)
    print("ESTRUCTURA DE TABLAS")
    print("=" * 60)

    for table_name in new_tables:
        if table_name in final_tables:
            columns = inspector.get_columns(table_name)
            print(f"\n📋 {table_name} ({len(columns)} columnas)")
            for col in columns[:5]:  # Show first 5 columns
                print(f"   - {col['name']}: {col['type']}")
            if len(columns) > 5:
                print(f"   ... y {len(columns) - 5} columnas más")


if __name__ == "__main__":
    main()
