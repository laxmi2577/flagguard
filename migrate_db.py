"""Migrate database to add new columns and tables."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flagguard.db")
print(f"DB path: {db_path}")

if not os.path.exists(db_path):
    print("No DB found - will be created on next server start")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Add 'role' column to users table
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    print(f"Current user columns: {cols}")
    
    if "role" not in cols:
        cursor.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "viewer"')
        print("✅ Added 'role' column to users table")
    else:
        print("✅ 'role' column already exists")
    
    # 2. Add environment_id to scans table
    cursor.execute("PRAGMA table_info(scans)")
    scan_cols = [row[1] for row in cursor.fetchall()]
    if "environment_id" not in scan_cols:
        cursor.execute("ALTER TABLE scans ADD COLUMN environment_id TEXT")
        print("✅ Added 'environment_id' column to scans table")
    
    # 3. Create new tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS environments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            project_id TEXT REFERENCES projects(id),
            flag_overrides JSON DEFAULT '{}',
            description TEXT DEFAULT '',
            is_default BOOLEAN DEFAULT 0,
            created_at DATETIME
        )
    """)
    print("✅ Created 'environments' table")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhook_configs (
            id TEXT PRIMARY KEY,
            project_id TEXT REFERENCES projects(id),
            url TEXT NOT NULL,
            secret TEXT,
            events JSON DEFAULT '[]',
            is_active BOOLEAN DEFAULT 1,
            description TEXT DEFAULT '',
            created_at DATETIME
        )
    """)
    print("✅ Created 'webhook_configs' table")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            details JSON DEFAULT '{}',
            ip_address TEXT,
            created_at DATETIME
        )
    """)
    print("✅ Created 'audit_logs' table")
    
    conn.commit()
    conn.close()
    print("\n🎉 Migration complete! You can now login normally.")
