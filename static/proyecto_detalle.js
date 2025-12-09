// JavaScript para proyecto_detalle.html

const proyectoId = window.location.pathname.split('/')[2];

// ========================================
// MODAL: NUEVO GASTO
// ========================================

function abrirModalNuevoGasto() {
    document.getElementById('modalNuevoGasto').style.display = 'flex';
    document.getElementById('formNuevoGasto').reset();
    calcularSubtotal();
}

function cerrarModalNuevoGasto() {
    document.getElementById('modalNuevoGasto').style.display = 'none';
}

// Calcular subtotal en tiempo real
document.addEventListener('DOMContentLoaded', function() {
    const cantidad = document.querySelector('input[name="cantidad"]');
    const precio = document.querySelector('input[name="precio_unitario"]');

    if (cantidad && precio) {
        cantidad.addEventListener('input', calcularSubtotal);
        precio.addEventListener('input', calcularSubtotal);
    }
});

function calcularSubtotal() {
    const cantidad = parseFloat(document.querySelector('input[name="cantidad"]').value) || 0;
    const precio = parseFloat(document.querySelector('input[name="precio_unitario"]').value) || 0;
    const subtotal = cantidad * precio;

    document.getElementById('subtotalDisplay').value = `$${subtotal.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

// Enviar formulario de nuevo gasto
document.getElementById('formNuevoGasto').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const data = {
        proyecto_id: proyectoId,
        concepto: formData.get('concepto'),
        proveedor: formData.get('proveedor'),
        cantidad: parseFloat(formData.get('cantidad')),
        unidad: formData.get('unidad'),
        precio_unitario: parseFloat(formData.get('precio_unitario')),
        notas: formData.get('notas')
    };

    try {
        const response = await fetch(`/api/proyectos/${proyectoId}/gastos/crear`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ Gasto creado exitosamente');
            location.reload();
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error al crear el gasto');
    }
});

// ========================================
// ACCIONES DE GASTOS
// ========================================

async function aprobarGasto(gastoId) {
    if (!confirm('¿Aprobar este gasto?')) return;

    try {
        const response = await fetch(`/api/gastos/${gastoId}/aprobar`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            alert('✅ Gasto aprobado');
            location.reload();
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error al aprobar el gasto');
    }
}

async function rechazarGasto(gastoId) {
    const motivo = prompt('¿Por qué rechazas este gasto? (opcional)');
    if (motivo === null) return; // Canceló

    try {
        const response = await fetch(`/api/gastos/${gastoId}/rechazar`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ motivo })
        });

        const result = await response.json();

        if (result.success) {
            alert('❌ Gasto rechazado');
            location.reload();
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error al rechazar el gasto');
    }
}

function marcarOrdenado(gastoId) {
    document.getElementById('gastoIdOrdenado').value = gastoId;
    document.getElementById('modalOrdenado').style.display = 'flex';

    // Establecer fecha actual
    const hoy = new Date().toISOString().split('T')[0];
    document.querySelector('input[name="fecha_orden"]').value = hoy;
}

function cerrarModalOrdenado() {
    document.getElementById('modalOrdenado').style.display = 'none';
}

document.getElementById('formOrdenado').addEventListener('submit', async function(e) {
    e.preventDefault();

    const gastoId = document.getElementById('gastoIdOrdenado').value;
    const formData = new FormData(this);

    try {
        const response = await fetch(`/api/gastos/${gastoId}/marcar-ordenado`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                numero_orden: formData.get('numero_orden'),
                fecha_orden: formData.get('fecha_orden')
            })
        });

        const result = await response.json();

        if (result.success) {
            alert('🟡 Gasto marcado como ordenado');
            location.reload();
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error al marcar como ordenado');
    }
});

async function marcarRecibido(gastoId) {
    if (!confirm('¿Marcar este gasto como recibido?')) return;

    try {
        const response = await fetch(`/api/gastos/${gastoId}/marcar-recibido`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            alert('🟢 Gasto marcado como recibido');
            location.reload();
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error al marcar como recibido');
    }
}

function editarGasto(gastoId) {
    // TODO: Implementar modal de edición
    alert('Función de edición en desarrollo');
}

// Cerrar modales al hacer click fuera
window.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.style.display = 'none';
    }
});
