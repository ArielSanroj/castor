#!/usr/bin/env python3
"""
Quick script to check how many leads are in the database.
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.database_service import DatabaseService

def main():
    try:
        db = DatabaseService()
        
        # Get total count
        total = db.count_leads()
        
        # Get counts by status
        nuevo = db.count_leads(status='nuevo')
        contactado = db.count_leads(status='contactado')
        convertido = db.count_leads(status='convertido')
        rechazado = db.count_leads(status='rechazado')
        
        # Get counts by candidacy type
        congreso = db.count_leads(candidacy_type='congreso')
        regionales = db.count_leads(candidacy_type='regionales')
        presidencia = db.count_leads(candidacy_type='presidencia')
        
        print("\n" + "="*50)
        print("LEADS EN LA BASE DE DATOS")
        print("="*50)
        print(f"\n📊 TOTAL DE LEADS: {total}")
        
        print("\n📈 Por Estado:")
        print(f"  • Nuevo: {nuevo}")
        print(f"  • Contactado: {contactado}")
        print(f"  • Convertido: {convertido}")
        print(f"  • Rechazado: {rechazado}")
        
        print("\n🎯 Por Tipo de Candidatura:")
        print(f"  • Congreso: {congreso}")
        print(f"  • Regionales: {regionales}")
        print(f"  • Presidencia: {presidencia}")
        
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()



