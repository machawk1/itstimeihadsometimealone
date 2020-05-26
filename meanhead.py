#!/usr/bin/env python

"""
This script goes through your exported tweet archive and finds users that you
follow that you have never interacted with before (a retweet, reply or like).
It then prompts you to see if you want to unfollow them.
"""

import os
import re
import sys
import json

from tqdm import tqdm
from pathlib import Path
from utils import twitter
from termcolor import colored
from collections import Counter


def prompt_boolean(s, default=True, boolean=False):
    result = prompt(s + " [Y,n]").lower()
    if result == "y":
        return True
    elif result == "n":
        return False
    elif result == "":
        return default
    else:
        return prompt_boolean(s, boolean)


def prompt(s):
    return input(colored(s + ": ", "green", attrs=["bold"]))


def error(s):
    sys.exit(colored(s, "red", attrs=["bold"]))


def bold(s):
    return colored(s, attrs=["bold"])


def parsejs(path):
    text = open(path).read()
    text = re.sub('^.+?= *', '', text)
    return json.loads(text)


def get_users(user_ids):
    users = {}
    bucket = []
    for user_id in tqdm(user_ids):
        if len(bucket) == 100:
            for user in twitter.lookup_users(bucket):
                users[user.id] = user._json
            bucket = []
        else:
            bucket.append(user_id)
    if len(bucket) > 0:
        for user in twitter.lookup_users(bucket):
            users[user.id] = user._json
    return users


def save_json(obj, path):
    if not path.parent.is_dir():
        path.parent.mkdir(parents=True)
    json.dump(obj, path.open("w"), indent=2)


archive = Path(prompt("Enter the path to your twitter archive"))
if not archive.is_dir():
    error(f"{archive} is not a directory!")

tweets_file = archive / "data" / "tweet.js"
if not tweets_file.is_file():
    error(f"{archive} is missing tweets.js file")

retweeted = Counter()
replied = Counter()
faved = Counter()

for obj in parsejs(tweets_file):
    tweet = obj['tweet']
    try:
        is_retweet = re.match('^RT:? ', tweet["full_text"])
        has_mentions = len(tweet["entities"]["user_mentions"]) > 0
        if is_retweet and has_mentions:
            screen_name = tweet["entities"]["user_mentions"][0]["screen_name"]
            retweeted[screen_name] += 1
        elif tweet.get("in_reply_to_screen_name"):
            replied[tweet["in_reply_to_screen_name"]] += 1
    except Exception:
        sys.exit(json.dumps(tweet, indent=2))

print(bold("\nHere are the 10 users you retweeted the most:\n"))
for user, count in retweeted.most_common(10):
    print('{:20s} {:5n}'.format(user, count))

print(bold("\nAnd here are the top 10 users you replied to the most:\n"))
for user, count in replied.most_common(10):
    print('{:20s} {:5n}'.format(user, count))

# the archive owners account information
account = parsejs(archive / "data" / "account.js")[0]["account"]

# the users who follow the archive owner
followers = parsejs(archive / "data" / "follower.js")
followers = list(map(lambda f: f["follower"]["accountId"], followers))

# the users that the archive owner follows
following = parsejs(archive / "data" / "following.js")
following = list(map(lambda f: f["following"]["accountId"], following))

report_string = (f"\nAccording to your archive you follow {len(following)} "
                 f"accounts and are followed by {len(followers)} accounts")
print(bold(report_string))

# combine all the user ids
user_ids = set(following).union(set(followers))

# look up all the users unless we have a copy already
users_path = archive / "extras" / "users.json"
use_cached = users_path.is_file()
if users_path.is_file():
    print("\n")
    msg_oldcopy = (f"I found an old copy of user information at {users_path} "
                   f"shall I use it?")
    use_cached = prompt_boolean(msg_oldcopy)

if not use_cached:
    users = get_users(user_ids)
    msg_fetch = (f"\nOk, I'm going to fetch the information for {len(users)}"
                 f" users from Twitter...")
    print(bold(msg_fetch))

else:
    users = json.load(users_path.open())
save_json(users, archive / "extras" / "users.json")

for user_id in followers:
    if user_id not in users:
        continue
    user = users[user_id]
    handle = "@" + user['screen_name']
    print(f"\n{user['name']} {bold(handle)}")
    print(f"https://twitter.com/{user['screen_name']}", end="\n\n")
    print(user["description"])
    prompt_boolean("Unfollow?", default=False)
