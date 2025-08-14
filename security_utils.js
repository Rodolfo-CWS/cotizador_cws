/**
 * UTILIDADES DE SEGURIDAD CWS
 * Funciones para prevenir XSS y sanitizar datos
 */

class SecurityUtils {
    /**
     * Escapa caracteres HTML para prevenir XSS
     * @param {string} unsafe - String no seguro
     * @returns {string} String escapado y seguro
     */
    static escapeHTML(unsafe) {
        if (typeof unsafe !== 'string') {
            return '';
        }
        
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
            .replace(/\//g, "&#x2F;");
    }

    /**
     * Sanitiza números financieros
     * @param {any} value - Valor a sanitizar
     * @param {number} defaultValue - Valor por defecto
     * @returns {number} Número validado y seguro
     */
    static sanitizeFinancialNumber(value, defaultValue = 0) {
        const num = parseFloat(value);
        
        // Validaciones de seguridad
        if (isNaN(num) || !isFinite(num)) {
            return defaultValue;
        }
        
        // Rango válido para datos financieros (0 a 1 millón)
        if (num < 0 || num > 1000000) {
            console.warn(`Valor financiero fuera de rango: ${num}`);
            return defaultValue;
        }
        
        return Math.round(num * 100) / 100; // Redondear a 2 decimales
    }

    /**
     * Crea elementos DOM de forma segura
     * @param {string} tag - Tag del elemento
     * @param {Object} attributes - Atributos del elemento
     * @param {string} textContent - Contenido de texto (será escapado)
     * @returns {HTMLElement} Elemento creado de forma segura
     */
    static createSecureElement(tag, attributes = {}, textContent = '') {
        const element = document.createElement(tag);
        
        // Establecer atributos de forma segura
        Object.keys(attributes).forEach(key => {
            if (key === 'innerHTML') {
                console.error('innerHTML no permitido - usar textContent');
                return;
            }
            element.setAttribute(key, this.escapeHTML(String(attributes[key])));
        });
        
        // Establecer contenido de forma segura
        if (textContent) {
            element.textContent = textContent;
        }
        
        return element;
    }

    /**
     * Actualiza contenido de forma segura usando textContent
     * @param {string} elementId - ID del elemento
     * @param {string} content - Contenido a establecer
     */
    static updateSecureContent(elementId, content) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = this.escapeHTML(String(content));
        }
    }

    /**
     * Valida y sanitiza datos de cotización
     * @param {Object} cotizacionData - Datos de la cotización
     * @returns {Object} Datos sanitizados
     */
    static sanitizeCotizacionData(cotizacionData) {
        const sanitized = {};
        
        // Sanitizar campos de texto
        const textFields = ['cliente', 'vendedor', 'proyecto', 'descripcion'];
        textFields.forEach(field => {
            if (cotizacionData[field]) {
                sanitized[field] = this.escapeHTML(cotizacionData[field]);
            }
        });
        
        // Sanitizar campos numéricos
        const numberFields = ['peso', 'cantidad', 'precio', 'subtotal', 'tipoCambio'];
        numberFields.forEach(field => {
            if (cotizacionData[field] !== undefined) {
                sanitized[field] = this.sanitizeFinancialNumber(cotizacionData[field]);
            }
        });
        
        return sanitized;
    }

    /**
     * Genera token CSRF simple para formularios
     * @returns {string} Token CSRF
     */
    static generateCSRFToken() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }

    /**
     * Agrega token CSRF a formularios
     * @param {HTMLFormElement} form - Formulario
     */
    static addCSRFTokenToForm(form) {
        const token = this.generateCSRFToken();
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = token;
        form.appendChild(input);
        
        // Almacenar en sessionStorage para validación
        sessionStorage.setItem('csrf_token', token);
    }
}

// Prevenir logging de datos sensibles en producción
if (window.location.hostname !== 'localhost') {
    console.log = function() {}; // Deshabilitar console.log en producción
    console.warn = function() {};
    console.error = function() {}; // Mantener errores solo para desarrollo
}

// Exportar para uso global
window.SecurityUtils = SecurityUtils;