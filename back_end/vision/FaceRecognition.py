import cv2
import os
import numpy as np
import insightface
from insightface.app import FaceAnalysis
import pickle
import uuid  # To create new unique identifiers

# --- Path Setup ---

# This is the directory this script is in:
# /.../HackUTDTBD/mobile_app
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# This is the project root:
# /.../HackUTDTBD
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# This is where your new frames are, as you specified:
# /.../HackUTDTBD/mobile_app/src/assets/tmp
TMP_PATH = os.path.join(SCRIPT_DIR,SCRIPT_DIR, "tmp")

# This is our "mock" database file, stored in the root
DB_PICKLE_FILE = os.path.join(PROJECT_ROOT, "face_database.pkl")

# This is where you can put "seed" images (e.g., "Srinivas.jpg")
# to build the first database.
LEGACY_IMG_DB = os.path.join(PROJECT_ROOT, "face_database")

# --- Global InsightFace App ---
print("Initializing InsightFace Model...")
APP = FaceAnalysis()
APP.prepare(ctx_id=-1)  # CPU
print("InsightFace Model Ready.")

# --- Match Threshold ---
# This is the "stiffness" of the match.
# Higher = stricter (e.g., 0.5). Lower = looser (e.g., 0.3).
MATCH_THRESHOLD = 0.45  # Cosine Similarity

def get_embedding_from_image(img_path):
    """Helper function to get a single embedding from an image path."""
    if not os.path.exists(img_path):
        print(f"--- ERROR: Image not found at {img_path} ---")
        return None
        
    img = cv2.imread(img_path)
    if img is None:
        print(f"--- ERROR: Could not read image {img_path} ---")
        return None
        
    faces = APP.get(img)
    if faces:
        return faces[0].embedding  # Return the first face found
    else:
        print(f"--- WARNING: No face detected in {img_path} ---")
        return None

def load_face_database():
    """
    Loads the face database from the .pkl file.
    If it doesn't exist, it builds it from the /face_database image folder.
    """
    if os.path.exists(DB_PICKLE_FILE):
        print(f"Loading fast database from: {DB_PICKLE_FILE}")
        with open(DB_PICKLE_FILE, 'rb') as f:
            database = pickle.load(f)
        return database
    else:
        print(f"Fast database not found. Building from images in: {LEGACY_IMG_DB}")
        database = {}
        if not os.path.exists(LEGACY_IMG_DB):
            print(f"--- WARNING: Image database folder not found at {LEGACY_IMG_DB} ---")
            print("--- Creating empty database. ---")
            return {}

        for filename in os.listdir(LEGACY_IMG_DB):
            if filename.lower().endswith((".jpg", ".png", ".jpeg")):
                # For this test, the "ID" is just the filename
                identifier = os.path.splitext(filename)[0]
                img_path = os.path.join(LEGACY_IMG_DB, filename)
                
                embedding = get_embedding_from_image(img_path)
                
                if embedding is not None:
                    print(f"Adding '{identifier}' to new database.")
                    database[identifier] = embedding
        
        save_face_database(database)
        return database

def save_face_database(database):
    """Saves the database dictionary to the .pkl file."""
    with open(DB_PICKLE_FILE, 'wb') as f:
        pickle.dump(database, f)
    print(f"\nDatabase saved with {len(database)} entries.")

def find_best_match(new_embedding, database):
    """Compares a new embedding to the database and finds the best match."""
    best_match_id = None
    best_score = -1  # Start at -1

    # Return early if database is empty
    if not database:
        return None, -1

    for identifier, db_embedding in database.items():
        score = np.dot(new_embedding, db_embedding) / (
            np.linalg.norm(new_embedding) * np.linalg.norm(db_embedding)
        )
        
        if score > best_score:
            best_score = score
            best_match_id = identifier
            
    return best_match_id, best_score

