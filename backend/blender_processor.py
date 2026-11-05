import bpy
import os
import uuid
import urllib.request
import addon_utils

def ensure_sourceio_installed():
    """
    SourceIO eklentisinin kurulu olup olmadığını kontrol eder.
    Kurulu değilse GitHub'dan son sürümünü indirip kurar ve aktif eder.
    (Headless bpy ortamı için yamalanmış özel versiyon)
    """
    addon_name = "SourceIO"
    
    is_installed = False
    is_enabled = False
    
    for mod in addon_utils.modules():
        if mod.__name__ == addon_name or addon_name.lower() in mod.__name__.lower():
            is_installed = True
            is_enabled = addon_utils.check(mod.__name__)[1]
            addon_name = mod.__name__
            break
            
    # Eğer daha önce kurulmuşsa, modülü aktif etmeyi dener
    if is_installed and is_enabled:
        return
        
    print("[Bilgi] SourceIO eklentisi bulunamadı veya pasif. Otomatik olarak indiriliyor...")
    import urllib.request
    import zipfile
    url = "https://github.com/REDxEYE/SourceIO/releases/latest/download/SourceIO.zip"
    zip_path = os.path.join(os.path.dirname(__file__), "SourceIO.zip")
    
    try:
        urllib.request.urlretrieve(url, zip_path)
        
        # Blender Eklenti Yolu
        addon_path = os.path.join(bpy.utils.user_resource('SCRIPTS'), 'addons')
        os.makedirs(addon_path, exist_ok=True)
        
        # Zipten çıkart
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(addon_path)
            
        # Headless (Arayüzsüz) Ortam Yaması:
        # SourceIO normalde UI gerektirir, register fonksiyonunu zorla export ediyoruz.
        init_path = os.path.join(addon_path, 'SourceIO', '__init__.py')
        if os.path.exists(init_path):
            with open(init_path, 'a') as f:
                f.write('\nfrom SourceIO.blender_bindings.bindings import register, unregister\n')
                
        # Eklentiyi Aktifleştir
        bpy.ops.preferences.addon_enable(module='SourceIO')
        
        if hasattr(bpy.ops.wm, 'save_userpref'):
            bpy.ops.wm.save_userpref()
        print("[Bilgi] SourceIO başarıyla kuruldu ve aktif edildi!")
    except Exception as e:
        print(f"[Hata] SourceIO kurulamadı: {e}")
    finally:
        if os.path.exists(zip_path):
            try: os.remove(zip_path)
            except: pass

def clear_scene():
    """
    Blender sahnesindeki tüm mevcut nesneleri, materyalleri ve mesh'leri temizler.
    Temiz bir başlangıç için gereklidir.
    """
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    for collection in [bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures]:
        for block in collection:
            if not block.users:
                collection.remove(block)

