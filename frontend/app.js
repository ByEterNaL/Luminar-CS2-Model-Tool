import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// === UI Elements ===
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadPanel = document.getElementById('upload-panel');
const loadingPanel = document.getElementById('loading-panel');
const canvasContainer = document.getElementById('canvas-container');
const btnCompile = document.getElementById('btn-compile');
const statusText = document.getElementById('status-text');
const statusIndicator = document.getElementById('status-indicator');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toast-msg');

// === Three.js Variables ===
let scene, camera, renderer, controls;
let currentModel = null;
let currentModelUrl = null;
let skeletonHelper = null;
let loadingInterval = null;

// === Notification System ===
function showToast(msg, isError = false) {
    toastMsg.textContent = msg;
    toast.style.borderColor = isError ? '#ff3366' : '#00ff88';
    toast.classList.remove('translate-x-full');
    setTimeout(() => {
        toast.classList.add('translate-x-full');
    }, 4000);
}

function updateLog(msg, state = 'info') {
    statusText.textContent = msg;
    if (state === 'error') {
        statusIndicator.className = 'w-2 h-2 rounded-full bg-red-500';
    } else if (state === 'success') {
        statusIndicator.className = 'w-2 h-2 rounded-full bg-neon shadow-[0_0_8px_#00ff88]';
    } else if (state === 'loading') {
        statusIndicator.className = 'w-2 h-2 rounded-full bg-yellow-400 animate-pulse';
    } else {
        statusIndicator.className = 'w-2 h-2 rounded-full bg-gray-500';
    }
}

// === File Upload Logic ===
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

async function handleFile(file) {
    // Check extension
    const validExtensions = ['.mdl', '.fbx', '.obj', '.smd', '.zip'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!validExtensions.includes(ext)) {
        showToast('Sadece MDL, FBX, OBJ, SMD veya ZIP desteklenmektedir.', true);
        return;
    }

    // UI Transition
    uploadPanel.classList.add('hidden');
    loadingPanel.classList.remove('hidden');
    loadingPanel.classList.add('flex');
    document.querySelector('main').classList.remove('hidden');

    updateLog(`Dosya yükleniyor: ${file.name}...`, 'loading');
    
    // Hacker Log Effect
    const loadingText = document.getElementById('loading-subtext');
    const hackerLogs = [
        "[INFO] Precomputing geometry keys...",
        "[DEBUG] Injecting SourceIO handlers...",
        "[INFO] Registered Source1 material handler...",
        "[INFO] Loading skeletal hierarchy...",
        "[INFO] Resetting object origin (0,0,0)...",
        "[INFO] Applying transforms...",
        "[INFO] Converting to GLTF 2.0 format...",
        "[SUCCESS] Extraction complete. Generating GLB..."
    ];
    let logIndex = 0;
    if (loadingInterval) clearInterval(loadingInterval);
    loadingText.textContent = hackerLogs[0];
    logIndex = 1;
    loadingInterval = setInterval(() => {
        if (logIndex < hackerLogs.length) {
            loadingText.textContent = hackerLogs[logIndex];
            logIndex++;
        }
    }, 800);

    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);

    try {
        // Send to FastAPI Backend
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Sunucu hatası');
        }

        const data = await response.json();
        currentModelUrl = data.modelUrl;
        updateLog('İşlem başarılı, model render ediliyor...', 'success');
        
        // Hide loader and main container to allow 3D interaction
        if (loadingInterval) clearInterval(loadingInterval);
        loadingPanel.classList.add('hidden');
        loadingPanel.classList.remove('flex');
        document.querySelector('main').classList.add('hidden');
        
        // Show Compile button and activate canvas
        btnCompile.classList.remove('hidden');
        btnCompile.classList.add('flex');
        canvasContainer.classList.add('active');

        // Init 3D Scene and load the model
        initThreeJS();
        loadModel(data.modelUrl);

    } catch (error) {
        updateLog(`Hata: ${error.message}`, 'error');
        showToast(`Yükleme başarısız: ${error.message}`, true);
        // Reset UI
        if (loadingInterval) clearInterval(loadingInterval);
        loadingPanel.classList.add('hidden');
        loadingPanel.classList.remove('flex');
        uploadPanel.classList.remove('hidden', 'opacity-0', 'scale-95');
        document.querySelector('main').classList.remove('hidden');
    }
}

