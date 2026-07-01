import os
import shutil
import zipfile
import tkinter as tk
from tkinter import messagebox, scrolledtext
import webbrowser
import re
import traceback
import threading

# Importação da biblioteca de Drag & Drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    print("ERRO: Você precisa instalar a biblioteca tkinterdnd2.")
    print("Execute: pip install tkinterdnd2")
    exit()

# Importação da biblioteca de Imagens Local
try:
    from PIL import Image
    TEM_PILLOW = True
except ImportError:
    TEM_PILLOW = False

# Importação da biblioteca para API
try:
    import requests
    TEM_REQUESTS = True
except ImportError:
    TEM_REQUESTS = False

# Importação da biblioteca de Vídeos e Progresso
try:
    from moviepy import VideoFileClip
    from proglog import ProgressBarLogger
    TEM_MOVIEPY = True

    class TkinterVideoLogger(ProgressBarLogger):
        def __init__(self, app, filename):
            super().__init__()
            self.app = app
            self.filename = filename
            self.last_percent = -1

        def bars_callback(self, bar, attr, value, old_value=None):
            if bar == 't': 
                total = self.bars[bar]['total']
                if total > 0:
                    percent = int((value / total) * 100)
                    if percent % 20 == 0 and percent > self.last_percent:
                        self.last_percent = percent
                        self.app.root.after(0, self.app.log, f"   [VÍDEO ⏳] {self.filename}: {percent}% concluído...", 'video')

except ImportError:
    TEM_MOVIEPY = False

# =========================================================
# CONFIGURAÇÃO DA API (iLoveAPI)
# =========================================================
PUBLIC_KEY = ""

class AutomacaoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Organizador Web Pro - HTML/Srcset Perfeitos")
        self.root.geometry("500x850")

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.soltar_arquivo)

        self.fila_arquivos = []
        self.processando = False
        self.threads_ativas = [] 

        self.label_instrucao = tk.Label(root, text="ARRASTE UM OU VÁRIOS ARQUIVOS ZIP AQUI", 
                                        font=("Arial", 18, "bold"), fg="#333", bg="#e0e0e0", pady=20)
        self.label_instrucao.pack(fill=tk.X, pady=10)

        frame_opcoes = tk.Frame(root)
        frame_opcoes.pack(pady=5)
        
        tk.Label(frame_opcoes, text="Método de Compressão de Imagens:", font=("Arial", 10, "bold")).pack(anchor="w")
        
        self.metodo_compressao = tk.StringVar(value="api")
        
        # NOVO: Opção para não comprimir as imagens
        rb_nenhuma = tk.Radiobutton(frame_opcoes, text="Nenhuma (Apenas organizar as pastas)", variable=self.metodo_compressao, value="nenhuma")
        rb_nenhuma.pack(anchor="w")

        rb_local = tk.Radiobutton(frame_opcoes, text="Rápida (Local / Pillow)", variable=self.metodo_compressao, value="local")
        rb_local.pack(anchor="w")
        
        rb_api = tk.Radiobutton(frame_opcoes, text="Avançada na Nuvem (iLoveAPI) - Com Status e %", variable=self.metodo_compressao, value="api")
        rb_api.pack(anchor="w")

        if not TEM_REQUESTS:
            rb_api.config(state=tk.DISABLED, text="Avançada na Nuvem (Requer 'pip install requests')")
            self.metodo_compressao.set("local")

        self.log_area = scrolledtext.ScrolledText(root, width=120, height=30, state='disabled', font=("Consolas", 10))
        self.log_area.pack(pady=15, padx=15)
        
        self.log_area.tag_config('error', background='black', foreground='#FF5555', font=("Consolas", 11, "bold"))
        self.log_area.tag_config('warning', background='#FFFACD', foreground='#D2691E', font=("Consolas", 10, "bold"))
        self.log_area.tag_config('success', foreground='#2E8B57', font=("Consolas", 10, "bold"))
        self.log_area.tag_config('alert_format', background='#FFD700', foreground='#B22222', font=("Consolas", 12, "bold"))
        self.log_area.tag_config('api_info', foreground='#0000FF', font=("Consolas", 10, "italic"))
        self.log_area.tag_config('fila', background='#E0F7FA', foreground='#006064', font=("Consolas", 11, "bold")) 
        self.log_area.tag_config('video', background='#4B0082', foreground='#00FFFF', font=("Consolas", 11, "bold")) 

        self.log("Sistema pronto. Arraste vários projetos ZIP para adicionar à fila.")
        if not TEM_MOVIEPY:
            self.log("[ AVISO ] A biblioteca 'moviepy' não foi encontrada. Instale para conversão de vídeo: pip install moviepy", "warning")

    def log(self, mensagem, level='normal'):
        self.log_area.config(state='normal')
        if level == 'error': self.log_area.insert(tk.END, f"\n[ !!! ERRO !!! ] {mensagem}\n", 'error')
        elif level == 'warning': self.log_area.insert(tk.END, f"[ AVISO ] {mensagem}\n", 'warning')
        elif level == 'success': self.log_area.insert(tk.END, f"[ OK ] {mensagem}\n", 'success')
        elif level == 'alert_format': self.log_area.insert(tk.END, f"\n{mensagem}\n", 'alert_format')
        elif level == 'api_info': self.log_area.insert(tk.END, f"       {mensagem}\n", 'api_info')
        elif level == 'fila': self.log_area.insert(tk.END, f"\n{mensagem}\n", 'fila')
        elif level == 'video': self.log_area.insert(tk.END, f"{mensagem}\n", 'video')
        else: self.log_area.insert(tk.END, mensagem + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update()

    def soltar_arquivo(self, event):
        arquivos_arrastados = self.root.tk.splitlist(event.data)
        adicionados = 0
        for caminho in arquivos_arrastados:
            if caminho.lower().endswith('.zip'):
                self.fila_arquivos.append(caminho)
                adicionados += 1
                self.log(f"   + Adicionado à fila: {os.path.basename(caminho)}")
            else:
                self.log(f"Arquivo ignorado (não é .zip): {os.path.basename(caminho)}", 'warning')
        
        if adicionados > 0:
            self.log(f"Total na fila agora: {len(self.fila_arquivos)} arquivo(s).", 'fila')

        if not self.processando and self.fila_arquivos:
            self.processar_proximo_da_fila()

    def processar_proximo_da_fila(self):
        if not self.fila_arquivos:
            self.processando = False
            self.log("\n" + "="*80)
            self.log("✅ TODAS AS TAREFAS DA FILA FORAM CONCLUÍDAS COM SUCESSO!", 'fila')
            self.log("="*80 + "\n")
            return

        self.processando = True
        caminho_zip = self.fila_arquivos.pop(0)
        
        restantes = len(self.fila_arquivos)
        self.log("\n" + "="*80)
        self.log(f"PROCESSANDO AGORA: {os.path.basename(caminho_zip)} (Faltam {restantes} na fila)")
        self.log("="*80)
        
        try:
            html_abs, nome_zip = self.processar_zip(caminho_zip)
            self.aguardar_threads_e_proximo(html_abs, nome_zip)
            
        except Exception as e:
            self.log(f"Erro crítico no arquivo {os.path.basename(caminho_zip)}: {str(e)}", 'error')
            traceback.print_exc()
            self.root.after(500, self.processar_proximo_da_fila) 
            
    def aguardar_threads_e_proximo(self, html_abs, nome_zip):
        self.threads_ativas = [t for t in self.threads_ativas if t.is_alive()]

        if self.threads_ativas:
            self.root.after(1000, self.aguardar_threads_e_proximo, html_abs, nome_zip)
        else:
            self.log(f"\n[ OK ] Projeto '{nome_zip}' 100% finalizado!", 'success')
            if html_abs and os.path.exists(html_abs):
                webbrowser.open('file://' + html_abs)
            self.root.after(500, self.processar_proximo_da_fila)

    def processar_zip(self, caminho_zip):
        diretorio_base = os.path.dirname(caminho_zip)
        cwd_original = os.getcwd()
        caminho_html_abs = None
        nome_zip_sem_extensao = os.path.splitext(os.path.basename(caminho_zip))[0]

        try:
            path_projeto = os.path.join(diretorio_base, nome_zip_sem_extensao)

            if not os.path.exists(path_projeto): os.makedirs(path_projeto)

            self.log(f"\n>> Extraindo arquivos para a nova pasta: '{nome_zip_sem_extensao}'...")
            with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                zip_ref.extractall(path_projeto)

            os.chdir(path_projeto)
            
            html_principal = self.organizar_html_raiz()
            if html_principal:
                caminho_html_abs = os.path.abspath(html_principal)

            mapa_mudancas, videos_convertidos = self.padronizar_pastas_raiz()

            # Lógica atualizada com a nova opção de não comprimir
            if self.metodo_compressao.get() == "api":
                self.otimizar_imagens_api()
            elif self.metodo_compressao.get() == "local":
                self.otimizar_imagens_local()
            else:
                self.log("\n>> Otimização de imagens ignorada (Opção 'Nenhuma' selecionada).", "warning")

            if html_principal:
                self.corrigir_caminhos_html(html_principal, videos_convertidos)
            
            self.corrigir_caminhos_css()
            self.limpar_pastas_vazias_total()

        finally:
            os.chdir(cwd_original)
            
        return caminho_html_abs, nome_zip_sem_extensao

    def organizar_html_raiz(self):
        html_encontrado = None
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.lower().endswith('.html'):
                    caminho_atual = os.path.join(root, file)
                    destino = 'index.html'
                    if os.path.abspath(caminho_atual) != os.path.abspath(destino):
                        self.mover_sobrescrever(caminho_atual, destino)
                    html_encontrado = destino
                    break
            if html_encontrado: break
        return html_encontrado

    def padronizar_pastas_raiz(self):
        self.log("\n>> Organizando Pastas e Analisando Formatos...")
        regras = {
            'css': ['.css'],
            'js': ['.js'],
            'img': ['.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.ico', '.bmp', '.mp4', '.webm'], 
            'font': ['.ttf', '.otf', '.woff', '.woff2', '.eot']
        }
        
        mapa = {}
        videos_convertidos = {} 

        for pasta in regras:
            if not os.path.exists(pasta): os.makedirs(pasta)

        for root, dirs, files in os.walk('.', topdown=False):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                
                if ext in ['.avi', '.mov', '.wmv', '.mkv']:
                    self.log(f"[ ALERTA ] Arquivo de vídeo inválido '{file}'. Converta manualmente para .webm", 'alert_format')
                elif ext in ['.svg', '.gif', '.bmp', '.ico', '.tiff']:
                    self.log(f"[ ALERTA ] FORMATO DE IMAGEM INVÁLIDO: '{file}'. Converta para .png, .jpg ou .webp", 'alert_format')

                pasta_alvo = next((p for p, exts in regras.items() if ext in exts), None)
                
                if pasta_alvo:
                    origem = os.path.join(root, file)
                    relativo_origem = os.path.relpath(origem, '.').replace('\\', '/')
                    destino = os.path.join(pasta_alvo, file)
                    
                    if ext == '.mp4':
                        resposta = messagebox.askyesno(
                            "Conversão Assíncrona de Vídeo", 
                            f"Encontramos o vídeo '{file}'.\n\nDeseja convertê-lo para .webm em segundo plano sem travar o aplicativo?"
                        )
                        if resposta:
                            nome_webm = file.replace('.mp4', '.webm')
                            destino_webm = os.path.join(pasta_alvo, nome_webm)
                            
                            origem_abs = os.path.abspath(origem)
                            destino_webm_abs = os.path.abspath(destino_webm)
                            
                            self.log(f"   [VÍDEO] Iniciando conversão de '{file}' em SEGUNDO PLANO...", 'video')
                            
                            thread_video = threading.Thread(
                                target=self.converter_mp4_para_webm_bg, 
                                args=(origem_abs, destino_webm_abs, file, nome_webm)
                            )
                            thread_video.daemon = True 
                            self.threads_ativas.append(thread_video) 
                            thread_video.start()
                            
                            videos_convertidos[file] = nome_webm
                            mapa[relativo_origem] = f"{pasta_alvo}/{nome_webm}"
                            continue 
                        else:
                            self.log(f"[ ALERTA ] ATENÇÃO: O vídeo '{file}' foi mantido como .mp4.", 'alert_format')

                    if os.path.abspath(origem) != os.path.abspath(destino):
                        self.mover_sobrescrever(origem, destino)
                        mapa[relativo_origem] = f"{pasta_alvo}/{file}"
                        
        return mapa, videos_convertidos

    def converter_mp4_para_webm_bg(self, arquivo_entrada, arquivo_saida, nome_original, nome_novo):
        try:
            if not TEM_MOVIEPY:
                self.root.after(0, self.log, "❌ A biblioteca 'moviepy' não está instalada.", 'error')
                return

            video = VideoFileClip(arquivo_entrada)
            logger = TkinterVideoLogger(self, nome_original)
            
            video.write_videofile(
                arquivo_saida, 
                codec='libvpx', 
                audio_codec='libvorbis',
                logger=logger
            )
            
            video.close()
            
            try: os.remove(arquivo_entrada)
            except: pass
            
            self.root.after(0, self.log, f"   [VÍDEO ✅] Sucesso total! {nome_original} convertido para {nome_novo}", 'success')
            
        except Exception as e:
            self.root.after(0, self.log, f"❌ Erro na conversão em segundo plano de {nome_original}: {e}", 'error')

    def otimizar_imagens_local(self):
        if not TEM_PILLOW: return
        self.log("\n>> Otimizando imagens (LOCAL/Pillow)...")
        path_img = 'img'
        if os.path.exists(path_img):
            for file in os.listdir(path_img):
                caminho = os.path.join(path_img, file)
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    try:
                        with Image.open(caminho) as img:
                            img.save(caminho, optimize=True, quality=95 if file.lower().endswith(('.jpg', '.jpeg')) else None)
                    except: pass
            self.log("   [OK] Compressão local concluída.", 'success')

    def otimizar_imagens_api(self):
        path_img = 'img'
        if not os.path.exists(path_img): return
        
        arquivos_img = [f for f in os.listdir(path_img) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        if not arquivos_img: return

        self.log(f"\n>> Otimizando {len(arquivos_img)} imagens (NUVEM/iLoveAPI)...")
        tamanho_original_total = sum(os.path.getsize(os.path.join(path_img, f)) for f in arquivos_img)
        
        try:
            session = requests.Session()
            base_url = "https://api.ilovepdf.com/v1"
            
            self.log("   -> Autenticando na API...")
            auth_resp = session.post(f"{base_url}/auth", data={"public_key": PUBLIC_KEY})
            self.log(f"Status Resposta: {auth_resp.status_code}", "api_info")
            if auth_resp.status_code != 200: return
            
            token = auth_resp.json()["token"]
            session.headers.update({"Authorization": f"Bearer {token}"})
            
            start_resp = session.get(f"{base_url}/start/compressimage")
            if start_resp.status_code != 200: return
                
            start_data = start_resp.json()
            server_url = f"https://{start_data['server']}/v1"
            task_id = start_data['task']

            self.log("   -> Fazendo upload das imagens...")
            arquivos_servidor = []
            
            for file in arquivos_img:
                caminho = os.path.join(path_img, file)
                with open(caminho, "rb") as f:
                    files = {"file": (file, f)}
                    data = {"task": task_id}
                    up_resp = session.post(f"{server_url}/upload", data=data, files=files)
                    
                    if up_resp.status_code == 200:
                        arquivos_servidor.append({
                            "server_filename": up_resp.json()["server_filename"],
                            "filename": file
                        })
            if not arquivos_servidor: return

            self.log("   -> Processando compressão...")
            process_payload = {"task": task_id, "tool": "compressimage", "files": arquivos_servidor}
            process_resp = session.post(f"{server_url}/process", json=process_payload)
            if process_resp.status_code != 200: return

            self.log("   -> Baixando imagens otimizadas...")
            download_resp = session.get(f"{server_url}/download/{task_id}")
            
            if download_resp.status_code == 200:
                if len(arquivos_servidor) > 1:
                    caminho_zip_api = os.path.join(path_img, "compressed_api.zip")
                    with open(caminho_zip_api, "wb") as f_out: f_out.write(download_resp.content)
                    with zipfile.ZipFile(caminho_zip_api, 'r') as zip_ref: zip_ref.extractall(path_img) 
                    os.remove(caminho_zip_api)
                else:
                    with open(os.path.join(path_img, arquivos_servidor[0]["filename"]), "wb") as f_out:
                        f_out.write(download_resp.content)

                tamanho_novo_total = sum(os.path.getsize(os.path.join(path_img, f)) for f in arquivos_img)
                economia_bytes = tamanho_original_total - tamanho_novo_total
                
                self.log(f"\n   [OK] Processo de nuvem concluído!", 'success')
                if economia_bytes > 0:
                    self.log(f"   [RESULTADO] Economia: {economia_bytes/1024:.2f} KB ({(economia_bytes / tamanho_original_total) * 100:.2f}%)", 'success')

        except Exception as e:
            self.log(f"   Erro API: {e}", 'error')

    def corrigir_caminhos_html(self, html_file, videos_convertidos):
        self.log("\n>> Corrigindo caminhos e atributos no HTML (src, href, srcset)...")
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            conteudo = f.read()

        # 1. Troca o nome e a extensão do vídeo no código-fonte
        for nome_mp4, nome_webm in videos_convertidos.items():
            if nome_mp4 in conteudo:
                conteudo = conteudo.replace(nome_mp4, nome_webm)
                self.log(f"   [HTML VÍDEO] Caminho trocado: '{nome_mp4}' -> '{nome_webm}'", 'video')

        # 2. Troca os attributes type="video/mp4" para type="video/webm"
        if 'video/mp4' in conteudo:
            conteudo = conteudo.replace('type="video/mp4"', 'type="video/webm"')
            conteudo = conteudo.replace("type='video/mp4'", "type='video/webm'")

        # 3. Força a padronização exata: attr="pasta_correta/nome_do_arquivo.extensao"
        def padronizar_caminho(match):
            atributo = match.group(1) 
            caminho_completo = match.group(2) 
            
            # TRATAMENTO ESPECIAL PARA SRCSET (Vários arquivos separados por vírgula)
            if atributo == 'srcset':
                partes = caminho_completo.split(',')
                novas_partes = []
                for parte in partes:
                    parte_limpa = parte.strip()
                    if not parte_limpa: continue
                    
                    sub_partes = parte_limpa.split(' ', 1)
                    url_original = sub_partes[0]
                    descritor = f" {sub_partes[1]}" if len(sub_partes) > 1 else ""
                    
                    nome_arquivo = os.path.basename(url_original)
                    ext = os.path.splitext(nome_arquivo)[1].lower()
                    
                    if ext in ['.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.ico', '.bmp']:
                        novas_partes.append(f"img/{nome_arquivo}{descritor}")
                    else:
                        novas_partes.append(parte_limpa)
                        
                novo_caminho = f'{atributo}="{", ".join(novas_partes)}"'
                if match.group(0) != novo_caminho:
                    self.log(f"   [HTML FIX] srcset atualizado.")
                return novo_caminho
            
            # TRATAMENTO NORMAL PARA SRC E HREF
            nome_arquivo = os.path.basename(caminho_completo)
            ext = os.path.splitext(nome_arquivo)[1].lower()
            
            pasta_correta = None
            if ext in ['.css']: pasta_correta = 'css'
            elif ext in ['.js']: pasta_correta = 'js'
            elif ext in ['.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.ico', '.bmp', '.mp4', '.webm']: pasta_correta = 'img'
            elif ext in ['.ttf', '.otf', '.woff', '.woff2', '.eot']: pasta_correta = 'font'
            
            if pasta_correta:
                novo_caminho = f'{atributo}="{pasta_correta}/{nome_arquivo}"'
                if match.group(0) != novo_caminho:
                    self.log(f"   [HTML FIX] Limpado: {match.group(0)} -> {novo_caminho}")
                return novo_caminho
            
            return match.group(0)

        # Adicionado 'srcset' na regex para rastrear e limpar
        regex_paths = r'(href|src|srcset)=["\'](?!http|#|data:|mailto:)([^"\']+)["\']'
        conteudo = re.sub(regex_paths, padronizar_caminho, conteudo)

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(conteudo)

    def corrigir_caminhos_css(self):
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
                    if ext in ['.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.ico', '.bmp', '.mp4', '.webm']:
                        return f"url('../img/{nome}')"
                    if ext in ['.ttf', '.otf', '.woff', '.woff2', '.eot']:
                        return f"url('../font/{nome}')"
                    return match.group(0)

                novo_conteudo = re.sub(r'url\((.*?)\)', fix_css_url, conteudo)
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(novo_conteudo)

    def limpar_pastas_vazias_total(self):
        for root, dirs, files in os.walk('.', topdown=False):
            for d in dirs:
                path = os.path.join(root, d)
                try:
                    if not os.listdir(path): os.rmdir(path)
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