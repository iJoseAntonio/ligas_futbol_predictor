import os
import sys
import pandas as pd
from sqlalchemy import create_engine, Integer

def migrate():
    # Pedir datos de conexión de forma interactiva
    print("=== MIGRACIÓN DE DATOS A RDS POSTGRESQL ===")
    host = input("1. Introduce el Endpoint de tu RDS (ej. xxxx.us-east-2.rds.amazonaws.com): ").strip()
    user = input("2. Introduce el Master username (default: postgres): ").strip() or "postgres"
    password = input("3. Introduce la contraseña maestra de tu RDS: ").strip()

    db_name = "postgres"  # RDS crea una base de datos por defecto llamada postgres
    port = 5432
    
    # Ruta del archivo CSV local
    csv_path = os.path.join(os.path.dirname(__file__), "data", "bd_liga1.csv")
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: No se encontró el archivo CSV en: {csv_path}")
        sys.exit(1)
        
    print(f"📖 Leyendo datos desde {csv_path}...")
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        print(f"✅ CSV cargado con éxito ({len(df)} partidos).")
    except Exception as e:
        print(f"❌ Error al leer el CSV: {e}")
        sys.exit(1)

    # Crear conexión de SQLAlchemy
    # postgresql://user:password@host:port/dbname
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    
    print("🔌 Conectando a la base de datos de AWS RDS...")
    try:
        engine = create_engine(connection_string)
        # Intentar conectar para verificar credenciales antes de subir
        with engine.connect() as conn:
            print("✅ Conexión establecida con éxito.")
            
        print("📤 Subiendo datos a la tabla 'partidos_liga1' (esto puede tardar unos segundos)...")
        # Subir el DataFrame a la tabla partidos_liga1
        df.to_sql("partidos_liga1", engine, if_exists="replace", index=False,
                  dtype={"goles_local": Integer, "goles_visitante": Integer})
        print("🎉 ¡DATOS MIGRADOS CON ÉXITO A POSTGRESQL EN RDS!")
        
    except Exception as e:
        print(f"\n❌ Error de conexión o escritura en la base de datos: {e}")
        print("\nVerifica si:")
        print("1. El Endpoint de RDS y la contraseña son correctos.")
        print("2. Ya habilitaste el acceso público (Publicly Accessible: Yes).")
        print("3. Las Reglas de Entrada (Inbound Rules) de tu Security Group en RDS permiten tráfico en el puerto 5432.")

if __name__ == "__main__":
    migrate()
