(function () {
    'use strict';

    var overlay = document.getElementById('modalEditarCotizacion');
    if (!overlay) return;

    var opcionMenor = document.getElementById('meOpcionMenor');
    var opcionRevision = document.getElementById('meOpcionRevision');
    var descRevision = document.getElementById('meDescRevision');
    var notaBloqueo = document.getElementById('meNotaBloqueo');
    var btnCerrar = document.getElementById('meCerrar');
    var btnCerrarFooter = document.getElementById('meCerrarFooter');

    var abortController = null;
    var timeoutId = null;

    function abrir() {
        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function cerrar() {
        overlay.style.display = 'none';
        document.body.style.overflow = '';
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
    }

    function setOpciones(tipo, numero) {
        var enc = encodeURIComponent(numero);
        // La edición menor siempre está disponible.
        opcionMenor.setAttribute('href',
            tipo === 'simple' ? '/cotizacion-pdf?numero=' + enc : '/formulario?edicion_menor=' + enc);
        // "Nueva revisión" guarda su URL; el href se fija solo al habilitarse.
        opcionRevision.setAttribute('data-url-revision',
            tipo === 'simple' ? '/cotizacion-pdf?revision=' + enc : '/formulario?revision=' + enc);
    }

    function deshabilitarRevision(motivo) {
        opcionRevision.setAttribute('aria-disabled', 'true');
        opcionRevision.removeAttribute('href');
        if (descRevision) descRevision.textContent = motivo || 'Verificando…';
    }

    function habilitarRevision(proximaRevision) {
        opcionRevision.removeAttribute('aria-disabled');
        var url = opcionRevision.getAttribute('data-url-revision');
        if (url) opcionRevision.setAttribute('href', url);
        if (descRevision) {
            descRevision.textContent = proximaRevision
                ? ('Crea R' + proximaRevision + ' con justificación obligatoria y conserva la R' + (proximaRevision - 1) + ' intacta.')
                : 'Crea una nueva revisión con justificación obligatoria y conserva la actual intacta.';
        }
    }

    function verificarEstado(numero) {
        deshabilitarRevision('Verificando…');
        notaBloqueo.style.display = 'none';
        notaBloqueo.innerHTML = '';

        if (abortController) abortController.abort();
        if (timeoutId) clearTimeout(timeoutId);
        var controller = new AbortController();
        abortController = controller;
        timeoutId = setTimeout(function () { controller.abort(); }, 5000);

        fetch('/api/revision-estado?numero=' + encodeURIComponent(numero), {
            signal: controller.signal,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (data) {
                if (timeoutId) { clearTimeout(timeoutId); timeoutId = null; }
                if (!data || data.success !== true || data.verificado === false) {
                    // Error, timeout o búsqueda no verificada: habilitar sin nota.
                    // El servidor es quien bloquea de verdad en GET ?revision=.
                    habilitarRevision(null);
                    return;
                }
                if (data.es_mas_reciente) {
                    var proxima = (data.revision_maxima || 0) + 1;
                    habilitarRevision(proxima);
                } else {
                    var max = data.revision_maxima;
                    deshabilitarRevision('Ya existe R' + max + '.');
                    if (data.numero_ultima_revision) {
                        var a = document.createElement('a');
                        a.href = '/desglose/' + encodeURIComponent(data.numero_ultima_revision);
                        a.textContent = 'Ver R' + max;
                        notaBloqueo.innerHTML = '';
                        notaBloqueo.appendChild(a);
                        notaBloqueo.style.display = 'block';
                    }
                }
            })
            .catch(function () {
                if (timeoutId) { clearTimeout(timeoutId); timeoutId = null; }
                habilitarRevision(null);
            });
    }

    // Delegación: un solo listener para cualquier botón .js-editar-cotizacion.
    document.addEventListener('click', function (e) {
        var target = e.target;
        var btn = target && target.closest ? target.closest('.js-editar-cotizacion') : null;
        if (!btn) return;
        e.preventDefault();
        var tipo = btn.getAttribute('data-tipo') || 'completa';
        var numero = btn.getAttribute('data-numero') || '';
        if (!numero) return;
        setOpciones(tipo, numero);
        abrir();
        verificarEstado(numero);
    });

    if (btnCerrar) btnCerrar.addEventListener('click', cerrar);
    if (btnCerrarFooter) btnCerrarFooter.addEventListener('click', cerrar);
    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) cerrar();
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && overlay.style.display === 'flex') cerrar();
    });
})();
