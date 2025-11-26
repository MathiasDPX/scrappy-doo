from dotenv import load_dotenv
from slack_bolt import App
from datetime import datetime, timezone
from slack_bolt.adapter.socket_mode import SocketModeHandler
from database import *

load_dotenv()
app = App()


@app.event("reaction_removed")
def handle_reaction_removed(event, say, client):
    reaction = event.get("reaction")

    if reaction != "scrappy-doo":
        return

    user_id = event.get("user")
    item = event.get("item", {})
    channel = item.get("channel")
    ts = item.get("ts")

    response = client.conversations_history(
        channel=channel, latest=ts, limit=1, inclusive=True
    )

    if not response["messages"]:
        return
    
    message = response["messages"][0]
    author = message.get("user")
    msg_id = message.get("client_msg_id")
    
    if author != user_id:
        return
    
    success = Post.delete_by_id(msg_id)
    
    if success:
        client.chat_postEphemeral(
            channel=event["item"]["channel"],
            user=user_id,
            text=f"You're post have been deleted!"
        )


@app.event("reaction_added")
def handle_reaction_added(event, say, client):
    reaction = event.get("reaction")

    if reaction != "scrappy-doo":
        return

    user_id = event.get("user")
    item = event.get("item", {})
    channel = item.get("channel")
    ts = item.get("ts")

    response = client.conversations_history(
        channel=channel, latest=ts, limit=1, inclusive=True
    )
    ts = datetime.fromtimestamp(float(ts), tz=timezone.utc)

    if not response["messages"]:
        return

    message = response["messages"][0]
    content = message.get("text")
    author = message.get("user")
    msg_id = message.get("client_msg_id")

    if author != user_id:
        return

    post = Post(
        message_id=msg_id, author=author, message=content, timestamp=ts, tags=[]
    )

    post.save()
    
    client.chat_postEphemeral(
        channel=event["item"]["channel"],
        user=user_id,
        text=f"You're post have been saved!"
    )


if __name__ == "__main__":
    handler = SocketModeHandler(app)
    handler.start()
