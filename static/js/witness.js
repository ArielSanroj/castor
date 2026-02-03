/**
 * Castor Control Electoral - Cliente de Testigos
 * Maneja registro, push notifications y asignaciones.
 */

// ============================================================
// CONFIGURACION
// ============================================================

const API_BASE = '/api/witness';
let witnessId = null;
let witnessData = null;
let swRegistration = null;

// ============================================================
// INICIALIZACION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Witness] Initializing...');

    // Verificar si hay witness guardado
    witnessId = localStorage.getItem('witnessId');
    if (witnessId) {
        await loadWitnessData();
    }

    // Registrar Service Worker
    if ('serviceWorker' in navigator) {
        try {
            swRegistration = await navigator.serviceWorker.register('/static/sw.js');
            console.log('[Witness] Service Worker registered');

            // Comunicar witness ID al SW
            if (witnessId && swRegistration.active) {
                swRegistration.active.postMessage({
                    type: 'SET_WITNESS_ID',
                    witnessId: parseInt(witnessId)
                });
            }
        } catch (error) {
            console.error('[Witness] SW registration failed:', error);
        }
    }

    // Setup formulario de registro si existe
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegistration);

        // Obtener codigo QR de URL
        const urlParams = new URLSearchParams(window.location.search);
        const qrCode = urlParams.get('code');
        if (qrCode) {
            document.getElementById('qr-code').value = qrCode;
        }

        // Cargar departamentos para zona de cobertura
        await loadDepartments();
        setupCoverageSelects();
    }

    // Setup boton de push
    const pushBtn = document.getElementById('enable-push-btn');
    if (pushBtn) {
        pushBtn.addEventListener('click', enablePushNotifications);
    }

    // Setup tracking de ubicacion
    if (witnessId) {
        startLocationTracking();
    }
});

// ============================================================
// GEOGRAFIA - ZONA DE COBERTURA
// ============================================================

let departmentsData = [];
let municipalitiesData = [];
let stationsData = [];

