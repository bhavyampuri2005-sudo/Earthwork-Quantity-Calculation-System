import os
import psycopg2

def get_db():
    print("Trying to connect...")
    
    conn = psycopg2.connect(
        host="localhost",
        database="earthwork_db",
        user="postgres",
        password=os.environ.get("DB_PASSWORD", "")
    )
    
    print("Connected!")
    return conn