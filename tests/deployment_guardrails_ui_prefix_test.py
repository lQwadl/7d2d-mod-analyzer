def test_ui_group_prefix_orders_hud_last():
    from logic.deployment_guardrails import ui_group_prefix

    assert ui_group_prefix("framework").startswith("0_")
    assert ui_group_prefix("extension").startswith("1_")
    assert ui_group_prefix("hud").startswith("2_")
