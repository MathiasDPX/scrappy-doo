from dotenv import load_dotenv
from slack_bolt import App
from datetime import datetime, timezone
from slack_bolt.adapter.socket_mode import SocketModeHandler
from database import *
from os import getenv
import traceback
import json

load_dotenv()
app = App()
bot_id = getenv("BOT_UID", "U09VC4NQXC6")

reactions:dict = []
with open("reactions.json", "r", encoding="utf-8") as f:
    # load reactions or die
    reactions = json.load(f)


def remove_reactions(shortcut, client):
    msg_id = shortcut["message"]["client_msg_id"]
    ts = shortcut["message"]["ts"]
    channel = shortcut["channel"]["id"]

    result = client.conversations_history(
        channel=channel, latest=ts, inclusive=True, limit=1
    )

    message = result.get("messages", [])[0]
    reactions = message.get("reactions", [])

    for reaction in reactions:
        if bot_id not in reaction["users"]:
            continue 
        
        client.reactions_remove(channel=channel, timestamp=ts, name=reaction["name"])


def add_reactions(shortcut, client):
    message = shortcut["message"]["text"]
    channel = shortcut["channel"]["id"]
    ts = shortcut["message"]["ts"]
    
    tags = []
    for keyword, emoji in reactions.items():
        if keyword not in message:
            continue
        
        try:
            client.reactions_add(
                channel=channel,
                timestamp=ts,
                name=emoji
            )
        except:
            pass
        
        tags.append(keyword)
        
    return tags



@app.shortcut("unpost_message")
def handle_unpost(ack, shortcut, client):
    try:
        ack()

        msg_id = shortcut["message"]["client_msg_id"]
        channel = shortcut["channel"]["id"]
        author = shortcut["message"]["user"]
        shortcut_author = shortcut["user"]["id"]

        if author != shortcut_author:
            client.chat_postEphemeral(
                channel=channel,
                user=shortcut_author,
                text="You can only unpost your own post :sadgua:",
            )
            return

        remove_reactions(shortcut, client)
        success = Post.delete_by_id(msg_id)

        if success:
            client.chat_postEphemeral(
                channel=channel,
                user=author,
                text="You're post have been deleted!",
            )
    except:
        client.chat_postEphemeral(
            channel=channel,
            user=author,
            text=f"Unable to delete this post :sadgua:\n```{traceback.format_exc()}```",
        )


@app.shortcut("post_message")
def handle_post(ack, shortcut, client):
    try:
        ack()

        message = shortcut["message"]["text"]
        msg_id = shortcut["message"]["client_msg_id"]
        channel = shortcut["channel"]["id"]
        author = shortcut["message"]["user"]
        shortcut_author = shortcut["user"]["id"]

        if author != shortcut_author:
            client.chat_postEphemeral(
                channel=channel,
                user=shortcut_author,
                text="You can only post your own message :sadgua:",
            )
            return

        ts = shortcut["message"]["ts"]
        ts = datetime.fromtimestamp(float(ts), tz=timezone.utc)

        tags = add_reactions(shortcut, client)
        post = Post(
            message_id=msg_id, author=author, message=message, timestamp=ts, tags=tags
        )

        success = post.save()

        if success:
            client.chat_postEphemeral(
                channel=channel,
                user=author,
                text="Your post has been saved!",
            )
        else:
            client.chat_postEphemeral(
                channel=channel,
                user=author,
                text="This has already been post :sadgua:",
            )
    except:
        client.chat_postEphemeral(
            channel=channel,
            user=author,
            text=f"Unable to post this message :sadgua:\n```{traceback.format_exc()}```",
        )


if __name__ == "__main__":
    handler = SocketModeHandler(app)
    handler.start()
