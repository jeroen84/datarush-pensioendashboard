from dash.testing.application_runners import import_app


DEFAULT_FOLDER = "Dash"
NUMBER_OF_FUNDS = 4  # number of pension funds in the database
NUMBER_OF_BINS = 2  # number of time bins in the dekkingsgraadcontributie


def test_dash_pensioendashboard(dash_duo):
    """ Test if the app loads """

    app = import_app("{}.index".format(DEFAULT_FOLDER))

    dash_duo.start_server(app)
    dash_duo.server_url = dash_duo.server_url + "/pensioendashboard"
    dash_duo.wait_for_element("#page-content-main")
    # Get the generated component input with selenium
    # The html input will be a children of the #input dash component
    dash_duo.wait_for_text_to_equal("h2", "Pensioendashboard", timeout=5)

    # --------------------
    # OVERZICHT TAB
    # --------------------

    # Does the dekkingsgraad graph show? (by default)
    assert dash_duo.wait_for_element_by_id("fig_dgr")

    # Click on the tab and does the equity graph show?
    dash_duo.driver.find_element_by_xpath(
        "/html/body/div[1]/div/div/div/"
        "div[3]/div/div[1]/div/ul/li[2]/a").click()
    assert dash_duo.wait_for_element_by_id("fig_equity")

    # Click on the tab and does the rates graph show?
    dash_duo.driver.find_element_by_xpath(
        "/html/body/div[1]/div/div/div/"
        "div[3]/div/div[1]/div/ul/li[3]/a").click()
    assert dash_duo.wait_for_element_by_id("fig_rates")

    # --------------------
    # DEKKINGSGRAADCONTRIBUTIE TAB
    # --------------------

    # go to the dekkingsgraad tab
    dash_duo.driver.find_element_by_xpath("//*[@id='page-2-link']").click()

    # Does the dekkingsgraad graph show? (by default)
    assert dash_duo.wait_for_element_by_id("contribution-graph")

    # check all combinations of funds and bins
    for _index in range(NUMBER_OF_FUNDS):
        for _bins in range(NUMBER_OF_BINS):

            dash_duo.select_dcc_dropdown("#fund-name-dropdown", index=_index)
            assert dash_duo.wait_for_element_by_id("contribution-graph")

            dash_duo.select_dcc_dropdown("#bin-dropdown", index=_bins)
            assert dash_duo.wait_for_element_by_id("contribution-graph")

    # --------------------
    # TOP 10 LANDEN EXPOSURE TAB
    # --------------------

    # go to the top 10 landen exposure tab
    dash_duo.driver.find_element_by_xpath("//*[@id='page-3-link']").click()

    # does the graph show?
    assert dash_duo.wait_for_element_by_id("country-graph")

    assert not dash_duo.get_logs()
