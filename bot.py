from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from time import time
from typing import List
import os
import pickle

from resources import constantes
from sheets import addRow, readInv

SEP_CALLBACK = "|"
CASIERS = constantes.CASIERS
INGREDIENTS = ["Lait d'avoine", "Lait de riz", "Choco", "Cacao", "Cannelle", "Matcha", "Épices de Noël"]
QUANTITES = [-1, 1, -5, 5, -6, 6]
LIMIT_RESPONSE = 300 #300s de délai entre dernière interaction et réponse

ADMINS = constantes.ADMINS
COMITE = constantes.COMITE
GROUPS = constantes.GROUPS
THREADS = constantes.THREADS

def fetch_inv(bot: TeleBot = None, message = None) -> dict:
    """
    Fetch the inventary. If a bot and message are provided, send a confirmation that the fetch has been completed.
    """
    
    DATA["INVENTARY"].update(readInv())

    if bot is not None and message is not None:
        bot.send_message(message.chat.id, "Fetch ok")
    
    return DATA["INVENTARY"]

#load bot data
dataPath = os.path.join("resources", "bot_data.p")
if os.path.exists(dataPath):
    DATA = pickle.load(open(dataPath, "rb"))
else:
    DATA = {"RECORD_INV": dict(), "INVENTARY": dict(), "WILL_SEND_BILL": set()}
    #don't forget to perform readInv on start
    
    #DATA["RECORD_INV"] is a dictionary {userId: {"casier":x, "timestamp":y, "ingredient":z, "quantite":a}}
    #DATA["INVENTARY"] is a dictionary {ingredient: {locker: quantity}}
    #DATA["WILL_SEND_BILL"] is a set {userId}

fetch_inv()

def save() -> None:
    """
    Save the bot data as a pickle file.
    """
    
    pickle.dump(DATA, open(dataPath, "wb"))

def ayo(bot: TeleBot, message) -> None:
    """
    Ayo !
    """
    
    bot.send_message(message.chat.id, "Ayo !")

def maj(bot: TeleBot, message) -> None:
    """
    Launch a bot update (recover the latest version on the git repository).
    """
    if message.from_user.id in ADMINS:
        bot.send_message(message.chat.id, "Mise à jour lancée")
        os.system("git pull")

def bill(bot: TeleBot, message) -> None:
    """
    To send a bill to the treasurer.
    """

    if message.chat.type == "private":
        DATA["WILL_SEND_BILL"].add(message.from_user.id)
        bot.send_message(message.chat.id, "Le prochain message que tu m'enverras sera retransmis dans le topic Remboursements du groupe Chocopoly - Trésorerie.")

def creeMarkup(cbName: str, options: List[str], userId: int) -> InlineKeyboardMarkup:
    """
    Create a markup with options for the user.
    """
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(*[InlineKeyboardButton(x, callback_data=SEP_CALLBACK.join([cbName, str(userId), x])) for x in options])

    return markup

def reg_inv(bot: TeleBot, message) -> None:
    """
    Start the interaction to let the user register a transaction of inventary.
    """
    bot.send_message(message.from_user.id, "Choisir le casier de transaction", reply_markup=creeMarkup("casier_inv", CASIERS, message.from_user.id))

def inv_cb(bot: TeleBot, call) -> None:
    """
    Callback for the registration of a transaction of inventary.
    """

    trigger = call.data.split(SEP_CALLBACK)[0]
    currentTime = time()

    toAffi = ["casier", "ingredient", "quantite"]
    affiResume = lambda recordUser: ", ".join(str(recordUser[k]) for k in toAffi if k in recordUser)

    dataRecord = DATA["RECORD_INV"]
    _, userIdraw, data = call.data.split(SEP_CALLBACK)
    userId = int(userIdraw)
    checkTime = lambda: (currentTime - dataRecord[userId]["timestamp"] < LIMIT_RESPONSE)

    if trigger == "casier_inv":
        casier = data
        
        if userId in dataRecord and checkTime():
            dataRecord[userId]["timestamp"] = currentTime
            dataRecord[userId]["casier"] = casier
        else:
            dataRecord[userId] = {"casier": casier, "timestamp": currentTime}

        bot.answer_callback_query(call.id, affiResume(dataRecord[userId]))

        if "ingredient" not in dataRecord[userId]:
            bot.send_message(userId, "Choisir l'ingrédient", reply_markup=creeMarkup("ingredient_inv", INGREDIENTS, userId))
    elif trigger == "ingredient_inv":
        ingredient = data

        if userId in dataRecord and checkTime():
            dataRecord[userId]["ingredient"] = ingredient

            bot.answer_callback_query(call.id, affiResume(dataRecord[userId]))
            if "quantite" not in dataRecord[userId]:
                bot.send_message(userId, "Quantité ajoutée dans le casier: 0", reply_markup=creeMarkup("qte_inv", [str(x) if x < 0 else f"+{x}" for x in QUANTITES] + ["OK"], userId))
        else:
            if userId in dataRecord:
                del dataRecord[userId]
    elif trigger == "qte_inv":
        ajout = int(data) if data != "OK" else None

        if userId in dataRecord and checkTime():
            if ajout:
                dataRecord[userId]["quantite"] = dataRecord[userId].get("quantite", 0) + ajout

                bot.answer_callback_query(call.id, affiResume(dataRecord[userId]))
                bot.edit_message_text(f"Quantité ajoutée dans le casier : {dataRecord[userId]['quantite']}", call.message.chat.id, call.message.message_id, reply_markup=creeMarkup("qte_inv", [str(x) if x < 0 else f"+{x}" for x in QUANTITES] + ["OK"], userId))
            else:
                casier, item, quantite = map(dataRecord[userId].get, ("casier", "ingredient", "quantite"))
                if quantite:
                    addRow(casier, item, quantite, COMITE[userId])
                    
                    bot.answer_callback_query(call.id, affiResume(dataRecord[userId]))
                    bot.send_message(userId, f"Enregistrement de : {quantite} {item} dans le casier {casier}")
                    DATA["INVENTARY"][item.split()[0]][casier] = DATA["INVENTARY"][item.split()[0]].get(casier, 0) + quantite
                    del dataRecord[userId]
                else:
                    bot.answer_callback_query(call.id, "Pas de changement à enregistrer")
                    bot.send_message(userId, "Pas de changement à enregistrer")
        else:
            if userId in dataRecord:
                del dataRecord[userId]

