// static/js/main.js

const uploadSection = document.getElementById('uploadSection');
const fileInput = document.getElementById('fileInput');
const loading = document.getElementById('loading');
const resultsSection = document.getElementById('resultsSection');
const messageContainer = document.getElementById('message-container');
const resultsTableContainer = document.getElementById('resultsTableContainer');
const resetBtn = document.getElementById('resetBtn');
const progressText = document.getElementById('progress-text');

const stagingSection = document.getElementById('stagingSection');
const stagingList = document.getElementById('stagingList');
const processButton = document.getElementById('processButton');
const fileCount = document.getElementById('fileCount');
const downloadBtn = document.getElementById('downloadButton');

let stagedFiles = []; // Array para guardar los archivos
let eventSource = null;

// --- 1. EVENT LISTENERS ---

// Al hacer clic en el área de subida
uploadSection.addEventListener('click', () => { fileInput.click(); });

// Al seleccionar archivos (se activa CADA VEZ que añades)
fileInput.addEventListener('change', (e) => {
    addFilesToStaging(e.target.files);
    // Limpiamos el valor para poder seleccionar el mismo archivo si se borró
    fileInput.value = ''; 
});

// Al arrastrar archivos
uploadSection.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadSection.classList.add('dragover');
});
uploadSection.addEventListener('dragleave', () => {
    uploadSection.classList.remove('dragover');
});
uploadSection.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadSection.classList.remove('dragover');
    addFilesToStaging(e.dataTransfer.files);
});

// Al hacer clic en "Procesar"
processButton.addEventListener('click', startGlobalUpload);

// Al hacer clic en la "X" para quitar un archivo
stagingList.addEventListener('click', (e) => {
    if (e.target.classList.contains('remove-btn')) {
        const fileName = e.target.dataset.name;
        removeFileFromStaging(fileName);
    }
});

// Al hacer clic en "Procesar otros" (Reset)
resetBtn.addEventListener('click', resetUpload);


// --- 2. LÓGICA DE STAGING (PREPARACIÓN) ---

/**
 * Añade archivos al array global 'stagedFiles'
 * @param {FileList} fileList - Lista de archivos a añadir
 */
function addFilesToStaging(fileList) {
    let filesAdded = 0;
    for (const file of fileList) {
        // Solo PDFs y que no estén ya en la lista
        if (file.type === 'application/pdf' && !stagedFiles.some(f => f.name === file.name)) {
            stagedFiles.push(file);
            filesAdded++;
        }
    }
    
    if (filesAdded > 0) {
        updateStagingUI();
    } else if (fileList.length > 0) {
        showMessage('Solo puedes añadir archivos PDF que no estén ya en la lista.', 'error');
    }
}

/**
 * Quita un archivo del array 'stagedFiles' por su nombre
 * @param {string} fileName - Nombre del archivo a quitar
 */
function removeFileFromStaging(fileName) {
    stagedFiles = stagedFiles.filter(file => file.name !== fileName);
    updateStagingUI();
}

/**
 * Actualiza la UI (lista de archivos y botón) basado en 'stagedFiles'
 */
