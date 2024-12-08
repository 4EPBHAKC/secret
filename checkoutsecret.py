from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import asyncio

# Token do bot
TOKEN = '7669234688:AAGQ3a-cNRwLwHuDvWwOIEpcVZt9Wq7FOrA'  # Substitua pelo seu token real

# Definindo a chave PIX (única para todos os planos)
PIX_KEY = 'lauracorreiamodel@gmail.com'  # Substitua pela sua chave PIX

# ID do administrador (você)
ADMIN_ID = 7338492112  # Substitua pelo seu ID de usuário no Telegram

# Função para enviar os planos
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🟢 Plano Mensal - R$ 15,00", callback_data='mensal')],
        [InlineKeyboardButton("🟠 Plano Trimestral - R$ 30,00", callback_data='trimestral')],
        [InlineKeyboardButton("🔵 Plano Vitalício - R$ 50,00", callback_data='vitalicio')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🎉 Olá! Escolha um plano para se inscrever e aproveite nosso conteúdo exclusivo! 🎉\n\nSelecione abaixo:', reply_markup=reply_markup)

# Função para exibir a chave PIX após o plano ser escolhido
async def plan_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    plan = query.data
    plan_name = {
        'mensal': 'Plano Mensal',
        'trimestral': 'Plano Trimestral',
        'vitalicio': 'Plano Vitalício'
    }
    price = {
        'mensal': 'R$ 15,00',
        'trimestral': 'R$ 30,00',
        'vitalicio': 'R$ 50,00'
    }
    
    await query.edit_message_text(
        text=f"✅ Você escolheu o {plan_name[plan]} - {price[plan]}.\n\n💳 Chave PIX: {PIX_KEY}\n\nApós realizar o pagamento, clique em 'Pago' para confirmar! 🏁"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Pago", callback_data=f'pagamento_{plan}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("🤑 Clique em 'Pago' após realizar o pagamento para confirmar sua inscrição!", reply_markup=reply_markup)

# Função para registrar o pagamento
async def pagamento(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    plan = query.data.split('_')[1]

    user_name = query.from_user.first_name
    user_id = query.from_user.id
    plan_name = {
        'mensal': 'Plano Mensal',
        'trimestral': 'Plano Trimestral',
        'vitalicio': 'Plano Vitalício'
    }

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💸 O usuário {user_name} (ID: {user_id}) informou que pagou o {plan_name[plan]}.\n🔄 Clique para verificar!",
        reply_markup=InlineKeyboardMarkup([ 
            [InlineKeyboardButton("✅ Verificado", callback_data=f'verificado_{plan}_{user_id}')],
        ])
    )

    await query.edit_message_text(text="👀 Aguardando a verificação do pagamento...")

# Função para verificar o pagamento e gerar o link temporário
async def verificar_pagamento(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        return

    plan_data = query.data.split('_')
    plan = plan_data[1]
    user_id = int(plan_data[2])

    # Gerando o link temporário
    link_temporario = "https://t.me/+cdI1QWC4io45YWFh"  # Link do grupo

    # Enviar confirmação ao usuário e link temporário
    await context.bot.send_message(user_id, text=f"🎉 Seu pagamento para o {plan} foi verificado! 🎉\n\nVocê foi adicionado ao grupo! 🎊\n\nAcesse o grupo com o link abaixo (válido por 3 minutos):\n\n{link_temporario} ⏳\n\nAproveite e seja bem-vindo! 👋")
    
    await query.edit_message_text(text="✅ Pagamento verificado! O usuário foi adicionado ao grupo com um link temporário.")

    # Aguardar 3 minutos e depois invalidar o link
    await asyncio.sleep(120)  # 180 segundos = 3 minutos
    # Aqui poderia invalidar o link ou enviar uma mensagem para lembrar sobre o tempo de expiração

# Função principal para rodar o bot
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(plan_choice, pattern='^(mensal|trimestral|vitalicio)$'))
    application.add_handler(CallbackQueryHandler(pagamento, pattern='^pagamento_.*$'))
    application.add_handler(CallbackQueryHandler(verificar_pagamento, pattern='^verificado_.*$'))

    # Print que indica que o bot foi iniciado
    print("Bot está rodando...")
    
    application.run_polling()

if __name__ == '__main__':
    main()
