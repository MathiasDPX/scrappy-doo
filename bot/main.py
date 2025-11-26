from dotenv import load_dotenv
from slack_bolt import App
from datetime import datetime, timezone
from slack_bolt.adapter.socket_mode import SocketModeHandler
from database import *
import traceback

load_dotenv()
app = App()


@app.shortcut("unpost_message")
def handle_unpost(ack, shortcut, client):
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
                text="You can only unpost your own post :sadgua:",
            )
            return

        ts = shortcut["message"]["ts"]
        ts = datetime.fromtimestamp(float(ts), tz=timezone.utc)

        post = Post(
            message_id=msg_id, author=author, message=message, timestamp=ts, tags=[]
        )

        post.save()

        success = Post.delete_by_id(msg_id)

        if success:
            client.chat_postEphemeral(
                channel=channel,
                user=author,
                text="You're post have been deleted!",
            )
    except Exception as e:
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

        post = Post(
            message_id=msg_id, author=author, message=message, timestamp=ts, tags=[]
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
    except Exception as e:
        client.chat_postEphemeral(
            channel=channel,
            user=author,
            text=f"Unable to post this message :sadgua:\n```{traceback.format_exc()}```",
        )


if __name__ == "__main__":
    handler = SocketModeHandler(app)
    handler.start()
