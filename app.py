import io
import os
import re
import uvicorn
import tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse
from pypdf import PdfReader
from docx import Document as DocxDocument
import easyocr
import whisper
import yt_dlp

# Configuración de FFmpeg
os.environ["PATH"] += os.pathsep + os.getcwd()

app = FastAPI(title="Sistema de Transcripción de Contenidos Educativos")

# CORS para permitir peticiones desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("=== SISTEMA DE TRANSCRIPCIÓN EDUCATIVA ===")

# Verificar FFmpeg
if os.path.exists("ffmpeg.exe") or os.system("ffmpeg -version > nul 2>&1") == 0:
    print("✅ FFmpeg detectado correctamente")
else:
    print("⚠️ ADVERTENCIA: FFmpeg no encontrado")

# Cargar motores
print("🔄 Cargando OCR (EasyOCR)...")
ocr_reader = easyocr.Reader(['es', 'en'], gpu=False)

print("🔄 Cargando Whisper (Transcripción de audio)...")
audio_model = whisper.load_model("base")

print("✅ TODOS LOS MOTORES LISTOS")
print("🌐 Abriendo navegador en http://localhost:7000\n")

# ==================== FUNCIONES DE EXTRACCIÓN ====================

def extract_pdf(file_bytes):
    """Extrae texto de PDFs"""
    try:
        reader_pdf = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader_pdf.pages:
            text += page.extract_text() + "\n"
        return text.strip() or "PDF procesado sin texto seleccionable."
    except Exception as e:
        return f"Error PDF: {str(e)}"

def extract_image_ocr(file_bytes):
    """OCR en imágenes"""
    try:
        return " ".join(ocr_reader.readtext(file_bytes, detail=0))
    except Exception as e:
        return f"Error OCR: {str(e)}"

def transcribe_audio_video(file_bytes, file_ext):
    """Transcripción de audio/video - solo texto"""
    try:
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name

        # Transcribir y obtener solo el texto
        result = audio_model.transcribe(tmp_path, fp16=False, verbose=False)
        
        os.remove(tmp_path)
        
        # Retornar solo el texto completo
        return result.get("text", "").strip()
        
    except Exception as e:
        return f"Error Transcripción: {str(e)}"

def transcribe_youtube(url):
    """Descarga audio de YouTube y transcribe - solo texto"""
    try:
        # Configuración de yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'temp_yt_audio.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        # Descargar audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Video de YouTube')
        
        # Transcribir
        audio_path = "temp_yt_audio.mp3"
        if not os.path.exists(audio_path):
            return "Error: No se pudo descargar el audio", None
        
        result = audio_model.transcribe(audio_path, fp16=False, verbose=False)
        
        # Limpiar archivo temporal
        os.remove(audio_path)
        
        # Retornar solo el texto completo
        return result.get("text", "").strip(), title
        
    except Exception as e:
        return f"Error YouTube: {str(e)}", None

def extract_plain_text(file_bytes):
    """Lee archivos de texto plano"""
    return file_bytes.decode("utf-8", errors="ignore")

# ==================== GENERACIÓN DE ARCHIVOS ====================

def generate_docx(text, filename="transcripcion.docx"):
    """Genera un archivo Word con el texto"""
    doc = DocxDocument()
    doc.add_heading('Transcripción de Contenido Educativo', 0)
    
    # Agregar párrafos
    for line in text.split('\n'):
        if line.strip():
            doc.add_paragraph(line)
    
    # Guardar en memoria
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream.getvalue()

