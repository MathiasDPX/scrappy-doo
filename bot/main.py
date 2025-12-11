from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient
from datetime import datetime, timezone
from dotenv import load_dotenv
from slack_bolt import App
from database import *
from os import getenv
import traceback
import requests
import json
import re

load_dotenv()
app = App()
bot_id = getenv("BOT_UID", "U09VC4NQXC6")
UNESCAPED_USER_PATTERN = r".+@(U[A-Z0-9]+).+"

reactions = {}
with open("reactions.json", "r", encoding="utf-8") as f:
    # load reactions or die
    reactions = json.load(f)


def remove_reactions(shortcut, client):
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
    for keyword, emoji in reactions["kv"].items():
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

    authorized = [author_id, bot_id, "U015D6A36AG"]  # scrappy

    for reaction in message.get("reactions", []):
        if any(user in [authorized] for user in reaction["users"]) and not (
            any(reaction["name"] in reactions["blacklist"])
        ):
            reactions.add(reaction["name"])
    return list(reactions)


def process_message_post(
    message: dict, channel: str, client: WebClient
) -> tuple[bool, str]:
    content = message["text"]
    msg_id = message["client_msg_id"]
    author = message["user"]
    ts = datetime.fromtimestamp(float(message["ts"]), tz=timezone.utc)

    files = []
    for file in message.get("files", []):
        if not (
            file["mimetype"].startswith("image/")
            or file["mimetype"].startswith("video/")
        ):
            continue
        files.append(file["url_private"])

    if len(files) == 0:
        return False, "You need to have images or videos in your post"

    tags = add_reactions({"message": message, "channel": {"id": channel}}, client)

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
        return True, "Your post has been saved!"
    else:
        return False, "This has already been post :sadgua:"


@app.event("message")
def new_message(event, say, client):
    if event.get("channel") not in ["C09VC37P2NA", "C01504DCLVD"]:
        # Only #scrappy-doo or #scrapbook
        return

    if event.get("subtype") == "message_deleted":
        msg_id = event["previous_message"]["client_msg_id"]
        Post.delete_by_id(msg_id)

        client.chat_postEphemeral(
            channel=event["channel"],
            user=event["previous_message"]["user"],
            text=f"Your post has been deleted :agabye:",
        )

        return

    if event.get("thread_ts") != None:
        # Message sent in a thread
        return

    # Check if message has files before processing
    if not event.get("files"):
        client.chat_postEphemeral(
            channel=event["channel"],
            user=event["user"],
            text="You need to have images or videos in your post",
        )
        return

    try:
        success, msg = process_message_post(
            message=event, channel=event["channel"], client=client
        )

        # Show message for both success and failure
        client.chat_postEphemeral(
            channel=event["channel"],
            user=event["user"],
            text=msg,
        )
    except Exception as e:
        client.chat_postEphemeral(
            channel=event["channel"],
            user=event["user"],
            text=f"Unable to auto-post this message :sadgua:\n```{str(e)}```",
        )


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


@app.command("/import-scrapbook")
def import_scrapbook(ack, respond, command):
    ack()
    username = command["user_name"]
    userid = command["user_id"]

    r = requests.get(f"https://scrapbook.hackclub.com/api/users/{username}")
    data = r.json()
    r.raise_for_status()

    posts_to_import = []
    for post_data in data.get("posts", []):
        try:
            tags = [tag["name"] for tag in post_data.get("reactions")]

            ts = datetime.fromtimestamp(
                float(post_data.get("timestamp")), tz=timezone.utc
            )
            post = Post(
                message_id=post_data.get("id"),
                message=post_data.get("text"),
                author=userid,
                timestamp=ts,
                tags=tags,
                files=post_data.get("attachments", []),
            )
            posts_to_import.append(post)
        except Exception as e:
            pass

    success_count = Post.save_batch(posts_to_import)
    respond(f":agabusiness: {success_count} posts exported!")


@app.command("/posts")
def userinfo(ack, respond, command, client):
    ack()

    userid = command["user_id"]

    if len(command["text"]) != 0:
        match = re.match(UNESCAPED_USER_PATTERN, command["text"])
        if match:
            if match.group(1):
                userid = match.group(1)

    posts = Post.get_by_author(userid, limit=5)

    def format_post_block(post):
        ts_str = post.timestamp.strftime("%Y-%m-%d %H:%M UTC")
        tags_str = ", ".join(post.tags) if post.tags else "No tags"
        file_count = len(post.files) if post.files else 0

        # Section with message text
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{ts_str}*\n{post.message or '_No text_'}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Tags: `{tags_str}`"},
                    {"type": "mrkdwn", "text": f"Files: {file_count}"},
                ],
            },
        ]

        if post.files:
            blocks.append(
                {"type": "image", "image_url": post.files[0], "alt_text": "attachment"}
            )

        blocks.append({"type": "divider"})
        return blocks

    blocks = []
    if posts:
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "User Posts", "emoji": True},
            }
        )
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Showing latest {len(posts)} posts for <@{userid}>",
                    }
                ],
            }
        )
        blocks.append({"type": "divider"})
        for post in posts:
            blocks.extend(format_post_block(post))
    else:
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"No posts found for <@{userid}>."},
            }
        ]

    client.views_open(
        trigger_id=command["trigger_id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "User Info"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": blocks,
        },
    )


@app.shortcut("post_message")
def handle_post(ack, shortcut, client: WebClient):
    try:
        ack()

        message = shortcut["message"]
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

        success, msg = process_message_post(
            message=message, channel=channel, client=client
        )

        client.chat_postEphemeral(
            channel=channel,
            user=author,
            text=msg,
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
