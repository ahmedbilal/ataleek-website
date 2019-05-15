from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired, URL, AnyOf
from github import Github


class CreateProjectForm(FlaskForm):
    repository = SelectField(validators=[DataRequired(), URL()])

    def __init__(self, *args, **kwargs):
        super(CreateProjectForm, self).__init__(*args, **kwargs)
        self.repo_urls = []
        repositories = []

        if "user" in kwargs.keys():
            user = kwargs.pop("user")
            access_token = user.github_access_token
            git_user = Github(access_token).get_user()
            for repo in git_user.get_repos():
                self.repo_urls.append(repo.html_url)
                repositories.append((repo.html_url, repo.name))

        self.repository.choices = repositories
        self.repository.validators.append(AnyOf(self.repo_urls, message=""))


class SubmitSolutionForm(FlaskForm):
    repository = SelectField(validators=[DataRequired(), URL()])

    def __init__(self, *args, **kwargs):
        super(SubmitSolutionForm, self).__init__(*args, **kwargs)

        self.repositories = []

        user = kwargs.pop("user")
        projects = kwargs.pop("projects")

        access_token = user.github_access_token
        git_user = Github(access_token).get_user()

        # URL of verified projects
        repo_urls = list(map(lambda r: r.html_url, projects))

        # User repositories who are fork of verified projects
        repos = filter(lambda r: r.parent and r.parent.html_url in repo_urls,
                       git_user.get_repos())

        self.repositories = list(map(lambda r: (r.html_url, r.name), repos))

        self.repository.choices = self.repositories

        # self.repository.validators.append(AnyOf(repo_urls, message="Khoja"))