def check_inv(bot: TeleBot, message) -> None:
    locker_or_someone = lambda name: any(x.isdigit() for x in name)
    affi_details = lambda details: ", ".join(f"{qty} au {locker_name}" if locker_or_someone(locker_name) else f"{qty} chez {locker_name}" for locker_name, qty in details.items())
    total_ing = lambda details: sum(details.values())
    bot.send_message(message.from_user.id, "*Inventaire*\n" + "\n".join(f"{categ} (total {total_ing(details)}) : {affi_details(details)}" for categ, details in DATA["INVENTARY"].items()))

def casiers(bot: TeleBot, message) -> None:
    bot.send_message(message.from_user.id, "*CM1-989*\n- Chocolat + Cacao\n- Gobelets\n- 2 Casseroles\n- Épices\n\n*CM1-1031*\n- Matos de vaisselle\n- Goodies\n- Plaques chauffantes\n\n*CM1-1058*\n- Lait\n- Factures")

def check_if_group(func):
    def do_if_group(bot: TeleBot, message):
        chat_info = bot.get_chat(message.chat.id)
        if chat_info.type in ["group", "supergroup"]:
            return func(bot, message)
        else:
            bot.send_message(message.chat.id, "Please use this command in a group.")
    return do_if_group

def check_if_private(func):
    def do_if_private(bot: TeleBot, message):
        chat_info = bot.get_chat(message.chat.id)
        if chat_info.type == "private":
            return func(bot, message)
        else:
            bot.send_message(message.chat.id, "Please use this command in a private chat with the bot.")
    return do_if_private

@check_if_group
def coffee(bot: TeleBot, message) -> None:
    '''Ban whomever uses this command'''
    chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if not chat_member.status in ['creator', 'administrator'] :
        #bot.ban_chat_member(message.chat.id, message.from_user.id)
        bot.send_message(message.chat.id, f"{message.from_user.first_name} used a forbidden command and had to be punished. Let this serve as an example.")

@check_if_private
def feedback(bot: TeleBot, message) -> None:
    msg = bot.send_message(message.chat.id, "Please write the message you would like to send to the committee.")
    bot.register_next_step_handler(msg, send_feedback, bot)

def send_feedback(message, bot: TeleBot):
    full_msg = f"Message sent by {message.from_user.full_name} \nTelegram username: {message.from_user.username}\nTelegram id: {message.from_user.id}\nMessage: {message.text}"
    bot.send_message(GROUPS["Comite"], full_msg, message_thread_id=THREADS["Comite"]["Feedback"])
#-------------------------------------------------------------------------------------------------------------------

funcs = {"/ayo": ayo, "/bill": bill, "/inv": reg_inv, "/màj": maj, "/check_inv": check_inv, "/fetch_inv": fetch_inv, "/coffee": coffee, "/feedback": feedback, "/casiers": casiers}
callbacks = {"inv": inv_cb}
def main() -> TeleBot:
    """
    Main function that defines how the bot handles messages.
    """
    
    bot = TeleBot(constantes.TOKEN)

    @bot.message_handler(func=lambda message: True)
    def messageHandler(message: TeleBot) -> None:
        """
        From a message do things.
        """
        
        author = message.from_user.id
        if author in COMITE:
            text = message.text if message.text else message.caption
            print(message.from_user.id, message.forward_from) #pour récupérer l'id telegram de quelqu'un

            if text.startswith("/"):
                command = text.split()[0]

                fun = funcs.get(command.lower())
                if fun:
                    fun(bot, message)
            elif author in DATA["WILL_SEND_BILL"]:
                bot.forward_message(GROUPS["Trésorerie"], message.chat.id, message.message_id, message_thread_id=THREADS["Trésorerie"]["Remboursement"])
                DATA["WILL_SEND_BILL"].remove(author)

    @bot.callback_query_handler(func=lambda call: True)
    def callback_query(call) -> None:
        """
        From a callback do things.
        """
        
        name_cb, *_ = call.data.split(SEP_CALLBACK)
        name_cb_type = name_cb.split("_")[-1]

        fun = callbacks.get(name_cb_type)
        if fun:
            fun(bot, call)

    return bot

print("Bot started at", time())
bot = main()
bot.infinity_polling()