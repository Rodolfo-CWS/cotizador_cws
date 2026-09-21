/* ============================================================
   Sifra — Calculadora temporal para campos numéricos
   ============================================================
   Botón ícono discreto que aparece al enfocar un campo numérico
   y abre una mini-calculadora (+, −, ×, ÷) para insertar el
   resultado sin salir del formulario.

   Uso:
       initCalcCalculator('.cantidad-item, .transporte, .instalacion');

   Sin dependencias (funciona con y sin Tailwind). Reusa las
   clases CSS de static/css/style.css (`.calc-trigger` / `.calc-pop`).
   ============================================================ */

(function (global) {
    'use strict';

    var MARGIN = 8;          // margen respecto a los bordes del viewport
    var TRIGGER_SIZE = 30;   // alto/ancho del botón flotante

    var initialized = false;
    var selector = '';

    var trigger = null;   // botón flotante (ícono calculadora)
    var pop = null;       // panel de la calculadora
    var displayEl = null; // pantalla de la calculadora

    var activeInput = null;  // input objetivo de la inserción
    var popOpen = false;

    var hideTimer = null;

    // Estado de la calculadora
    var calc = { current: '', previous: null, op: null, resetNext: false, error: false };

    /* ---------- util ---------- */
    function formatNumber(n) {
        if (!isFinite(n)) return null;
        var rounded = Math.round(n * 1e10) / 1e10;
        return String(rounded);
    }

    function compute(a, b, op) {
        var x = parseFloat(a);
        var y = parseFloat(b);
        if (op === '÷' && y === 0) return null; // división entre cero
        var r;
        if (op === '+') r = x + y;
        else if (op === '−') r = x - y;
        else if (op === '×') r = x * y;
        else if (op === '÷') r = x / y;
        else r = y;
        return formatNumber(r);
    }

    function displayText() {
        if (calc.error) return 'Error';
        if (calc.current !== '') return calc.current;
        if (calc.previous !== null && calc.previous !== '') return calc.previous;
        return '0';
    }

    function renderDisplay() {
        if (displayEl) displayEl.textContent = displayText();
    }

    /* ---------- lógica de la calculadora ---------- */
    function clearAll() {
        calc.current = '';
        calc.previous = null;
        calc.op = null;
        calc.resetNext = false;
        calc.error = false;
        renderDisplay();
    }

    function digit(d) {
        if (calc.resetNext || calc.error) {
            calc.current = '';
            calc.previous = null;
            calc.op = null;
            calc.resetNext = false;
            calc.error = false;
        }
        if (d === '.') {
            if (calc.current.indexOf('.') !== -1) return;
            if (calc.current === '') calc.current = '0';
            calc.current += '.';
        } else {
            if (calc.current === '0') calc.current = d;
            else calc.current += d;
        }
        renderDisplay();
    }

    function backspace() {
        if (calc.error) { clearAll(); return; }
        if (calc.resetNext) return;
        if (calc.current !== '') {
            calc.current = calc.current.slice(0, -1);
        }
        renderDisplay();
    }

    function chooseOp(op) {
        if (calc.error) return;
        if (calc.op && calc.current !== '' && calc.previous !== null) {
            var r = compute(calc.previous, calc.current, calc.op);
            if (r === null) { showError(); return; }
            calc.previous = r;
            calc.current = '';
        } else if (calc.current !== '') {
            calc.previous = calc.current;
            calc.current = '';
        }
        calc.op = op;
        calc.resetNext = false;
        renderDisplay();
    }

    function equals() {
        if (calc.error) return;
        if (calc.op && calc.previous !== null && calc.current !== '') {
            var r = compute(calc.previous, calc.current, calc.op);
            if (r === null) { showError(); return; }
            calc.current = r;
            calc.previous = null;
            calc.op = null;
            calc.resetNext = true;
            renderDisplay();
        }
    }

    function showError() {
        calc.current = '';
        calc.previous = null;
        calc.op = null;
        calc.resetNext = false;
        calc.error = true;
        renderDisplay();
    }

    /* ---------- apertura / cierre ---------- */
    function seedFromInput() {
        clearAll();
        if (!activeInput) return;
        var v = (activeInput.value || '').trim().replace(',', '.');
        if (v !== '' && isFinite(parseFloat(v))) {
            calc.current = v;
        }
        renderDisplay();
    }

    function openPop(input) {
        activeInput = input;
        seedFromInput();
        pop.style.display = 'block';
        pop.style.visibility = 'hidden';
        positionPop();
        pop.style.visibility = 'visible';
        popOpen = true;
        hideTrigger();
    }

    function closePop() {
        pop.style.display = 'none';
        popOpen = false;
    }

    function insertResult() {
        var val = displayText();
        if (val === 'Error') { closePop(); return; }
        val = val.replace(/\.$/, '');
        var num = parseFloat(val);
        if (!isFinite(num)) { closePop(); return; }
        if (activeInput && activeInput.isConnected) {
            activeInput.value = formatNumber(num);
            // Dispara el recálculo existente en cada formulario
            // (formulario.html usa listeners delegados en document;
            //  pdf_simple.html usa oninput="recalcular()").
            activeInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        closePop();
    }

    /* ---------- posicionamiento ---------- */
    function positionTrigger() {
        if (!activeInput) return;
        var r = activeInput.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) { hideTrigger(); return; }

        var left = r.right + 4;
        if (left + TRIGGER_SIZE > global.innerWidth - MARGIN) left = r.left - TRIGGER_SIZE - 4;
        if (left < MARGIN) left = r.right - TRIGGER_SIZE - 4;

        var top = r.top + (r.height - TRIGGER_SIZE) / 2;
        top = Math.max(MARGIN, Math.min(top, global.innerHeight - TRIGGER_SIZE - MARGIN));

        trigger.style.left = left + 'px';
        trigger.style.top = top + 'px';
        trigger.style.display = 'flex';
    }

    function positionPop() {
        if (!activeInput) return;
        var r = activeInput.getBoundingClientRect();
        var pw = pop.offsetWidth || 232;
        var ph = pop.offsetHeight || 320;

        var left = Math.max(MARGIN, Math.min(r.left, global.innerWidth - pw - MARGIN));
        var top = r.bottom + 6;
        if (top + ph > global.innerHeight - MARGIN) {
            top = r.top - ph - 6;
            if (top < MARGIN) top = MARGIN;
        }

        pop.style.left = left + 'px';
        pop.style.top = top + 'px';
    }

    function inputInView() {
        if (!activeInput) return false;
        var r = activeInput.getBoundingClientRect();
        return r.bottom > 0 && r.top < global.innerHeight && r.right > 0 && r.left < global.innerWidth;
    }

    function syncPositions() {
        if (!inputInView()) {
            hideTrigger();
            if (popOpen) closePop();
            return;
        }
        if (trigger.style.display !== 'none') positionTrigger();
        if (popOpen) positionPop();
    }

    function showTriggerFor(input) {
        if (popOpen && input !== activeInput) {
            // Si el popover está abierto y se enfoca otro campo, lo re-encauza
            activeInput = input;
            seedFromInput();
            positionPop();
            return;
        }
        activeInput = input;
        clearTimeout(hideTimer);
        positionTrigger();
    }

    function hideTrigger() {
        clearTimeout(hideTimer);
        if (trigger) trigger.style.display = 'none';
    }

    /* ---------- construcción del DOM ---------- */
    function buildTrigger() {
        trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'calc-trigger';
        trigger.setAttribute('aria-label', 'Abrir calculadora');
        trigger.setAttribute('title', 'Calculadora');
        trigger.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
            'stroke-linecap="round" stroke-linejoin="round">' +
            '<rect x="4" y="2" width="16" height="20" rx="2"></rect>' +
            '<line x1="8" y1="6" x2="16" y2="6"></line>' +
            '<line x1="8" y1="11" x2="8" y2="11.01"></line>' +
            '<line x1="12" y1="11" x2="12" y2="11.01"></line>' +
            '<line x1="16" y1="11" x2="16" y2="11.01"></line>' +
            '<line x1="8" y1="15" x2="8" y2="15.01"></line>' +
            '<line x1="12" y1="15" x2="12" y2="15.01"></line>' +
            '<line x1="16" y1="15" x2="16" y2="18"></line>' +
            '</svg>';
        trigger.style.display = 'none';
        trigger.addEventListener('pointerdown', function (e) {
            e.preventDefault();
            if (activeInput) openPop(activeInput);
        });
        document.body.appendChild(trigger);
    }

    var KEYS = [
        { t: 'C', a: 'ac', cls: 'calc-pop__key--ac' },
        { t: '⌫', a: 'back' },
        { t: '÷', a: 'op', v: '÷', cls: 'calc-pop__key--op' },
        { t: '×', a: 'op', v: '×', cls: 'calc-pop__key--op' },
        { t: '7', a: 'digit', v: '7' },
        { t: '8', a: 'digit', v: '8' },
        { t: '9', a: 'digit', v: '9' },
        { t: '−', a: 'op', v: '−', cls: 'calc-pop__key--op' },
        { t: '4', a: 'digit', v: '4' },
        { t: '5', a: 'digit', v: '5' },
        { t: '6', a: 'digit', v: '6' },
        { t: '+', a: 'op', v: '+', cls: 'calc-pop__key--op' },
        { t: '1', a: 'digit', v: '1' },
        { t: '2', a: 'digit', v: '2' },
        { t: '3', a: 'digit', v: '3' },
        { t: '.', a: 'dot', v: '.' },
        { t: '0', a: 'digit', v: '0', cls: 'calc-pop__key--zero' },
        { t: '=', a: 'eq', cls: 'calc-pop__key--eq' }
    ];

    function handleKey(key) {
        switch (key.a) {
            case 'ac': clearAll(); break;
            case 'back': backspace(); break;
            case 'digit': digit(key.v); break;
            case 'dot': digit('.'); break;
            case 'op': chooseOp(key.v); break;
            case 'eq': equals(); break;
        }
    }

    function buildPop() {
        pop = document.createElement('div');
        pop.className = 'calc-pop';
        pop.style.display = 'none';
        pop.setAttribute('role', 'dialog');
        pop.setAttribute('aria-label', 'Calculadora');

        var head =
            '<div class="calc-pop__head">' +
            '<span class="calc-pop__title">Calculadora</span>' +
            '<button type="button" class="calc-pop__close" aria-label="Cerrar">✕</button>' +
            '</div>';
        var display = '<div class="calc-pop__display"></div>';

        var keysHtml = KEYS.map(function (k) {
            return '<button type="button" class="calc-pop__key ' + (k.cls || '') + '" data-key="' + k.a + '" data-val="' + (k.v || '') + '">' + k.t + '</button>';
        }).join('');

        var ok = '<button type="button" class="calc-pop__key--ok">Insertar ✓</button>';

        pop.innerHTML =
            head +
            '<div class="calc-pop__body">' +
            display +
            '<div class="calc-pop__keys">' + keysHtml + '</div>' +
            '</div>' +
            ok;

        document.body.appendChild(pop);
        displayEl = pop.querySelector('.calc-pop__display');

        pop.querySelector('.calc-pop__close').addEventListener('click', closePop);
        pop.querySelector('.calc-pop__key--ok').addEventListener('click', insertResult);

        // Delegación de teclas dentro del popover
        pop.querySelector('.calc-pop__keys').addEventListener('click', function (e) {
            var btn = e.target.closest('.calc-pop__key');
            if (!btn) return;
            var a = btn.getAttribute('data-key');
            var v = btn.getAttribute('data-val');
            handleKey({ a: a, v: v });
        });
    }

    /* ---------- listeners globales ---------- */
    function setup() {
        buildTrigger();
        buildPop();

        // Mostrar el botón al enfocar/tocar un campo objetivo
        document.addEventListener('focusin', function (e) {
            if (e.target && e.target.matches && e.target.matches(selector)) {
                showTriggerFor(e.target);
            }
        });
        document.addEventListener('click', function (e) {
            if (e.target && e.target.matches && e.target.matches(selector)) {
                showTriggerFor(e.target);
            }
        });

        // Ocultar el botón al salir del campo (con un pequeño delay)
        document.addEventListener('focusout', function (e) {
            if (e.target === activeInput) {
                clearTimeout(hideTimer);
                hideTimer = setTimeout(hideTrigger, 180);
            }
        });

        // Cerrar el popover al tocar fuera (excepto dentro del pop, el botón o un campo objetivo)
        document.addEventListener('pointerdown', function (e) {
            if (!popOpen) return;
            if (pop.contains(e.target)) return;
            if (e.target === trigger) return;
            if (e.target && e.target.matches && e.target.matches(selector)) return;
            closePop();
        });

        // Esc cierra el popover
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closePop();
                hideTrigger();
            }
        });

        // Mantener posiciones correctas al hacer scroll / redimensionar
        global.addEventListener('scroll', syncPositions, true);
        global.addEventListener('resize', syncPositions);
    }

    function initCalcCalculator(sel) {
        if (typeof sel !== 'string' || !sel) return;
        selector = sel;
        if (initialized) return;
        initialized = true;
        setup();
    }

    global.initCalcCalculator = initCalcCalculator;
})(window);
