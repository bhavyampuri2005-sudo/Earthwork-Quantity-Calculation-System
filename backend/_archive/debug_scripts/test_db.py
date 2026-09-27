from database import get_db

try:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT version();")
    version = cursor.fetchone()

    print("✅ PostgreSQL connected successfully!")
    print("Version:", version[0])

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Database connection failed!")
    print("Error:", e)
    
