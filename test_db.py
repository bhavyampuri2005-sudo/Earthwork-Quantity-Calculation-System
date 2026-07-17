import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="earthwork_db",
        user="postgres",
        password="Bhavyam@123"
    )
    print("PostgreSQL connected successfully!")
    conn.close()

except Exception as e:
    print("ERROR:", e)