async function loadDepartments() {
    try {
        const response = await fetch(`${API_BASE}/geography/departments`);
        const data = await response.json();

        if (data.success) {
            departmentsData = data.departments;
            const select = document.getElementById('coverage-dept');
            if (select) {
                select.innerHTML = '<option value="">-- Seleccione departamento --</option>';
                departmentsData.forEach(dept => {
                    const option = document.createElement('option');
                    option.value = dept.code;
                    option.textContent = dept.name;
                    option.dataset.name = dept.name;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('[Witness] Error loading departments:', error);
    }
}

async function loadMunicipalities(deptCode) {
    try {
        const response = await fetch(`${API_BASE}/geography/municipalities/${deptCode}`);
        const data = await response.json();

        if (data.success) {
            municipalitiesData = data.municipalities;
            const select = document.getElementById('coverage-muni');
            if (select) {
                select.innerHTML = '<option value="">-- Seleccione municipio --</option>';
                municipalitiesData.forEach(muni => {
                    const option = document.createElement('option');
                    option.value = muni.code;
                    option.textContent = muni.name;
                    option.dataset.name = muni.name;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('[Witness] Error loading municipalities:', error);
    }
}

async function loadPollingStations(muniCode) {
    try {
        const response = await fetch(`${API_BASE}/geography/stations/${muniCode}`);
        const data = await response.json();

        if (data.success) {
            stationsData = data.stations;
            const select = document.getElementById('coverage-station');
            if (select) {
                select.innerHTML = '<option value="">-- Todos los puestos --</option>';
                stationsData.forEach(station => {
                    const option = document.createElement('option');
                    option.value = station.name;
                    option.textContent = `${station.name} - ${station.address}`;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('[Witness] Error loading stations:', error);
    }
}

function setupCoverageSelects() {
    const deptSelect = document.getElementById('coverage-dept');
    const muniSelect = document.getElementById('coverage-muni');
    const stationSelect = document.getElementById('coverage-station');

    if (deptSelect) {
        deptSelect.addEventListener('change', async () => {
            const deptCode = deptSelect.value;
            if (deptCode) {
                await loadMunicipalities(deptCode);
            } else {
                if (muniSelect) muniSelect.innerHTML = '<option value="">-- Seleccione municipio --</option>';
            }
            if (stationSelect) stationSelect.innerHTML = '<option value="">-- Todos los puestos --</option>';
        });
    }

    if (muniSelect) {
        muniSelect.addEventListener('change', async () => {
            const muniCode = muniSelect.value;
            if (muniCode) {
                await loadPollingStations(muniCode);
            } else {
                if (stationSelect) stationSelect.innerHTML = '<option value="">-- Todos los puestos --</option>';
            }
        });
    }
}

// ============================================================
// REGISTRO DE TESTIGO
// ============================================================

async function handleRegistration(event) {
    event.preventDefault();

    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;

    // Obtener datos de cobertura
    const deptSelect = form.querySelector('#coverage-dept');
    const muniSelect = form.querySelector('#coverage-muni');
    const stationSelect = form.querySelector('#coverage-station');

    const deptName = deptSelect?.selectedOptions[0]?.dataset.name || null;
    const muniName = muniSelect?.selectedOptions[0]?.dataset.name || null;

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Registrando...';

        const data = {
            qr_code: form.querySelector('#qr-code').value,
            full_name: form.querySelector('#full-name').value,
            phone: form.querySelector('#phone').value,
            cedula: form.querySelector('#cedula')?.value || null,
            email: form.querySelector('#email')?.value || null,
            // Zona de cobertura
            coverage_dept_code: deptSelect?.value || null,
            coverage_dept_name: deptName,
            coverage_muni_code: muniSelect?.value || null,
            coverage_muni_name: muniName,
            coverage_station_name: stationSelect?.value || null
        };

        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Error en el registro');
        }

        // Guardar witness ID
        witnessId = result.witness_id;
        localStorage.setItem('witnessId', witnessId);
        localStorage.setItem('witnessRegistrationCode', result.registration_code);

        // Comunicar al SW
        if (swRegistration?.active) {
            swRegistration.active.postMessage({
                type: 'SET_WITNESS_ID',
                witnessId: witnessId
            });
        }

        showMessage('success', result.message);

        // Mostrar seccion de push
        document.getElementById('registration-section').style.display = 'none';
        document.getElementById('push-section').style.display = 'block';

    } catch (error) {
        console.error('[Witness] Registration error:', error);
        showMessage('error', error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// ============================================================
// PUSH NOTIFICATIONS
// ============================================================

async function enablePushNotifications() {
    const pushBtn = document.getElementById('enable-push-btn');
    const originalText = pushBtn.textContent;

    try {
        pushBtn.disabled = true;
        pushBtn.textContent = 'Activando...';

        // Verificar soporte
        if (!('Notification' in window)) {
            throw new Error('Este navegador no soporta notificaciones');
        }

        if (!('serviceWorker' in navigator)) {
            throw new Error('Service Workers no soportados');
        }

        // Pedir permiso
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            throw new Error('Permiso de notificaciones denegado');
        }

        // Obtener VAPID key del servidor
        const vapidResponse = await fetch(`${API_BASE}/vapid-public-key`);
        const vapidData = await vapidResponse.json();

        // Comunicar VAPID key al SW
        if (swRegistration?.active) {
            swRegistration.active.postMessage({
                type: 'SET_VAPID_KEY',
                vapidKey: vapidData.public_key
            });
        }

        // Suscribir a push
        const subscription = await swRegistration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapidData.public_key)
        });

        // Enviar subscription al servidor
        const subscribeResponse = await fetch(`${API_BASE}/push/subscribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                witness_id: witnessId,
                subscription: subscription.toJSON()
            })
        });

        const subscribeResult = await subscribeResponse.json();

        if (!subscribeResponse.ok) {
            throw new Error(subscribeResult.error || 'Error al activar notificaciones');
        }

        showMessage('success', 'Notificaciones activadas correctamente');

        // Mostrar dashboard de testigo
        document.getElementById('push-section').style.display = 'none';
        document.getElementById('dashboard-section').style.display = 'block';

        // Iniciar tracking de ubicacion
        startLocationTracking();

    } catch (error) {
        console.error('[Witness] Push error:', error);
        showMessage('error', error.message);
    } finally {
        pushBtn.disabled = false;
        pushBtn.textContent = originalText;
    }
}

/**
 * Verifica si push esta habilitado
 */
async function checkPushStatus() {
    if (!swRegistration) return false;

    const subscription = await swRegistration.pushManager.getSubscription();
    return !!subscription;
}

/**
 * Desactiva push notifications
 */
async function disablePushNotifications() {
    try {
        const subscription = await swRegistration.pushManager.getSubscription();
        if (subscription) {
            await subscription.unsubscribe();

            await fetch(`${API_BASE}/push/unsubscribe`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ witness_id: witnessId })
            });

            showMessage('info', 'Notificaciones desactivadas');
        }
    } catch (error) {
        console.error('[Witness] Unsubscribe error:', error);
    }
}

// ============================================================
// UBICACION
// ============================================================

let locationWatchId = null;

function startLocationTracking() {
    if (!('geolocation' in navigator)) {
        console.warn('[Witness] Geolocation not supported');
        return;
    }

    // Pedir permiso y empezar tracking
    navigator.geolocation.getCurrentPosition(
        (position) => {
            updateLocation(position);

            // Iniciar tracking continuo
            locationWatchId = navigator.geolocation.watchPosition(
                updateLocation,
                (error) => console.warn('[Witness] Location error:', error),
                {
                    enableHighAccuracy: true,
                    timeout: 30000,
                    maximumAge: 60000
                }
            );
        },
        (error) => {
            console.warn('[Witness] Initial location error:', error);
        },
        {
            enableHighAccuracy: false,
            timeout: 10000
        }
    );
}

async function updateLocation(position) {
    if (!witnessId) return;

    const { latitude, longitude, accuracy } = position.coords;

    try {
        await fetch(`${API_BASE}/${witnessId}/location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: latitude,
                lon: longitude,
                accuracy: accuracy
            })
        });
        console.log('[Witness] Location updated:', latitude, longitude);

        // Actualizar UI si existe
        const locationEl = document.getElementById('current-location');
        if (locationEl) {
            locationEl.textContent = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
        }
    } catch (error) {
        console.error('[Witness] Location update failed:', error);
    }
}

function stopLocationTracking() {
    if (locationWatchId) {
        navigator.geolocation.clearWatch(locationWatchId);
        locationWatchId = null;
    }
}

// ============================================================
// ASIGNACIONES
// ============================================================

async function loadAssignments() {
    if (!witnessId) return;

    try {
        const response = await fetch(`${API_BASE}/assignments?witness_id=${witnessId}`);
        const data = await response.json();

        if (data.success) {
            renderAssignments(data.assignments);
        }
    } catch (error) {
        console.error('[Witness] Load assignments error:', error);
    }
}

function renderAssignments(assignments) {
    const container = document.getElementById('assignments-list');
    if (!container) return;

    if (assignments.length === 0) {
        container.innerHTML = '<p class="empty-state">No tienes asignaciones pendientes</p>';
        return;
    }

    container.innerHTML = assignments.map(a => `
        <div class="assignment-card status-${a.status.toLowerCase()}">
            <div class="assignment-header">
                <span class="mesa-id">${a.mesa_id}</span>
                <span class="status-badge">${getStatusLabel(a.status)}</span>
            </div>
            <div class="assignment-reason">${a.reason || 'Sin detalles'}</div>
            <div class="assignment-time">Asignado: ${formatDate(a.assigned_at)}</div>
            ${renderAssignmentActions(a)}
        </div>
    `).join('');
}

function renderAssignmentActions(assignment) {
    switch (assignment.status) {
        case 'PENDING':
            return `
                <div class="assignment-actions">
                    <button onclick="updateAssignment(${assignment.id}, 'ACCEPTED')" class="btn-primary">Aceptar</button>
                    <button onclick="updateAssignment(${assignment.id}, 'REJECTED')" class="btn-secondary">Rechazar</button>
                </div>
            `;
        case 'ACCEPTED':
            return `
                <div class="assignment-actions">
                    <button onclick="updateAssignment(${assignment.id}, 'IN_TRANSIT')" class="btn-primary">En Camino</button>
                </div>
            `;
        case 'IN_TRANSIT':
            return `
                <div class="assignment-actions">
                    <button onclick="updateAssignment(${assignment.id}, 'ON_SITE')" class="btn-primary">Llegue</button>
                </div>
            `;
        case 'ON_SITE':
            return `
                <div class="assignment-actions">
                    <button onclick="updateAssignment(${assignment.id}, 'COMPLETED')" class="btn-primary">Completar</button>
                </div>
            `;
        default:
            return '';
    }
}

async function updateAssignment(assignmentId, status) {
    try {
        const response = await fetch(`${API_BASE}/assignments/${assignmentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });

        const result = await response.json();

        if (response.ok) {
            showMessage('success', `Estado actualizado a ${getStatusLabel(status)}`);
            loadAssignments();
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        showMessage('error', error.message);
    }
}

// ============================================================
// HELPERS
// ============================================================

async function loadWitnessData() {
    try {
        const response = await fetch(`${API_BASE}/${witnessId}`);
        const data = await response.json();

        if (data.success) {
            witnessData = data.witness;
            updateWitnessUI();
        }
    } catch (error) {
        console.error('[Witness] Load data error:', error);
    }
}

function updateWitnessUI() {
    if (!witnessData) return;

    const nameEl = document.getElementById('witness-name');
    if (nameEl) nameEl.textContent = witnessData.full_name;

    const statusEl = document.getElementById('witness-status');
    if (statusEl) {
        statusEl.textContent = getStatusLabel(witnessData.status);
        statusEl.className = `status-badge status-${witnessData.status.toLowerCase()}`;
    }
}

function getStatusLabel(status) {
    const labels = {
        'PENDING': 'Pendiente',
        'ACTIVE': 'Activo',
        'ASSIGNED': 'Asignado',
        'BUSY': 'Ocupado',
        'OFFLINE': 'Desconectado',
        'INACTIVE': 'Inactivo',
        'ACCEPTED': 'Aceptado',
        'IN_TRANSIT': 'En Camino',
        'ON_SITE': 'En el Sitio',
        'COMPLETED': 'Completado',
        'CANCELLED': 'Cancelado',
        'REJECTED': 'Rechazado'
    };
    return labels[status] || status;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('es-CO', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showMessage(type, message) {
    const container = document.getElementById('message-container');
    if (!container) {
        alert(message);
        return;
    }

    const div = document.createElement('div');
    div.className = `message message-${type}`;
    div.textContent = message;

    container.appendChild(div);

    setTimeout(() => {
        div.remove();
    }, 5000);
}

/**
 * Convierte VAPID key de base64 a Uint8Array
 */
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// ============================================================
// EXPORTS para uso global
// ============================================================

window.enablePushNotifications = enablePushNotifications;
window.disablePushNotifications = disablePushNotifications;
window.updateAssignment = updateAssignment;
window.loadAssignments = loadAssignments;
