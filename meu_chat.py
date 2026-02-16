import flet as ft
import sqlite3
import os
from datetime import datetime

def main(page: ft.Page):
    # --- CONFIGURAÇÃO ---
    page.title = "Sistema Tático - Clean"
    page.theme_mode = "dark"
    page.bgcolor = "#0f0f12"
    page.padding = 20
    
    # CONFIGURAÇÃO DE ALINHAMENTO INICIAL (LOGIN NO CENTRO)
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = None # Desativa rolagem no login para ficar fixo

    # --- BANCO DE DADOS ---
    conn = sqlite3.connect("chat_dados.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS mensagens (canal TEXT, usuario TEXT, hora TEXT, texto TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS salas (nome TEXT UNIQUE)")
    try:
        cursor.execute("INSERT INTO salas VALUES ('Geral')")
        conn.commit()
    except:
        pass

    usuario_atual = ""
    canal_atual = "Geral"

    # ==============================================================================
    # 1. PEÇAS DO CHAT
    # ==============================================================================
    
    coluna_mensagens = ft.Column(spacing=10, scroll="always")
    
    container_chat = ft.Container(
        content=coluna_mensagens,
        width=800,   
        height=350,  
        bgcolor="#18181b", 
        border=ft.border.all(1, "#3f3f46"), 
        border_radius=15, 
        padding=15,
    )

    linha_salas = ft.Row(scroll="always", height=60)
    titulo_canal = ft.Text(f"CANAL: {canal_atual.upper()}", size=16, weight="bold", color="#60a5fa")

    txt_msg = ft.TextField(
        hint_text="Digite aqui...", 
        width=400,
        height=50, 
        bgcolor="#27272a",
        border_radius=15,
        color="white",
        content_padding=10,
        autofocus=True
    )

    # --- FUNÇÕES ---
    def carregar_mensagens():
        coluna_mensagens.controls.clear()
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
                        bgcolor="#2563eb" if is_me else "#3f3f46", 
                        padding=10,
                        border_radius=10,
                        width=300
                    )
                ], alignment="end" if is_me else "start")
            )
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
                page.update()
            except: pass

    txt_msg.on_submit = enviar
    btn_enviar = ft.ElevatedButton("ENVIAR", on_click=enviar, bgcolor="#2563eb", color="white")

    def mudar_sala(e):
        nonlocal canal_atual
        canal_atual = e.control.data
        titulo_canal.value = f"CANAL: {canal_atual.upper()}"
        carregar_mensagens()
        carregar_salas()
        page.update()

    def deletar_sala(e):
        nonlocal canal_atual
        nome_para_deletar = e.control.data
        if nome_para_deletar == "Geral": return 
        try:
            cursor.execute("DELETE FROM salas WHERE nome = ?", (nome_para_deletar,))
            cursor.execute("DELETE FROM mensagens WHERE canal = ?", (nome_para_deletar,))
            conn.commit()
            
            if canal_atual == nome_para_deletar:
                canal_atual = "Geral"
                titulo_canal.value = "CANAL: GERAL"
                carregar_mensagens()
            carregar_salas()
            page.update()
        except: pass

    def carregar_salas():
        linha_salas.controls.clear()
        cursor.execute("SELECT nome FROM salas")
        for s in cursor.fetchall():
            nome_sala = s[0]
            is_active = (nome_sala == canal_atual)
            is_geral = (nome_sala == "Geral")

            conteudo_botao = [
                ft.TextButton(
                    f"# {nome_sala}", 
                    data=nome_sala, 
                    on_click=mudar_sala,
                    style=ft.ButtonStyle(color="white")
                )
            ]
            if not is_geral:
                conteudo_botao.append(
                    ft.Container(
                        content=ft.Text("X", size=12, weight="bold", color="white"),
                        bgcolor="red",
                        padding=5,
                        border_radius=5,
                        data=nome_sala,
                        on_click=deletar_sala,
                        width=30, height=30,
                        alignment=ft.Alignment(0, 0)
                    )
                )
            linha_salas.controls.append(
                ft.Container(
                    content=ft.Row(conteudo_botao, spacing=5, alignment="center"),
                    bgcolor="#2563eb" if is_active else "#27272a", 
                    border_radius=5,
                    padding=ft.padding.only(left=5, right=5, top=2, bottom=2)
                )
            )
        page.update()

    txt_nova_sala = ft.TextField(label="Nova Sala", width=150, height=40)
    
    def criar_sala(e):
        if txt_nova_sala.value:
            try:
                nome_limpo = txt_nova_sala.value.strip().replace(" ", "-")
                cursor.execute("INSERT INTO salas VALUES (?)", (nome_limpo,))
                conn.commit()
                txt_nova_sala.value = ""
                carregar_salas()
                page.update()
            except: pass

    # ==============================================================================
    # 2. PEÇAS DO PERFIL
    # ==============================================================================
    
    txt_novo_nome = ft.TextField(label="Novo Nickname", width=250, text_align="center")
    txt_stats_msgs = ft.Text("0", size=40, weight="bold", color="#60a5fa")
    
    def atualizar_dados_perfil():
        try:
            cursor.execute("SELECT COUNT(*) FROM mensagens WHERE usuario=?", (usuario_atual,))
            total = cursor.fetchone()[0]
            txt_stats_msgs.value = str(total)
            txt_novo_nome.value = usuario_atual
            page.update()
        except: pass

    def salvar_novo_nome(e):
        nonlocal usuario_atual
        if txt_novo_nome.value and txt_novo_nome.value != usuario_atual:
            novo = txt_novo_nome.value
            antigo = usuario_atual
            try:
                cursor.execute("UPDATE mensagens SET usuario = ? WHERE usuario = ?", (novo, antigo))
                conn.commit()
                usuario_atual = novo
                page.snack_bar = ft.SnackBar(ft.Text(f"Identidade alterada para: {novo}"), bgcolor="green")
                page.snack_bar.open = True
                carregar_mensagens()
                atualizar_dados_perfil()
                page.update()
            except: pass

    # ==============================================================================
    # 3. ESTRUTURA VISUAL
    # ==============================================================================

    # Layout CHAT
    container_tela_chat = ft.Container(
        content=ft.Column([
            ft.Text("CENTRAL DE COMANDO", size=12, color="grey"),
            ft.Row([txt_nova_sala, ft.ElevatedButton("CRIAR", on_click=criar_sala)], alignment="center"),
            ft.Divider(color="grey"),
            linha_salas,
            ft.Divider(color="transparent"),
            titulo_canal,
            container_chat, 
            ft.Divider(color="transparent"),
            ft.Container(
                content=ft.Row([txt_msg, btn_enviar], alignment="center"),
                bgcolor="#111111", padding=10, border_radius=10
            )
        ], horizontal_alignment="center", spacing=10),
        visible=True 
    )

    # Layout PERFIL (SEM ICONE!)
    container_tela_perfil = ft.Container(
        content=ft.Column([
            # REMOVI O ÍCONE AQUI. AGORA É SÓ TEXTO.
            ft.Text("=== FICHA DO OPERADOR ===", size=20, weight="bold", color="white"),
            ft.Divider(color="grey"),
            ft.Container(
                content=ft.Column([
                    ft.Text("MENSAGENS ENVIADAS:", size=12),
                    txt_stats_msgs,
                    ft.Divider(color="transparent", height=20),
                    ft.Text("ALTERAR IDENTIDADE:", size=12),
                    txt_novo_nome,
                    ft.ElevatedButton("SALVAR ALTERAÇÃO", on_click=salvar_novo_nome, bgcolor="#2563eb", color="white")
                ], horizontal_alignment="center"),
                bgcolor="#18181b",
                padding=30,
                border_radius=15,
                border=ft.border.all(1, "#3f3f46"),
                width=400
            )
        ], horizontal_alignment="center", spacing=20),
        visible=False
    )

    # --- NAVEGAÇÃO ---
    def navegar(e):
        destino = e.control.data
        if destino == "chat":
            container_tela_chat.visible = True
            container_tela_perfil.visible = False
            btn_menu_chat.bgcolor = "#2563eb"
            btn_menu_perfil.bgcolor = "#27272a"
            carregar_salas()
            carregar_mensagens()
            txt_msg.focus()
        elif destino == "perfil":
            container_tela_chat.visible = False
            container_tela_perfil.visible = True
            btn_menu_chat.bgcolor = "#27272a"
            btn_menu_perfil.bgcolor = "#2563eb"
            atualizar_dados_perfil()
        page.update()

    btn_menu_chat = ft.ElevatedButton("CHAT TÁTICO", data="chat", on_click=navegar, bgcolor="#2563eb", color="white")
    btn_menu_perfil = ft.ElevatedButton("MEU PERFIL", data="perfil", on_click=navegar, bgcolor="#27272a", color="white")

    # --- TELA DE LOGIN (SEM ÍCONE E CENTRALIZADA) ---
    login_nome = ft.TextField(label="SEU NOME", width=250, text_align="center")

    def entrar(e):
        if login_nome.value:
            nonlocal usuario_atual
            usuario_atual = login_nome.value
            page.clean()
            
            # ALTERA O ALINHAMENTO PARA O CHAT (Para cima)
            page.vertical_alignment = ft.MainAxisAlignment.START
            page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            page.scroll = "auto" # Ativa rolagem só agora se precisar
            
            page.add(
                ft.Column([
                    ft.Container(
                        content=ft.Row([btn_menu_chat, btn_menu_perfil], alignment="center"),
                        padding=10,
                        bgcolor="#1e1f22"
                    ),
                    ft.Divider(height=1, color="grey"),
                    container_tela_chat,
                    container_tela_perfil
                ])
            )
            
            carregar_salas()
            carregar_mensagens()
            txt_msg.focus()

    # MONTAGEM DO LOGIN (CENTRO DA TELA)
    page.add(
        ft.Container(
            content=ft.Column([
                # REMOVI O ÍCONE. AGORA É SÓ TEXTO.
                ft.Text("LOGIN TÁTICO", size=25, weight="bold", color="white"),
                login_nome,
                ft.ElevatedButton("ENTRAR", on_click=entrar, bgcolor="#5865F2", color="white")
            ], horizontal_alignment="center", spacing=20),
            alignment=ft.Alignment(0, 0),
            padding=50
        )
    )

port = int(os.environ.get("PORT", 8550))
ft.app(target=main, view=ft.WEB_BROWSER, port=port, host="0.0.0.0")