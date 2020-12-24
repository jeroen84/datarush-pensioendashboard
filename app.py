import dash
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    meta_tags=[
        {
            "name": "description",
            "content": "Actuele situatie van Nederlandse pensioenfondsen "
                    "in een overzichtelijk dashboard"
        },
        {
            "name": "keywords",
            "content": "dekkingsgraad, pensioenfondsen, dashboard, datarush"
        },
        {
            "name": "author",
            "content": "Jeroen van de Erve"
        },
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1.0"
        },
        {
            "http-equiv": "X-UA-Compatible",
            "content": "IE=edge"
        },
    ],
    suppress_callback_exceptions=True
    )

server = app.server
