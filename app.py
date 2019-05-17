# TODO:
#       - use environment variables before uploading it anywhere
#       - remove my own access token from index()

import json
import os
from datetime import datetime
from functools import reduce
from urllib.parse import urljoin

import requests
from flask import (Flask, render_template, request,
                   url_for, flash, redirect, session,
                   g)
from flask_bootstrap import Bootstrap
from flask_github import GitHub
from github import Github as Github2

from forms import CreateProjectForm, SubmitSolutionForm
from helpers import (Navigation, login_required,
                     check_project_files,
                     Project, Comment, github_repo_ls,
                     get_username_and_repo)
from models import User, Solution, Mentor

nav = Navigation()
nav.add("index", "Home", "/")
nav.add("projects", "Projects", "/projects")
nav.add("submit_solution", "Submit Solution", "/submit-solution")

# Constants
ABK_ACCESS_TOKEN = "41168124b046fbd6485d78ac2f65a41187ef304d"
ADMIN = "ahmedbilal"

environment_status = os.getenv("environment")

if environment_status == "cloud":
    def configure_app(_app):
        _app.config['GITHUB_CLIENT_ID'] = 'ee6f0a5e76b99a909c75'
        _app.config['GITHUB_CLIENT_SECRET'] = 'b876e39b1b6fa85180e03f19025fcf8cf41bfc71'
        _app.config["SECRET_KEY"] = "hello"
        _app.config["RECAPTCHA_PUBLIC_KEY"] = "6Ldvd94SAAAAAIlZcypMyY7EoSwkvf9bWW-cp5o6"
        _app.config["RECAPTCHA_PRIVATE_KEY"] = "6Ldvd94SAAAAADQ6e-pS_lEfgfyA6Zfe-kDCZFki"
else:
    def configure_app(_app):
        _app.config['GITHUB_CLIENT_ID'] = '3c465736912b5ed0c14f'
        _app.config['GITHUB_CLIENT_SECRET'] = '4aaf9c47b21192af51b8f1b5430d53ef3aa58324'
        _app.config["SECRET_KEY"] = "hello"
        _app.config["RECAPTCHA_PUBLIC_KEY"] = "6Ldvd94SAAAAAIlZcypMyY7EoSwkvf9bWW-cp5o6"
        _app.config["RECAPTCHA_PRIVATE_KEY"] = "6Ldvd94SAAAAADQ6e-pS_lEfgfyA6Zfe-kDCZFki"


class OrgGithub(object):
    def __init__(self, _app, _github, organization):
        self.github = _github
        self.client_secret = _app.config.get("GITHUB_CLIENT_SECRET")
        self.client_id = _app.config.get("GITHUB_CLIENT_ID")
        self.session = requests.session()
        self.organization = organization
        self.organization_access_token = "41168124b046fbd6485d78ac2f65a41187ef304d"

    def is_member(self, username):
        return self.get(f"/orgs/ataleek/public_members/{username}") is not None

    def get(self, resource, data=None, *args, **kwargs):
        if not data:
            data = {'organization': self.organization}
        else:
            data['organization'] = self.organization

        try:
            return self.github.get(resource, data, *args,
                                   access_token=self.organization_access_token,
                                   **kwargs)
        except:
            return None

    def post(self, resource, data=None):
        if not data:
            data = {'organization': self.organization}
        else:
            data['organization'] = self.organization
        try:
            return self.github.post(resource, data,
                                    access_token=self.organization_access_token)
        except:
            return None

    def create_fork(self, owner, repo):
        return self.post(f'/repos/{owner}/{repo}/forks')

    def get_repos(self):
        return self.get("/orgs/ataleek/repos", headers={"Accept": "application/vnd.github.mercy-preview+json"})

    def create_issue(self, repo, data):
        return self.post(f"/repos/{self.organization}/{repo}/issues",
                         data={"title": data.get("title") or "",
                               "body": data.get("body") or "",
                               "labels": data.get("labels") or ""})

    def ls_projects(self):
        organization_repos = ["ataleek"]
        repositories = list(filter(lambda r: not r["private"] and
                                   r["name"] not in organization_repos,
                                   self.get_repos()))
        projects = []
        for repo in repositories:
            projects.append(Project(repo))
        return projects


