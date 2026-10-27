"""How a processor ends a run other than by returning: raise one of these from `process`."""


class Skip(Exception):
    """Nothing to do for this email (e.g. no parser for the sender, no PDF). Not a failure."""


class Fail(Exception):
    """This email can't be processed (e.g. the document isn't in the expected format). Safe to show."""


class NeedsInput(Exception):
    """The run needs something only the user can give, e.g. a PDF password. It waits; the Home page
    asks for it (`prompt`), and saving it (for `name` and `scope`) runs the email again."""

    def __init__(self, name: str, scope: str, prompt: str, *, wrong: bool = False):
        super().__init__(f"{prompt} (the saved one didn't work)" if wrong else prompt)
        self.name = name
        self.scope = scope
        self.prompt = prompt
        self.wrong = wrong


class Retry(Exception):
    """Try again later (a transient problem the processor detected itself)."""

    def __init__(self, message: str, after: float | None = None):
        super().__init__(message)
        self.after = after
