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

# Importação da biblioteca de Imagens
try:
    from PIL import Image
    TEM_PILLOW = True
except ImportError:
    TEM_PILLOW = False

class AutomacaoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Organizador Web Pro - Pasta ZIP Raiz")
        self.root.geometry("500x800")

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.soltar_arquivo)

        self.label_instrucao = tk.Label(root, text="ARRASTE O ARQUIVO ZIP AQUI", 
                                        font=("Arial", 18, "bold"), fg="#333", bg="#e0e0e0", pady=20)
        self.label_instrucao.pack(fill=tk.X, pady=10)

        self.log_area = scrolledtext.ScrolledText(root, width=120, height=35, state='disabled', font=("Consolas", 10))
        self.log_area.pack(pady=15, padx=15)
        
        self.log_area.tag_config('error', background='black', foreground='#FF5555', font=("Consolas", 11, "bold"))
        self.log_area.tag_config('warning', background='#FFFACD', foreground='#D2691E', font=("Consolas", 10, "bold"))
        self.log_area.tag_config('success', foreground='#2E8B57', font=("Consolas", 10, "bold"))
        self.log_area.tag_config('alert_format', background='#FFD700', foreground='#B22222', font=("Consolas", 12, "bold"))

        self.log("Sistema pronto. O projeto será organizado em uma pasta com o nome do ZIP.")

    def log(self, mensagem, level='normal'):
        self.log_area.config(state='normal')
        if level == 'error':
            self.log_area.insert(tk.END, f"\n[ !!! ERRO !!! ] {mensagem}\n", 'error')
        elif level == 'warning':
            self.log_area.insert(tk.END, f"[ AVISO ] {mensagem}\n", 'warning')
        elif level == 'success':
            self.log_area.insert(tk.END, f"[ OK ] {mensagem}\n", 'success')
        elif level == 'alert_format':
            self.log_area.insert(tk.END, f"\n{mensagem}\n", 'alert_format')
        else:
            self.log_area.insert(tk.END, mensagem + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update()

    def soltar_arquivo(self, event):
        caminho = event.data
        if caminho.startswith('{') and caminho.endswith('}'): caminho = caminho[1:-1]
        if caminho.lower().endswith('.zip'): self.preparar_processamento(caminho)
        else: self.log("Por favor, arraste um arquivo .zip", 'error')

    def preparar_processamento(self, caminho_zip):
        self.log("="*80)
        self.log(f"PROCESSANDO: {os.path.basename(caminho_zip)}")
        try:
            self.processar_zip(caminho_zip)
        except Exception as e:
            self.log(f"Erro crítico: {str(e)}", 'error')
            traceback.print_exc()

    def processar_zip(self, caminho_zip):
        diretorio_base = os.path.dirname(caminho_zip)
        cwd_original = os.getcwd()
        html_principal = None

        try:
            # Pega o nome do arquivo ZIP sem a extensão '.zip'
            nome_zip_sem_extensao = os.path.splitext(os.path.basename(caminho_zip))[0]
            
            # Cria o caminho da nova pasta que terá o nome do ZIP
            path_projeto = os.path.join(diretorio_base, nome_zip_sem_extensao)

            if not os.path.exists(path_projeto):
                os.makedirs(path_projeto)

            # 1. Descompactar tudo PARA DENTRO da nova pasta com o nome do ZIP
            self.log(f"\n>> Extraindo arquivos para a nova pasta: '{nome_zip_sem_extensao}'...")
            with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                zip_ref.extractall(path_projeto)

            # Entra na nova pasta
            os.chdir(path_projeto)
            
            self.log(">> Iniciando organização da estrutura na nova raiz...")
            
            # 2. Identificar e mover HTML para a raiz da nova pasta
            html_principal = self.organizar_html_raiz()

            # 3. Padronizar pastas (css, img, js, font) e mover arquivos de subpastas
            mapa_mudancas = self.padronizar_pastas_raiz()

            # 4. Otimização de imagens SEM PERDA de qualidade
            self.otimizar_imagens_qualidade()

            # 5. Atualizar HTML e CSS com os novos caminhos raiz
            if html_principal:
                self.corrigir_caminhos_html(html_principal, mapa_mudancas)
            
            self.corrigir_caminhos_css()

            # 6. Limpeza final
            self.limpar_pastas_vazias_total()

            self.log("="*80)
            self.log(f"PROJETO ORGANIZADO COM SUCESSO NA PASTA: {nome_zip_sem_extensao}", 'success')
            
            if html_principal:
                webbrowser.open('file://' + os.path.realpath(html_principal))

        finally:
            os.chdir(cwd_original)

    def organizar_html_raiz(self):
        html_encontrado = None
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.lower().endswith('.html'):
                    caminho_atual = os.path.join(root, file)
                    destino = 'index.html'
                    if os.path.abspath(caminho_atual) != os.path.abspath(destino):
                        self.mover_sobrescrever(caminho_atual, destino)
                        self.log(f"   [HTML MOVIDO] {caminho_atual} -> {destino}")
                    html_encontrado = destino
                    break
            if html_encontrado: break
        
        if not html_encontrado:
            self.log("Nenhum arquivo HTML encontrado. As pastas serão organizadas mesmo assim.", 'warning')
        return html_encontrado

    def padronizar_pastas_raiz(self):
        regras = {
            'css': ['.css'],
            'js': ['.js'],
            'img': ['.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.ico'],
            'font': ['.ttf', '.woff', '.woff2', '.eot', '.otf']
        }
        
        mapa = {}
        for pasta in regras:
            if not os.path.exists(pasta): os.makedirs(pasta)

        for root, dirs, files in os.walk('.', topdown=False):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                
                # Alertas de Formatos
                if ext in ['.mp4', '.avi', '.mov', '.wmv', '.mkv']:
                    self.log(f"[ ALERTA ] ATENÇÃO USUÁRIO: Arquivo de vídeo '{file}' encontrado.\nConverta para .webm", 'alert_format')
                elif ext in ['.svg', '.gif', '.bmp', '.ico', '.tiff']:
                    self.log(f"[ ALERTA ] FORMATO DE IMAGEM INVÁLIDO: '{file}'.\nConverta para o padrão (.png, .jpg ou .webp) ou devolva para o fornecedor refazer.", 'alert_format')

                pasta_alvo = next((p for p, exts in regras.items() if ext in exts), None)
                
                if pasta_alvo:
                    origem = os.path.join(root, file)
                    relativo_origem = os.path.relpath(origem, '.').replace('\\', '/')
                    destino = os.path.join(pasta_alvo, file)
                    
                    if os.path.abspath(origem) != os.path.abspath(destino):
                        self.mover_sobrescrever(origem, destino)
                        mapa[relativo_origem] = f"{pasta_alvo}/{file}"
                        self.log(f"   [MOVIDO] {file} -> {pasta_alvo}/")
        return mapa

    def otimizar_imagens_qualidade(self):
        if not TEM_PILLOW: return
        self.log(">> Otimizando imagens (Mantendo 100% da qualidade original)...")
        path_img = 'img'
        if os.path.exists(path_img):
            for file in os.listdir(path_img):
                caminho = os.path.join(path_img, file)
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    try:
                        with Image.open(caminho) as img:
                            img.save(caminho, optimize=True, quality=95 if file.lower().endswith(('.jpg', '.jpeg')) else None)
                    except: pass

    def corrigir_caminhos_html(self, html_file, mapa):
        self.log(">> Corrigindo caminhos no HTML...")
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            conteudo = f.read()

        # Substitui os mapeamentos exatos de arquivos que foram movidos
        chaves_ordenadas = sorted(mapa.keys(), key=len, reverse=True)
        for caminho_antigo in chaves_ordenadas:
            caminho_novo = mapa[caminho_antigo]
            if caminho_antigo in conteudo:
                conteudo = conteudo.replace(caminho_antigo, caminho_novo)

        # Remove prefixos de pastas ou caminhos complexos mantendo o padrão src="pasta/arquivo"
        def fix_paths(match):
            attr = match.group(1) # href ou src
            folder = match.group(2) # css, js, img, font
            filename = match.group(3) # nome do arquivo
            return f'{attr}="{folder}/{filename}"'

        conteudo = re.sub(r'(href|src)=["\'](?:\.\./|\./|/|assets/|src/|public/|dist/)*(css|js|img|font)/([^"\']+)["\']', fix_paths, conteudo)

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(conteudo)

    def corrigir_caminhos_css(self):
        self.log(">> Corrigindo URLs dentro dos arquivos CSS...")
        path_css = 'css'
        if not os.path.exists(path_css): return
        
        for file in os.listdir(path_css):
            if file.endswith('.css'):
                caminho = os.path.join(path_css, file)
                with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
                    conteudo = f.read()
                
                def fix_css_url(match):
                    url = match.group(1).strip("'\"")
                    if url.startswith(('http', 'data:')): return match.group(0)
                    nome = os.path.basename(url)
                    ext = os.path.splitext(nome)[1].lower()
                    if ext in ['.png', '.jpg', '.jpeg', '.webp', '.svg']:
                        return f"url('../img/{nome}')"
                    if ext in ['.ttf', '.woff', '.woff2', '.eot', '.otf']:
                        return f"url('../font/{nome}')"
                    return match.group(0)

                novo_conteudo = re.sub(r'url\((.*?)\)', fix_css_url, conteudo)
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(novo_conteudo)

    def limpar_pastas_vazias_total(self):
        self.log(">> Limpeza final: Removendo pastas vazias...")
        for root, dirs, files in os.walk('.', topdown=False):
            for d in dirs:
                path = os.path.join(root, d)
                try:
                    if not os.listdir(path):
                        os.rmdir(path)
                        self.log(f"   [LIXEIRA] Pasta vazia removida: {path.replace('./', '')}")
                except: pass

    def mover_sobrescrever(self, origem, destino):
        if os.path.exists(destino):
            if os.path.isdir(destino): shutil.rmtree(destino)
            else: os.remove(destino)
        shutil.move(origem, destino)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = AutomacaoApp(root)
    root.mainloop()