app = Flask(__name__)
configure_app(app)

github = GitHub(app)
Bootstrap(app)

org_github = OrgGithub(app, github, "ataleek")


@app.before_request
def index():
    _user = User.get_or_none(id=session.get("user_id", None))
    if _user:
        g.user = _user


@app.route('/')
def index():
    # oauth_token = User.get_or_none(id=session.get("user_id", None)).github_access_token
    # print(oauth_token)
    # git_user = Github2(oauth_token).get_user()
    # for repo in git_user.get_repos():
    #     print(repo.name)
    #     print(repo.html_url)
    #     # print(dir(repo))

    # _user = User.get_or_none(id=session.get("user_id", None))
    # github_access_token = None
    # if _user:
    #     github_access_token = _user.github_access_token
    #     git_user = Github2(github_access_token)
    #     repo = git_user.get_repo("ataleek/ataleek")
    return render_template("index.html", nav=nav)


@app.route('/login')
def login():
    return github.authorize(scope="public_repo")
    # if session.get('user_id', None) is None:
    #     return github.authorize()
    # else:
    #     flash("You are already logged in")
    #     return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    g.user = None
    flash("User Logged Out")
    return redirect(url_for('index'))


@app.route('/github-callback')
@github.authorized_handler
def authorized(oauth_token):
    next_url = request.args.get('next') or url_for('index')
    if oauth_token is None:
        flash("Authorization failed.")
        return redirect(next_url)

    _user = User.select().where(User.github_access_token == oauth_token).first()
    if _user is None:
        _user = User.create(github_access_token=oauth_token)
        _user.save()

    g.user = _user

    session['user_id'] = _user.get_id()

    return redirect(next_url)


@github.access_token_getter
def token_getter():
    _user = g.user
    if _user is not None:
        return _user.github_access_token


@app.before_request
def apply_for_mentor():
    _user = User.get_or_none(id=session.get("user_id", None))
    if _user:
        g.user = _user


@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_for_mentor():
    if request.method == "POST":
        user_info = github.get("/user", access_token=g.user.github_access_token)
        print("Userinfo", user_info["login"])
        m = Mentor.get_or_none(username=user_info["login"])
        if m:
            flash(f"You have already applied for mentorship."
                  f" Your Status is {m.status}"
                  f"{f' and Reason is {m.status_reason}.' if m.status == 'rejected' else '.'}")
        else:
            print("M is ", m)
            m = Mentor(username=user_info["login"], status="pending",
                       profile_link=user_info["html_url"], status_reason="")
            m.save()
            flash("Submitted Successfully. It takes approximately 1 week to process"
                  " application. If you want to check your application status later"
                  " then click the same apply_mentor button")
    return render_template("apply_mentor.html", nav=nav)


def get_comments(url, usernames=None, body=None, sort=True):
    comments = (requests.get(url)).json()

    _comments = []
    for comment in comments:
        _comments.append(Comment(comment["user"]["login"],
                                 comment["body"],
                                 datetime.strptime(comment["updated_at"], "%Y-%m-%dT%H:%M:%SZ")))

    # Sort Comments by ACCENDING ORDER
    if sort:
        sorted(_comments, key=lambda x: x.date_time)

    def user_filtering_func(x):
        return x if x.user in usernames else None

    if not usernames:
        def user_filtering_func(x): return x

    def body_filtering_func(x):
        return x if x.body in body else None

    if not body:
        def body_filtering_func(x): return x

    _comments = list(filter(user_filtering_func and body_filtering_func, _comments))
    return _comments


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    request_json = request.get_json()
    f = open("webhook.json", "w")
    json.dump(request_json, f)
    f.close()

    action = request_json.get("action")
    if action == "closed":
        issue = request_json.get("issue")
        pull_request = request_json.get("pull_request")
        if issue:
            user = issue["user"]
            _username = user["login"]

            repo_link = issue["title"]
            username, repo = get_username_and_repo(repo_link)

            if _username == ADMIN:
                comments_url = issue["comments_url"]
                comments = get_comments(comments_url, usernames=[ADMIN],
                                        body=["ACCEPTED!", "REJECTED!"])

                for comment in comments:
                    if comment.body == "ACCEPTED!":
                        org_github.create_fork(username, repo)
                        break
                    elif comment.body == "REJECTED!":
                        break
        elif pull_request:
            labels = pull_request["labels"]
            for label in labels:
                if label["name"] == "solution":
                    head_url = pull_request["head"]["repo"]["html_url"]
                    username, repo = get_username_and_repo(head_url)
                    head_sha = pull_request["head"]["sha"]
                    _url = reduce(urljoin, [f"{head_url}/", "tree/", head_sha])
                    Solution.create(url=_url, username=username)

    return ""


