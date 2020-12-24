import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from pathlib import Path

# for pytest, a fallback import needs to be
# defined
try:
    from app import app
except ImportError:
    from .app import app

try:
    from demo1 import app as app1
except ImportError:
    from multiapp.demo1 import app as app1

try:
    from pensioendashboard import app as app2
except ImportError:
    from multiapp.pensioendashboard import app as app2

app.title = "Dashboards by Datarush"
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content-main")
])

@app.callback(Output("page-content-main", "children"),
              [Input("url", "pathname")])
def display_page(pathname):
    if pathname is not None:
        p = Path(pathname)

        if len(p.parts) == 1:
            # this means at "/" level:
            return dbc.Jumbotron([
                dcc.Markdown("# Welcome"),
                html.Hr(),
                dcc.Markdown("Please go to one of the dashboards "
                             "by clicking on below buttons"),
                dbc.Button("Pensioendashboard", href="/pensioendashboard"),
                dbc.Button("Demo dashboard", href="/demo1")
            ])
        else:
            if p.parts[1] == "demo1":
                return app1.layout
            elif p.parts[1] == "pensioendashboard":
                return app2.layout
            else:
                return "404"
    else:
        pass


if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
