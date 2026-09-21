/* ============================================================
   Sifra — Calculadora flotante global
   ============================================================
   Botón flotante fijo (FAB), independiente de cualquier campo y
   siempre visible sin importar el scroll. Al hacer clic abre una
   mini-calculadora (+, −, ×, ÷) en popup; el resultado se copia
   al portapapeles para pegarlo donde el usuario necesite.

   Uso:
       initFloatingCalculator();

   Sin dependencias (funciona con y sin Tailwind). Reusa las
   clases CSS de static/css/style.css (`.calc-fab` / `.calc-pop`).
   ============================================================ */

(function (global) {
    'use strict';

    var MARGIN = 12; // margen respecto a los bordes del viewport

    var initialized = false;

    var fab = null;       // botón flotante fijo
    var pop = null;       // panel de la calculadora
    var displayEl = null; // pantalla de la calculadora
    var copyBtn = null;   // botón "Copiar"

    var popOpen = false;
    var copyResetTimer = null;

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
    function positionPop() {
        if (!fab || !pop) return;
        var fabRect = fab.getBoundingClientRect();
        var pw = pop.offsetWidth || 240;
        var ph = pop.offsetHeight || 360;

        // Anclado a la derecha, alineado con el FAB
        var left = fabRect.right - pw;
        left = Math.max(MARGIN, Math.min(left, global.innerWidth - pw - MARGIN));

        // Arriba del FAB; si no cabe, debajo (clampado al viewport)
        var top = fabRect.top - ph - 8;
        if (top < MARGIN) {
            top = fabRect.bottom + 8;
            if (top + ph > global.innerHeight - MARGIN) top = global.innerHeight - ph - MARGIN;
        }

        pop.style.left = left + 'px';
        pop.style.top = top + 'px';
    }

    function openPop() {
        pop.style.display = 'block';
        pop.style.visibility = 'hidden';
        positionPop();
        pop.style.visibility = 'visible';
        popOpen = true;
    }

    function closePop() {
        pop.style.display = 'none';
        popOpen = false;
    }

    function togglePop() {
        if (popOpen) closePop();
        else openPop();
    }

    /* ---------- copiar al portapapeles ---------- */
    function fallbackCopy(text, onDone) {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.top = '0';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, ta.value.length);
        var ok = false;
        try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
        document.body.removeChild(ta);
        onDone(!!ok);
    }

    function copyResult() {
        var val = displayText();
        if (val === 'Error') val = '0';
        val = val.replace(/\.$/, '');

        function onDone(ok) {
            if (!copyBtn) return;
            copyBtn.textContent = ok ? 'Copiado ✓' : 'No se pudo copiar';
            copyBtn.classList.toggle('calc-pop__copy--ok', ok);
            clearTimeout(copyResetTimer);
            copyResetTimer = setTimeout(function () {
                copyBtn.textContent = 'Copiar';
                copyBtn.classList.remove('calc-pop__copy--ok');
            }, 1500);
        }

        if (global.navigator && navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(val).then(
                function () { onDone(true); },
                function () { fallbackCopy(val, onDone); }
            );
        } else {
            fallbackCopy(val, onDone);
        }
    }

    /* ---------- construcción del DOM ---------- */
    function buildFab() {
        fab = document.createElement('button');
        fab.type = 'button';
        fab.className = 'calc-fab';
        fab.setAttribute('aria-label', 'Abrir calculadora');
        fab.setAttribute('title', 'Calculadora');
        fab.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
            '<rect x="4" y="2" width="16" height="20" rx="2"></rect>' +
            '<line x1="8" y1="6" x2="16" y2="6"></line>' +
            '<line x1="8" y1="11" x2="8" y2="11.01"></line>' +
            '<line x1="12" y1="11" x2="12" y2="11.01"></line>' +
            '<line x1="16" y1="11" x2="16" y2="11.01"></line>' +
            '<line x1="8" y1="15" x2="8" y2="15.01"></line>' +
            '<line x1="12" y1="15" x2="12" y2="15.01"></line>' +
            '<line x1="16" y1="15" x2="16" y2="18"></line>' +
            '</svg>';
        fab.addEventListener('click', function (e) {
            e.stopPropagation();
            togglePop();
        });
        document.body.appendChild(fab);
    }

    var KEYS = [
        { t: 'C',  a: 'ac',              cls: 'calc-pop__key--ac' },
        { t: '⌫', a: 'back' },
        { t: '÷',  a: 'op', v: '÷',      cls: 'calc-pop__key--op' },
        { t: '×',  a: 'op', v: '×',      cls: 'calc-pop__key--op' },
        { t: '7',  a: 'digit', v: '7' },
        { t: '8',  a: 'digit', v: '8' },
        { t: '9',  a: 'digit', v: '9' },
        { t: '−',  a: 'op', v: '−',      cls: 'calc-pop__key--op' },
        { t: '4',  a: 'digit', v: '4' },
        { t: '5',  a: 'digit', v: '5' },
        { t: '6',  a: 'digit', v: '6' },
        { t: '+',  a: 'op', v: '+',      cls: 'calc-pop__key--op' },
        { t: '1',  a: 'digit', v: '1' },
        { t: '2',  a: 'digit', v: '2' },
        { t: '3',  a: 'digit', v: '3' },
        { t: '.',  a: 'dot', v: '.' },
        { t: '0',  a: 'digit', v: '0',   cls: 'calc-pop__key--zero' },
        { t: '=',  a: 'eq',              cls: 'calc-pop__key--eq' }
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

        var copy = '<button type="button" class="calc-pop__copy">Copiar</button>';

        pop.innerHTML =
            head +
            '<div class="calc-pop__body">' +
            display +
            '<div class="calc-pop__keys">' + keysHtml + '</div>' +
            '</div>' +
            copy;

        document.body.appendChild(pop);
        displayEl = pop.querySelector('.calc-pop__display');
        copyBtn = pop.querySelector('.calc-pop__copy');

        pop.querySelector('.calc-pop__close').addEventListener('click', closePop);
        copyBtn.addEventListener('click', copyResult);

        // Delegación de teclas dentro del popup
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
        // Cerrar al tocar fuera del popup y fuera del FAB
        document.addEventListener('pointerdown', function (e) {
            if (!popOpen) return;
            if (pop.contains(e.target)) return;
            if (fab && fab.contains(e.target)) return;
            closePop();
        });

        // Esc cierra el popup
        document.addEventListener('keydown', function (e) {
            if (e.key !== 'Escape' || !popOpen) return;
            closePop();
        });

        // Teclado físico cuando el popup está abierto (opcional, no roba foco)
        document.addEventListener('keydown', function (e) {
            if (!popOpen) return;
            var k = e.key;
            if (k >= '0' && k <= '9') { e.preventDefault(); handleKey({ a: 'digit', v: k }); }
            else if (k === '.') { e.preventDefault(); handleKey({ a: 'dot', v: '.' }); }
            else if (k === '+') { e.preventDefault(); handleKey({ a: 'op', v: '+' }); }
            else if (k === '-') { e.preventDefault(); handleKey({ a: 'op', v: '−' }); }
            else if (k === '*' || k === 'x' || k === 'X') { e.preventDefault(); handleKey({ a: 'op', v: '×' }); }
            else if (k === '/') { e.preventDefault(); handleKey({ a: 'op', v: '÷' }); }
            else if (k === 'Enter' || k === '=') { e.preventDefault(); handleKey({ a: 'eq' }); }
            else if (k === 'Backspace') { e.preventDefault(); handleKey({ a: 'back' }); }
        });

        // Mantener la posición correcta al redimensionar
        global.addEventListener('resize', function () {
            if (popOpen) positionPop();
        });
    }

    function initFloatingCalculator() {
        if (initialized) return;
        initialized = true;
        buildFab();
        buildPop();
        setup();
    }

    global.initFloatingCalculator = initFloatingCalculator;
})(window);
