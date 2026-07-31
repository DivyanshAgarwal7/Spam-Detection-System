import os
import sqlite3
import threading
import time
from pathlib import Path
import pytest

from email_connectors import imap_store

def test_sqlite_concurrency_and_configuration(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_concurrency.db")
    
    # Monkeypatch DB_PATH to verify application's initialization path
    monkeypatch.setattr(imap_store, "DB_PATH", db_path)
    
    # 1. Verify WAL mode via application initialization
    imap_store.init_db()
    
    conn1 = None
    try:
        conn1 = imap_store.get_db_connection(db_path)
        journal_mode = conn1.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode.lower() == "wal", f"Expected WAL mode, got {journal_mode}"
        
        # 2. Assert busy_timeout configuration
        busy_timeout = conn1.execute("PRAGMA busy_timeout").fetchone()[0]
        assert int(busy_timeout) == 5000, f"Expected busy_timeout 5000, got {busy_timeout}"
        
        # Ensure a table exists to write to
        conn1.execute("CREATE TABLE IF NOT EXISTS test_lock (id INTEGER PRIMARY KEY, val TEXT)")
        conn1.commit()
    finally:
        if conn1:
            conn1.close()

    # 3. Test transient lock contention with threading.Event
    lock_acquired = threading.Event()
    
    bg_error = []
    
    def background_writer():
        conn2 = None
        try:
            conn2 = imap_store.get_db_connection(db_path)
            # Begin an exclusive transaction to lock the database
            conn2.execute("BEGIN EXCLUSIVE")
            lock_acquired.set()
            
            # Hold the lock for 1 second, simulating a concurrent write operation
            time.sleep(1)
            conn2.execute("INSERT INTO test_lock (val) VALUES ('bg')")
            conn2.commit()
        except Exception as e:
            bg_error.append(e)
        finally:
            if conn2:
                try:
                    conn2.close()
                except:
                    pass
                
    bg_thread = threading.Thread(target=background_writer)
    bg_thread.start()
    
    # Wait for background thread to actually acquire the lock
    lock_acquired.wait(timeout=5)
    assert lock_acquired.is_set(), "Background thread failed to acquire lock"
    
    # Main thread: try to write. The background thread holds the lock for 1 second.
    # Our busy_timeout is 5 seconds (5000ms), so this should wait and succeed.
    main_error = None
    conn3 = None
    start_time = time.time()
    try:
        conn3 = imap_store.get_db_connection(db_path)
        conn3.execute("INSERT INTO test_lock (val) VALUES ('main')")
        conn3.commit()
    except Exception as e:
        main_error = e
    finally:
        if conn3:
            conn3.close()
            
    elapsed = time.time() - start_time
            
    bg_thread.join(timeout=5)
    
    assert not bg_error, f"Background thread raised error: {bg_error[0]}"
    assert main_error is None, f"Main thread failed with error: {main_error}"
    
    # The main thread should have been blocked for at least some fraction of a second
    assert elapsed >= 0.5, f"Expected main thread to block, but took {elapsed}s"
