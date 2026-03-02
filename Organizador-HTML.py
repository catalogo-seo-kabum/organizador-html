import os
import shutil
import zipfile
import tkinter as tk
from tkinter import messagebox, scrolledtext
import webbrowser
import re
import traceback

# Importação da biblioteca de Drag & Drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    print("ERRO: Você precisa instalar a biblioteca tkinterdnd2.")
    print("Execute: pip install tkinterdnd2")
    exit()

class AutomacaoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Organizador Full Stack - Buscador de HTML")
        self.root.geometry("600x800")

        # Configurar Drag and Drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.soltar_arquivo)

        # UI Elements
        self.label_instrucao = tk.Label(root, text="ARRASTE O ARQUIVO ZIP AQUI", 
                                        font=("Arial", 18, "bold"), fg="#333", bg="#e0e0e0", pady=20)
        self.label_instrucao.pack(fill=tk.X, pady=10)

        self.label_status = tk.Label(root, text="O sistema mostrará abaixo cada alteração feita nos arquivos.", fg="#666")
        self.label_status.pack()

        # Log Area com fonte monospaced para alinhar texto
        self.log_area = scrolledtext.ScrolledText(root, width=120, height=35, state='disabled', font=("Consolas", 9))
        self.log_area.pack(pady=15, padx=15)
        
        self.log("Sistema pronto. Aguardando arquivo ZIP...")

    def log(self, mensagem):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, mensagem + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update()

    def soltar_arquivo(self, event):
        caminho = event.data
        if caminho.startswith('{') and caminho.endswith('}'):
            caminho = caminho[1:-1]
        
        if caminho.lower().endswith('.zip'):
            self.preparar_processamento(caminho)
        else:
            self.log("ERRO: O arquivo deve ser um .zip")

    def preparar_processamento(self, caminho_zip):
        self.log("=" * 80)
        self.log(f"INICIANDO PROCESSAMENTO: {os.path.basename(caminho_zip)}")
        self.log("=" * 80)
        try:
            self.processar_zip(caminho_zip)
        except Exception as e:
            self.log(f"ERRO CRÍTICO: {str(e)}")
            traceback.print_exc()
            messagebox.showerror("Erro", f"Ocorreu um erro: {str(e)}")

    def processar_zip(self, caminho_zip):
        diretorio_base = os.path.dirname(caminho_zip)
        cwd_original = os.getcwd() # Salva local original

        path_extraido_absoluto = None
        caminho_html_navegador = None

        try:
            # 1. Descompactar
            self.log("\n[ETAPA 1] Descompactando arquivo...")
            with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                zip_ref.extractall(diretorio_base)
                primeira_pasta = zip_ref.namelist()[0].split('/')[0]
                path_extraido_absoluto = os.path.join(diretorio_base, primeira_pasta)

            if not os.path.isdir(path_extraido_absoluto):
                self.log("Erro: Estrutura do ZIP inválida.")
                return
            
            os.chdir(path_extraido_absoluto)
            self.log(f"   Pasta acessada: {primeira_pasta}")
            
            # 2. Pré-limpeza (Assets)
            path_assets = os.path.join(os.getcwd(), 'assets')
            if os.path.exists(path_assets):
                self.log("\n[ETAPA 2] Detectada pasta 'assets'. Esvaziando...")
                for item in os.listdir(path_assets):
                    origem = os.path.join(path_assets, item)
                    destino = os.path.join(os.getcwd(), item)
                    self.mover_sobrescrever(origem, destino)
                    self.log(f"   [MOVIDO DE ASSETS] {item} -> Raiz")
                if not os.listdir(path_assets):
                    os.rmdir(path_assets)
                    self.log("   Pasta 'assets' vazia removida.")

            # 3. Buscar e Trazer HTML para a Raiz
            self.log("\n[ETAPA 3] Buscando arquivo HTML em todas as pastas...")
            caminho_html_original = None
            nome_html_final = 'index.html'

            # Faz uma varredura profunda procurando o HTML
            for root_dir, dirs, files in os.walk('.'):
                for file in files:
                    if file.lower().endswith('.html'):
                        # Dá preferência se o arquivo já se chamar index.html
                        if caminho_html_original is None or file.lower() == 'index.html':
                            caminho_html_original = os.path.join(root_dir, file).replace('\\', '/')

            if caminho_html_original:
                destino_html = os.path.join('.', nome_html_final)
                # Se o arquivo não estiver na raiz exata com o nome index.html, nós movemos
                if os.path.abspath(caminho_html_original) != os.path.abspath(destino_html):
                    self.log(f"   [HTML ENCONTRADO] Movendo '{caminho_html_original}' >>> Raiz como '{nome_html_final}'")
                    self.mover_sobrescrever(caminho_html_original, destino_html)
                else:
                    self.log(f"   Arquivo HTML já está na raiz como {nome_html_final}.")
            else:
                self.log("   AVISO: Nenhum arquivo HTML encontrado em todo o projeto.")
                with open(nome_html_final, 'w') as f: f.write("")

            # 4. PADRONIZAÇÃO E EXTRAÇÃO DAS SUBPASTAS DE IMAGEM
            mapa_mudancas = self.padronizar_pastas()

            # 5. Atualizar HTML
            if os.path.exists(nome_html_final):
                self.atualizar_html(nome_html_final, mapa_mudancas)

            # 6. Atualizar CSS
            self.processar_arquivos_css()

            caminho_html_navegador = 'file://' + os.path.realpath(nome_html_final)
            self.log("\n" + "=" * 80)
            self.log("SUCESSO! Projeto 100% Organizado.")
            self.log("=" * 80)

        except Exception as e:
            self.log(f"Erro durante o processo: {e}")
            raise e
        
        finally:
            os.chdir(cwd_original)
            self.log("\n[SISTEMA] Pasta liberada para edição pelo Windows.")

            if caminho_html_navegador:
                webbrowser.open(caminho_html_navegador)

    def padronizar_pastas(self):
        self.log("\n[ETAPA 4] Organizando Pastas, Extraindo Subpastas e Movendo Arquivos...")
        regras = {
            'css': ['.css'],
            'js': ['.js'],
            'img': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp'],
            'font': ['.ttf', '.otf', '.woff', '.woff2', '.eot']
        }

        # Cria pastas padrão e avisa
        for pasta in regras.keys():
            if not os.path.exists(pasta):
                os.makedirs(pasta)
                self.log(f"   [CRIAR PASTA] {pasta}/")

        mapa_mudancas = {} 

        for root, dirs, files in os.walk('.', topdown=False):
            for file in files:
                extensao = os.path.splitext(file)[1].lower()
                pasta_destino = None

                for pasta_key, exts in regras.items():
                    if extensao in exts:
                        pasta_destino = pasta_key
                        break
                
                if pasta_destino:
                    origem_abs = os.path.join(root, file)
                    relativo_origem = os.path.relpath(origem_abs, '.').replace('\\', '/')
                    
                    if relativo_origem.startswith(pasta_destino + '/'):
                        if relativo_origem.count('/') == 1:
                            continue

                    destino_abs = os.path.join(pasta_destino, file)
                    relativo_destino = os.path.join(pasta_destino, file).replace('\\', '/')

                    try:
                        self.mover_sobrescrever(origem_abs, destino_abs)
                        
                        if 'images/' in relativo_origem.lower() or ('img/' in relativo_origem.lower() and relativo_origem.count('/') > 1):
                            self.log(f"   [EXTRAINDO DE SUBPASTA] {relativo_origem}  >>>  {relativo_destino}")
                        else:
                            self.log(f"   [ARQUIVO MOVIDO] {relativo_origem}  >>>  {relativo_destino}")
                            
                        mapa_mudancas[relativo_origem] = relativo_destino
                    except Exception as e:
                        self.log(f"   [ERRO AO MOVER] {file}: {e}")

        # Varredura RIGOROSA para apagar pastas vazias
        self.log("   Verificando e apagando pastas vazias...")
        for root, dirs, files in os.walk('.', topdown=False):
            for name in dirs:
                if name in regras.keys() and root == '.': 
                    continue
                
                caminho_dir = os.path.join(root, name)
                try:
                    if not os.listdir(caminho_dir): 
                        os.rmdir(caminho_dir)
                        self.log(f"   [PASTA APAGADA] A pasta vazia '{caminho_dir}' foi removida.")
                except: pass
        
        return mapa_mudancas

    def processar_arquivos_css(self):
        path_css_folder = os.path.join(os.getcwd(), 'css')
        if not os.path.exists(path_css_folder): return

        self.log("\n[ETAPA 6] Corrigindo referências internas nos arquivos CSS...")
        arquivos_css = [f for f in os.listdir(path_css_folder) if f.endswith('.css')]
        
        for css_file in arquivos_css:
            caminho_arquivo = os.path.join(path_css_folder, css_file)
            self.log(f"   > Lendo arquivo: {css_file}")
            
            try:
                with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                
                mudancas_neste_arquivo = 0

                def substituir_url(match):
                    nonlocal mudancas_neste_arquivo
                    url_original = match.group(1)
                    full_match = match.group(0)

                    if url_original.startswith(('http', 'https', 'data:', '//')):
                        return full_match
                    
                    nome_arquivo = os.path.basename(url_original)
                    extensao = os.path.splitext(nome_arquivo)[1].lower()
                    
                    novo_caminho = None
                    if extensao in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp']:
                        novo_caminho = f"../img/{nome_arquivo}"
                    elif extensao in ['.ttf', '.otf', '.woff', '.woff2', '.eot']:
                        novo_caminho = f"../font/{nome_arquivo}"
                    
                    if novo_caminho and not url_original.endswith(novo_caminho):
                        novo_full = f"url('{novo_caminho}')"
                        self.log(f"     [CSS FIX] {url_original}  >>>  {novo_caminho}")
                        mudancas_neste_arquivo += 1
                        return novo_full
                    
                    return full_match

                novo_conteudo = re.sub(r"url\s*\((?:'|\")?(.*?)(?:'|\")?\)", substituir_url, conteudo)
                
                if mudancas_neste_arquivo > 0:
                    with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                        f.write(novo_conteudo)
                    self.log(f"     -> Salvo com {mudancas_neste_arquivo} correções.")
                else:
                    self.log("     -> Nenhuma correção necessária.")

            except Exception as e:
                self.log(f"   Erro CSS {css_file}: {e}")

    def atualizar_html(self, arquivo_html, mapa_mudancas):
        self.log("\n[ETAPA 5] Atualizando Código HTML...")
        try:
            try:
                with open(arquivo_html, 'r', encoding='utf-8') as f: conteudo = f.read()
            except UnicodeDecodeError:
                with open(arquivo_html, 'r', encoding='latin-1') as f: conteudo = f.read()

            if 'assets/' in conteudo:
                self.log("   [HTML] Removendo referências 'assets/' genéricas...")
                conteudo = conteudo.replace('assets/', '')
            
            count_updates = 0
            chaves_ordenadas = sorted(mapa_mudancas.keys(), key=len, reverse=True)

            for caminho_antigo in chaves_ordenadas:
                caminho_novo = mapa_mudancas[caminho_antigo]
                if caminho_antigo in conteudo:
                    self.log(f"   [HTML FIX] '{caminho_antigo}'  >>>  '{caminho_novo}'")
                    conteudo = conteudo.replace(caminho_antigo, caminho_novo)
                    count_updates += 1
            
            if count_updates == 0:
                self.log("   Nenhuma referência antiga encontrada no HTML.")
            else:
                self.log(f"   Total de linhas alteradas no HTML: {count_updates}")

            with open(arquivo_html, 'w', encoding='utf-8') as f:
                f.write(conteudo)
        except Exception as e:
            self.log(f"Erro HTML: {e}")

    def mover_sobrescrever(self, origem, destino):
        if os.path.exists(destino):
            if os.path.samefile(origem, destino): return
            if os.path.isdir(destino): shutil.rmtree(destino)
            else: os.remove(destino)
        shutil.move(origem, destino)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = AutomacaoApp(root)
    root.mainloop()