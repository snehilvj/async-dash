import asyncio
import mimetypes
import pkgutil
import sys
from contextvars import copy_context

import dash
import flask
import quart
from dash import _callback, _validate
from dash._utils import inputs_to_vals
from dash.dash import with_app_context_async
from dash.exceptions import DuplicateCallback
from dash.fingerprint import check_fingerprint


class Dash(dash.Dash):
    server: quart.Quart

    async def serve_component_suites(self, package_name, fingerprinted_path):
        path_in_pkg, has_fingerprint = check_fingerprint(fingerprinted_path)

        _validate.validate_js_path(self.registered_paths, package_name, path_in_pkg)

        extension = "." + path_in_pkg.split(".")[-1]
        mimetype = mimetypes.types_map.get(extension, "application/octet-stream")

        package = sys.modules[package_name]
        self.logger.debug(
            "serving -- package: %s[%s] resource: %s => location: %s",
            package_name,
            package.__version__,
            path_in_pkg,
            package.__path__,
        )

        response = quart.Response(
            pkgutil.get_data(package_name, path_in_pkg), mimetype=mimetype
        )

        if has_fingerprint:
            # Fingerprinted resources are good forever (1 year)
            # No need for ETag as the fingerprint changes with each build
            response.cache_control.max_age = 31536000  # 1 year
        else:
            # Non-fingerprinted resources are given an ETag that
            # will be used / check on future requests
            await response.add_etag()
            tag = response.get_etag()[0]

            request_etag = quart.request.headers.get("If-None-Match")

            if '"{}"'.format(tag) == request_etag:
                response = quart.Response(None, status=304)

        return response

    def setup_apis(self):
        """
        Register API endpoints for all callbacks defined using `dash.callback`.

        This method must be called after all callbacks are registered and before the app is served.
        It ensures that all callback API routes are available for the Dash app to function correctly.

        Typical usage:
            app = Dash(__name__)
            # Register callbacks here
            app.setup_apis()
            app.run()

        If not called, callback endpoints will not be available and the app will not function as expected.
        """
        for k in list(_callback.GLOBAL_API_PATHS):
            if k in self.callback_api_paths:
                raise DuplicateCallback(
                    f"The callback `{k}` provided with `dash.callback` was already "
                    "assigned with `app.callback`."
                )
            self.callback_api_paths[k] = _callback.GLOBAL_API_PATHS.pop(k)

        # In Quart, all handlers need to be async since request.get_json() is async
        def make_parse_body_sync(func):
            """Wrap a sync function in an async handler for Quart."""

            async def _parse_body():
                if quart.request.is_json:
                    data = await quart.request.get_json()
                    return quart.jsonify(func(**data))
                return quart.jsonify({})

            return _parse_body

        def make_parse_body_async(func):
            """Wrap an async function in an async handler for Quart."""

            async def _parse_body_async():
                if quart.request.is_json:
                    data = await quart.request.get_json()
                    result = await func(**data)
                    return quart.jsonify(result)
                return quart.jsonify({})

            return _parse_body_async

        for path, func in self.callback_api_paths.items():
            if asyncio.iscoroutinefunction(func):
                self._add_url(path, make_parse_body_async(func), ["POST"])
            else:
                self._add_url(path, make_parse_body_sync(func), ["POST"])

    @with_app_context_async
    async def async_dispatch(self):
        body = await quart.request.get_json()
        g = self._initialize_context(body)
        func = self._prepare_callback(g, body)
        args = inputs_to_vals(g.inputs_list + g.states_list)

        ctx = copy_context()
        partial_func = self._execute_callback(func, args, g.outputs_list, g)
        if asyncio.iscoroutinefunction(func):
            response_data = await ctx.run(partial_func)
        else:
            response_data = ctx.run(partial_func)

        if asyncio.iscoroutine(response_data):
            response_data = await response_data

        g.dash_response.set_data(response_data)
        return g.dash_response


def apply():
    flask.Flask = quart.Quart  # type: ignore
    flask.Blueprint = quart.Blueprint  # type: ignore
    flask.jsonify = quart.jsonify  # type: ignore
    flask.Response = quart.Response  # type: ignore
    flask.request = quart.request  # type: ignore
    flask.has_request_context = quart.has_request_context  # type: ignore
    flask.g = quart.g  # type: ignore
    flask.helpers = quart.helpers  # type: ignore
    flask.current_app = quart.current_app  # type: ignore
    flask.url_for = quart.url_for  # type: ignore
    flask.abort = quart.abort  # type: ignore
    flask.redirect = quart.redirect  # type: ignore
