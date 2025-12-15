# 🐾 scrappy-doo

scrappy-doo is a lightweight system for collecting, storing, and showcasing images shared in Slack. It turns a Slack channel into a collaborative scrapbook using a simple API and an emoji-reacting bot.

## 🌟 Features

scrappy-doo is made of two parts:

* an **API** to proxies media, and retrieve posts from the database
* a **Slack Bot** to reacts to messages and send message to the database

Together, they make saving and curating Slack content effortless.

## 🛠️ Installation

## 🔌 API Setup

The API is in [`/api`](./api)

1. Copy `.env.example` into `.env`
2. Fill in required env variables

### Notes

* The **SLACK_BOT_TOKEN** and **PUBLIC_PREFIX** are required to proxy images correctly
* Images are proxied from messages sent in the [#scrappy-doo](https://hackclub.enterprise.slack.com/archives/C09VC37P2NA) channel

## 🤖 Bot Setup

The Slack bot lives in [`/bot`](./bot).

1. Copy `.env.example` into `.env`
2. Fill in required env variables
