from functools import wraps
from flask import (request, url_for, redirect, session)
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse


class Link(object):
    def __init__(self, display_name, link):
        self.display_name = display_name
        self.link = link


class Navigation(object):
    def __init__(self):
        self.navigation = {}

    def add(self, view_name, display_name, link):
        self.navigation[view_name] = Link(display_name, link)

    def __getitem__(self, item):
        return self.navigation.get(item)

    def __iter__(self):
        return iter(self.navigation.keys())


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id", None):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@dataclass
class GithubTreeNode:
    path: str
    type: str


class Project(object):
    def __init__(self, repo):
        self.name = repo["name"]
        self.full_name = repo["full_name"]
        self.html_url = repo["html_url"]
        self.description = repo["description"]
        self.fork = repo["fork"]
        self.private = repo["private"]
        self.language = repo["language"]
        self.topics = ", ".join(repo["topics"])


@dataclass()
class Comment(object):
    user: str
    body: str
    date_time: datetime


def get_username_and_repo(url):
    url_components = urlparse(url)
    url_path = url_components.path.split("/")[1:]
    username = url_path[0]
    repo = url_path[1]

    return username, repo


def github_repo_ls(_github, repo_link):
    owner, repo = get_username_and_repo(repo_link)
    response = _github.get(f"/repos/{owner}/{repo}/git/trees/master")
    repo_tree = response['tree']
    all_files = []
    for item in repo_tree:
        all_files.append(GithubTreeNode(item['path'], item['type']))
    return all_files


def check_project_files(files_list):
    errors = []
    if GithubTreeNode("README.md", "blob") not in files_list:
        errors.append("README.md not found.")

    if GithubTreeNode("code", "tree") not in files_list:
        errors.append("\"code\" directory not found.")

    if GithubTreeNode("tests", "tree") not in files_list:
        errors.append("\"tests\" directory not found.")

    return errors
