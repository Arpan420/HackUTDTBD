#!/usr/bin/env python3
"""Test database connection and diagnose issues."""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import socket

# Add back_end/speech to path
project_root = Path(__file__).parent.parent
speech_path = project_root / "back_end" / "speech"
sys.path.insert(0, str(speech_path))

from dotenv import load_dotenv

load_dotenv()


def test_dns(hostname):
    """Test if hostname resolves."""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✓ DNS resolution successful: {hostname} → {ip}")
        return True
    except socket.gaierror as e:
        print(f"✗ DNS resolution failed: {e}")
        return False


def test_port(hostname, port):
    """Test if port is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()
        if result == 0:
            print(f"✓ Port {port} is reachable")
            return True
        else:
            print(f"✗ Port {port} is not reachable (connection refused)")
            return False
    except Exception as e:
        print(f"✗ Port test failed: {e}")
        return False


def main():
    """Main diagnostic function."""
    print("=" * 60)
    print("Database Connection Diagnostic")
    print("=" * 60)
    print()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return 1
    
    print(f"✓ Found DATABASE_URL")
    print()
    
    # Parse connection string
    try:
        parsed = urlparse(database_url)
        hostname = parsed.hostname
        port = parsed.port or 5432
        username = parsed.username
        database = parsed.path.lstrip('/')
        
        print("Connection Details:")
        print(f"  Hostname: {hostname}")
        print(f"  Port: {port}")
        print(f"  Username: {username}")
        print(f"  Database: {database}")
        print(f"  Has Password: {'Yes' if parsed.password else 'No'}")
        print()
        
        # Test DNS
        print("Testing DNS resolution...")
        dns_ok = test_dns(hostname)
        print()
        
        if not dns_ok:
            print("⚠️  DNS resolution failed. Possible issues:")
            print("  1. The project reference might be incorrect")
            print("  2. The Supabase project might be paused or deleted")
            print("  3. Check your Supabase dashboard for the correct connection string")
            print("  4. Verify the project is active (not paused)")
            print()
            return 1
        
        # Test port
        print("Testing port connectivity...")
        port_ok = test_port(hostname, port)
        print()
        
        if not port_ok:
            print("⚠️  Port is not reachable. Possible issues:")
            print("  1. Your IP might not be allowed in Supabase network restrictions")
            print("  2. Firewall might be blocking the connection")
            print("  3. Check Supabase Dashboard → Settings → Database → Network Restrictions")
            print()
            return 1
        
        # Try actual database connection
        print("Testing database connection...")
        try:
            from conversation.database import DatabaseManager
            db = DatabaseManager()
            print("✓ Database connection successful!")
            db.close()
            return 0
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            print()
            print("Possible issues:")
            print("  1. Password might be incorrect")
            print("  2. Database user permissions")
            print("  3. Check Supabase Dashboard for correct password")
            return 1
        
    except Exception as e:
        print(f"❌ Error parsing connection string: {e}")
        print()
        print("Connection string format should be:")
        print("  postgresql://postgres:password@db.project-ref.supabase.co:5432/postgres")
        return 1


if __name__ == "__main__":
    sys.exit(main())

