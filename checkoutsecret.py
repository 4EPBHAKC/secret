from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import asyncio
import datetime

# Token do bot
TOKEN = '7669234688:AAGQ3a-cNRwLwHuDvWwOIEpcVZt9Wq7FOrA'  # Substitua pelo seu token real

# Definindo a chave PIX (única para todos os planos)
PIX_KEY = 'lauracorreiamodel@gmail.com'  # Substitua pela sua chave PIX

# ID do administrador (você)
ADMIN_ID = 7338492112  # Substitua pelo seu ID de usuário no Telegram

# ID do supergrupo
GROUP_ID = "-1002278029742"  # Substitua pelo ID do seu grupo

# Duração dos planos em minutos
PLAN_DURATION = {
    'quinze_dias': 21600,  # 2 minutos (ajuste do plano quinzenal)
    'mensal': 43200,  # 30 dias em minutos
    'trimestral': 129600,  # 90 dias em minutos
    'vitalicio': None  # Vitalício não expira
}

# Armazenar os usuários verificados (dicionário: {user_id: nome})
verificados = {}

# Função para enviar os planos
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("🟢 Plano 15 dias - R$ 7,50", callback_data='quinze_dias')],
        [InlineKeyboardButton("🟢 Plano Mensal - R$ 15,00", callback_data='mensal')],
        [InlineKeyboardButton("🟠 Plano Trimestral - R$ 30,00", callback_data='trimestral')],
        [InlineKeyboardButton("🔵 Plano Vitalício - R$ 50,00", callback_data='vitalicio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '🎉 Olá! Escolha um plano para se inscrever e aproveite nosso conteúdo exclusivo! 🎉\n\nSelecione abaixo:', 
        reply_markup=reply_markup
    )

# Função para exibir a chave PIX após o plano ser escolhido
async def plan_choice(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    plan = query.data
    plan_name = {
        'quinze_dias': 'Plano 15 Dias',
        'mensal': 'Plano Mensal',
        'trimestral': 'Plano Trimestral',
        'vitalicio': 'Plano Vitalício'
    }
    price = {
        'quinze_dias': 'R$ 7,50',
        'mensal': 'R$ 15,00',
        'trimestral': 'R$ 30,00',
        'vitalicio': 'R$ 50,00'
    }
    
    await query.edit_message_text(
        text=f"✅ Você escolheu o {plan_name[plan]} - {price[plan]}.\n\n💳 Chave PIX: {PIX_KEY}\n\n👉 Instrução: Segure em cima do e-mail informado como chave PIX e clique em 'Copiar e-mail'. Depois, vá até seu banco, cole o e-mail no campo de pagamento do PIX e conclua a transação.\n\nApós realizar o pagamento, clique em 'Pago' para confirmar! 🏁"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Pago", callback_data=f'pagamento_{plan}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "🤑 Clique em 'Pago' após realizar o pagamento para confirmar sua inscrição!", 
        reply_markup=reply_markup
    )

async def pagamento(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    plan = query.data.split('_')[1]
    user_name = query.from_user.first_name
    user_id = query.from_user.id

    # Verificando se o usuário já está verificado
    if user_id in verificados:
        # Se o usuário já estiver verificado, trata-se de uma mudança de plano
        verificados[user_id]['plano'] = plan  # Atualiza o plano
        
        # Verificando a expiração: se não for vitalício, calcula a expiração
        if plan != 'vitalicio':
            verificados[user_id]['expiracao'] = datetime.datetime.now() + datetime.timedelta(minutes=PLAN_DURATION.get(plan, 0))
        else:
            verificados[user_id]['expiracao'] = None  # Para plano vitalício, não há expiração
        
        # Enviar mensagem de solicitação de confirmação ao administrador novamente
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💸 O usuário {user_name} (ID: {user_id}) trocou de plano para {plan}. Verifique o pagamento e reenvie o link!",
            reply_markup=InlineKeyboardMarkup([ 
                [InlineKeyboardButton("✅ Verificado", callback_data=f'verificado_{plan}_{user_id}')],
            ])
        )

        await query.edit_message_text(text="👀 O pagamento foi registrado. Aguardando a confirmação do pagamento.")
    else:
        # Armazenando o usuário verificado pela primeira vez
        verificados[user_id] = {
            'nome': user_name,
            'plano': plan,
            'expiracao': datetime.datetime.now() + datetime.timedelta(minutes=PLAN_DURATION.get(plan, 0)) if plan != 'vitalicio' else None
        }

        # Enviar mensagem de solicitação de confirmação ao administrador
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💸 O usuário {user_name} (ID: {user_id}) informou que pagou o plano {plan}.\n🔄 Clique para verificar!",
            reply_markup=InlineKeyboardMarkup([ 
                [InlineKeyboardButton("✅ Verificado", callback_data=f'verificado_{plan}_{user_id}')],
            ])
        )

        await query.edit_message_text(text="👀 Aguardando a confirmação do pagamento. Esse processo pode levar alguns minutos ou até algumas horas.")

# Função para verificar o pagamento e gerar o link temporário
async def verificar_pagamento(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        return

    plan_data = query.data.split('_')
    plan = plan_data[1]
    user_id = int(plan_data[2])

    # Verificando a duração do plano selecionado
    duration_minutes = PLAN_DURATION.get(plan, 0)

    if duration_minutes:
        expire_date = int((datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes)).timestamp())
    else:
        expire_date = None  # Não expira para plano vitalício

    link_temporario = await context.bot.create_chat_invite_link(
        chat_id=GROUP_ID,  # ID do supergrupo
        member_limit=1,
        expire_date=expire_date  # Passando o timestamp Unix
    )

    # Enviar link ao usuário
    await context.bot.send_message(
        user_id, 
        text=f"🎉 Pagamento verificado para o {plan}! 🎉\n\nAcesse o grupo com o link abaixo (válido por 3 minutos):\n{link_temporario.invite_link}\n\nBem-vindo! 👋"
    )

    await query.edit_message_text(text="✅ Pagamento verificado! O link foi enviado ao usuário.")

# Função para listar os usuários verificados
async def listar_verificados(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Você não tem permissão para usar esse comando.")
        return

    if verificados:
        verified_users = "\n".join([
            f"{verificados[user_id]['nome']} (ID: {user_id}) - {verificados[user_id]['plano']} - "
            f"Expira em: {verificados[user_id]['expiracao'].strftime('%d/%m/%Y %H:%M') if verificados[user_id]['expiracao'] else 'Vitalício'}"
            for user_id in verificados
        ])
        await update.message.reply_text(f"Usuários verificados:\n{verified_users}")
    else:
        await update.message.reply_text("Não há usuários verificados no momento.")

# Função para remover um membro do grupo
async def remover_membro(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Você não tem permissão para usar esse comando.")
        return

    if context.args:
        try:
            user_id = int(context.args[0])
            await context.bot.ban_chat_member(chat_id=GROUP_ID, user_id=user_id, revoke_messages=True)
            await update.message.reply_text(f"Usuário com ID {user_id} foi removido do grupo.")
        except ValueError:
            await update.message.reply_text("Por favor, forneça um ID válido de usuário.")
    else:
        await update.message.reply_text("Por favor, forneça o ID do usuário a ser removido.")

# Função principal para rodar o bot
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(plan_choice, pattern='^(quinze_dias|mensal|trimestral|vitalicio)$'))
    application.add_handler(CallbackQueryHandler(pagamento, pattern='^pagamento_.*$'))
    application.add_handler(CallbackQueryHandler(verificar_pagamento, pattern='^verificado_.*$'))
    application.add_handler(CommandHandler('verificados', listar_verificados))
    application.add_handler(CommandHandler('remover', remover_membro))

    print("Bot está rodando...")
    application.run_polling()

if __name__ == '__main__':
    main()
