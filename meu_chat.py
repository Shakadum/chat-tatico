import flet as ft
import sqlite3
import hashlib
import os
from datetime import datetime

def main(page: ft.Page):
    # --- CONFIGURAÇÃO ---
    page.title = "For Glory"
    page.theme_mode = "dark"
    page.bgcolor = "#0b0c10"
    page.padding = 20
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # CORES
    COR_PRINCIPAL = "#66fcf1" 
    COR_SECUNDARIA = "#45a29e"
    COR_FUNDO = "#1f2833"

    # --- BANCO DE DADOS ---
    print("Conectando ao banco...")
    conn = sqlite3.connect("chat_dados.db", check_same_thread=False, timeout=30.0)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
    except: pass
    
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

    usuario_atual = ""
    canal_atual = "Geral"

    # --- TEXTO DE STATUS (O DEDO-DURO) ---
    # Esse texto vai aparecer na tela para te contar o que aconteceu
    txt_status = ft.Text("", size=14, color="yellow")

    # --- FUNÇÕES ---
    def criptografar(senha):
        return hashlib.sha256(senha.encode()).hexdigest()

    def registrar_conta(e):
        txt_status.value = "Processando registro..."
        txt_status.color = "yellow"
        page.update()
        
        user = campo_user.value
        pwd = campo_pass.value
        
        print(f"Tentando registrar: {user}") # Olha no terminal preto!

        if not user or not pwd:
            txt_status.value = "ERRO: Digite Nome e Senha!"
            txt_status.color = "red"
            page.update()
            return

        try:
            pwd_hash = criptografar(pwd)
            cursor.execute("INSERT INTO usuarios (username, senha_hash) VALUES (?, ?)", (user, pwd_hash))
            conn.commit()
            
            txt_status.value = "CONTA CRIADA COM SUCESSO! FAÇA LOGIN."
            txt_status.color = "green"
            campo_user.value = ""
            campo_pass.value = ""
            page.update()
            print("Usuário criado com sucesso.")
            
        except sqlite3.IntegrityError:
            txt_status.value = "ERRO: Esse nome já existe!"
            txt_status.color = "orange"
            page.update()
        except Exception as erro:
            txt_status.value = f"ERRO CRÍTICO: {erro}"
            txt_status.color = "red"
            print(f"Erro no Python: {erro}")
            page.update()

    def entrar(e):
        txt_status.value = "Verificando credenciais..."
        page.update()
        
        nonlocal usuario_atual
        user = campo_user.value
        pwd = campo_pass.value
        pwd_hash = criptografar(pwd)
        
        try:
            cursor.execute("SELECT id FROM usuarios WHERE username = ? AND senha_hash = ?", (user, pwd_hash))
            if cursor.fetchone():
                usuario_atual = user
                iniciar_sistema()
            else:
                txt_status.value = "LOGIN FALHOU: Nome ou senha errados."
                txt_status.color = "red"
                page.update()
        except Exception as erro:
            txt_status.value = f"Erro no Login: {erro}"
            page.update()

    # --- TELA DE LOGIN ---
    campo_user = ft.TextField(label="SEU CODINOME", width=300, bgcolor=COR_FUNDO, border_color=COR_SECUNDARIA)
    campo_pass = ft.TextField(label="SUA SENHA", width=300, password=True, can_reveal_password=True, bgcolor=COR_FUNDO, border_color=COR_SECUNDARIA)
    
    btn_login = ft.ElevatedButton("ACESSAR SISTEMA", on_click=entrar, bgcolor=COR_PRINCIPAL, color="black", width=300)
    btn_registro = ft.OutlinedButton("CRIAR NOVA CONTA", on_click=registrar_conta, width=300, style=ft.ButtonStyle(color=COR_PRINCIPAL))

    tela_login = ft.Container(
        content=ft.Column([
            ft.Text("FOR GLORY", size=40, weight="bold", color=COR_PRINCIPAL),
            ft.Text("SECURE LOGIN", size=12, color=COR_SECUNDARIA),
            ft.Divider(color="transparent"),
            campo_user,
            campo_pass,
            ft.Divider(color="transparent"),
            btn_login,
            btn_registro,
            ft.Divider(color="transparent"),
            txt_status # AQUI ESTÁ O AVISO NA TELA
        ], horizontal_alignment="center", spacing=10),
        padding=40,
        border=ft.border.all(2, COR_SECUNDARIA),
        border_radius=20,
        bgcolor="#121212"
    )

    # --- SISTEMA DE CHAT (RESTAURADO) ---
    coluna_mensagens = ft.Column(spacing=10, scroll="always")
    container_chat = ft.Container(content=coluna_mensagens, width=800, height=350, bgcolor=COR_FUNDO, border_radius=15, padding=15)
    txt_msg = ft.TextField(hint_text="Comando...", width=400, bgcolor="#27272a")
    
    def enviar(e):
        if txt_msg.value:
            hora = datetime.now().strftime("%H:%M")
            cursor.execute("INSERT INTO mensagens VALUES (?, ?, ?, ?)", (canal_atual, usuario_atual, hora, txt_msg.value))
            conn.commit()
            txt_msg.value = ""
            carregar_mensagens()
            txt_msg.focus()
            page.update()

    def carregar_mensagens():
        coluna_mensagens.controls.clear()
        cursor.execute("SELECT usuario, hora, texto FROM mensagens WHERE canal=?", (canal_atual,))
        for msg in cursor.fetchall():
            usuario, hora, texto = msg
            is_me = (usuario == usuario_atual)
            coluna_mensagens.controls.append(
                ft.Row([
                    ft.Container(
                        content=ft.Column([ft.Text(f"{usuario} - {hora}", size=10), ft.Text(texto, size=14)]),
                        bgcolor=COR_SECUNDARIA if is_me else "#3f3f46", 
                        padding=10, border_radius=10
                    )
                ], alignment="end" if is_me else "start")
            )
        page.update()

    def iniciar_sistema():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        # Layout do Chat
        page.add(
            ft.Column([
                ft.Text(f"OPERADOR: {usuario_atual}", color=COR_PRINCIPAL, weight="bold"),
                container_chat,
                ft.Row([txt_msg, ft.ElevatedButton("ENVIAR", on_click=enviar, bgcolor=COR_PRINCIPAL, color="black")], alignment="center")
            ], horizontal_alignment="center")
        )
        carregar_mensagens()

    page.add(tela_login)

# Porta 8550 (Padrão)
port = int(os.environ.get("PORT", 8550))
ft.app(target=main, view="web_browser", port=port, host="0.0.0.0")