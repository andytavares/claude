"""PreToolUse hook: block Bash commands that zsh runs differently from bash."""

import json
import re
import sys

HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)(\w+)\1")
UNQUOTED_GLOB = re.compile(r"--(?:include|exclude)=\S*\*")
VARIABLE_AS_COMMAND = re.compile(
    r"(?:^|[;&|(\n]|\b(?:do|then|else|elif)\b)[ \t]*\$(?!\{=)[{\w]"
)
GLOB_MESSAGE = (
    "zsh expands an unquoted --include/--exclude glob before grep sees it, "
    "and fails with 'no matches found'. Quote the glob: --include='*.md'."
)
VARIABLE_MESSAGE = (
    "zsh does not split words in an unquoted $var, so '$c' runs one command "
    "named by the whole value. Write each command out, or use ${=var}."
)


def drop_heredoc_bodies(command):
    kept, delimiters = [], []
    for line in command.split("\n"):
        if delimiters:
            if line.strip() == delimiters[0]:
                delimiters.pop(0)
            continue
        kept.append(line)
        delimiters = [match.group(2) for match in HEREDOC.finditer(line)]
    return "\n".join(kept)


def mask_quoted(command):
    """Replace quoted and escaped text with Q, so only shell code is left."""
    pattern = r"'[^']*'|\"(?:\\.|[^\"\\])*\"|\\."
    return re.sub(pattern, "Q", command, flags=re.DOTALL)


def problem(command):
    code = mask_quoted(drop_heredoc_bodies(command))
    if UNQUOTED_GLOB.search(code):
        return GLOB_MESSAGE
    if VARIABLE_AS_COMMAND.search(code):
        return VARIABLE_MESSAGE
    return None


def main():
    hook = json.load(sys.stdin)
    if hook.get("tool_name") != "Bash":
        return 0
    message = problem(hook.get("tool_input", {}).get("command", ""))
    if message:
        print(message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
