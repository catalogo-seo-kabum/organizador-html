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
        self.root.title("Organizador Full Stack - Validação de Formatos e Caminhos")
        self.root.geometry("500x800")

        # Configurar Drag and Drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.soltar_arquivo)

        # UI Elements
        self.label_instrucao = tk.Label(root, text="ARRASTE O ARQUIVO ZIP AQUI", 
                                        font=("Arial", 18, "bold"), fg="#333", bg="#e0e0e0", pady=20)
        self.label_instrucao.pack(fill=tk.X, pady=10)

        self.label_status = tk.Label(root, text="Organização completa, correção de caminhos de raiz (/) e validação de formatos.", fg="#666")
        self.label_status.pack()

        # Log Area
        self.log_area = scrolledtext.ScrolledText(root, width=120, height=35, state='disabled', font=("Consolas", 10))
        self.log_area.pack(pady=15, padx=15)
        
        # Configuração das Cores do Log (Tags)
        self.log_area.tag_config('error', background='black', foreground='#FF5555', font=("Consolas", 11, "bold"))
        self.log_area.tag_config('warning', background='#FFFACD', foreground='#D2691E', font=("Consolas", 10, "bold"))
        self.log_area.tag_config('normal', foreground='#333333')
        
        # NOVO: Alerta visual bem destacado para validação de formatos (vídeos/imagens fora do padrão)
        self.log_area.tag_config('alert_format', background='#FFD700', foreground='#B22222', font=("Consolas", 12, "bold"))
        
        self.log("Sistema pronto. Aguardando arquivo ZIP...")

    def log(self, mensagem, level='normal'):
        """Grava no log usando o nível de cor especificado"""
        self.log_area.config(state='normal')
        
        if level == 'error':
            self.log_area.insert(tk.END, f"\n[ !!! ERRO CRÍTICO !!! ]\n{mensagem}\n\n", 'error')
        elif level == 'alert_format':
            self.log_area.insert(tk.END, f"\n{mensagem}\n\n", 'alert_format')
        elif level == 'warning':
            self.log_area.insert(tk.END, f"[ AVISO ] {mensagem}\n", 'warning')
        else:
            self.log_area.insert(tk.END, mensagem + "\n", 'normal')
            
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
            self.log("O arquivo arrastado não é um .zip", 'error')

    def preparar_processamento(self, caminho_zip):
        self.log("=" * 80)
        self.log(f"INICIANDO PROCESSAMENTO: {os.path.basename(caminho_zip)}")
        self.log("=" * 80)
        try:
            self.processar_zip(caminho_zip)
        except Exception as e:
            self.log(f"Falha na execução do script: {str(e)}", 'error')
            traceback.print_exc()

    def processar_zip(self, caminho_zip):
        diretorio_base = os.path.dirname(caminho_zip)
        cwd_original = os.getcwd()

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
                self.log("Estrutura do ZIP inválida ou não pôde ser lida.", 'error')
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
            else:
                self.log("Pasta 'assets' não encontrada (Pulando limpeza inicial).", 'warning')

            # 3. Buscar e Trazer HTML para a Raiz
            self.log("\n[ETAPA 3] Buscando arquivo HTML em todas as pastas...")
            caminho_html_original = None
            nome_html_final = 'index.html'

            for root_dir, dirs, files in os.walk('.'):
                for file in files:
                    if file.lower().endswith('.html'):
                        if caminho_html_original is None or file.lower() == 'index.html':
                            caminho_html_original = os.path.join(root_dir, file).replace('\\', '/')

            if caminho_html_original:
                destino_html = os.path.join('.', nome_html_final)
                if os.path.abspath(caminho_html_original) != os.path.abspath(destino_html):
                    self.log(f"   [HTML ENCONTRADO] Movendo '{caminho_html_original}' >>> Raiz como '{nome_html_final}'")
                    self.mover_sobrescrever(caminho_html_original, destino_html)
                else:
                    self.log(f"   Arquivo HTML já está na raiz como {nome_html_final}.")
            else:
                self.log("Nenhum arquivo HTML encontrado. O script organizará as pastas mesmo assim.", 'warning')
                with open(nome_html_final, 'w') as f: f.write("")

            # 4. PADRONIZAÇÃO, VALIDAÇÃO DE EXTENSÕES E EXTRAÇÃO DAS SUBPASTAS DE IMAGEM
            mapa_mudancas = self.padronizar_pastas()

            # 5. Atualizar HTML (Inclui agora a remoção de barras / e ../)
            if os.path.exists(nome_html_final):
                self.atualizar_html(nome_html_final, mapa_mudancas)

            # 6. Atualizar CSS
            self.processar_arquivos_css()

            # 7. VARREDURA FINAL DE PASTAS VAZIAS
            self.varredura_final_pastas()

            caminho_html_navegador = 'file://' + os.path.realpath(nome_html_final)
            self.log("\n" + "=" * 80)
            self.log("SUCESSO! Projeto 100% Organizado e Validado.")
            self.log("=" * 80)

        except Exception as e:
            self.log(f"Erro inesperado durante a organização dos arquivos: {e}", 'error')
            raise e
        
        finally:
            os.chdir(cwd_original)
            self.log("\n[SISTEMA] Pasta liberada para edição pelo Windows.")

            if caminho_html_navegador:
                webbrowser.open(caminho_html_navegador)

    def padronizar_pastas(self):
        self.log("\n[ETAPA 4] Organizando Pastas e Validando Formatos...")
        regras = {
            'css': ['.css'],
            'js': ['.js'],
            'img': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.bmp'],
            'font': ['.ttf', '.otf', '.woff', '.woff2', '.eot']
        }

        for pasta in regras.keys():
            if not os.path.exists(pasta):
                os.makedirs(pasta)
                self.log(f"   [CRIAR PASTA] {pasta}/")

        mapa_mudancas = {} 

        for root, dirs, files in os.walk('.', topdown=False):
            for file in files:
                extensao = os.path.splitext(file)[1].lower()
                
                # =========================================================
                # NOVO: VALIDAÇÕES DE ARQUIVOS INFORME O USUÁRIO (ALERTA)
                # =========================================================
                if extensao in ['.mp4', '.avi', '.mov', '.wmv', '.mkv']:
                    self.log(f"[ ALERTA ] ATENÇÃO USUÁRIO: Arquivo de vídeo '{file}' encontrado.\nConverta para .webm", 'alert_format')
                
                elif extensao in ['.svg', '.gif', '.bmp', '.ico', '.tiff']:
                    self.log(f"[ ALERTA ] FORMATO DE IMAGEM INVÁLIDO: '{file}'.\nConverta para o padrão (.png, .jpg ou .webp) ou devolva para o fornecedor refazer.", 'alert_format')
                # =========================================================

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
                            self.log(f"   [EXTRAINDO] {relativo_origem}  >>>  {relativo_destino}")
                        else:
                            self.log(f"   [MOVIDO] {relativo_origem}  >>>  {relativo_destino}")
                            
                        mapa_mudancas[relativo_origem] = relativo_destino
                    except Exception as e:
                        self.log(f"Erro ao tentar mover o arquivo {file}: {e}", 'error')
        
        return mapa_mudancas

    def processar_arquivos_css(self):
        path_css_folder = os.path.join(os.getcwd(), 'css')
        if not os.path.exists(path_css_folder): 
            return

        self.log("\n[ETAPA 6] Corrigindo referências internas nos arquivos CSS...")
        arquivos_css = [f for f in os.listdir(path_css_folder) if f.endswith('.css')]

        for css_file in arquivos_css:
            caminho_arquivo = os.path.join(path_css_folder, css_file)
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
                    self.log(f"     -> '{css_file}' salvo com {mudancas_neste_arquivo} correções.")

            except Exception as e:
                self.log(f"Falha ao ler e editar o arquivo CSS {css_file}: {e}", 'error')

    def atualizar_html(self, arquivo_html, mapa_mudancas):
        self.log("\n[ETAPA 5] Atualizando e Padronizando Código HTML...")
        try:
            try:
                with open(arquivo_html, 'r', encoding='utf-8') as f: conteudo = f.read()
            except UnicodeDecodeError:
                with open(arquivo_html, 'r', encoding='latin-1') as f: conteudo = f.read()

            if 'assets/' in conteudo:
                self.log("   [HTML] Removendo referências 'assets/' genéricas...")
                conteudo = conteudo.replace('assets/', '')
            
            count_updates = 0
            
            # Passo 5.1: Mapear as antigas posições para a nova estrutura
            chaves_ordenadas = sorted(mapa_mudancas.keys(), key=len, reverse=True)
            for caminho_antigo in chaves_ordenadas:
                caminho_novo = mapa_mudancas[caminho_antigo]
                if caminho_antigo in conteudo:
                    self.log(f"   [HTML RE-LINK] '{caminho_antigo}'  >>>  '{caminho_novo}'")
                    conteudo = conteudo.replace(caminho_antigo, caminho_novo)
                    count_updates += 1
            
            # =========================================================
            # NOVO PASSO 5.2: PADRONIZAÇÃO DE BARRAS DE DIRETÓRIO
            # Remove /css/ ou ../img/ ou ./js/ deixando apenas css/, img/, js/
            # =========================================================
            def fix_paths(match):
                attr = match.group(1) # href ou src
                folder = match.group(2) # css, js, img, font
                filename = match.group(3) # nome do arquivo
                novo_caminho = f'{attr}="{folder}/{filename}"'
                
                if match.group(0) != novo_caminho:
                    self.log(f"   [HTML PATH FIX] {match.group(0)}  >>>  {novo_caminho}")
                    
                return novo_caminho

            # Regex caça: href="/css/..." ou src="../img/..."
            conteudo_limpo = re.sub(r'(href|src)=["\'](?:\.\./|\./|/)+(css|js|img|font)/([^"\']+)["\']', fix_paths, conteudo)
            
            if conteudo != conteudo_limpo:
                conteudo = conteudo_limpo
                count_updates += 1 # Computa que houve modificações de padronização
            # =========================================================

            if count_updates == 0:
                self.log("Nenhuma referência precisou ser alterada no HTML.", 'warning')
            else:
                self.log(f"   Processamento do HTML concluído com sucesso.")

            with open(arquivo_html, 'w', encoding='utf-8') as f:
                f.write(conteudo)
                
        except Exception as e:
            self.log(f"Falha grave ao tentar atualizar o HTML: {e}", 'error')

    def varredura_final_pastas(self):
        """Passa um 'Aspirador de Pó' no projeto inteiro apagando pastas vazias."""
        self.log("\n[ETAPA 7] Varredura Final: Eliminando pastas vazias...")
        pastas_protegidas = ['css', 'js', 'img', 'font']
        apagadas = 0

        for root_dir, dirs, files in os.walk('.', topdown=False):
            for name in dirs:
                if name in pastas_protegidas and root_dir == '.':
                    continue
                
                caminho_dir = os.path.join(root_dir, name)
                try:
                    if not os.listdir(caminho_dir): 
                        os.rmdir(caminho_dir)
                        self.log(f"   [LIXEIRA] Pasta vazia deletada: {caminho_dir.replace('./', '')}")
                        apagadas += 1
                except Exception as e:
                    self.log(f"Não foi possível apagar a pasta {caminho_dir}: {e}", 'warning')
        
        if apagadas == 0:
            self.log("   Nenhuma pasta inútil foi encontrada nesta varredura.")

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