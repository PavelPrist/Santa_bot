

def algoritm()->list[list]:
    data = ...


    for ... in data:
        ...
    return ...


def sand_massages(data:list[list]):
    for list1 in data:
        text = f"""
            {list1['...']}
            {list1['...']}
            {list1['...']}
            {list1['...']}
        """

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
        )