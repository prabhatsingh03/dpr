import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
import os
import sys

load_dotenv()

def get_db_connection():
    """
    Get a database connection from the pool.
    """
    try:
        # Check if pool exists, if not create it
        if not hasattr(get_db_connection, "pool"):
            dbconfig = {
                "host": os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "localhost")),
                "port": int(os.getenv("DB_PORT", os.getenv("MYSQL_PORT", 3306))),
                "database": os.getenv("DB_NAME", os.getenv("MYSQL_DATABASE", "dpr_database")),
                "user": os.getenv("DB_USER", os.getenv("MYSQL_USER", "root")),
                "password": os.getenv("DB_PASSWORD", os.getenv("MYSQL_PASSWORD", "")),
                "charset": "utf8mb4",
                "use_unicode": True,
            }
            try:
                get_db_connection.pool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name="dpr_pool",
                    pool_size=5,
                    **dbconfig
                )
            except mysql.connector.Error as err:
                 print(f"Error creating connection pool: {err}")
                 sys.exit(1)

        connection = get_db_connection.pool.get_connection()
        return connection
    except mysql.connector.Error as err:
        print(f"Error getting connection from pool: {err}")
        # If pool is exhausted or other error, try creating a direct connection as fallback or re-raise
        # For production, logging and maybe retry logic would be better.
        # But for now, let's propagate the error so the caller knows something is wrong.
        raise err
