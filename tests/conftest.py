import asyncio
import inspect


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: execute test within an event loop")


def pytest_pyfunc_call(pyfuncitem):
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        marker = pyfuncitem.get_closest_marker("asyncio")
        if marker is not None:
            kwargs = {
                name: pyfuncitem.funcargs[name]
                for name in pyfuncitem._fixtureinfo.argnames
                if name in pyfuncitem.funcargs
            }
            asyncio.run(pyfuncitem.obj(**kwargs))
            return True
    return None
