
import os
import sys
import importlib.util
import traceback
import json
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def get_all_py_files(root_dir):
    py_files = []
    for root, dirs, files in os.walk(root_dir):
        if "venv" in root or ".git" in root or "dist" in root or "build" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files

def test_imports(files):
    results = {"success": [], "failed": []}
    print(f"Testing imports for {len(files)} files...")
    
    for file_path in files:
        module_name = os.path.relpath(file_path, PROJECT_ROOT).replace(os.path.sep, ".").replace(".py", "")
        if module_name == "run_full_diagnostics": continue
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                # Just loading the module, not executing it fully if it has main block
                # However, for syntax check, we need to correct syntax
                with open(file_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), file_path, 'exec')
                
            results["success"].append(module_name)
        except SyntaxError as e:
            results["failed"].append({"module": module_name, "error": f"SyntaxError: {str(e)}", "file": file_path})
        except Exception as e:
            # We might catch ImportError here if we actually tried to load it, 
            # but strict compile only checks syntax. 
            # Let's try to actually import it to check dependencies too.
            try:
                importlib.import_module(module_name)
                results["success"].append(module_name)
            except Exception as import_err:
                 results["failed"].append({"module": module_name, "error": f"Import/Runtime Error: {str(import_err)}", "file": file_path})

    return results

def test_database():
    print("Testing Database Integrity...")
    try:
        from src.database import Database
        db = Database()
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in db.cursor.fetchall()]
        return {"status": "success", "tables": tables, "count": len(tables)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

def generated_report():
    files = get_all_py_files(PROJECT_ROOT)
    import_results = test_imports(files)
    db_results = test_database()
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_files": len(files),
        "syntax_check": {
            "passed": len(import_results["success"]),
            "failed": len(import_results["failed"]),
            "failures": import_results["failed"]
        },
        "database_check": db_results
    }
    
    with open("DIAGNOSTIC_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
        
    print("\n" + "="*50)
    print("DIAGNOSTIC REPORT SUMMARY")
    print("="*50)
    print(f"Total Files Scanned: {len(files)}")
    print(f"Syntax/Import Passed: {len(import_results['success'])}")
    print(f"Syntax/Import Failed: {len(import_results['failed'])}")
    
    if import_results["failed"]:
        print("\nFAILURES:")
        for fail in import_results["failed"]:
            print(f"- {fail['module']}: {fail['error']}")
            
    print("\nDATABASE STATUS:")
    if db_results["status"] == "success":
        print(f"Connection: OK")
        print(f"Tables Found: {db_results['count']}")
    else:
        print(f"Connection: FAILED ({db_results['error']})")
        
    print("="*50)
    print("Full report saved to DIAGNOSTIC_REPORT.json")

if __name__ == "__main__":
    generated_report()
