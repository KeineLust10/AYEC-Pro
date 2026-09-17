import os
import sys
import subprocess

def read_file(filepath):
    """Reads a file and returns its content wrapped in markdown code blocks."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            ext = os.path.splitext(filepath)[1][1:] # get extension without dot
            return f"\\n# File: {filepath}\\n```{ext}\\n{content}\\n```\\n"
    except Exception as e:
        return f"\\n# File: {filepath}\\nError reading file: {e}\\n"

def copy_to_clipboard(text):
    """Copies text to clipboard using Windows 'clip' command."""
    try:
        process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, close_fds=True)
        process.communicate(input=text.encode('utf-16')) # clip expects utf-16 usually on some systems or just simple encoding
        print("[SUCCESS] Context copied to clipboard!")
    except Exception as e:
        print(f"[ERROR] Could not copy to clipboard: {e}")
        print("Here is the content (you can select and copy):")
        print(text)

def main():
    if len(sys.argv) < 2:
        print("Usage: python prepare_context.py <file1> <file2> ...")
        sys.exit(1)

    files = sys.argv[1:]
    combined_context = "# Context for Claude Code\\n"
    
    print(f"Processing {len(files)} files...")
    
    for file in files:
        if os.path.exists(file):
            combined_context += read_file(file)
        else:
            print(f"❌ File not found: {file}")
            combined_context += f"\\n# File: {file}\\n(File not found)\\n"

    copy_to_clipboard(combined_context)

if __name__ == "__main__":
    main()
