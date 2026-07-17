import psycopg2

def get_db():
    print("Trying to connect...")
    
    conn = psycopg2.connect(
        host="localhost",
        database="earthwork_db",
        user="postgres",
        password="Bhavyam@123"
    )
    
    print("Connected!")
    return conn