def analyze_and_update_db(image_path, database):
    """
    This is the core test function.
    It checks for a match and updates the database if no match is found.
    """
    print(f"--- Analyzing: {os.path.basename(image_path)} ---")
    
    # 1. Get embedding for the new image
    new_embedding = get_embedding_from_image(image_path)
    if new_embedding is None:
        print("-> STATUS: No face found. Skipping.")
        return {"status": "error", "message": "No face found"}
        
    # 2. Compare to database
    best_match_id, best_score = find_best_match(new_embedding, database)
    
    # 3. Decide: Match or New Person?
    
    # SCENARIO 1: IT'S A MATCH
    if best_match_id and best_score >= MATCH_THRESHOLD:
        print(f"-> STATUS: Match Found!")
        result = {
            "status": "match",
            "identifier": best_match_id,
            "similarity": float(best_score)
        }
        print(f"-> Returns: {result}")
        return result
        
    # SCENARIO 2: IT'S A NEW PERSON
    else:
        if best_match_id:
            print(f"-> STATUS: No match found. (Closest was {best_match_id} with score {best_score:.2f})")
        else:
            print("-> STATUS: No match found. (Database was empty)")

        # As requested: "makes a new unique identifier for the database"
        new_identifier = f"person_{uuid.uuid4().hex[:8]}"
        
        # "that matches the embedding returned as well"
        # We add the new person to the database in memory
        database[new_identifier] = new_embedding
        
        print(f"-> Action: Created new ID: {new_identifier}")
        
        result = {
            "status": "new",
            "identifier": new_identifier,
            "embedding": new_embedding
        }
        print(f"-> Returns: {{'status': 'new', 'identifier': '{new_identifier}'}}")
        return result


# --- This is the Main Test Runner ---
if __name__ == "__main__":
    
    # --- SETUP ---
    # 1. IMPORTANT: Delete your old "face_database.pkl" file
    #    in the HackUTDTBD/ folder to start this test fresh.
    #
    # 2. Make sure you have all your images in
    #    /HackUTDTBD/mobile_app/src/assets/tmp/
    # ---
    
    print("--- FULL TEST START ---")
    
    # 1. Load our "mock" database
    db = load_face_database()
    print(f"Database loaded with {len(db)} entries: {list(db.keys())}")
    
    # --- Find ALL test images ---
    try:
        all_tmp_files = [f for f in os.listdir(TMP_PATH) if f.lower().endswith('.jpg')]
        # Sort them to get a consistent order
        all_tmp_files.sort() 
        
        # --- THIS IS THE CHANGE ---
        # Get the full paths for ALL images, not just 15
        test_images = [os.path.join(TMP_PATH, f) for f in all_tmp_files]
        # ------------------------
        
        if len(test_images) == 0:
            raise FileNotFoundError("No .jpg files found.")
            
        print(f"\nFound {len(test_images)} images to test.")
        
    except Exception as e:
        print(f"\n--- FATAL ERROR ---")
        print(f"Could not find images in {TMP_PATH}. Error: {e}")
        print("Please add .jpg files to that folder to run the test.")
        print("-------------------\n")
        exit()

    # --- PHASE 1: ENROLLMENT PASS ---
    print("\n--- PHASE 1: ENROLLMENT PASS ---")
    print("Looping through all images. New faces will be enrolled.")
    print("--------------------------------")
    for image_file in test_images:
        analyze_and_update_db(image_file, db)
        print("...") # Add a small separator

    print("\n--- PHASE 1 COMPLETE ---")
    print(f"Database now contains {len(db)} entries: {list(db.keys())}")


    # --- PHASE 2: RECOGNITION PASS ---
    print("\n--- PHASE 2: RECOGNITION PASS ---")
    print("Looping through all images again. Should find matches now.")
    print("-----------------------------------")
    match_count = 0
    fail_count = 0
    for image_file in test_images:
        result = analyze_and_update_db(image_file, db)
        
        if result["status"] == "match":
            match_count += 1
        elif result["status"] != "error": # Don't count "no face found" as a fail
            fail_count += 1
        print("...") # Add a small separator

    print("\n--- PHASE 2 COMPLETE ---")
    print("--- TEST SUMMARY ---")
    print(f"Total images analyzed: {len(test_images)}")
    print(f"Successful matches:  {match_count}")
    print(f"New enrollments (unexpected): {fail_count}")
    print(f"(Note: 'No face found' errors are not counted in summary)")

    # 7. Save the final database
    save_face_database(db)
    print("--- FULL TEST COMPLETE ---")