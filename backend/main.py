import xml.etree.ElementTree as ET
import pandas as pd
import re
import uuid
import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import glob
import time
import atexit

# Define base directory (backend folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

# Create directories if they don't exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app = FastAPI(title="KML Pole Number Extractor")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tinashe-code.github.io",  # Your GitHub Pages URL (without trailing slash)
        "http://localhost:8000",           # For local testing
        "http://localhost:3000",           # For frontend development
        "*"                                # For testing - remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to parse KML
def parse_kml_points_to_df(kml_content: str) -> pd.DataFrame:
    """Parse KML content and extract placemarks with coordinates."""
    try:
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        root = ET.fromstring(kml_content)
        
        placemarks = root.findall('.//kml:Placemark', ns)
        data = []
        
        for placemark in placemarks:
            name_elem = placemark.find('kml:name', ns)
            coords_elem = placemark.find('.//kml:Point/kml:coordinates', ns)
            
            if name_elem is not None and coords_elem is not None:
                id_text = name_elem.text.strip() if name_elem.text else ""
                coords_text = coords_elem.text.strip()
                parts = coords_text.split(',')
                
                if len(parts) >= 2:
                    lon, lat = parts[0], parts[1]
                    data.append({
                        'ID': id_text,
                        'Latitude': float(lat),
                        'Longitude': float(lon)
                    })
        
        return pd.DataFrame(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing KML: {str(e)}")

# Function to extract pole numbers
def extract_number(id_str):
    """Extract integer from ID string following specific rules."""
    if pd.isna(id_str) or not isinstance(id_str, str):
        return 0
    
    id_str = str(id_str).strip().upper()
    
    if not id_str or id_str.replace(' ', '').isalpha():
        return 0
    
    # Split by space and check each part
    parts = id_str.split()
    
    for part in parts:
        digit_match = re.search(r'\d+', part)
        if digit_match:
            number_str = digit_match.group()
            return int(number_str.lstrip('0') or 0)
    
    # If no parts with digits, search entire string
    matches = re.findall(r'\d+', id_str)
    if matches:
        number_str = matches[0]
        return int(number_str.lstrip('0') or 0)
    
    return 0

# Main processing function
def process_kml_file(kml_content: str) -> Dict[str, Any]:
    """Process KML content and return results."""
    # Parse KML to DataFrame
    df = parse_kml_points_to_df(kml_content)
    
    if df.empty:
        raise HTTPException(status_code=400, detail="No valid placemarks found in KML file")
    
    # Extract numbers and sort
    df['number'] = df['ID'].apply(extract_number)
    df['formatted_ID'] = df.apply(
        lambda row: f'P{row["number"]}' if row["number"] > 0 else str(row["ID"]).strip().upper(), 
        axis=1
    )
    
    # Sort by number
    df = df.sort_values(by='number')
    
    # Find duplicates
    duplicated_df = df[df.duplicated(subset=['number'], keep=False)]
    duplicated_numbers = duplicated_df['number'].unique().tolist()
    
    # Filter out 0 from duplicates (non-numeric IDs)
    duplicated_numbers = [num for num in duplicated_numbers if num > 0]
    
    # Create response
    result = {
        "total_poles": len(df),
        "duplicate_numbers": duplicated_numbers,
        "duplicate_count": len(duplicated_numbers),
        "sample_data": df.head(10).to_dict('records')
    }
    
    return df, result

# @app.get("/", response_class=HTMLResponse)
# async def get_upload_page():
#     """Serve the HTML upload page."""
#     # Try multiple locations for index.html
#     possible_paths = [
#         os.path.join(TEMPLATES_DIR, "index.html"),  # backend/templates/index.html
#         os.path.join(BASE_DIR, "index.html"),       # backend/index.html
#         os.path(DOCS_DIR, "index.html"),       # backend/docs/index.html
#         "index.html"                                 # Current directory
#     ]
    
#     html_content = "<h1>KML Pole Number Extractor API is running</h1><p>Use the frontend at <a href='https://tinashe-code.github.io/KMLverification/'>GitHub Pages</a></p>"
    
#     for path in possible_paths:
#         if os.path.exists(path):
#             try:
#                 with open(path, "r") as f:
#                     html_content = f.read()
#                 break
#             except Exception:
#                 continue
    
#     return HTMLResponse(content=html_content)

@app.get("/", response_class=HTMLResponse)
async def get_upload_page():
    """Serve a simple API info page."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KML Pole Number Extractor API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #333; }
            .card { background: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .endpoint { background: #e8f4f8; padding: 10px; margin: 10px 0; border-left: 4px solid #2196F3; }
            code { background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
            a { color: #2196F3; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 KML Pole Number Extractor API</h1>
            <p>This is the backend API for processing KML files and extracting pole numbers.</p>
            
            <div class="card">
                <h2>API Endpoints:</h2>
                <div class="endpoint">
                    <strong>GET /health</strong> - Health check endpoint
                </div>
                <div class="endpoint">
                    <strong>POST /upload-kml/</strong> - Upload and process KML file
                </div>
                <div class="endpoint">
                    <strong>GET /download-csv/{filename}</strong> - Download processed CSV
                </div>
            </div>
            
            <div class="card">
                <h2>Frontend:</h2>
                <p>Use the frontend application at:</p>
                <p><a href="https://tinashe-code.github.io/KMLverification/" target="_blank">
                    https://tinashe-code.github.io/KMLverification/
                </a></p>
            </div>
            
            <div class="card">
                <h2>Status:</h2>
                <p>✅ API is running and ready to process requests.</p>
                <p>📁 Uploads directory: <code>backend/uploads/</code></p>
                <p>📁 Processed directory: <code>backend/processed/</code></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "KML Pole Number Extractor"}

@app.post("/upload-kml/")
async def upload_kml(file: UploadFile = File(...)):
    """Handle KML file upload and processing."""
    if not file.filename.lower().endswith('.kml'):
        raise HTTPException(status_code=400, detail="File must be a KML file (.kml extension)")
    
    try:
        # Read the uploaded file
        content = await file.read()
        
        # Try multiple encodings
        try:
            kml_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                kml_content = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                try:
                    kml_content = content.decode('latin-1')
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid file encoding. Please upload a UTF-8 encoded KML file.")
        
        # Process the KML
        df, result = process_kml_file(kml_content)
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        csv_filename = f"pole_data_{file_id}.csv"
        csv_path = os.path.join(PROCESSED_DIR, csv_filename)
        
        # Save CSV
        df.to_csv(csv_path, index=False)
        
        # Return processing results
        return JSONResponse({
            "message": "File processed successfully",
            "csv_filename": csv_filename,
            "processing_results": result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error processing file: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@app.get("/download-csv/{filename}")
async def download_csv(filename: str):
    """Download the processed CSV file."""
    # Security: Only allow filenames with expected pattern
    if not filename.startswith("pole_data_") or not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join(PROCESSED_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=f"pole_data_processed.csv",
        media_type='text/csv'
    )

# Cleanup function
def cleanup_old_files():
    """Remove files older than 1 hour."""
    try:
        for folder in [UPLOADS_DIR, PROCESSED_DIR]:
            if os.path.exists(folder):
                for file in glob.glob(os.path.join(folder, "*")):
                    try:
                        if os.path.getmtime(file) < time.time() - 3600:  # 1 hour
                            os.remove(file)
                    except:
                        continue
    except:
        pass

# Register cleanup on exit
atexit.register(cleanup_old_files)

# For Render deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)











# import xml.etree.ElementTree as ET
# import pandas as pd
# import re
# import uuid
# import os
# from fastapi import FastAPI, File, UploadFile, HTTPException
# from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from typing import List, Dict, Any
# import tempfile
# import shutil

# app = FastAPI(title="KML Pole Number Extractor")

# from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI(title="KML Pole Number Extractor")

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "https://tinashe-code.github.io/KMLverification/",  # Your GitHub Pages URL
#         "http://localhost:8000",  # For local testing
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# # Create directories if they don't exist
# os.makedirs("uploads", exist_ok=True)
# os.makedirs("processed", exist_ok=True)

# # Function to parse KML
# def parse_kml_points_to_df(kml_content: str) -> pd.DataFrame:
#     """Parse KML content and extract placemarks with coordinates."""
#     try:
#         ns = {'kml': 'http://www.opengis.net/kml/2.2'}
#         root = ET.fromstring(kml_content)
        
#         placemarks = root.findall('.//kml:Placemark', ns)
#         data = []
        
#         for placemark in placemarks:
#             name_elem = placemark.find('kml:name', ns)
#             coords_elem = placemark.find('.//kml:Point/kml:coordinates', ns)
            
#             if name_elem is not None and coords_elem is not None:
#                 id_text = name_elem.text.strip() if name_elem.text else ""
#                 coords_text = coords_elem.text.strip()
#                 parts = coords_text.split(',')
                
#                 if len(parts) >= 2:
#                     lon, lat = parts[0], parts[1]
#                     data.append({
#                         'ID': id_text,
#                         'Latitude': float(lat),
#                         'Longitude': float(lon)
#                     })
        
#         return pd.DataFrame(data)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Error parsing KML: {str(e)}")

# # Function to extract pole numbers
# def extract_number(id_str):
#     """Extract integer from ID string following specific rules."""
#     if pd.isna(id_str) or not isinstance(id_str, str):
#         return 0
    
#     id_str = str(id_str).strip().upper()
    
#     if not id_str or id_str.replace(' ', '').isalpha():
#         return 0
    
#     # Split by space and check each part
#     parts = id_str.split()
    
#     for part in parts:
#         digit_match = re.search(r'\d+', part)
#         if digit_match:
#             number_str = digit_match.group()
#             return int(number_str.lstrip('0') or 0)
    
#     # If no parts with digits, search entire string
#     matches = re.findall(r'\d+', id_str)
#     if matches:
#         number_str = matches[0]
#         return int(number_str.lstrip('0') or 0)
    
#     return 0

# # Main processing function
# def process_kml_file(kml_content: str) -> Dict[str, Any]:
#     """Process KML content and return results."""
#     # Parse KML to DataFrame
#     df = parse_kml_points_to_df(kml_content)
    
#     if df.empty:
#         raise HTTPException(status_code=400, detail="No valid placemarks found in KML file")
    
#     # Extract numbers and sort
#     df['number'] = df['ID'].apply(extract_number)
#     df['formatted_ID'] = df.apply(
#         lambda row: f'P{row["number"]}' if row["number"] > 0 else str(row["ID"]).strip().upper(), 
#         axis=1
#     )
    
#     # Sort by number
#     df = df.sort_values(by='number')
    
#     # Find duplicates
#     duplicated_df = df[df.duplicated(subset=['number'], keep=False)]
#     duplicated_numbers = duplicated_df['number'].unique().tolist()
    
#     # Filter out 0 from duplicates (non-numeric IDs)
#     duplicated_numbers = [num for num in duplicated_numbers if num > 0]
    
#     # Create response
#     result = {
#         "total_poles": len(df),
#         "duplicate_numbers": duplicated_numbers,
#         "duplicate_count": len(duplicated_numbers),
#         "sample_data": df.head(10).to_dict('records')
#     }
    
#     return df, result

# @app.get("/", response_class=HTMLResponse)
# async def get_upload_page():
#     """Serve the HTML upload page."""
#     with open("index.html", "r") as f:
#         html_content = f.read()
#     return HTMLResponse(content=html_content)

# @app.post("/upload-kml/")
# async def upload_kml(file: UploadFile = File(...)):
#     """Handle KML file upload and processing."""
#     if not file.filename.endswith('.kml'):
#         raise HTTPException(status_code=400, detail="File must be a KML file")
    
#     try:
#         # Read the uploaded file
#         content = await file.read()
#         kml_content = content.decode('utf-8')
        
#         # Process the KML
#         df, result = process_kml_file(kml_content)
        
#         # Generate unique filename
#         file_id = str(uuid.uuid4())
#         csv_filename = f"pole_data_{file_id}.csv"
#         csv_path = os.path.join("processed", csv_filename)
        
#         # Save CSV
#         df.to_csv(csv_path, index=False)
        
#         # Return processing results
#         return JSONResponse({
#             "message": "File processed successfully",
#             "csv_filename": csv_filename,
#             "processing_results": result
#         })
        
#     except UnicodeDecodeError:
#         raise HTTPException(status_code=400, detail="Invalid file encoding. Please upload a UTF-8 encoded KML file.")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# @app.get("/download-csv/{filename}")
# async def download_csv(filename: str):
#     """Download the processed CSV file."""
#     file_path = os.path.join("processed", filename)
    
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found")
    
#     return FileResponse(
#         path=file_path,
#         filename=f"pole_data_processed.csv",
#         media_type='text/csv'
#     )

# # Cleanup old files periodically (optional)
# import atexit
# import glob
# import time

# def cleanup_old_files():
#     """Remove files older than 1 hour."""
#     try:
#         for folder in ["uploads", "processed"]:
#             if os.path.exists(folder):
#                 for file in glob.glob(os.path.join(folder, "*")):
#                     if os.path.getmtime(file) < time.time() - 3600:  # 1 hour
#                         os.remove(file)
#     except:
#         pass

# atexit.register(cleanup_old_files)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)