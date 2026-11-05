import os
import zipfile

def generate_source2_project(temp_dir: str, base_filename: str):
    """
    FBX dosyasından VMDL ve VMAT dosyaları üretir ve bir ZIP içerisine paketler.
    :param temp_dir: Dosyaların bulunduğu klasör (ör. temp_models)
    :param base_filename: model_uuid.fbx tarzı dosya adı
    """
    fbx_name = os.path.basename(base_filename)
    model_name = fbx_name.replace('.fbx', '')
    
    # Dosya yolları
    fbx_path = os.path.join(temp_dir, fbx_name)
    vmdl_path = os.path.join(temp_dir, f"{model_name}.vmdl")
    zip_path = os.path.join(temp_dir, f"{model_name}_cs2_project.zip")
    mat_txt_path = os.path.join(temp_dir, f"{model_name}_materials.txt")
    
    # Basit bir VMAT Şablonu (CSGO Complex)
    vmat_content_template = """<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->
{
	shader = "csgo_complex.vfx"
	F_PAINT_VERTEX_COLORS = 1
    
	TextureColor = "materials/default/default_color.tga"
	TextureNormal = "materials/default/default_normal.tga"
	TextureAmbientOcclusion = "materials/default/default_ao.tga"
	TextureRoughness = "materials/default/default_rough.tga"
}
"""

    # Basit bir VMDL Şablonu
    vmdl_content = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc36:version{{972dada4-b828-45a4-bb93-7795cf0585da}} -->
{{
	rootNode = 
	{{
		_class = "RootNode"
		children = 
		[
			{{
				_class = "RenderMeshList"
				children = 
				[
					{{
						_class = "RenderMeshFile"
						name = "{model_name}"
						filename = "models/{model_name}/{fbx_name}"
						import_translation = [ 0.0, 0.0, 0.0 ]
						import_rotation = [ 0.0, 0.0, 0.0 ]
						import_scale = 1.0
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						parent_bone = ""
						import_filter = 
						{{
							exclude_by_default = false
							exception_list = [  ]
						}}
					}},
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
	}}
}}
"""
    
    with open(vmdl_path, "w", encoding="utf-8") as f:
        f.write(vmdl_content)
        
    # Materyalleri JSON'dan Oku ve Yaz
    import json
    mat_json_path = os.path.join(temp_dir, f"{model_name}_materials.json")
    
    materials_data = {"material": {}} # Default fallback
    if os.path.exists(mat_json_path):
        with open(mat_json_path, "r", encoding="utf-8") as f:
            materials_data = json.load(f)
            
    vmat_files = []
    image_files_to_copy = [] # [(src_absolute, target_filename), ...]
    
    for mat_name, textures in materials_data.items():
        mat_safe = "".join(c if c.isalnum() else "_" for c in mat_name).lower()
        vmat_p = os.path.join(temp_dir, f"{mat_safe}.vmat")
        
        # CS2 Workshop varsayılan boş dokuları
        color_path = "materials/default/default_color.tga"
        normal_path = "materials/default/default_normal.tga"
        rough_path = "materials/default/default_rough.tga"
        
        # JSON'dan gelen resimler varsa oyun içi yolları oluştur
        if "Color" in textures and os.path.exists(textures["Color"]):
            ext = os.path.splitext(textures["Color"])[1].lower()
            target_name = f"{mat_safe}_color{ext}"
            color_path = f"materials/models/{model_name}/{target_name}"
            image_files_to_copy.append((textures["Color"], target_name))
            
        if "Normal" in textures and os.path.exists(textures["Normal"]):
            ext = os.path.splitext(textures["Normal"])[1].lower()
            target_name = f"{mat_safe}_normal{ext}"
            normal_path = f"materials/models/{model_name}/{target_name}"
            image_files_to_copy.append((textures["Normal"], target_name))
            
        if "Roughness" in textures and os.path.exists(textures["Roughness"]):
            ext = os.path.splitext(textures["Roughness"])[1].lower()
            target_name = f"{mat_safe}_rough{ext}"
            rough_path = f"materials/models/{model_name}/{target_name}"
            image_files_to_copy.append((textures["Roughness"], target_name))
            
        vmat_content = f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:generic:version{{7412167c-06e9-4698-aff2-e63eb59037e7}} -->
{{
	shader = "csgo_complex.vfx"
	F_PAINT_VERTEX_COLORS = 1
    
	TextureColor = "{color_path}"
	TextureNormal = "{normal_path}"
	TextureAmbientOcclusion = "materials/default/default_ao.tga"
	TextureRoughness = "{rough_path}"
}}
"""
        vmat_files.append((vmat_p, f"{mat_safe}.vmat"))
        with open(vmat_p, "w", encoding="utf-8") as f:
            f.write(vmat_content)
        
    # === OTONOM DERLEME SÜRECİ (CS2 WORKSHOP TOOLS) ===
    import subprocess
    import shutil
    
    cs2_base = r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive"
    compiler_exe = os.path.join(cs2_base, "game", "bin", "win64", "resourcecompiler.exe")
    
    is_compiled = False
    
    if os.path.exists(compiler_exe):
        addon_name = "luminar_tmp"
        content_models_dir = os.path.join(cs2_base, "content", "csgo_addons", addon_name, "models", model_name)
        game_models_dir = os.path.join(cs2_base, "game", "csgo_addons", addon_name, "models", model_name)
        
        content_materials_dir = os.path.join(cs2_base, "content", "csgo_addons", addon_name, "materials", "models", model_name)
        
        os.makedirs(content_models_dir, exist_ok=True)
        os.makedirs(content_materials_dir, exist_ok=True)
        
        c_fbx_path = os.path.join(content_models_dir, fbx_name)
        c_vmdl_path = os.path.join(content_models_dir, f"{model_name}.vmdl")
        
        packed_textures_dir = os.path.join(content_models_dir, "textures", "packed")
        os.makedirs(packed_textures_dir, exist_ok=True)
        
        if os.path.exists(fbx_path):
            shutil.copy2(fbx_path, c_fbx_path)
        shutil.copy2(vmdl_path, c_vmdl_path)
        
        for vmat_path_abs, vmat_name in vmat_files:
            shutil.copy2(vmat_path_abs, os.path.join(packed_textures_dir, vmat_name))
            
        # Resim (Texture) dosyalarını CS2 klasörüne kopyala
        for src_img, target_name in image_files_to_copy:
            shutil.copy2(src_img, os.path.join(content_materials_dir, target_name))
        
        # resourcecompiler.exe çalıştır
        print(f"[Bilgi] CS2 Compiler çalıştırılıyor: {c_vmdl_path}")
        try:
            result = subprocess.run([compiler_exe, "-i", c_vmdl_path], capture_output=True, text=True, check=True)
            print("[Bilgi] Derleme başarılı!")
            is_compiled = True
        except subprocess.CalledProcessError as e:
            print(f"[Hata] Derleme başarısız:\n{e.stdout}\n{e.stderr}")
            
    # ZIP içine al
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if is_compiled:
            # Ana klasör adı (kullanıcının sürükleyip bırakacağı klasör)
            root_folder = f"CustomWeapon_{model_name}"
            
            # Compiled dosyaları ekle
            compiled_vmdl = os.path.join(game_models_dir, f"{model_name}.vmdl_c")
            if os.path.exists(compiled_vmdl):
                zipf.write(compiled_vmdl, f"{root_folder}/models/{model_name}/{model_name}.vmdl_c")
                
            game_packed_dir = os.path.join(game_models_dir, "textures", "packed")
            for _, vmat_name in vmat_files:
                compiled_vmat = os.path.join(game_packed_dir, vmat_name + "_c")
                if os.path.exists(compiled_vmat):
                    zipf.write(compiled_vmat, f"{root_folder}/models/{model_name}/textures/packed/{vmat_name}_c")
                    
            game_materials_dir = os.path.join(cs2_base, "game", "csgo_addons", addon_name, "materials", "models", model_name)
            for _, target_name in image_files_to_copy:
                vtex_name = target_name + "_c"
                compiled_vtex = os.path.join(game_materials_dir, vtex_name)
                if os.path.exists(compiled_vtex):
                    zipf.write(compiled_vtex, f"{root_folder}/materials/models/{model_name}/{vtex_name}")
                
            # Sistemi temizle
            try:
                shutil.rmtree(os.path.join(cs2_base, "content", "csgo_addons", addon_name))
                shutil.rmtree(os.path.join(cs2_base, "game", "csgo_addons", addon_name))
            except: pass
        else:
            # Derleyici yoksa kaynak dosyaları ekle
            if os.path.exists(fbx_path):
                zipf.write(fbx_path, fbx_name)
            zipf.write(vmdl_path, f"{model_name}.vmdl")
            for vmat_path_abs, vmat_name in vmat_files:
                zipf.write(vmat_path_abs, vmat_name)
        
    return zip_path
