import sys
import os
import sqlite3
import shutil
from unittest.mock import patch

# Ensure the script can import modules from the current directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the database path to use a test database file
TEST_DB_PATH = "test_repro.db"

def run_test():
    # Remove existing test db
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Patch the DB_PATH in core.database.connection
    # We need to import it first
    from core.database import connection, schema
    
    # Patch the global variable in the module
    print(f"Original DB Path: {connection.DB_PATH}")
    connection.DB_PATH = TEST_DB_PATH
    print(f"Patched DB Path: {connection.DB_PATH}")

    # Initialize the database schema
    print("Initializing database schema...")
    try:
        schema.create_all_tables()
    except Exception as e:
        print(f"Schema creation failed (might be due to missing vector extension, but we can verify doc creation anyway): {e}")

    # Create dummy files
    print("Creating dummy files...")
    content = "This is a test document content."
    
    with open("test1.txt", "w", encoding="utf-8") as f:
        f.write(content)
        
    with open("test2.txt", "w", encoding="utf-8") as f:
        f.write(content) # Identical to test1
        
    with open("test3.txt", "w", encoding="utf-8") as f:
        f.write(content + " ") # Slightly different

    # Import ingestion module
    from core import ingestion_v3

    # We need to mock database.save_chunk_embedding because we might not have the vector extension loaded or working in this test env, 
    # and we only care about document creation/deduplication which happens before chunking/embedding.
    # Actually, ingestion_v3 calls database.create_document_enhanced BEFORE parsing/embedding.
    # But it continues to parse and embed. If embedding fails, it returns success=False?
    # No, it returns success=True but maybe with errors in chunks.
    # Let's mock the parsing/embedding to avoid errors and save time.
    
    with patch('core.ai_core.analyze_slide') as mock_analyze:
        mock_analyze.return_value = ("Summary", 100) # Mock AI response
        
        with patch('core.ai_core.get_embedding') as mock_embed:
            mock_embed.return_value = ([0.1]*1536, 100) # Mock embedding

            print("\n--- Processing text1.txt ---")
            # We need to prevent metadata extraction from failing or using real API
            # auto_extract_metadata=False for speed and isolation
            res1 = ingestion_v3.process_document_v3(
                "test1.txt", "Knowledge", 
                analysis_mode="text_only", 
                auto_extract_metadata=False
            )
            print(f"Result 1: {res1}")

            print("\n--- Processing text2.txt (Identical) ---")
            res2 = ingestion_v3.process_document_v3(
                "test2.txt", "Knowledge", 
                analysis_mode="text_only", 
                auto_extract_metadata=False
            )
            print(f"Result 2: {res2}")

            print("\n--- Processing text3.txt (Slightly different) ---")
            res3 = ingestion_v3.process_document_v3(
                "test3.txt", "Knowledge", 
                analysis_mode="text_only", 
                auto_extract_metadata=False
            )
            print(f"Result 3: {res3}")

            print("\n--- Analysis ---")
            if res1['doc_id'] == res2['doc_id']:
                print("PASS: Identical files return same doc_id.")
            else:
                print(f"FAIL: Identical files return DIFFERENT doc_ids ({res1['doc_id']} vs {res2['doc_id']}).")
                
            if res1['doc_id'] != res3['doc_id']:
                print("PASS: Different files return different doc_ids.")
            else:
                print("FAIL: Different files return SAME doc_id.")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except:
                pass
        for f in ["test1.txt", "test2.txt", "test3.txt"]:
            if os.path.exists(f):
                os.remove(f)
