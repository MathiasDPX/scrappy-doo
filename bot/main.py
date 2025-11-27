from dotenv import load_dotenv
from slack_bolt import App
from datetime import datetime, timezone
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient
from database import *
from os import getenv
import traceback
import json

load_dotenv()
app = App()
bot_id = getenv("BOT_UID", "U09VC4NQXC6")

reactions: dict = []
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
            client.reactions_add(channel=channel, timestamp=ts, name=emoji)
        except:
            pass

        tags.append(keyword)

    return tags


def get_reactions(message: dict, author_id: str, bot_id: str) -> list[str]:
    reactions = set()
    for reaction in message.get("reactions", []):
        if any(user == author_id for user in reaction["users"]):
            reactions.add(reaction["name"])
        if any(user == bot_id for user in reaction["users"]):
            reactions.add(reaction["name"])
    return list(reactions)


@app.event("reaction_added")
@app.event("reaction_removed")
def handle_reaction(event, say, client):
    if event["user"] != event["item_user"]:
        return

    response = client.conversations_history(
        channel=event["item"]["channel"],
        latest=event["item"]["ts"],
        inclusive=True,
        limit=1,
    )
    message = response["messages"][0]
    msg_id = message["client_msg_id"]

    post = Post.get_by_id(msg_id)
    if not post:
        return

    reactions = get_reactions(message, event["item_user"], bot_id)
    post.set_tags(reactions)


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
def handle_post(ack, shortcut, client: WebClient):
    try:
        ack()

        message = shortcut["message"]
        content = message["text"]
        msg_id = message["client_msg_id"]
        channel = shortcut["channel"]["id"]
        author = message["user"]
        shortcut_author = shortcut["user"]["id"]

        if author != shortcut_author:
            client.chat_postEphemeral(
                channel=channel,
                user=shortcut_author,
                text="You can only post your own message :sadgua:",
            )
            return

        ts = message["ts"]
        ts = datetime.fromtimestamp(float(ts), tz=timezone.utc)

        files = []
        for file in message.get("files", []):
            if not (
                file["mimetype"].startswith("image/")
                or file["mimetype"].startswith("video/")
            ):
                continue

            # TODO  Make the link public
            files.append(file["url_private"])

        if len(files) == 0:
            client.chat_postEphemeral(
                channel=channel,
                user=author,
                text="You need to have images or videos in your post",
            )
            return

        tags = add_reactions(shortcut, client)
        post = Post(
            message_id=msg_id,
            author=author,
            message=content,
            timestamp=ts,
            tags=tags,
            files=files,
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
