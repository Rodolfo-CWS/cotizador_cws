/* ============================================
   CWS Cotizador — Toast Notification System
   Usa las clases CSS definidas en style.css
   ============================================ */

/**
 * Muestra un toast de notificación no bloqueante.
 * @param {string} mensaje - Texto a mostrar
 * @param {string} tipo - 'success' | 'error' | 'warning' | 'info'
 * @param {number} duracion - ms antes de auto-dismiss (default: 4000 success/info, 6000 error/warning)
 */
function showToast(mensaje, tipo, duracion) {
    tipo = tipo || 'info';
    duracion = duracion || (tipo === 'error' || tipo === 'warning' ? 6000 : 4000);

    // Crear o reusar el contenedor
    var container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    // Crear el toast
    var toast = document.createElement('div');
    toast.className = 'toast ' + tipo;

    // Icono según tipo
    var iconos = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    toast.innerHTML = '<span>' + (iconos[tipo] || '') + '</span><span>' + mensaje + '</span>';

    container.appendChild(toast);

    // Auto-dismiss
    setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
            // Limpiar contenedor vacío
            if (container.children.length === 0 && container.parentNode) {
                container.parentNode.removeChild(container);
            }
        }, 300);
    }, duracion);
}

/**
 * Muestra un toast de confirmación con botones Aceptar/Cancelar.
 * @param {string} mensaje - Pregunta a mostrar
 * @returns {Promise<boolean>} - true si aceptó, false si canceló
 */
function showConfirm(mensaje) {
    return new Promise(function (resolve) {
        var container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        var toast = document.createElement('div');
        toast.className = 'toast warning';
        toast.style.flexDirection = 'column';
        toast.style.gap = '12px';
        toast.style.alignItems = 'stretch';

        toast.innerHTML =
            '<div style="display:flex;align-items:center;gap:10px;">' +
            '<span>⚠️</span>' +
            '<span style="flex:1;">' + mensaje + '</span>' +
            '</div>' +
            '<div style="display:flex;gap:8px;justify-content:flex-end;">' +
            '<button class="btn-cancel" style="padding:6px 16px;border:1px solid #d1d5db;border-radius:6px;background:white;color:#374151;cursor:pointer;font-size:13px;font-weight:500;">Cancelar</button>' +
            '<button class="btn-accept" style="padding:6px 16px;border:none;border-radius:6px;background:var(--primary,#4f46e5);color:white;cursor:pointer;font-size:13px;font-weight:500;">Aceptar</button>' +
            '</div>';

        container.appendChild(toast);

        function limpiar() {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(function () {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
                if (container.children.length === 0 && container.parentNode) {
                    container.parentNode.removeChild(container);
                }
            }, 300);
        }

        toast.querySelector('.btn-accept').onclick = function () {
            limpiar();
            resolve(true);
        };
        toast.querySelector('.btn-cancel').onclick = function () {
            limpiar();
            resolve(false);
        };

        // Auto-dismiss después de 15s si no responde
        setTimeout(function () {
            if (toast.parentNode) {
                limpiar();
                resolve(false);
            }
        }, 15000);
    });
}
