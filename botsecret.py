import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import pytz
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configurações do bot
BOT_TOKEN = "7876623926:AAHSk2j5YYvbn1mc6pjqOfDmmkl6izevak0"
GROUP_ID = -1002375640119  # ID do supergrupo

# Configuração do fuso horário
TIMEZONE = pytz.timezone("America/Sao_Paulo")

# Inicializa o agendador
scheduler = BackgroundScheduler(timezone=TIMEZONE)
scheduler.start()

# Lista de usuários autorizados
AUTHORIZED_USERS = [7338492112]  # Substitua pelo user_id autorizado

async def check_user_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Verifica se o usuário está autorizado a usar o bot."""
    user_id = update.effective_user.id
    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("⛔ Acesso proibido!")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando inicial do bot."""
    if not await check_user_access(update, context):
        return
    await update.message.reply_text(
        "Olá! Vamos agendar uma postagem no grupo. Envie as mídias (fotos ou vídeos), todas de uma vez ou uma por vez."
    )


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com mídia enviada pelo usuário (fotos ou vídeos)."""
    if not await check_user_access(update, context):
        return
    media_files = context.user_data.get("media", {"photos": [], "videos": []})

    # Coleta todas as fotos
    if update.message.photo:
        # Apenas a foto com a maior resolução será armazenada
        highest_resolution_photo = update.message.photo[-1].file_id
        if highest_resolution_photo not in media_files["photos"]:
            media_files["photos"].append(highest_resolution_photo)

    # Coleta todos os vídeos
    if update.message.video:
        if update.message.video.file_id not in media_files["videos"]:
            media_files["videos"].append(update.message.video.file_id)

    # Atualiza o contexto com as mídias processadas
    context.user_data["media"] = media_files

    if media_files["photos"] or media_files["videos"]:
        # Remove mensagens duplicadas sobre o status
        if "status_message" in context.user_data:
            try:
                await context.user_data["status_message"].delete()
            except:
                pass  # Ignora erros ao tentar deletar uma mensagem inexistente

        # Envia uma única mensagem atualizada com o número total de fotos e vídeos
        status_message = await update.message.reply_text(
            f"Recebemos {len(media_files['photos'])} foto(s) e {len(media_files['videos'])} vídeo(s)!\n\nAgora, escolha a data do envio. Responda com:\n1 - Para *Hoje*\n2 - Para *Amanhã*"
        )

        # Salva a mensagem de status para possíveis exclusões futuras
        context.user_data["status_message"] = status_message
        context.user_data["step"] = "choose_date"
    else:
        await update.message.reply_text(
            "Não conseguimos identificar mídias na mensagem. Por favor, envie fotos ou vídeos novamente."
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gerencia a interação com o usuário durante o agendamento."""
    if not await check_user_access(update, context):
        return

    # Resto do código de processamento de texto...
    user_response = update.message.text.lower()
    step = context.user_data.get("step")

    if step == "choose_date":
        if user_response in ["1", "hoje"]:
            context.user_data["date"] = datetime.now(TIMEZONE).date()
            await update.message.reply_text(
                "Você escolheu *Hoje*. Agora, digite o horário no formato HH:MM (exemplo: 19:25)."
            )
            context.user_data["step"] = "choose_time"
        elif user_response in ["2", "amanhã"]:
            context.user_data["date"] = (datetime.now(TIMEZONE) + timedelta(days=1)).date()
            await update.message.reply_text(
                "Você escolheu *Amanhã*. Agora, digite o horário no formato HH:MM (exemplo: 19:25)."
            )
            context.user_data["step"] = "choose_time"
        else:
            await update.message.reply_text(
                "Escolha inválida. Por favor, responda com '1' para Hoje ou '2' para Amanhã."
            )
    elif step == "choose_time":
        try:
            hours, minutes = map(int, user_response.split(":"))
            if 0 <= hours < 24 and 0 <= minutes < 60:
                scheduled_datetime = TIMEZONE.localize(
                    datetime.combine(context.user_data["date"], datetime.min.time()) + timedelta(hours=hours, minutes=minutes)
                )

                if scheduled_datetime < datetime.now(TIMEZONE):
                    await update.message.reply_text(
                        "O horário informado é inválido porque está no passado. Por favor, tente novamente."
                    )
                    return

                context.user_data["scheduled_time"] = scheduled_datetime
                context.user_data["step"] = "add_caption"
                await update.message.reply_text(
                    "Deseja adicionar um texto à postagem? Responda com 'Sim' ou 'Não'."
                )
            else:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "Formato de horário inválido. Por favor, insira no formato HH:MM (exemplo: 19:25)."
            )
    elif step == "add_caption":
        if user_response in ["sim", "s"]:
            context.user_data["step"] = "enter_caption"
            await update.message.reply_text(
                "Por favor, digite o texto que deseja adicionar à postagem."
            )
        elif user_response in ["não", "nao", "n"]:
            context.user_data["caption"] = None
            await schedule_post(update, context)
        else:
            await update.message.reply_text(
                "Resposta inválida. Responda com 'Sim' ou 'Não'."
            )
    elif step == "enter_caption":
        context.user_data["caption"] = update.message.text
        await schedule_post(update, context)
    else:
        await update.message.reply_text(
            "Por favor, envie uma mídia para começar o agendamento."
        )

async def schedule_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Agenda o envio da postagem."""
    media_files = context.user_data["media"]
    caption = context.user_data.get("caption")
    scheduled_time = context.user_data["scheduled_time"]

    scheduler.add_job(
        sync_send_post_to_group,
        trigger=DateTrigger(run_date=scheduled_time),
        args=[media_files, caption],
        id=f"{update.effective_chat.id}_{scheduled_time.isoformat()}",
        misfire_grace_time=60,
    )

    confirmation_message = f"📅 Postagem agendada para {scheduled_time.strftime('%d/%m/%Y às %H:%M')}."
    if caption:
        confirmation_message += f"\n\nTexto: {caption}"
    await update.message.reply_text(confirmation_message)

    context.user_data.clear()


def sync_send_post_to_group(media_files: dict, caption: str) -> None:
    """Wrapper síncrono para o envio da postagem ao grupo."""
    asyncio.run(send_post_to_group(media_files, caption))


def chunk_list(lst, n):
    """Divide uma lista em blocos de tamanho n."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


async def send_post_to_group(media_files: dict, caption: str) -> None:
    """Envia a postagem ao grupo como um álbum, combinando fotos e vídeos."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    async with app:
        try:
            # Combina fotos e vídeos em uma única lista
            all_media = media_files["photos"] + media_files["videos"]

            # Divide em blocos de até 10 itens
            media_chunks = list(chunk_list(all_media, 10))

            for chunk_index, media_chunk in enumerate(media_chunks):
                media_group = []

                for i, media in enumerate(media_chunk):
                    # Determina se o item é foto ou vídeo
                    is_photo = media in media_files["photos"]
                    if i == 0 and chunk_index == 0 and caption:  # Adiciona a legenda ao 1º item
                        if is_photo:
                            media_group.append(InputMediaPhoto(media=media, caption=caption, parse_mode="Markdown"))
                        else:
                            media_group.append(InputMediaVideo(media=media, caption=caption, parse_mode="Markdown"))
                    else:
                        if is_photo:
                            media_group.append(InputMediaPhoto(media=media))
                        else:
                            media_group.append(InputMediaVideo(media=media))

                # Envia o bloco como álbum
                await app.bot.send_media_group(chat_id=GROUP_ID, media=media_group)

        except Exception as e:
            print(f"Erro ao enviar a postagem ao grupo: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot está rodando...")
    app.run_polling()