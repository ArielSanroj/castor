"""
Test rápido: ver si el CAPTCHA se activa o no
"""
import asyncio
from playwright.async_api import async_playwright

async def test_captcha():
    print("🧪 Probando comportamiento de CAPTCHA...\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            locale='es-CO',
        )
        
        # Inyectar anti-detección
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)
        
        page = await context.new_page()
        
        for i in range(3):
            print(f"[Intento {i+1}/3]")
            
            # Navegar
            await page.goto("https://e14_congreso_2022.registraduria.gov.co/", wait_until='networkidle')
            await asyncio.sleep(2)
            
            # Seleccionar un departamento
            await page.select_option('#selectDepto', '1')  # Antioquia
            await asyncio.sleep(1.5)
            
            # Seleccionar un municipio
            await page.select_option('#selectMpio', '1')  # Medellín
            await asyncio.sleep(1.5)
            
            # Verificar si hay CAPTCHA visible
            captcha_frame = await page.query_selector('iframe[src*="recaptcha"]')
            captcha_challenge = await page.query_selector('.g-recaptcha')
            
            # Intentar hacer clic en consultar
            btn = await page.query_selector('button[type="submit"], .btn-consultar, #btnConsultar')
            if btn:
                await btn.click()
                await asyncio.sleep(3)
            
            # Verificar resultado
            error_msg = await page.query_selector('.error, .alert-danger')
            success = await page.query_selector('.resultado, .e14-data, table')
            
            if success:
                print("   ✅ Pasó SIN captcha manual!")
            elif error_msg:
                text = await error_msg.inner_text()
                print(f"   ⚠️ Error: {text[:100]}")
            else:
                print("   🔄 Resultado no claro, posible CAPTCHA")
            
            # Recargar para siguiente intento
            await asyncio.sleep(2)
        
        await browser.close()
        print("\n✅ Test completado")

asyncio.run(test_captcha())
