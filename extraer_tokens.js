/**
 * Script para extraer tokens de actas E14
 *
 * INSTRUCCIONES:
 * 1. Abre https://e14_pres1v_2022.registraduria.gov.co/
 * 2. Navega hasta ver las mesas de votación
 * 3. Abre la consola del navegador (F12 -> Console)
 * 4. Copia y pega este script completo
 * 5. Presiona Enter
 * 6. Los tokens se mostrarán y también se copiarán al portapapeles
 */

(function() {
    console.log('='.repeat(60));
    console.log('  EXTRACTOR DE TOKENS - ACTAS E14');
    console.log('='.repeat(60));

    const tokens = [];

    // Método 1: Buscar en atributos onclick
    document.querySelectorAll('[onclick]').forEach((el, idx) => {
        const onclick = el.getAttribute('onclick');
        const matches = onclick.match(/(?:descargar|download|descargae14)\(['"](.*?)['"]\)/);
        if (matches) {
            const nombre = el.textContent.trim() || `mesa_${idx + 1}`;
            tokens.push({
                token: matches[1],
                nombre: nombre.replace(/[^a-zA-Z0-9_-]/g, '_') + '.pdf'
            });
        }
    });

    // Método 2: Buscar data-token
    document.querySelectorAll('[data-token]').forEach((el, idx) => {
        const token = el.getAttribute('data-token');
        const nombre = el.textContent.trim() || `mesa_${idx + 1}`;
        tokens.push({
            token: token,
            nombre: nombre.replace(/[^a-zA-Z0-9_-]/g, '_') + '.pdf'
        });
    });

    // Método 3: Buscar en formularios
    document.querySelectorAll('form[action*="descarga"] input[name="token"]').forEach((input, idx) => {
        tokens.push({
            token: input.value,
            nombre: `acta_form_${idx + 1}.pdf`
        });
    });

    // Método 4: Buscar botones de mesa
    document.querySelectorAll('button, a').forEach((el) => {
        const text = el.textContent.toLowerCase();
        if (text.includes('mesa') || text.includes('descargar') || text.includes('ver acta')) {
            // Intentar encontrar token en el elemento o sus padres
            const dataToken = el.getAttribute('data-token') ||
                              el.closest('[data-token]')?.getAttribute('data-token');
            if (dataToken && !tokens.find(t => t.token === dataToken)) {
                tokens.push({
                    token: dataToken,
                    nombre: el.textContent.trim().replace(/[^a-zA-Z0-9_-]/g, '_') + '.pdf'
                });
            }
        }
    });

    if (tokens.length === 0) {
        console.log('\n[!] No se encontraron tokens automaticamente.');
        console.log('[!] Puede que necesites navegar a una pagina con mesas de votacion.');
        console.log('\n[INFO] Intentando buscar enlaces de descarga...\n');

        // Buscar cualquier enlace que parezca de descarga
        document.querySelectorAll('a[href*="descarga"], a[href*="token"], a[href*="e14"]').forEach((el, idx) => {
            console.log(`Enlace ${idx + 1}: ${el.href}`);
        });

        return;
    }

    console.log(`\n[OK] Encontrados ${tokens.length} tokens:\n`);

    // Mostrar tokens
    tokens.forEach((t, idx) => {
        console.log(`${idx + 1}. ${t.nombre}`);
        console.log(`   Token: ${t.token.substring(0, 50)}...`);
    });

    // Generar código Python
    const pythonCode = `
# Tokens extraidos - ${new Date().toLocaleString()}
# Copia esto en tu script de Python

tokens_y_nombres = [
${tokens.map(t => `    ("${t.token}", "${t.nombre}"),`).join('\n')}
]

# Para usar con el descargador:
# descargador.procesar_lote(tokens_y_nombres)
`;

    console.log('\n' + '='.repeat(60));
    console.log('  CODIGO PYTHON GENERADO:');
    console.log('='.repeat(60));
    console.log(pythonCode);

    // Intentar copiar al portapapeles
    try {
        navigator.clipboard.writeText(pythonCode).then(() => {
            console.log('\n[OK] Codigo copiado al portapapeles!');
        });
    } catch (e) {
        console.log('\n[INFO] No se pudo copiar automaticamente. Copia manualmente el codigo de arriba.');
    }

    // También guardar en variable global para acceso fácil
    window.tokensE14 = tokens;
    window.codigoPython = pythonCode;

    console.log('\n[TIP] Los tokens tambien estan disponibles en: window.tokensE14');
    console.log('[TIP] El codigo Python esta en: window.codigoPython');

    return tokens;
})();
