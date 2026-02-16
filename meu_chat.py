import flet as ft
import sqlite3
import hashlib
import os
from datetime import datetime

def main(page: ft.Page):
    # --- CONFIGURAÇÃO VISUAL "FOR GLORY" ---
    page.title = "For Glory"
    page.theme_mode = "dark"
    page.bgcolor = "#0b0c10"
    page.padding = 20
    
    # Cores do Tema
    COR_PRINCIPAL = "#66fcf1" 
    COR_SECUNDARIA = "#45a29e"
    COR_FUNDO = "#1f2833"
    
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # ==============================================================================
    # BANCO DE DADOS (CORREÇÃO ANTI-TRAVAMENTO)
    # ==============================================================================
    # 1. timeout=30: Espera até 30s se o banco estiver ocupado (antes de dar erro)
    conn = sqlite3.connect("chat_dados.db", check_same_thread=False, timeout=30.0)
    cursor = conn.cursor()
    
    # 2. Ativar Modo WAL: Permite leitura e escrita simultâneas (TURBO)
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
    except:
        pass # Se der erro nisso, segue o jogo
    
    # Tabelas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS mensagens (canal TEXT, usuario TEXT, hora TEXT, texto TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS salas (nome TEXT UNIQUE)")
    try:
        cursor.execute("INSERT INTO salas VALUES ('Geral')")
        conn.commit()
    except: pass

    # Variáveis de Estado
    usuario_atual = ""
    id_usuario_atual = None
    canal_atual = "Geral"

    # ==============================================================================
    # SISTEMA DE SEGURANÇA
    # ==============================================================================
    
    def criptografar(senha):
        return hashlib.sha256(senha.encode()).hexdigest()

    def tentar_login(e):
        nonlocal usuario_atual, id_usuario_atual
        user = campo_user.value
        pwd = campo_pass.value
        
        if not user or not pwd: return

        pwd_hash = criptografar(pwd)
        
        # O cursor.execute pode travar se não tiver o timeout, agora está protegido
        cursor.execute("SELECT id FROM usuarios WHERE username = ? AND senha_hash = ?", (user, pwd_hash))
        resultado = cursor.fetchone()
        
        if resultado:
            id_usuario_atual = resultado[0]
            usuario_atual = user
            iniciar_sistema()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Falha na autenticação! Verifique suas credenciais."), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    def registrar_conta(e):
        user = campo_user.value
        pwd = campo_pass.value
        
        if not user or not pwd: return

        pwd_hash = criptografar(pwd)
        
        try:
            cursor.execute("INSERT INTO usuarios (username, senha_hash) VALUES (?, ?)", (user, pwd_hash))
            conn.commit() # O momento crítico do travamento
            
            page.snack_bar = ft.SnackBar(ft.Text("Recruta registrado! Faça login agora."), bgcolor="green")
            page.snack_bar.open = True
            
            # Limpa campos para forçar login
            campo_user.value = ""
            campo_pass.value = ""
            page.update()
            
        except sqlite3.IntegrityError:
            page.snack_bar = ft.SnackBar(ft.Text("Este codinome já está em uso!"), bgcolor="orange")
            page.snack_bar.open = True
            page.update()
        except sqlite3.OperationalError as erro:
            # Se ainda der erro de lock, avisa o usuário
            page.snack_bar = ft.SnackBar(ft.Text(f"Erro de tráfego (Lock). Tente de novo: {erro}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    # Campos de Login
    campo_user = ft.TextField(label="CODINOME", width=300, bgcolor=COR_FUNDO, border_color=COR_SECUNDARIA)
    campo_pass = ft.TextField(label="SENHA DE ACESSO", width=300, password=True, can_reveal_password=True, bgcolor=COR_FUNDO, border_color=COR_SECUNDARIA)
    
    btn_login = ft.ElevatedButton("ACESSAR SISTEMA", on_click=tentar_login, bgcolor=COR_PRINCIPAL, color="black", width=300)
    btn_registro = ft.OutlinedButton("CRIAR NOVA CONTA", on_click=registrar_conta, width=300, style=ft.ButtonStyle(color=COR_PRINCIPAL))

    # TELA DE LOGIN
    tela_login = ft.Container(
        content=ft.Column([
            ft.Text("FOR GLORY", size=40, weight="bold", color=COR_PRINCIPAL, font_family="Verdana"),
            ft.Text("SECURE LOGIN SYSTEM", size=12, color=COR_SECUNDARIA),
            ft.Divider(height=20, color="transparent"),
            campo_user,
            campo_pass,
            ft.Divider(height=10, color="transparent"),
            btn_login,
            btn_registro
        ], horizontal_alignment="center", spacing=10),
        padding=40,
        border=ft.border.all(2, COR_SECUNDARIA),
        border_radius=20,
        bgcolor="#121212"
    )

    # ==============================================================================
    # SISTEMA PRINCIPAL
    # ==============================================================================
    
    coluna_mensagens = ft.Column(spacing=10, scroll="always")
    container_chat = ft.Container(
        content=coluna_mensagens,
        width=800, height=350,  
        bgcolor=COR_FUNDO, 
        border=ft.border.all(1, COR_SECUNDARIA), 
        border_radius=15, padding=15,
    )
    linha_salas = ft.Row(scroll="always", height=60)
    titulo_canal = ft.Text(f"CANAL: {canal_atual.upper()}", size=16, weight="bold", color=COR_PRINCIPAL)
    txt_msg = ft.TextField(hint_text="Comando...", width=400, height=50, bgcolor="#27272a", border_radius=15, content_padding=10)

    def carregar_mensagens():
        coluna_mensagens.controls.clear()
        try:
            cursor.execute("SELECT usuario, hora, texto FROM mensagens WHERE canal=?", (canal_atual,))
            for msg in cursor.fetchall():
                usuario, hora, texto = msg
                is_me = (usuario == usuario_atual)
                coluna_mensagens.controls.append(
                    ft.Row([
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{usuario} - {hora}", size=10, color="grey"),
                                ft.Text(texto, size=14, color="white")
                            ], spacing=2),
                            bgcolor=COR_SECUNDARIA if is_me else "#3f3f46", 
                            padding=10, border_radius=10, width=300
                        )
                    ], alignment="end" if is_me else "start")
                )
        except: pass
        page.update()

    def enviar(e):
        if txt_msg.value:
            try:
                hora = datetime.now().strftime("%H:%M")
                cursor.execute("INSERT INTO mensagens VALUES (?, ?, ?, ?)", (canal_atual, usuario_atual, hora, txt_msg.value))
                conn.commit()
                txt_msg.value = ""
                carregar_mensagens()
                txt_msg.focus()
            except: pass

    txt_msg.on_submit = enviar
    btn_enviar = ft.ElevatedButton("ENVIAR", on_click=enviar, bgcolor=COR_PRINCIPAL, color="black")

    def mudar_sala(e):
        nonlocal canal_atual
        canal_atual = e.control.data
        titulo_canal.value = f"CANAL: {canal_atual.upper()}"
        carregar_mensagens()
        carregar_salas()
        page.update()

    def criar_sala(e):
        if txt_nova_sala.value:
            try:
                nome = txt_nova_sala.value.strip().replace(" ", "-")
                cursor.execute("INSERT INTO salas VALUES (?)", (nome,))
                conn.commit()
                txt_nova_sala.value = ""
                carregar_salas()
                page.update()
            except: pass

    def carregar_salas():
        linha_salas.controls.clear()
        try:
            cursor.execute("SELECT nome FROM salas")
            for s in cursor.fetchall():
                nome = s[0]
                linha_salas.controls.append(
                    ft.Container(
                        content=ft.TextButton(f"# {nome}", data=nome, on_click=mudar_sala, style=ft.ButtonStyle(color=COR_PRINCIPAL)),
                        bgcolor=COR_FUNDO, border_radius=5, padding=5
                    )
                )
        except: pass
        page.update()

    txt_nova_sala = ft.TextField(label="Nova Base", width=150, height=40)

    txt_stats_msgs = ft.Text("0", size=40, weight="bold", color=COR_PRINCIPAL)
    
    def carregar_perfil():
        try:
            cursor.execute("SELECT COUNT(*) FROM mensagens WHERE usuario=?", (usuario_atual,))
            total = cursor.fetchone()[0]
            txt_stats_msgs.value = str(total)
            page.update()
        except: pass

    # --- LAYOUTS ---
    layout_chat = ft.Column([
        ft.Text("CENTRAL DE COMANDO", size=12, color="grey"),
        ft.Row([txt_nova_sala, ft.ElevatedButton("CRIAR", on_click=criar_sala, bgcolor=COR_SECUNDARIA, color="white")], alignment="center"),
        linha_salas,
        titulo_canal,
        container_chat, 
        ft.Row([txt_msg, btn_enviar], alignment="center")
    ], horizontal_alignment="center", spacing=10)

    layout_perfil = ft.Column([
        ft.Text(f"OPERADOR: {usuario_atual}", size=25, weight="bold", color=COR_PRINCIPAL),
        ft.Divider(color="grey"),
        ft.Text("ESTATÍSTICAS GLOBAIS", size=15, color="white"),
        ft.Text("Mensagens Enviadas:", size=12),
        txt_stats_msgs,
        ft.Text("(Sistema de Amigos em Desenvolvimento...)", color="grey")
    ], horizontal_alignment="center", spacing=20)

    container_main = ft.Container(visible=False)

    def navegar(e):
        destino = e.control.data
        if destino == "chat":
            container_main.content = layout_chat
            carregar_salas()
            carregar_mensagens()
        elif destino == "perfil":
            container_main.content = layout_perfil
            carregar_perfil()
        page.update()

    btn_menu_chat = ft.ElevatedButton("CHAT", data="chat", on_click=navegar, bgcolor=COR_PRINCIPAL, color="black")
    btn_menu_perfil = ft.ElevatedButton("PERFIL", data="perfil", on_click=navegar, bgcolor=COR_FUNDO, color="white")

    def iniciar_sistema():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.add(
            ft.Column([
                ft.Row([btn_menu_chat, btn_menu_perfil], alignment="center"),
                ft.Divider(height=1, color=COR_SECUNDARIA),
                container_main
            ])
        )
        container_main.visible = True
        navegar(ft.Control(data="chat"))

    page.add(tela_login)

port = int(os.environ.get("PORT", 8550))
ft.app(target=main, view="web_browser", port=port, host="0.0.0.0")