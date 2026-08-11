import os
import sqlite3  # ← ADD THIS!
from ingestion.auth import authenticate_google
from ingestion.metadata_db import get_relationship_db as get_metadata_db
from ingestion.processor import process_course
from googleapiclient.discovery import build

def main():
    # Force the working directory to the repo root so relative paths resolve consistently.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 60)
    print("📚 GCR-RAG: Step 3 - Process Files in Memory")
    print("=" * 60)
    
    # Authenticate
    print("\n🔐 Authenticating...")
    creds = authenticate_google()
    if not creds:
        print("❌ Authentication failed!")
        return
    
    print("✅ Authentication successful!")
    
    # Build services
    classroom_service = build('classroom', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Get courses
    print("\n📋 Fetching your courses...")
    courses = classroom_service.courses().list(pageSize=20).execute().get('courses', [])
    
    if not courses:
        print("❌ No courses found!")
        return
    
    print(f"✅ Found {len(courses)} courses:")
    for i, course in enumerate(courses, 1):
        print(f"   {i}. {course.get('name')}")
    
    # Menu
    print("\n" + "=" * 60)
    print("What would you like to do?")
    print("=" * 60)
    print("  1. Process ALL courses (new/modified files)")
    print("  2. Process a specific course")
    print("  3. Show database status")
    print("  4. Reset database")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    db = get_metadata_db()
    
    if choice == '1':
        print("\n🔄 Processing all courses...\n")
        total = {'new': 0, 'modified': 0, 'deleted': 0}
        
        for course in courses:
            result = process_course(
                course['id'], 
                course['name'], 
                drive_service, 
                classroom_service
            )
            total['new'] += result['new']
            total['modified'] += result['modified']
            total['deleted'] += result['deleted']
        
        print("\n" + "=" * 60)
        print(f"✅ Complete!")
        print(f"   🆕 New files processed: {total['new']}")
        print(f"   📝 Modified files processed: {total['modified']}")
        print(f"   🗑️ Deleted files removed: {total['deleted']}")
    
    elif choice == '2':
        print("\n📚 Available courses:")
        for i, course in enumerate(courses, 1):
            print(f"  {i}. {course.get('name')}")
        
        try:
            selection = int(input("\nSelect course number: ")) - 1
            if 0 <= selection < len(courses):
                course = courses[selection]
                result = process_course(
                    course['id'], 
                    course['name'], 
                    drive_service, 
                    classroom_service
                )
                print("\n" + "=" * 60)
                print(f"✅ Complete!")
                print(f"   🆕 New files: {result['new']}")
                print(f"   📝 Modified files: {result['modified']}")
                print(f"   🗑️ Deleted files: {result['deleted']}")
            else:
                print("❌ Invalid selection!")
        except ValueError:
            print("❌ Please enter a valid number!")
    
    elif choice == '3':
        stats = db.get_stats()
        print("\n📊 Database Status:")
        print(f"   Total files tracked: {stats['total_files']}")
        print(f"   Total courses: {stats['total_courses']}")
        
        # Show files by type - FIXED with proper import
        try:
            conn = sqlite3.connect('metadata.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT file_type, COUNT(*) 
                FROM documents 
                WHERE file_type IS NOT NULL AND file_type != ''
                GROUP BY file_type
            ''')
            by_type = cursor.fetchall()
            if by_type:
                print("   Files by type:")
                for file_type, count in by_type:
                    print(f"     - {file_type}: {count}")
            else:
                print("   Files by type: (no file types recorded yet)")
            conn.close()
        except Exception as e:
            print(f"   Could not get file types: {e}")
    
    elif choice == '4':
        confirm = input("\n⚠️ Delete ALL metadata? (y/n): ")
        if confirm.lower() == 'y':
            import shutil
            if os.path.exists('metadata.db'):
                shutil.copy('metadata.db', 'metadata.backup.db')
                print("💾 Backup saved: metadata.backup.db")
            db.reset()
            print("✅ Database reset!")
        else:
            print("❌ Reset cancelled")
    
    else:
        print("❌ Invalid choice!")

if __name__ == "__main__":
    main()