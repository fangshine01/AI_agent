
import logging
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.intent_router import router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_router():
    # Force refresh just in case
    router._refresh_cache()
    
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("\n=== Cache Inspection ===")
    print(f"Products ({len(router._products)}): {router._products}")
    print(f"Defects ({len(router._defects)}): {router._defects}")
    
    # Test Query
    test_queries = [
        "N706 在良率上的損失",
        "N706 良率損失",
        "N706 defect",
    ]
    
    print("\n=== Matching Logic Check ===")
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        query_upper = query.upper()
        
        matched_product = None
        for prod in router._products:
            if prod in query_upper:
                matched_product = prod
                print(f"  [MATCH] Product: '{prod}'")
        
        matched_defect = None
        for defect in router._defects:
            if defect in query_upper:
                matched_defect = defect
                print(f"  [MATCH] Defect: '{defect}'")
                
        if matched_product and matched_defect:
             print("  => RESULT: Exact Match Triggered!")
        else:
             print("  => RESULT: No Match")

if __name__ == "__main__":
    debug_router()
