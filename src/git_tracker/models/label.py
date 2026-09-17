from git_tracker.models.response_base_model import ResponseBaseModel


class GithubLabel(ResponseBaseModel):
    name: str
    description: str
    color: str
