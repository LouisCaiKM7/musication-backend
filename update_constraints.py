"""
Update database constraints to support new analysis methods and statuses.
Run this script to update the database without losing data.
"""
from sqlalchemy import text
from database import engine

def update_constraints():
    """Drop and recreate check constraints with updated values."""
    
    print("Updating database constraints...")
    
    with engine.begin() as conn:
        try:
            # Drop old constraints
            print("1. Dropping old analyses.method constraint...")
            conn.execute(text(
                "ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_method_check"
            ))
            
            print("2. Dropping old analyses.status constraint...")
            conn.execute(text(
                "ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_status_check"
            ))
            
            print("3. Dropping old artifacts.artifact_type constraint...")
            conn.execute(text(
                "ALTER TABLE artifacts DROP CONSTRAINT IF EXISTS artifacts_type_check"
            ))
            
            # Add new constraints with updated values
            print("4. Adding updated analyses.method constraint...")
            conn.execute(text(
                "ALTER TABLE analyses ADD CONSTRAINT analyses_method_check "
                "CHECK (method IN ('chromaprint','hpcp','dtw','lyrics','music_identification','similarity_detection','other'))"
            ))
            
            print("5. Adding updated analyses.status constraint...")
            conn.execute(text(
                "ALTER TABLE analyses ADD CONSTRAINT analyses_status_check "
                "CHECK (status IN ('pending','processing','running','completed','succeeded','failed'))"
            ))
            
            print("6. Adding updated artifacts.artifact_type constraint...")
            conn.execute(text(
                "ALTER TABLE artifacts ADD CONSTRAINT artifacts_type_check "
                "CHECK (artifact_type IN ('chromaprint','hpcp','dtw_matrix','dtw_path','plot_image','feature_json','music_matches','other'))"
            ))
            
            print("✅ Database constraints updated successfully!")
            
        except Exception as e:
            print(f"❌ Error updating constraints: {e}")
            raise

if __name__ == "__main__":
    update_constraints()
