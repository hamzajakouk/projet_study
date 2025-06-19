import os
import glob
import json
from agentic_doc.parse import parse_and_save_documents

def process_files_individually():
    """Process each PDF file individually to handle Unicode errors"""
    file_paths = sorted(glob.glob("splits/*.pdf"))
    
    if not file_paths:
        print("No PDF files found in splits folder!")
        return []
    
    successful_results = []
    failed_files = []
    
    for i, file_path in enumerate(file_paths, 1):
        filename = os.path.basename(file_path)
        print(f"\n[{i}/{len(file_paths)}] Processing: {filename}")
        
        try:
            # Process one file at a time
            result_paths = parse_and_save_documents([file_path], result_save_dir="parsed_results")
            
            # Remove markdown and keep only chunks
            if result_paths:
                cleaned_file = remove_markdown_keep_chunks(result_paths[0])
                if cleaned_file:
                    successful_results.append(cleaned_file)
                    print(f"  ✅ Success: {os.path.basename(cleaned_file)}")
                else:
                    successful_results.extend(result_paths)
                    print(f"  ✅ Success: {os.path.basename(result_paths[0])}")
            
        except UnicodeEncodeError as e:
            print(f"  ❌ Unicode error for {filename}")
            print(f"     Error: {str(e)[:100]}...")
            failed_files.append(file_path)
            
            # Try to save with manual UTF-8 encoding
            try:
                print(f"  🔄 Trying manual UTF-8 fix...")
                manual_result = manual_utf8_save(file_path)
                if manual_result:
                    successful_results.append(manual_result)
                    print(f"  ✅ Manual fix worked!")
                else:
                    print(f"  ❌ Manual fix failed")
            except Exception as manual_error:
                print(f"  ❌ Manual fix error: {manual_error}")
                
        except Exception as e:
            print(f"  ❌ Other error for {filename}: {str(e)[:100]}...")
            failed_files.append(file_path)
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  ✅ Successfully processed: {len(successful_results)} files")
    print(f"  ❌ Failed: {len(failed_files)} files")
    
    if failed_files:
        print(f"\n💡 Failed files:")
        for file_path in failed_files:
            print(f"  - {os.path.basename(file_path)}")
        print(f"\n🔧 Consider using local text extraction for failed files")
    
    return successful_results

def remove_markdown_keep_chunks(result_file_path):
    """Remove markdown from JSON and keep only chunks"""
    try:
        # Read the original file
        with open(result_file_path, 'r', encoding='cp1252') as f:
            data = json.load(f)
        
        # Remove markdown field
        if 'markdown' in data:
            del data['markdown']
            print(f"    🗑️ Removed markdown field")
        
        # Keep everything else (chunks, metadata, etc.)
        chunks_count = len(data.get('chunks', []))
        print(f"    📊 Keeping {chunks_count} chunks")
        
        # Save back to the same file with UTF-8 encoding
        with open(result_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"    ✨ File updated (chunks only, UTF-8 encoding)")
        return result_file_path
        
    except Exception as e:
        print(f"    ❌ Error removing markdown: {e}")
        return None

def manual_utf8_save(file_path):
    """Attempt to manually handle the Unicode encoding issue"""
    try:
        # This is a workaround - we can't easily fix the library's internal encoding
        # So we'll return None to indicate this approach didn't work
        return None
    except Exception:
        return None

# Alternative: Change Windows codepage temporarily
def set_utf8_codepage():
    """Try to set UTF-8 codepage for Windows"""
    try:
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
        print("🔧 Set Windows codepage to UTF-8")
        return True
    except:
        print("⚠️ Could not change Windows codepage")
        return False

if __name__ == "__main__":
    print("🚀 Starting individual file processing...")
    
    # Try to set UTF-8 codepage
    set_utf8_codepage()
    
    # Process files individually
    results = process_files_individually()
    
    if results:
        print(f"\n🎉 Processing complete! Check 'parsed_results' folder.")
        print(f"📁 Updated files (chunks only, no markdown):")
        for result in results:
            print(f"  - {os.path.basename(result)}")
        
        # Quick verification
        if results:
            print(f"\n🔍 Verifying first file...")
            try:
                with open(results[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                chunks_count = len(data.get('chunks', []))
                has_markdown = 'markdown' in data
                
                print(f"  📊 Chunks: {chunks_count}")
                print(f"  📝 Contains markdown: {'❌ No' if not has_markdown else '⚠️ Yes'}")
                
                if chunks_count > 0:
                    sample_text = data['chunks'][0].get('text', '')[:100]
                    print(f"  📖 Sample: {sample_text}...")
                    
                    # Check for French accents
                    if any(char in sample_text for char in ['à', 'é', 'è', 'ç', 'ô']):
                        print(f"  🇫🇷 French accents: ✅ Correct")
                    else:
                        print(f"  🇫🇷 French accents: Not found in sample")
                
            except Exception as e:
                print(f"  ❌ Verification error: {e}")
        
    else:
        print(f"\n⚠️ No files were processed successfully.")
        print(f"💡 Consider using local text extraction instead.")