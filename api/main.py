from flask import Flask, Response, request
from dotenv import load_dotenv
from database import *
import requests

load_dotenv()
app = Flask(__name__)
public_preffix = os.getenv("PUBLIC_PREFIX", "http://127.0.0.1:5000/")

headers = {"Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}"}


def fix_links(posts):
    for post in posts:
        files = post.get("files", [])
        for i, file in enumerate(files):
            if file.startswith("https://files.slack.com/"):
                files[i] = file.replace("https://files.slack.com/files-pri/", public_preffix + "file/")

    return posts


@app.route("/")
def index():
    return Response("Scrappy-doo API", mimetype="text/plain")


@app.route("/user/<userid>")
def user(userid):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    posts = Post.get_by_author(userid, limit=limit, offset=offset)
    json_posts = [post.asdict() for post in posts]
    json_posts = fix_links(json_posts)

    return json_posts


@app.route("/tag/<tag>")
def tag(tag):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    posts = Post.get_by_tag(tag, limit=limit, offset=offset)
    json_posts = [post.asdict() for post in posts]
    json_posts = fix_links(json_posts)

    return json_posts


@app.route("/file/<id>/<filename>")
def file_proxy(id, filename):
    url = f"https://files.slack.com/files-pri/{id}/{filename}"

    r = requests.get(url, headers=headers)
    resp = Response(r.content, mimetype=r.headers["content-type"])
    return resp


@app.route("/latests")
def latests():
    limit = request.args.get("limit", 50, type=int)

    posts = Post.get_latests(limit=limit)
    json_posts = [post.asdict() for post in posts]
    json_posts = fix_links(json_posts)

    return json_posts

if __name__ == "__main__":
    app.run()
