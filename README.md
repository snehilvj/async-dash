## Async Dash

`async-dash` is an async port of [Plotly Dash](https://github.com/plotly/dash) library, created by replacing its Flask
backend with its async counterpart [Quart](https://pgjones.gitlab.io/quart/index.html).

It started with my need to be able to create realtime dashboards with `dash`, specifically with event-driven
architecture. Using `async-dash` with components from [dash-extensions](https://github.com/thedirtyfew/dash-extensions)
such as WebSocket, EventSource, etc. you can create truly event-based or realtime dashboards.

#### Table Of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Motivation](#motivation)
- [Caveats](#caveats)
- [TODO](#todo)

### Installation

```bash
pip install async-dash
```

### Usage

```python
from async_dash import Dash
from dash import html, dcc
```

### Examples

#### Basic Async Callback

```python
import asyncio
import time

from dash import Input, Output, html
from quart import Quart

from async_dash import Dash

server = Quart(__name__)
app = Dash(__name__, server=server)

app.layout = html.Div([
    html.Button("Async Request (2s delay)", id="async-btn", n_clicks=0),
    html.Div(id="async-output"),
])


@app.callback(
    Output("async-output", "children"),
    Input("async-btn", "n_clicks"),
    prevent_initial_call=True,
)
async def async_callback(n_clicks):
    """Async callback that simulates a slow async operation (e.g., API call, DB query)."""
    start = time.time()
    # This is non-blocking - other requests can be processed during this sleep
    await asyncio.sleep(2)
    elapsed = time.time() - start
    return f"Async callback #{n_clicks} completed in {elapsed:.2f}s (non-blocking!)"


if __name__ == "__main__":
    app.run(debug=True, port=8050)
```

#### Sync Callbacks Still Work

```python
from dash import Input, Output, html
from quart import Quart

from async_dash import Dash

server = Quart(__name__)
app = Dash(__name__, server=server)

app.layout = html.Div([
    html.Button("Sync Request", id="sync-btn", n_clicks=0),
    html.Div(id="sync-output"),
])


@app.callback(
    Output("sync-output", "children"),
    Input("sync-btn", "n_clicks"),
    prevent_initial_call=True,
)
def sync_callback(n_clicks):
    """Sync callback - still works with async-dash."""
    return f"Sync callback #{n_clicks} completed instantly!"


if __name__ == "__main__":
    app.run(debug=True, port=8050)
```

#### WebSocket Example

Using websockets for real-time updates with [dash-extensions](https://github.com/thedirtyfew/dash-extensions):

```python
import asyncio
import random

from dash import Input, Output, dcc, html
from dash_extensions import WebSocket
from quart import Quart, json, websocket

from async_dash import Dash

server = Quart(__name__)
app = Dash(__name__, server=server)

app.layout = html.Div([
    WebSocket(id="ws", url="/ws"),
    html.H3("Live Random Data (via WebSocket)"),
    dcc.Graph(id="graph"),
])

app.clientside_callback(
    """
function(msg) {
    if (msg) {
        const data = JSON.parse(msg.data);
        return {data: [{y: data, type: "scatter"}]};
    } else {
        return {};
    }
}""",
    Output("graph", "figure"),
    [Input("ws", "message")],
)


@server.websocket("/ws")
async def random_data():
    while True:
        output = json.dumps([random.random() for _ in range(10)])
        await websocket.send(output)
        await asyncio.sleep(1)


if __name__ == "__main__":
    app.run()
```

#### Running with Uvicorn

For production, use an ASGI server like uvicorn:

```bash
uvicorn example:server --host 0.0.0.0 --port 8050
```

### Motivation

In addition to all the advantages of writing async code, `async-dash` enables you to:

1. Run truly asynchronous callbacks
2. Use websockets, server sent events, etc. without needing to monkey patch the Python standard library
3. Use `quart` / [`fastapi`](https://fastapi.tiangolo.com) / [`starlette`](https://www.starlette.io) frameworks with
   your dash apps side by side
4. Use HTTP/2 (especially server push) if you use an HTTP/2 enabled server such
   as [`hypercorn`](https://pgjones.gitlab.io/hypercorn/)

### Caveats

I'm maintaining this library as a proof of concept for now. It should not be used for production.
If you do decide to use it, I'd love to hear your feedback.

### TODO

1. Gather reviews and feedback from the Dash Community.