# ==================== HTML EMBEBIDO ====================

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema de Transcripción Educativa</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --primary: #0891b2;
            --primary-hover: #0e7490;
            --secondary: #06b6d4;
            --accent: #10b981;
            --bg-body: #f0fdfa;
            --bg-card: #ffffff;
            --bg-card-hover: #ecfeff;
            --text-main: #0f172a;
            --text-sub: #475569;
            --border: #cbd5e1;
            --radius: 16px;
            --shadow: 0 4px 6px -1px rgba(8, 145, 178, 0.1), 0 2px 4px -1px rgba(8, 145, 178, 0.06);
            --shadow-lg: 0 20px 25px -5px rgba(8, 145, 178, 0.1), 0 10px 10px -5px rgba(8, 145, 178, 0.04);
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #ecfeff 0%, #f0fdfa 100%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        .header p {
            color: var(--text-sub);
            font-size: 1.1rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
        }
        
        .card {
            background: var(--bg-card);
            border-radius: var(--radius);
            padding: 30px;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
        }
        
        .card:hover {
            box-shadow: var(--shadow-lg);
            transform: translateY(-2px);
        }
        
        .card-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .upload-zone {
            border: 3px dashed var(--border);
            border-radius: var(--radius);
            padding: 50px 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: var(--bg-card-hover);
        }
        
        .upload-zone:hover {
            border-color: var(--primary);
            background: white;
            transform: scale(1.02);
        }
        
        .upload-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            box-shadow: 0 8px 16px rgba(8, 145, 178, 0.2);
        }
        
        .upload-icon i {
            font-size: 36px;
            color: white;
        }
        
        .upload-zone h3 {
            color: var(--text-main);
            margin-bottom: 10px;
        }
        
        .upload-zone p {
            color: var(--text-sub);
            font-size: 0.95rem;
        }
        
        .youtube-input-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .youtube-input {
            flex: 1;
            padding: 14px 18px;
            border: 2px solid var(--border);
            border-radius: 12px;
            font-size: 1rem;
            transition: all 0.3s;
        }
        
        .youtube-input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.1);
        }
        
        .btn {
            padding: 14px 28px;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1rem;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(8, 145, 178, 0.4);
        }
        
        .btn-secondary {
            background: var(--accent);
            color: white;
        }
        
        .btn-secondary:hover {
            background: #059669;
        }
        
        .btn-outline {
            background: white;
            color: var(--primary);
            border: 2px solid var(--primary);
        }
        
        .btn-outline:hover {
            background: var(--primary);
            color: white;
        }
        
        .results-area {
            display: none;
            animation: fadeIn 0.5s ease;
        }
        
        .results-area.active {
            display: block;
        }
        
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 20px;
            background: linear-gradient(135deg, var(--bg-card-hover), white);
            border-radius: 12px;
            border: 1px solid var(--border);
        }
        
        .file-info h3 {
            color: var(--text-main);
            font-size: 1.2rem;
            margin-bottom: 5px;
        }
        
        .file-meta {
            color: var(--text-sub);
            font-size: 0.9rem;
        }
        
        .badge {
            background: linear-gradient(135deg, var(--accent), #34d399);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
        }
        
        .text-display {
            position: relative;
            border: 2px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            background: white;
        }
        
        .text-area {
            width: 100%;
            min-height: 400px;
            padding: 20px;
            border: none;
            font-family: 'Courier New', monospace;
            font-size: 0.95rem;
            line-height: 1.6;
            resize: vertical;
            color: var(--text-main);
        }
        
        .text-area:focus {
            outline: none;
        }
        
        .action-bar {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            padding: 15px 20px;
            background: var(--bg-card-hover);
            border-top: 1px solid var(--border);
        }
        
        .btn-small {
            padding: 10px 18px;
            font-size: 0.9rem;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid var(--bg-card-hover);
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        .loading-text {
            color: var(--text-sub);
            font-size: 1.1rem;
        }
        
        @keyframes spin {
            100% { transform: rotate(360deg); }
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .stats {
            display: flex;
            gap: 15px;
            margin-top: 15px;
        }
        
        .stat-item {
            background: white;
            padding: 12px 20px;
            border-radius: 10px;
            border: 1px solid var(--border);
            flex: 1;
            text-align: center;
        }
        
        .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
        }
        
        .stat-label {
            font-size: 0.85rem;
            color: var(--text-sub);
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fa-solid fa-graduation-cap"></i> Sistema de Transcripción Educativa</h1>
            <p>Extrae y transcribe contenido de cursos en múltiples formatos</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <div class="card-title">
                    <i class="fa-solid fa-cloud-arrow-up"></i> Subir Archivo
                </div>
                <div class="upload-zone" id="upload-zone">
                    <input type="file" id="file-input" hidden>
                    <div class="upload-icon">
                        <i class="fa-solid fa-file-arrow-up"></i>
                    </div>
                    <h3>Arrastra archivos aquí</h3>
                    <p>PDF, Imágenes, Audio, Video</p>
                    <p style="font-size: 0.8rem; margin-top: 8px; color: #94a3b8;">
                        MP3, MP4, WAV, PNG, JPG, PDF
                    </p>
                </div>
            </div>
            
            <div class="card">
                <div class="card-title">
                    <i class="fa-brands fa-youtube"></i> Transcribir desde URL
                </div>
                <p style="margin-bottom: 20px; color: var(--text-sub);">
                    Pega el enlace de YouTube u otro video público
                </p>
                <div class="youtube-input-group">
                    <input 
                        type="text" 
                        id="youtube-url" 
                        class="youtube-input" 
                        placeholder="https://www.youtube.com/watch?v=..."
                    >
                    <button class="btn btn-primary" onclick="transcribeYouTube()">
                        <i class="fa-solid fa-play"></i> Transcribir
                    </button>
                </div>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p class="loading-text">Procesando contenido...</p>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-top: 10px;">
                Las transcripciones pueden tomar varios minutos
            </p>
        </div>
        
        <div class="results-area" id="results">
            <div class="card">
                <div class="result-header">
                    <div class="file-info">
                        <h3 id="result-filename">archivo.pdf</h3>
                        <div class="file-meta">
                            <span id="result-processor">Procesado</span>
                        </div>
                    </div>
                    <span class="badge" id="result-badge">COMPLETADO</span>
                </div>
                
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value" id="stat-chars">0</div>
                        <div class="stat-label">Caracteres</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="stat-words">0</div>
                        <div class="stat-label">Palabras</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="stat-lines">0</div>
                        <div class="stat-label">Líneas</div>
                    </div>
                </div>
                
                <div class="text-display" style="margin-top: 20px;">
                    <textarea id="result-text" class="text-area" placeholder="El contenido aparecerá aquí..."></textarea>
                    <div class="action-bar">
                        <button class="btn btn-outline btn-small" onclick="copyText()">
                            <i class="fa-regular fa-copy"></i> Copiar
                        </button>
                        <button class="btn btn-secondary btn-small" onclick="downloadFile('txt')">
                            <i class="fa-solid fa-download"></i> TXT
                        </button>
                        <button class="btn btn-primary btn-small" onclick="downloadFile('docx')">
                            <i class="fa-solid fa-file-word"></i> DOCX
                        </button>
                        <button class="btn btn-outline btn-small" onclick="resetApp()">
                            <i class="fa-solid fa-rotate-left"></i> Nuevo
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const fileInput = document.getElementById('file-input');
        const uploadZone = document.getElementById('upload-zone');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const resultText = document.getElementById('result-text');
        
        uploadZone.addEventListener('click', () => fileInput.click());
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.style.borderColor = 'var(--primary)';
            uploadZone.style.background = 'white';
        });
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.style.borderColor = 'var(--border)';
            uploadZone.style.background = 'var(--bg-card-hover)';
        });
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.style.borderColor = 'var(--border)';
            uploadZone.style.background = 'var(--bg-card-hover)';
            if (e.dataTransfer.files.length) processFile(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) processFile(e.target.files[0]);
        });
        
        async function processFile(file) {
            showLoading();
            const formData = new FormData();
            formData.append("file", file);
            
            try {
                const response = await fetch("/upload/", {
                    method: "POST",
                    body: formData
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || "Error en el servidor");
                showResults(data, file.name);
            } catch (error) {
                alert("Error: " + error.message);
                hideLoading();
            }
        }
        
        async function transcribeYouTube() {
            const url = document.getElementById('youtube-url').value.trim();
            if (!url) {
                alert("Por favor ingresa una URL");
                return;
            }
            
            showLoading();
            const formData = new FormData();
            formData.append("url", url);
            
            try {
                const response = await fetch("/transcribe-youtube/", {
                    method: "POST",
                    body: formData
                });
                const data = await response.json();
                if (data.error) throw new Error(data.message);
                showResults(data, data.filename);
            } catch (error) {
                alert("Error: " + error.message);
                hideLoading();
            }
        }
        
        function showResults(data, filename) {
            hideLoading();
            results.classList.add('active');
            
            document.getElementById('result-filename').textContent = filename;
            document.getElementById('result-processor').textContent = data.processor;
            document.getElementById('result-badge').textContent = 'COMPLETADO';
            resultText.value = data.extracted_data;
            
            const text = data.extracted_data;
            document.getElementById('stat-chars').textContent = text.length.toLocaleString();
            document.getElementById('stat-words').textContent = text.split(/\\s+/).filter(w => w).length.toLocaleString();
            document.getElementById('stat-lines').textContent = text.split('\\n').length.toLocaleString();
        }
        
        function showLoading() {
            results.classList.remove('active');
            loading.classList.add('active');
        }
        
        function hideLoading() {
            loading.classList.remove('active');
        }
        
        function copyText() {
            resultText.select();
            navigator.clipboard.writeText(resultText.value);
            alert("✅ Texto copiado al portapapeles");
        }
        
        async function downloadFile(format) {
            const text = resultText.value;
            const formData = new FormData();
            formData.append("text", text);
            formData.append("format", format);
            
            try {
                const response = await fetch("/download/", {
                    method: "POST",
                    body: formData
                });
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `transcripcion.${format}`;
                a.click();
            } catch (error) {
                alert("Error al descargar: " + error.message);
            }
        }
        
        function resetApp() {
            fileInput.value = '';
            document.getElementById('youtube-url').value = '';
            resultText.value = '';
            results.classList.remove('active');
        }
    </script>
</body>
</html>
"""

# ==================== ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse)
def root():
    """Sirve la interfaz HTML"""
    return HTML_CONTENT

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Procesa archivos subidos"""
    content = await file.read()
    filename = file.filename.lower()
    
    # IMÁGENES → OCR
    if filename.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        data = extract_image_ocr(content)
        proc = "OCR (EasyOCR)"
        
    # AUDIO/VIDEO → TRANSCRIPCIÓN
    elif filename.endswith((".mp3", ".wav", ".mp4", ".mpeg", ".m4a", ".ogg", ".webm")):
        ext = os.path.splitext(filename)[1]
        data = transcribe_audio_video(content, ext)
        proc = "Transcripción (Whisper AI)"
        
    # PDF
    elif filename.endswith(".pdf"):
        data = extract_pdf(content)
        proc = "Extracción PDF"
        
    # TEXTO PLANO
    elif filename.endswith((".txt", ".md", ".py", ".json", ".csv")):
        data = extract_plain_text(content)
        proc = "Texto Plano"
        
    else:
        data = "Formato no soportado."
        proc = "Desconocido"

    return {
        "filename": file.filename,
        "processor": proc,
        "extracted_data": data,
        "char_count": len(data),
        "word_count": len(data.split())
    }

@app.post("/transcribe-youtube/")
async def transcribe_youtube_endpoint(url: str = Form(...)):
    """Transcribe videos de YouTube"""
    text, title = transcribe_youtube(url)
    
    if title is None:
        return {
            "error": True,
            "message": text
        }
    
    return {
        "filename": title,
        "processor": "YouTube + Whisper AI",
        "extracted_data": text,
        "char_count": len(text),
        "word_count": len(text.split())
    }

@app.post("/download/")
async def download_text(text: str = Form(...), format: str = Form("txt")):
    """Genera archivo descargable (TXT o DOCX)"""
    if format == "docx":
        content = generate_docx(text)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = "transcripcion.docx"
    else:
        content = text.encode("utf-8")
        media_type = "text/plain"
        filename = "transcripcion.txt"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    # Abrir navegador automáticamente
    import webbrowser
    from threading import Timer
    
    def open_browser():
        webbrowser.open("http://localhost:7000")
    
    Timer(1.5, open_browser).start()
    
    uvicorn.run(app, host="0.0.0.0", port=7000)