def process_model(input_path: str, output_dir: str) -> str:
    """
    Verilen dosyayı (mdl, fbx, obj, smd) Blender'a alır, origin'ini sıfırlar ve .glb olarak export eder.
    """
    # 100% Otonom SourceIO kontrolü
    ensure_sourceio_installed()
    
    clear_scene()
    
    file_ext = os.path.splitext(input_path)[1].lower()
    
    try:
        # 1. Modeli İçe Aktarma (Import)
        if file_ext == '.mdl':
            # Önce objeleri temizle
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            print("[DEBUG] Varsayılan objeler silindi. Mevcut objeler:", len(bpy.data.objects))
            
            dname = os.path.dirname(input_path)
            fname = os.path.basename(input_path)
            # SourceIO eklentisinin mdl import fonksiyonu
            print(f"[DEBUG] SourceIO import başlatılıyor: {input_path}")
            if hasattr(bpy.ops.sourceio, 'mdl'):
                res = bpy.ops.sourceio.mdl(
                    filepath=input_path,
                    directory=dname,
                    files=[{'name': fname}],
                    discover_resources=True
                )
                print(f"[DEBUG] SourceIO.mdl sonucu: {res}")
            else:
                res = bpy.ops.import_scene.sourceio_mdl(
                    filepath=input_path,
                    directory=dname,
                    files=[{'name': fname}]
                )
                print(f"[DEBUG] import_scene.sourceio_mdl sonucu: {res}")
                
            print("[DEBUG] Import sonrası mevcut objeler:", len(bpy.data.objects))
            if len(bpy.data.objects) == 0:
                print("[HATA] SourceIO hiçbir obje oluşturmadı! Dosyalar eksik olabilir (vvd, vtx).")
                raise ValueError("SourceIO model geometrisini bulamadı! Lütfen modelin .vvd ve .vtx dosyalarının aynı klasörde (.zip içinde) olduğundan emin olun.")
        elif file_ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=input_path)
        elif file_ext == '.obj':
            if hasattr(bpy.ops.wm, 'obj_import'):
                bpy.ops.wm.obj_import(filepath=input_path)
            else:
                bpy.ops.import_scene.obj(filepath=input_path)
        elif file_ext == '.smd':
            try:
                # SourceIO ayrıca smd de destekler
                if hasattr(bpy.ops.sourceio, 'smd'):
                    bpy.ops.sourceio.smd(filepath=input_path)
                else:
                    bpy.ops.import_scene.smd(filepath=input_path)
            except AttributeError:
                raise Exception(".smd içe aktarılamadı.")
        else:
            raise ValueError(f"Desteklenmeyen dosya formatı: {file_ext}")

        # 2. Seçili objelerin merkezini sıfırlama (Reset Origin)
        bpy.ops.object.select_all(action='SELECT')
        
        for obj in bpy.context.selected_objects:
            if obj.type in ['MESH', 'ARMATURE']:
                obj.location = (0.0, 0.0, 0.0)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Tüm materyalleri Three.js'de görünür olması için zorla (SourceIO bazen saydam yapar)
        for mat in bpy.data.materials:
            mat.blend_method = 'OPAQUE'
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        if 'Alpha' in node.inputs:
                            node.inputs['Alpha'].default_value = 1.0
                            # Eğer Alpha'ya bir link varsa kopar (saydamlık maskelerini iptal et)
                            for link in node.inputs['Alpha'].links:
                                mat.node_tree.links.remove(link)

        # 3. Modeli GLB Olarak Dışa Aktarma (Export)
        output_filename = f"model_{uuid.uuid4().hex[:8]}.glb"
        output_path = os.path.join(output_dir, output_filename)
        
        # FBX olarak da dışa aktar (Derleme aşaması için)
        fbx_filename = output_filename.replace('.glb', '.fbx')
        fbx_path = os.path.join(output_dir, fbx_filename)
        
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            use_selection=False,
            export_apply=True
        )
        
        bpy.ops.export_scene.fbx(
            filepath=fbx_path,
            use_selection=False,
            add_leaf_bones=False,
            bake_anim=False
        )

        # Materyal ve Kaplama Resimlerini (Texture) Analiz Edip JSON Olarak Kaydet
        import json
        materials_data = {}
        for mat in bpy.data.materials:
            mat_info = {}
            if mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image and getattr(node.image, 'filepath', None):
                        # Resmin mutlak yolunu (Absolute Path) al
                        img_path = bpy.path.abspath(node.image.filepath)
                        if not os.path.exists(img_path):
                            continue # Dosya yoksa atla
                            
                        # Bu resim hangi yuvaya (Socket) bağlı?
                        for link in node.outputs[0].links:
                            target_node = link.to_node
                            socket_name = link.to_socket.name
                            
                            if target_node.type == 'BSDF_PRINCIPLED':
                                if socket_name in ['Base Color', 'Color']:
                                    mat_info['Color'] = img_path
                                elif socket_name == 'Normal':
                                    mat_info['Normal'] = img_path
                                elif socket_name == 'Roughness':
                                    mat_info['Roughness'] = img_path
                                elif socket_name in ['Metallic', 'Metalness']:
                                    mat_info['Metallic'] = img_path
                            elif target_node.type == 'NORMAL_MAP':
                                mat_info['Normal'] = img_path
            
            # Eğer hiçbir bağlantı bulunamadıysa ama resim varsa, rastgele Color ataması yap
            if not mat_info and mat.use_nodes and mat.node_tree:
                for node in mat.node_tree.nodes:
                     if node.type == 'TEX_IMAGE' and node.image and getattr(node.image, 'filepath', None):
                         img_path = bpy.path.abspath(node.image.filepath)
                         if os.path.exists(img_path):
                             mat_info['Color'] = img_path
                             break

            materials_data[mat.name] = mat_info

        mat_json_path = os.path.join(output_dir, f"{output_filename.replace('.glb', '')}_materials.json")
        with open(mat_json_path, "w", encoding="utf-8") as f:
            json.dump(materials_data, f, indent=4)

        print(f"[BAŞARILI] İşlem tamamlandı. Dosyalar: {output_path}, {fbx_path}")
        return output_filename

    except Exception as e:
        print(f"[Hata] Blender işleme sırasında bir hata oluştu: {e}")
        raise e
