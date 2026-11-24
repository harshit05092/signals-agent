"""The Signal agent in a browser.

    streamlit run app.py

Secrets: OPENROUTER_API_KEY, OPENROUTER_MODEL and APP_PASSWORD, in Streamlit's secrets.
Without APP_PASSWORD the app stays shut: anyone with the link would spend the key.
"""

import hmac
import os
import queue
import threading
from typing import Any

import streamlit as st

st.set_page_config(page_title="Signal agent", page_icon="🎯", layout="wide")


def secret(key: str) -> str:
    try:
        return str(st.secrets[key])
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, "")


for key in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL"):  # agent.py reads the environment
    if secret(key):
        os.environ[key] = secret(key)

try:
    import agent as core
except RuntimeError as error:
    st.error(f"{error}. Add it in the app's secrets.")
    st.stop()
import make_data

ANSWER_SECONDS = 900  # a question nobody answers stops the turn
STARTERS = [
    "Make 3 strict hot Signals for 5 L oil buyers. Do not use discounts.",
    "Find Signals for people who leave at checkout.",
    "Make 2 cold Signals from chat only.",
]


class Session:
    """One browser's agent. A turn runs in its own thread, so the page stays live."""

    def __init__(self) -> None:
        self.agent = core.Agent(self.show, self.ask)
        self.log: list[tuple[str, Any]] = []
        self.question: tuple[str, list[str]] | None = None
        self.answers: queue.Queue[str] = queue.Queue()
        self.thread: threading.Thread | None = None

    @property
    def busy(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def show(self, kind: str, data: Any) -> None:
        # a card changes later; the log keeps what it said at the time
        self.log.append((kind, f"{data['name']}: {core.matches(data)}" if kind == "card" else data))

    def ask(self, question: str, options: list[str]) -> str:
        self.log.append(("say", question))
        while not self.answers.empty():
            self.answers.get()
        self.question = (question, options)
        try:
            for _ in range(ANSWER_SECONDS):
                if self.agent.stop.is_set():
                    break
                try:
                    return self.answers.get(timeout=1)
                except queue.Empty:
                    continue
            raise core.Stopped
        finally:
            self.question = None

    def send(self, text: str) -> None:
        self.log.append(("operator", text))
        if self.question:
            self.answers.put(text)
        elif self.busy:
            self.agent.inbox.append(text)  # read after the check it is on
        else:
            self.agent.stop.clear()
            # words typed as the last turn ended are not lost
            waiting, self.agent.inbox = self.agent.inbox, []
            self.thread = threading.Thread(target=self.agent.turn, args=("\n".join([*waiting, text]),), daemon=True)
            self.thread.start()


@st.cache_resource
def shop() -> dict[str, int]:
    """The made-up store, made once, and how much is in it."""
    if not core.DB.exists():
        make_data.main()
    return {t: core.run_sql(f"SELECT count(*) FROM {t}")[1][0][0] for t in ("people", "orders", "website_events", "messages")}


def signed_in() -> bool:
    password = secret("APP_PASSWORD")
    if not password:
        st.error("APP_PASSWORD is not set. Add it in the app's secrets.")
        return False
    if st.session_state.get("ok"):
        return True
    st.title("Signal agent")
    with st.form("login"):
        typed = st.text_input("Password", type="password")
        if st.form_submit_button("Open"):
            if hmac.compare_digest(typed.encode(), password.encode()):
                st.session_state.ok = True
                st.rerun()
            st.error("Wrong password.")
    return False


def draw_log(session: Session) -> None:
    """The chat. Work between two messages folds into one box."""
    work: list[tuple[str, Any]] = []

    def flush(last: bool = False) -> None:
        if not work:
            return
        plan = next((data for kind, data in reversed(work) if kind == "plan"), None)
        lines = [(kind, data) for kind, data in work if kind != "plan"]
        with st.chat_message("assistant"):
            if plan:
                marks = {"done": "✅", "doing": "▶️"}
                st.markdown("\n".join(f"- {marks.get(s.get('state', ''), '⬜')} {s.get('step', '')}" for s in plan))
            if lines:
                with st.expander(f"{len(lines)} steps · {lines[-1][1]}", expanded=last and session.busy):
                    icons = {"wrote": "➕", "dropped": "➖", "card": "📊"}
                    for kind, data in lines:
                        st.caption(f"{icons.get(kind, '·')} {data}")
        work.clear()

    for kind, data in list(session.log):
        if kind in ("operator", "say", "note"):
            flush()
            if kind == "note":
                st.warning(data)
            else:
                st.chat_message("user" if kind == "operator" else "assistant").markdown(data)
        else:
            work.append((kind, data))
    flush(last=True)


def draw_signal(session: Session, number: int, s: dict) -> None:
    colour = {"hot": "red", "warm": "orange", "cold": "blue"}[s["polarity"]]
    with st.container(border=True):
        st.markdown(f"**{number}. {s['name']}** :{colour}-badge[{s['polarity'].upper()}] :gray-badge[{s['strength']}] :gray-badge[{s['evidence']}]")
        st.write(s["description"])
        (st.success if s["proof"] and s["proof"]["matched"] else st.warning)(core.matches(s))
        with st.expander("Proof"):
            st.markdown("**Why this number** (the agent's words)")
            st.write(s["why_number"])
            st.markdown("**Why it matters** (the agent's words)")
            st.write(s["reason"])
            if s["evidence"] == "chat":
                st.markdown("**Question asked of each chat**")
                st.write(s["question"])
            else:
                st.markdown("**Rule, run by code**")
                st.code(s["sql"], language="sql", wrap_lines=True)
            for example in (s["proof"] or {}).get("examples", []):
                st.markdown(f"**Example: {example['person']}**")
                st.text("\n".join(example["shows"]))
            for q in s["based_on"]:
                st.caption(f"From query {q}")
                st.code(session.agent.queries[q], language="sql", wrap_lines=True)
        left, right = st.columns(2)
        with left.popover("Change", width="stretch"), st.form(f"change-{s['name']}", clear_on_submit=True):
            words = st.text_input("What should change?", placeholder="Make it stricter")
            if st.form_submit_button("Send") and words.strip():
                session.send(f'Change the Signal "{s["name"]}": {words.strip()}')
                st.rerun()
        if right.button("Remove", key=f"remove-{s['name']}", width="stretch", disabled=session.busy):
            session.agent.remove(s["name"])
            st.rerun()


def page(session: Session) -> None:
    chat, draft = st.columns([3, 2], gap="large")
    with chat:
        with st.container(height=560, border=False):
            if not session.log:
                st.chat_message("assistant").markdown(
                    "Tell me what Signals you want. I look through the data, write them, run each one on the data and show you the proof."
                )
            draw_log(session)
        if session.question:
            for i, option in enumerate(session.question[1]):
                if st.button(option, key=f"option-{i}", width="stretch"):
                    session.send(option)
                    st.rerun()
        if session.busy:
            stopping = session.agent.stop.is_set()
            status, button = st.columns([4, 1])
            status.caption("Stopping after this step…" if stopping else "Waiting for your answer" if session.question else "Working… you can type to steer me")
            if button.button("Stop", disabled=stopping, width="stretch"):
                session.agent.stop.set()
                st.rerun()
        elif not session.log:
            for starter in STARTERS:
                if st.button(starter, width="stretch"):
                    session.send(starter)
                    st.rerun()
    with draft:
        signals = list(session.agent.signals.values())
        spent = session.agent.spent
        st.caption(f"Used: {spent['calls']} model calls, {spent['in'] + spent['out']:,} tokens")
        st.subheader(f"Draft Signals ({len(signals)})")
        if not signals:
            st.caption("They appear here as the agent writes them.")
        with st.container(height=480, border=False):
            for number, s in enumerate(signals, 1):
                draw_signal(session, number, s)
        if signals and not session.busy:
            everything = st.checkbox("Also the ones with no check or no matches")
            rows = session.agent.saved(everything)
            st.download_button(f"Save {len(rows)} Signals", core.as_json(rows), "signals.json", "application/json",
                               type="primary", disabled=not rows, width="stretch")


def main() -> None:
    if not signed_in():
        return
    counts = shop()
    session: Session = st.session_state.setdefault("session", None) or Session()
    st.session_state.session = session

    with st.sidebar:
        st.title("🎯 Signal agent")
        st.info("All data here is made up.")
        if st.button("New chat", width="stretch"):
            session.agent.stop.set()
            st.session_state.session = Session()
            st.rerun()
        for table, count in counts.items():
            st.caption(f"{table.replace('_', ' ')}: {count:,}")
        st.caption(f"Model: {core.MODEL}")

    @st.fragment(run_every=1.5 if session.busy else None)
    def live() -> None:
        was = st.session_state.get("was_busy", False)
        st.session_state.was_busy = session.busy
        if was and not session.busy:
            st.rerun()  # the turn ended: draw once more and stop refreshing
        page(session)

    st.session_state.was_busy = session.busy
    live()
    if text := st.chat_input("Give the agent a task, or tell it what to change…"):
        session.send(text.strip())
        st.rerun()


main()
