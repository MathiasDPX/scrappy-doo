from flask import Flask, Response, request
from dotenv import load_dotenv
from database import *

load_dotenv()
app = Flask(__name__)


@app.route("/")
def index():
    return Response("Scrappy-doo API", mimetype="text/plain")


@app.route("/user/<userid>")
def user(userid):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    
    posts = Post.get_by_author(userid, limit=limit, offset=offset)
    json_posts = [post.asdict() for post in posts]
    
    return json_posts

@app.route("/tag/<tag>")
def tag(tag):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    
    posts = Post.get_by_tag(tag, limit=limit, offset=offset)
    json_posts = [post.asdict() for post in posts]
    
    return json_posts

if __name__ == "__main__":
    app.run()
