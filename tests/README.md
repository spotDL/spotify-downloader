# Running tests

## Installing dependencies

FFmpeg has to be installed globally.

All the required dependencies for python can be installed via `pip`, by using the following
command:

```shell
pip install -e .[test]
```

## Executing tests

After installing all the required modules, just call the following command from the root
directory:

```shell
pytest
```

To see code coverage use:

```shell
pytest --cov=spotdl
```

## Enable network communication

To speed up the test execution, the network requests are mocked. That means that each HTTP
request does not reach the server, and the response is faked by the
[vcrpy](https://vcrpy.readthedocs.io/en/latest/index.html) module. This greatly increases the
test performance, but also may cause a problem whenever something changes in the real server
response. It is recommended to run the test suite without mocked network from time to time
(preferably on CI).

To run tests with a real network communication use this command:

```shell
pytest --disable-vcr
```

Whenever the server response will change and affect the tests behavior, the stored responses
can be updated by wiping the [tests/cassetes](tests/cassetes) directory and running `pytest`
again (without `--disable-vcr`).
