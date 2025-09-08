import os
import getpass
import pymysql
from typing import Optional

def _ask(prompt: str, default: Optional[str] = None, required: bool = True) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        val = input(f"{prompt}{suffix}: ").strip()
        if val:
            return val
        if default is not None:
            return default
        if not required:
            return ""
        print("This value is required.")

def connect():
    """
    Prompts for MySQL details and returns a live PyMySQL connection.
    """
    host = _ask("Host (Aiven hostname or IP)")
    # Aiven often uses a custom port; default to 3306 if unsure.
    while True:
        port_str = _ask("Port", "3306")
        try:
            port = int(port_str)
            break
        except ValueError:
            print("Port must be an integer.")

    user = _ask("User")
    password = getpass.getpass("Password: ")
    dbname = _ask("Database name")

    
    ca_path = _ask("Path to CA certificate (press Enter if not using SSL)", default="", required=False)
    ssl_args = None
    if ca_path:
        if not os.path.isfile(ca_path):
            raise FileNotFoundError(f"CA file not found: {ca_path}")
        ssl_args = {"ca": ca_path}

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=dbname,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        ssl=ssl_args,  
    )

if __name__ == "__main__":
    try:
        conn = connect()
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version_row = cur.fetchone()
            cur.execute("SELECT DATABASE()")
            db_row = cur.fetchone()
            cur.execute("SHOW STATUS LIKE 'Ssl_cipher'")
            ssl_row = cur.fetchone()

        
        version = next(iter(version_row.values()))
        current_db = next(iter(db_row.values()))
        ssl_cipher = ssl_row.get("Value") if ssl_row else ""

        print("\n✅ Connected successfully!")
        print(f"   Server version : {version}")
        print(f"   Database       : {current_db}")
        print(f"   SSL            : {'ENABLED (' + ssl_cipher + ')' if ssl_cipher else 'not requested or not negotiated'}")

    except Exception as e:
        print("\n❌ Connection failed.")
        print(f"   Error: {e}")
        print("   Hints:")
        print("   - Check host/port/user/password/database.")
        print("   - For Aiven/remote, provide a valid CA file path.")
        print("   - Ensure your IP is allowed (Aiven allowlist / firewall).")
        # raise  # uncomment if you want a non-zero exit for CI