@app.route('/add-project', methods=['GET', 'POST'])
@login_required
def add_project():
    user = User.get_or_none(id=session.get("user_id", None))

    form = CreateProjectForm(user=user)
    if request.method == 'POST':
        if form.validate_on_submit():
            print(form.repository.data)
            _errors = check_project_files(github_repo_ls(github, form.repository.data))
            form.repository.errors += _errors
            if not _errors:
                issue_data = {"title": form.repository.data,
                              "body": f"Please verify all aspects of [{form.repository.data}]({form.repository.data})"
                              f" according to Project Specification Guideline. Leave your comments"
                              f" and critics about the project. Feel free to contribute"
                              f" to the project repo to make it better",
                              "labels": ["New Project"]}
                org_github.create_issue("ataleek", issue_data)
                flash("Your project's repository is under review. We will add it once it is verified.")

    return render_template("add_project.html", nav=nav, form=form)


@app.route('/projects')
def list_projects():
    return render_template("projects.html", projects=org_github.ls_projects(), nav=nav)


@app.route('/submit-solution', methods=["GET", "POST"])
@login_required
def submit_solution():
    user = User.get_or_none(id=session.get("user_id", None))

    form = SubmitSolutionForm(user=user, projects=org_github.ls_projects())

    if request.method == 'POST':
        if form.validate_on_submit():
            _errors = check_project_files(github_repo_ls(github, form.repository.data))
            form.repository.errors += _errors
            if not _errors:
                username, repo = get_username_and_repo(form.repository.data)
                github_user = Github2(user.github_access_token).get_user()
                github_repo = github_user.get_repo(repo)
                response = {'url': ""}
                try:
                    response = github.post(f"/repos/{github_repo.parent.full_name}/pulls",
                                           data={"title": "Solution",
                                                 "head": f"{username}:master",
                                                 "base": "master"},
                                           access_token=user.github_access_token)
                except:
                    form.repository.errors += ["""Make sure that you have incorporated
                     some changes in your solution repository"""]
                if not form.repository.errors:
                    flash(f"Your solution is under review at {response['url']}")

    return render_template("submit_solution.html", nav=nav, form=form)


@app.route('/search/<string:query>', methods=["GET"])
def search(query):
    result = "["
    solutions_by_user = Solution.select().where(Solution.username.contains(query))
    mentors = Mentor.select().where(
        (Mentor.username.contains(query)) &
        (Mentor.status == "accepted"))
    for solution in solutions_by_user:
        result += "{" + f"'solution_url': '{solution.url}'," \
            f"'username': '{solution.username}'" + "}"

    for mentor in mentors:
        result += "{" + f"'username': '{mentor.username}'," \
            f"'profile_url': '{mentor.profile_link}'" + "}"
    result += "]"
    return json.dumps(result)


@app.route('/user/<string:username>', methods=["GET"])
def user_profile(username):
    solutions_by_user = Solution.select().where(Solution.username == username)
    user_info = org_github.get(f"/users/{username}")
    user_status = "Student"
    if org_github.is_member(username):
        user_status = "Mentor"

    print(user_info)
    return render_template("profile.html", user=username,
                           solutions=solutions_by_user,
                           user_info=user_info, user_status=user_status)


if __name__ == '__main__':
    app.run()
