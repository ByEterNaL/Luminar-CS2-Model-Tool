import os
import shutil
import zipfile
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from blender_processor import process_model

app = FastAPI(title="Luminar CS2 Modding Tool API")

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(os.path.dirname(BASE_DIR), "temp_models")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

os.makedirs(TEMP_DIR, exist_ok=True)


def find_model_in_dir(directory: str) -> str:
    """Klasör içinde desteklenen bir 3D model dosyası arar."""
    allowed = ('.mdl', '.fbx', '.obj', '.smd')
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(allowed):
                return os.path.join(root, file)
    return None

@app.post("/api/upload")
async def upload_model(file: UploadFile = File(...)):
    """
    Kullanıcıdan model veya zip dosyasını alır. Zip ise çıkartıp modeli bulur.
    Sonra Blender ile işleyip GLB formatına çevirir ve URL'ini döner.
    """
    allowed_extensions = (".mdl", ".fbx", ".obj", ".smd", ".zip")
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Desteklenmeyen dosya türü: {file_ext}. Sadece mdl, fbx, obj, smd veya zip.")

    # Çakışmayı önlemek için geçici dosyayı benzersiz adla kaydet
    input_filepath = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{file_ext}")
    extracted_dir = None
    
    try:
        with open(input_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        model_to_process = input_filepath
        
        # Eğer yüklenen bir ZIP arşivi ise
        if file_ext == ".zip":
            extracted_dir = os.path.join(TEMP_DIR, uuid.uuid4().hex)
            os.makedirs(extracted_dir, exist_ok=True)
            with zipfile.ZipFile(input_filepath, 'r') as zip_ref:
                zip_ref.extractall(extracted_dir)
                
            found_model = find_model_in_dir(extracted_dir)
            if not found_model:
                raise HTTPException(status_code=400, detail="Zip arşivi içinde desteklenen bir 3D model (mdl, fbx, obj, smd) bulunamadı.")
            
            model_to_process = found_model
            print(f"[Bilgi] Zip içinden model bulundu: {found_model}")
            
        # Blender ile işle
        print(f"[Bilgi] Model işleniyor: {model_to_process}")
        glb_filename = process_model(model_to_process, TEMP_DIR)
        print(f"[Bilgi] Başarıyla dışa aktarıldı: {glb_filename}")
        
        return JSONResponse(content={
            "message": "Model başarıyla işlendi.",
            "modelUrl": f"/models/{glb_filename}"
        })
        
    except Exception as e:
        print(f"[Hata] API upload hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # İşi biten geçici dosyaları (orijinal zip, çıkarılan klasör vb.) temizle
        if os.path.exists(input_filepath):
            try: os.remove(input_filepath)
            except: pass
        if extracted_dir and os.path.exists(extracted_dir):
            try: 
                shutil.rmtree(extracted_dir)
            except: pass

from pydantic import BaseModel
from fastapi.responses import FileResponse
from source2_generator import generate_source2_project

class CompileRequest(BaseModel):
    filename: str

@app.post("/api/compile")
async def compile_model(request: CompileRequest):
    try:
        if not request.filename or not request.filename.endswith('.fbx'):
            raise HTTPException(status_code=400, detail="Geçersiz dosya adı.")
            
        zip_path = generate_source2_project(TEMP_DIR, request.filename)
        
        if os.path.exists(zip_path):
            return FileResponse(zip_path, media_type="application/zip", filename=os.path.basename(zip_path))
        else:
            raise HTTPException(status_code=500, detail="ZIP dosyası oluşturulamadı.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Statik dosyaları sunmak (Frontend ve geçici glb dosyaları) - ROUTING SIRASI ÖNEMLİDİR, EN ALTTA OLMALI
app.mount("/models", StaticFiles(directory=TEMP_DIR), name="models")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
