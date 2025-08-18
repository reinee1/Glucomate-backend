import psycopg2
from urllib.parse import quote_plus

try:
    conn = psycopg2.connect(
        host="database-glucomate.cwt606ekoliv.us-east-1.rds.amazonaws.com",
        dbname="Glucomate_db",
        user="postgres",
        password="Glucomate123",
        connect_timeout=5  # Fail fast if unreachable
    )
    print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
finally:
    if 'conn' in locals():
        conn.close()