function updateStagingUI() {
    // 1. Limpiar lista actual
    stagingList.innerHTML = '';
    
    // 2. Mostrar u ocultar la sección de staging
    if (stagedFiles.length > 0) {
        stagingSection.style.display = 'block';
        
        // 3. Rellenar la lista
        stagedFiles.forEach(file => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span>${file.name}</span>
                <button type="button" class="remove-btn" data-name="${file.name}" title="Quitar">&times;</button>
            `;
            stagingList.appendChild(li);
        });
        
        // 4. Actualizar botón
        fileCount.textContent = stagedFiles.length;
        processButton.disabled = false;

    } else {
        stagingSection.style.display = 'none';
        processButton.disabled = true;
        fileCount.textContent = 0;
    }
}

// --- 3. LÓGICA DE SUBIDA Y PROCESAMIENTO ---

/**
 * Esta función se llama al presionar "Procesar"
 * Toma los archivos de 'stagedFiles' y los sube.
 */
function startGlobalUpload() {
    if (stagedFiles.length === 0) {
        showMessage('No hay archivos para procesar.', 'error');
        return;
    }
    
    // 1. Crear FormData con los archivos preparados
    const formData = new FormData();
    for (const file of stagedFiles) {
        formData.append('files[]', file);
    }
    
    // 2. Cambiar UI a modo "Cargando"
    uploadSection.style.display = 'none';
    stagingSection.style.display = 'none';
    resultsSection.style.display = 'none';
    loading.style.display = 'block';
    progressText.textContent = 'Subiendo archivos...';
    messageContainer.innerHTML = '';
    
    // 3. (PASO 1) Subir el lote
    fetch('/upload_multiple', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.batch_id) {
            progressText.textContent = 'Archivos subidos. Conectando al procesador...';
            // 4. (PASO 2) Conectar al stream
            startProcessingStream(data.batch_id);
        } else {
            throw new Error(data.error || 'Error al subir los archivos.');
        }
    })
    .catch(error => {
        console.error('Error en startGlobalUpload:', error);
        loading.style.display = 'none';
        showMessage('Error: ' + error.message, 'error');
        resetUpload(); // Reseteamos para que pueda intentarlo de nuevo
    });
}

/**
 * (Función Corregida y Re-integrada)
 * Se conecta al stream SSE y escucha eventos
 * @param {string} batchId - El ID del lote devuelto por el servidor
 */
function startProcessingStream(batchId) {
    eventSource = new EventSource(`/process_stream/${batchId}`);
    progressText.textContent = 'Procesando...';

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.status === 'progress') {
            // Muestra el progreso
            progressText.textContent = data.message;
        
        } else if (data.status === 'complete') {
    console.log('Status complete recibido. Datos:', data);
    loading.style.display = 'none';
    resultsSection.style.display = 'block';
    displayResults(data.data);

    showMessage('PDFs procesados y extraídos con éxito.', 'success');

    // Botón de descarga
    console.log('download_filename:', data.download_filename);
    console.log('downloadBtn element:', downloadBtn);
    
    if (data.download_filename) {
        if (downloadBtn) {
            downloadBtn.href = '/download/' + data.download_filename;
            downloadBtn.style.display = 'block';
            downloadBtn.style.margin = '20px auto';
            downloadBtn.setAttribute('download', data.download_filename);
            downloadBtn.textContent = 'Descargar Excel';
            console.log('Botón de descarga configurado:', downloadBtn.href);
        } else {
            console.warn('Elemento downloadBtn no encontrado en el DOM. No se puede mostrar el botón de descarga.');
        }
    } else {
        console.warn('No hay download_filename en la respuesta');
        if (downloadBtn) {
            downloadBtn.style.display = 'none';
        }
    }
    
    // Close the EventSource to prevent automatic reconnection attempts
    if (eventSource) {
        try { eventSource.close(); } catch (e) { /* ignore */ }
        eventSource = null;
    }
} else if (data.status === 'error') {
            // Error
            progressText.textContent = '';
            loading.style.display = 'none';
            showMessage('Error: ' + data.message, 'error');
            if (eventSource) eventSource.close();
            resetUpload(); // Resetea la UI
        }
    };

    // Maneja errores de conexión
    eventSource.onerror = function(err) {
        console.error('Error de EventSource (conexión perdida):', err);
        loading.style.display = 'none';
        showMessage('Error: Se perdió la conexión con el servidor.', 'error');
        resetUpload();
        if (eventSource) eventSource.close();
    };
}


// --- 4. FUNCIONES AUXILIARES ---

/**
 * Resetea toda la interfaz
 */
function resetUpload() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    
    stagedFiles = []; // Limpiar array
    fileInput.value = '';
    
    // Mostrar/Ocultar secciones
    uploadSection.style.display = 'block'; 
    loading.style.display = 'none';
    resultsSection.style.display = 'none';
    messageContainer.innerHTML = '';
    resultsTableContainer.innerHTML = '';
    progressText.textContent = '';
    
    // --- ¡LÓGICA DEL BOTÓN RE-AGREGADA! ---
    downloadBtn.style.display = 'none';
    downloadBtn.href = '#';
    
    updateStagingUI(); // Esto ocultará la sección de staging
}

/**
 * Muestra los datos JSON en una tabla HTML
 */
function displayResults(data) {
    const recibos = data.recibos;
    if (!recibos || recibos.length === 0) {
        resultsTableContainer.innerHTML = '<p>No se encontraron recibos en el documento.</p>';
        return;
    }
    let tableHTML = '<table class="results-table">';
    tableHTML += '<thead><tr><th>Nombre</th><th>Apellido</th><th>Sueldo</th></tr></thead>';
    tableHTML += '<tbody>';
    recibos.forEach(recibo => {
        tableHTML += `
            <tr>
                <td>${recibo.nombre || 'N/A'}</td>
                <td>${recibo.apellido || 'N/A'}</td>
                <td class="currency">${formatCurrency(recibo.sueldo)}</td>
            </tr>
        `;
    });
    tableHTML += '</tbody></table>';
    resultsTableContainer.innerHTML = tableHTML;
}

/**
 * Formatea un número como moneda
 */
function formatCurrency(number) {
    if (typeof number !== 'number') return 'N/A';
    return '$' + number.toLocaleString('es-AR', { 
        minimumFractionDigits: 2, 
        maximumFractionDigits: 2 
    });
}

/**
 * Muestra un mensaje en el contenedor de mensajes
 */
function showMessage(message, type) {
    messageContainer.innerHTML = `<div class="message ${type}">${message}</div>`;
}

// --- 5. INICIALIZACIÓN ---
// Llama a resetUpload() al cargar para mostrar el estado inicial
window.addEventListener('load', () => {
    // Aseguramos estado inicial
    resetUpload();
});