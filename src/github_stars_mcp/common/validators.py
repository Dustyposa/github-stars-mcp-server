"""Common validation utilities."""

from ..exceptions import ValidationError


def validate_github_username(username: str) -> str:
    """Validate GitHub username format.

    Args:
        username: GitHub username to validate

    Returns:
        Validated username

    Raises:
        ValidationError: If username is invalid
    """
    if not username or not isinstance(username, str):
        raise ValidationError("Username must be a non-empty string")

    username = username.strip()
    if not username:
        raise ValidationError("Username cannot be empty or whitespace")

    # Basic GitHub username validation
    if len(username) > 39:
        raise ValidationError("Username cannot be longer than 39 characters")

    # GitHub usernames can contain alphanumeric characters and hyphens
    # but cannot start or end with hyphens
    if username.startswith('-') or username.endswith('-'):
        raise ValidationError("Username cannot start or end with hyphens")

    if '--' in username:
        raise ValidationError("Username cannot contain consecutive hyphens")

    # Check for valid characters
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
    if not all(c in valid_chars for c in username):
        raise ValidationError("Username can only contain alphanumeric characters and hyphens")

    return username



def validate_repo_name(repo_name: str) -> str:
    """Validate GitHub repository name format.

    Args:
        repo_name: Repository name to validate

    Returns:
        Validated repository name

    Raises:
        ValidationError: If repository name is invalid
    """
    if not repo_name or not isinstance(repo_name, str):
        raise ValidationError("Repository name must be a non-empty string")

    repo_name = repo_name.strip()
    if not repo_name:
        raise ValidationError("Repository name cannot be empty or whitespace")

    # GitHub repository names have specific rules
    if len(repo_name) > 100:
        raise ValidationError("Repository name cannot be longer than 100 characters")

    # Cannot start with . or -
    if repo_name.startswith('.') or repo_name.startswith('-'):
        raise ValidationError("Repository name cannot start with '.' or '-'")

    # Cannot end with .
    if repo_name.endswith('.'):
        raise ValidationError("Repository name cannot end with '.'")

    return repo_name