// === Compile Action ===
btnCompile.addEventListener('click', async () => {
    btnCompile.disabled = true;
    btnCompile.innerHTML = `<div class="loader border-2 border-darker rounded-full w-4 h-4 mr-2"></div> Derleniyor...`;
    updateLog('Derleme işlemi başlatıldı (Valve Tools)...', 'loading');

    try {
        const modelFilename = currentModelUrl.split('/').pop().replace('.glb', '.fbx');
        
        const response = await fetch('/api/compile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: modelFilename })
        });
        
        if (response.ok) {
            // Eğer yanıt bir dosyaysa (ZIP), indirmeyi başlat
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.download = modelFilename.replace('.fbx', '_cs2_project.zip');
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            
            showToast("Projeyi içeren ZIP dosyası indiriliyor!", false);
            updateLog('Model başarıyla CS2 projesi olarak paketlendi!', 'success');
        } else {
            const errData = await response.json();
            throw new Error(errData.detail || 'Derleme hatası');
        }
    } catch (error) {
        showToast(error.message, true);
        updateLog('Derleme başarısız oldu.', 'error');
    } finally {
        btnCompile.disabled = false;
        btnCompile.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg> Derle (Compile)`;
    }
});

// === Three.js Setup ===
function initThreeJS() {
    if (scene) return; // Zaten oluşturulmuşsa tekrar oluşturma

    // Scene setup
    scene = new THREE.Scene();
    // Hafif karanlık hacker ambiyansı
    scene.fog = new THREE.FogExp2(0x050505, 0.05);

    // Camera setup
    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(5, 5, 5);

    // Renderer setup
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    canvasContainer.appendChild(renderer.domElement);

    // OrbitControls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x00ff88, 1);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);
    
    const blueLight = new THREE.DirectionalLight(0x00e5ff, 0.5);
    blueLight.position.set(-5, 5, -7);
    scene.add(blueLight);

    // Grid Helper (Estetik için)
    const gridHelper = new THREE.GridHelper(20, 20, 0x00ff88, 0x333333);
    gridHelper.material.opacity = 0.2;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    // Window resize handler
    window.addEventListener('resize', onWindowResize);

    // Start animation loop
    animate();
}

function loadModel(url) {
    const loader = new GLTFLoader();
    
    loader.load(
        url,
        (gltf) => {
            // Önceki model varsa temizle
            if (currentModel) scene.remove(currentModel);
            if (skeletonHelper) scene.remove(skeletonHelper);

            currentModel = gltf.scene;
            scene.add(currentModel);

            // SkeletonHelper ekle (Kemikleri göstermek için)
            skeletonHelper = new THREE.SkeletonHelper(currentModel);
            // Kemik renklerini neon yapalım (Three.js varsayılan renkleri ezer, ama materyale müdahale edebiliriz)
            skeletonHelper.material.color.setHex(0x00e5ff);
            skeletonHelper.material.linewidth = 3;
            scene.add(skeletonHelper);

            // Kamerayı modele odakla (Bounding Box ile)
            const box = new THREE.Box3().setFromObject(currentModel);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            
            console.log("Model Bounding Box Size:", size);
            console.log("Model Bounding Box Center:", center);
            
            // Eğer Box boşsa (NaN ise), sıfırla
            if (isNaN(center.x)) center.set(0, 0, 0);
            if (isNaN(size.x) || size.x === 0) size.set(1, 1, 1);

            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            // Doğru formül: uzaklık = (boyut / 2) / tan(fov / 2)
            let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            
            if (isNaN(cameraZ) || cameraZ === 0) cameraZ = 5;
            
            cameraZ *= 1.5; // Biraz boşluk bırak
            console.log("Calculated cameraZ:", cameraZ);
            
            camera.position.set(center.x + cameraZ*0.5, center.y + cameraZ*0.2, center.z + cameraZ);
            controls.target.copy(center);
            controls.maxDistance = cameraZ * 10;
            controls.minDistance = 0.01;
            controls.update();
            
            // Tıklama olaylarının sorunsuz çalışması için canvas-container'ı öne al ama arayüzün arkasında kalsın
            canvasContainer.style.zIndex = '5';
            
            // Hata ayıklama için basit bir kırmızı küp ekleyelim ki sahnenin çalışıp çalışmadığını görelim
            const debugBox = new THREE.Mesh(
                new THREE.BoxGeometry(0.5, 0.5, 0.5),
                new THREE.MeshBasicMaterial({color: 0xff0000, wireframe: true})
            );
            debugBox.position.copy(center);
            scene.add(debugBox);

            updateLog('Model başarıyla yüklendi ve render edildi.', 'success');
            showToast('Model başarıyla yüklendi. Kamera kontrol edilebilir.', false);
        },
        (xhr) => {
            const percent = Math.round((xhr.loaded / xhr.total) * 100);
            updateLog(`GLB indiriliyor: %${percent}`, 'info');
        },
        (error) => {
            console.error(error);
            showToast('GLB yüklenirken hata oluştu.', true);
        }
    );
}

function onWindowResize() {
    if (!camera || !renderer) return;
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    // skeletonHelper.update() metodu Three.js yeni sürümlerinde kaldırıldı, bu render loopunu çökertiyordu!
    if (renderer && scene && camera) renderer.render(scene, camera);
}
