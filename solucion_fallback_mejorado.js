// SOLUCIÓN: Mejorar el fallback automático en home.html
// Reemplazar la función buscar() existente con esta versión mejorada:

function buscar() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        mostrarMensaje('Por favor ingresa un término de búsqueda', 'error');
        return;
    }

    ultimaBusqueda = query;
    const btnBuscar = document.getElementById('searchButton');
    btnBuscar.disabled = true;
    btnBuscar.classList.add('loading');
    btnBuscar.innerHTML = '<svg class="animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z" opacity=".25"/><path d="M10.14,1.16A11,11,0,0,0,9,5.74V3A8,8,0,0,1,10.14,1.16Z"/></svg>';
    
    console.log(`🔍 Buscando: "${query}"`);
    
    // MEJORADO: Intentar primero PDFs, luego fallback automático
    fetch('/buscar_pdfs', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        console.log('📄 Respuesta de PDFs:', data);
        
        // NUEVO: Si no hay resultados en PDFs, hacer fallback AUTOMÁTICO
        if (!data.resultados || data.resultados.length === 0) {
            console.log('🔄 Sin resultados en PDFs, ejecutando fallback a cotizaciones...');
            
            return fetch('/buscar', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(fallbackData => {
                console.log('✅ Fallback exitoso - cotizaciones:', fallbackData);
                
                // Marcar los resultados como provenientes de cotizaciones
                if (fallbackData.resultados) {
                    fallbackData.resultados.forEach(resultado => {
                        resultado._es_de_cotizaciones = true;
                        resultado.tiene_desglose = true; // Asegurar que tenga desglose
                    });
                }
                
                return fallbackData;
            });
        }
        
        return data;
    })
    .then(data => {
        if (data.error) {
            mostrarMensaje(`Error: ${data.error}`, 'error');
            return;
        }
        
        procesarRespuesta(data);
    })
    .catch(error => {
        console.error('❌ Error completo en búsqueda:', error);
        mostrarMensaje(`Error al buscar: ${error.message}`, 'error');
    })
    .finally(() => {
        btnBuscar.disabled = false;
        btnBuscar.classList.remove('loading');
        btnBuscar.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>';
    });
}

// SOLUCIÓN: Mejorar la detección en mostrarResultados
function mostrarResultados(pdfs, total) {
    const div = document.getElementById('resultados');
    
    if (!pdfs || pdfs.length === 0) {
        mostrarMensaje(`No se encontraron PDFs para "${ultimaBusqueda}"`, 'error');
        return;
    }

    let html = `
        <div class="stats">
            <strong>${pdfs.length}</strong> PDF(s) encontrado(s)
            ${ultimaBusqueda ? `para "<em>${ultimaBusqueda}</em>"` : ''}
        </div>
    `;
    
    pdfs.forEach((pdf, index) => {
        // MEJORADO: Mejor detección del origen
        const esCotizacion = pdf._es_de_cotizaciones || (pdf._id && !pdf.numero_cotizacion);
        const identificador = esCotizacion ? pdf._id : (pdf.numero_cotizacion || `PDF-${index + 1}`);
        const numeroDisplay = esCotizacion ? 
            (pdf.numeroCotizacion || pdf.datosGenerales?.numeroCotizacion || identificador) : 
            (pdf.numero_cotizacion || `PDF-${index + 1}`);
            
        const clienteDisplay = esCotizacion ? 
            (pdf.datosGenerales?.cliente || 'Cliente no especificado') : 
            (pdf.cliente || 'Cliente no especificado');
            
        const vendedorDisplay = esCotizacion ? 
            (pdf.datosGenerales?.vendedor || 'Vendedor no especificado') : 
            (pdf.vendedor || 'Vendedor no especificado');
            
        const proyectoDisplay = esCotizacion ? 
            (pdf.datosGenerales?.proyecto || 'Proyecto no especificado') : 
            (pdf.proyecto || 'Proyecto no especificado');
            
        const fechaDisplay = esCotizacion ? 
            (pdf.datosGenerales?.fecha || pdf.fechaCreacion || 'Fecha no especificada') : 
            (pdf.fecha || 'Fecha no especificada');
            
        const tipoDisplay = pdf.tipo === 'nueva' ? 'Nueva' : 
                           esCotizacion ? 'Cotización' : 'Histórica';
                           
        // CORREGIDO: Asegurar que las cotizaciones siempre tengan desglose disponible
        const tieneDesglose = esCotizacion ? true : (pdf.tiene_desglose || false);
        
        // Función para resaltar coincidencias
        const resaltarTexto = (texto) => {
            if (!ultimaBusqueda) return texto;
            const regex = new RegExp(`(${ultimaBusqueda})`, 'gi');
            return texto.replace(regex, '<mark>$1</mark>');
        };
        
        html += `
            <div class="result-item" style="cursor: default;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <div class="result-field">
                            <strong>Número:</strong> 
                            <span class="value" style="color: #4f46e5; font-weight: bold;">${resaltarTexto(numeroDisplay)}</span>
                        </div>
                        <div class="result-field">
                            <strong>Cliente:</strong> 
                            <span class="value">${resaltarTexto(clienteDisplay)}</span>
                        </div>
                        <div class="result-field">
                            <strong>Vendedor:</strong> 
                            <span class="value">${resaltarTexto(vendedorDisplay)}</span>
                        </div>
                        <div class="result-field">
                            <strong>Proyecto:</strong> 
                            <span class="value">${resaltarTexto(proyectoDisplay)}</span>
                        </div>
                        <div class="result-field">
                            <strong>Fecha:</strong> 
                            <span class="value">${fechaDisplay}</span>
                        </div>
                        <div class="result-field">
                            <strong>Tipo:</strong> 
                            <span class="value" style="color: ${esCotizacion ? '#10b981' : (pdf.tipo === 'nueva' ? '#10b981' : '#f59e0b')};">${tipoDisplay}</span>
                        </div>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 8px; margin-left: 15px;">
                        <button onclick="verPDF('${numeroDisplay}')" 
                                class="icon-button btn-search" 
                                style="width: auto; padding: 8px 12px; font-size: 12px;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                            </svg>
                            Ver PDF
                        </button>
                        ${tieneDesglose ? `
                        <button onclick="verDesglose('${esCotizacion ? identificador : numeroDisplay}')" 
                                class="icon-button" 
                                style="width: auto; padding: 8px 12px; font-size: 12px; background: #10b981; color: white; border-color: #10b981;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M3,3H21V5H3V3M3,7H21V9H3V7M3,11H21V13H3V11M3,15H21V17H3V15M3,19H21V21H3V19Z"/>
                            </svg>
                            Desglose
                        </button>
                        ` : `
                        <div style="font-size: 11px; color: #6c757d; text-align: center; padding: 8px;">
                            Sin desglose<br>disponible
                        </div>
                        `}
                    </div>
                </div>
            </div>
        `;
    });

    div.innerHTML = html;
}