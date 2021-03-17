from traceback import format_exc

from pyrogram.errors import RPCError
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from alita import HELP_COMMANDS, LOGGER
from alita.bot_class import Alita
from alita.database.chats_db import Chats
from alita.database.notes_db import Notes
from alita.database.rules_db import Rules
from alita.tr_engine import tlang
from alita.utils.msg_types import Types
from alita.utils.string import build_keyboard, parse_button

# Initialize
rules_db = Rules()
notes_db = Notes()
chats_db = Chats()


async def send_cmd(client: Alita, msgtype):
    GET_FORMAT = {
        Types.TEXT.value: client.send_message,
        Types.DOCUMENT.value: client.send_document,
        Types.PHOTO.value: client.send_photo,
        Types.VIDEO.value: client.send_video,
        Types.STICKER.value: client.send_sticker,
        Types.AUDIO.value: client.send_audio,
        Types.VOICE.value: client.send_voice,
        Types.VIDEO_NOTE.value: client.send_video_note,
        Types.ANIMATION.value: client.send_animation,
        Types.ANIMATED_STICKER.value: client.send_sticker,
        Types.CONTACT: client.send_contact,
    }
    return GET_FORMAT[msgtype]


async def gen_cmds_kb(m):
    """Generate the keyboard for languages."""
    if isinstance(m, CallbackQuery):
        m = m.message

    cmds = sorted(list(HELP_COMMANDS.keys()))
    kb = []

    while cmds:
        if cmds:
            cmd = cmds[0]
            a = [
                InlineKeyboardButton(
                    tlang(m, cmd),
                    callback_data=f"get_mod.{cmd.lower()}",
                ),
            ]
            cmds.pop(0)
        if cmds:
            cmd = cmds[0]
            a.append(
                InlineKeyboardButton(
                    tlang(m, cmd),
                    callback_data=f"get_mod.{cmd.lower()}",
                ),
            )
            cmds.pop(0)
        if cmds:
            cmd = cmds[0]
            a.append(
                InlineKeyboardButton(
                    tlang(m, cmd),
                    callback_data=f"get_mod.{cmd.lower()}",
                ),
            )
            cmds.pop(0)
        kb.append(a)
    return kb


async def gen_start_kb(q):
    """Generate keyboard with start menu options."""

    from alita import BOT_USERNAME

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"📚 {(tlang(q, 'start.commands_btn'))}",
                    callback_data="commands",
                ),
                InlineKeyboardButton(
                    f"ℹ️ {(tlang(q, 'start.infos_btn'))}",
                    callback_data="infos",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"🌐 {(tlang(q, 'start.language_btn'))}",
                    callback_data="chlang",
                ),
                InlineKeyboardButton(
                    f"➕ {(tlang(q, 'start.add_chat_btn'))}",
                    url=f"https://t.me/{BOT_USERNAME}?startgroup=new",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"🗃️ {(tlang(q, 'start.source_code'))}",
                    url="https://github.com/Divkix/Alita_Robot",
                ),
            ],
        ],
    )
    return keyboard


async def get_private_note(c: Alita, m: Message, help_option: str):
    """Get the note in pm of user, with parsing enabled."""
    from alita import BOT_USERNAME

    help_lst = m.text.split("_")
    chat_id = int(help_lst[1])

    if len(help_lst) == 2:
        chat_id = help_option.replace("notes_", "")
        all_notes = notes_db.get_all_notes(chat_id)
        chat_title = chats_db.get_chat_info(chat_id)["chat_title"]
        rply = f"Notes in {chat_title}:\n\n"
        for note in all_notes:
            rply += f"- [{note[0]}](https://t.me/{BOT_USERNAME}?start=note_{chat_id}_{note[1]})\n"
        await m.reply_text(rply, disable_web_page_preview=True, quote=True)
        return
    if len(help_lst) == 3:
        note_hash = help_option.split("_")[2]
        getnotes = notes_db.get_note_by_hash(note_hash)
    else:
        return

    msgtype = getnotes["msgtype"]
    if not msgtype:
        await m.reply_text(
            "<b>Error:</b> Cannot find a type for this note!!",
            quote=True,
        )
        return

    if msgtype == Types.TEXT:
        teks, button = await parse_button(getnotes["note_value"])
        button = await build_keyboard(button)
        button = InlineKeyboardMarkup(button) if button else None
        if button:
            try:
                await m.reply_text(
                    teks,
                    reply_markup=button,
                    disable_web_page_preview=True,
                    quote=True,
                )
                return
            except RPCError as ef:
                await m.reply_text(
                    "An error has occured! Cannot parse note.",
                    quote=True,
                )
                LOGGER.error(ef)
                LOGGER.error(format_exc())
                return
        else:
            await m.reply_text(teks, quote=True)
            return
    elif msgtype in (
        Types.STICKER,
        Types.VIDEO_NOTE,
        Types.CONTACT,
        Types.ANIMATED_STICKER,
    ):
        await (await send_cmd(c, msgtype))(m.chat.id, getnotes["fileid"])
    else:
        if getnotes["note_value"]:
            teks, button = await parse_button(getnotes["note_value"])
            button = await build_keyboard(button)
            button = InlineKeyboardMarkup(button) if button else None
        else:
            teks = ""
            button = None
        if button:
            try:
                await (await send_cmd(c, msgtype))(
                    m.chat.id,
                    getnotes["fileid"],
                    caption=teks,
                    reply_markup=button,
                )
                return
            except RPCError as ef:
                await m.reply_text(
                    teks,
                    quote=True,
                    reply_markup=button,
                    disable_web_page_preview=True,
                )
                LOGGER.error(ef)
                LOGGER.error(format_exc())
                return
        else:
            await (await send_cmd(c, msgtype))(
                m.chat.id,
                getnotes["fileid"],
                caption=teks,
            )
    return


async def get_private_rules(_, m: Message, help_option: str):
    chat_id = int(help_option.split("_")[1])
    rules = rules_db.get_rules(chat_id)
    chat_title = chats_db.get_chat_info(chat_id)["chat_title"]
    await m.reply_text(
        (tlang(m, "rules.get_rules")).format(
            chat=chat_title,
            rules=rules,
        ),
        quote=True,
        disable_web_page_preview=True,
    )
    return


async def get_help_msg(m, help_option: str):
    """Helper function for getting help_msg and it's keyboard."""

    help_msg = None
    help_kb = None

    if help_option == "help":
        help_msg = tlang(m, "general.commands_available")
        help_kb = InlineKeyboardMarkup(
            [
                *(await gen_cmds_kb(m)),
                [
                    InlineKeyboardButton(
                        f"« {(tlang(m, 'general.back_btn'))}",
                        callback_data="start_back",
                    ),
                ],
            ],
        )
    else:
        help_cmd_keys = sorted(
            [i.split(".")[1].lower() for i in list(HELP_COMMANDS.keys())],
        )
        if help_option in help_cmd_keys:
            help_option_value = HELP_COMMANDS[f"plugins.{help_option}.main"]
            help_msg = tlang(m, help_option_value)
            help_kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"« {(tlang(m, 'general.back_btn'))}",
                            callback_data="commands",
                        ),
                    ],
                ],
            )

    return help_msg, help_kb