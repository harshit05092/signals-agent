# Signal agent (prototype)

Give it a task in plain words. It digs through the data, writes Signals, runs each one on
the data and shows the proof. Nothing is saved until you type `/save`.

    python3 make_data.py      # once: makes shop.db, all made up
    python3 agent.py          # start the chat

Nothing to install. It needs `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`, in `.env` (here or one
folder up) or in the environment, and sends the made-up data to that model. To try another model: `SIGNAL_AGENT_MODEL=<name> python3 agent.py`.

## In a browser

    pip install -r requirements.txt
    APP_PASSWORD=<choose one> streamlit run app.py

On Streamlit Community Cloud, set the main file to `app.py` and add three secrets:

    OPENROUTER_API_KEY = "..."
    OPENROUTER_MODEL = "anthropic/claude-haiku-5.5"
    APP_PASSWORD = "..."

Without `APP_PASSWORD` the app stays shut, since anyone with the link would spend the key.
Signals are downloaded, not kept: the server's disk is wiped on every restart.

## Files

- `make_data.py`: the made-up store
- `agent.py`: the agent, its tools and the chat
- `app.py`: the same agent in a browser
- `signals.json`: what `/save` writes. The app's live Signals are never touched.
