from async_dash import monkey_patch_dash

monkey_patch_dash.apply()

Dash = monkey_patch_dash.Dash

__all__ = ["Dash"]
