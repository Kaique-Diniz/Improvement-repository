"""Smoke test de navegador: só exemplo fictício, sem processar fontes reais.

Opcional: pip install playwright==1.56.0; informar Chromium já instalado.
Não registra a chave, cookies ou dados de documentos no terminal.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--chave-arquivo',type=Path,required=True)
    parser.add_argument('--chromium',default='/usr/bin/chromium')
    parser.add_argument('--captura',type=Path,default=Path('/tmp/conversor-mvp-demo.png'))
    args=parser.parse_args()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1450,'height':1100},locale='pt-BR')
        errors=[]
        page.on('pageerror',lambda e:errors.append(type(e).__name__))
        page.goto(args.url)
        page.fill('#chave',args.chave_arquivo.read_text().strip())
        page.get_by_role('button',name='Entrar',exact=True).click()
        page.locator('#app').wait_for(state='visible')
        page.locator('#demo').click()
        page.locator('#resultado').wait_for(state='visible',timeout=60000)
        assert page.locator('#linhas tr').count()==3
        page.locator('#cotas-agrupadas>summary').click()
        assert page.locator('.cota-grupo').count()==2
        grupo=page.locator('.cota-grupo').first
        grupo.locator(':scope>summary').click()
        assert grupo.locator('.boleto-grupo').count()==2
        boleto=grupo.locator('.boleto-grupo').first
        boleto.locator('summary').click()
        boleto.get_by_role('heading',name='Composição original').wait_for(state='visible')
        page.locator('#cotas-agrupadas>summary').click()
        for coluna in ('Elegibilidade financeira', 'Contatos da unidade', 'Pendências documentais', 'Resultado da prévia'):
            assert page.get_by_role('columnheader',name=coluna,exact=True).is_visible()
        assert page.locator('#operacional').is_disabled()
        page.select_option('#filtro','nao_elegivel')
        assert page.locator('#linhas tr').count()==1
        page.get_by_role('button',name='Detalhes',exact=True).click()
        assert page.locator('#detalhes').is_visible()
        assert page.locator('#detalhes-legiveis').get_by_role('heading',name='Informações de contato da unidade').is_visible()
        page.get_by_role('button',name='Fechar',exact=True).click()
        page.select_option('#filtro','todas')
        with page.expect_download() as download:page.locator('#download').click()
        assert download.value.suggested_filename.startswith('TESTE_LOCAL_NAO_IMPORTAR_')
        with page.expect_download() as manifesto:page.locator('#manifesto').click()
        dados_manifesto=json.loads(Path(manifesto.value.path()).read_text())
        assert dados_manifesto['arquivo']['sha256']==sha256(Path(download.value.path()).read_bytes()).hexdigest()
        assert not dados_manifesto['permite_exportacao_operacional']
        page.screenshot(path=str(args.captura),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(args.captura.with_name(args.captura.stem+'-mobile.png')),full_page=True)
        assert not errors
        print(json.dumps({'login':True,'exemplo_sintetico':True,'filtros':True,
            'cotas_e_boletos_separados':True,'expansao_componentes':True,
            'detalhes':True,'download_xlsx':True,'manifesto_vinculado_ao_xlsx':True,'operacional_desativado':True,
            'mobile_sem_overflow':True,'erros_javascript':0},ensure_ascii=False))
        browser.close()


if __name__=='__main__':main()
