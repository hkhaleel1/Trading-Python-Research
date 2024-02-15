import requests


class API(object):
    uri = 'https://api.kraken.com'
    public_endpoint = '/0/public'
    ohlc_endpoint = '/OHLC'

    def __init__(self, key='', secret=''):
        self.key = key
        self.secret = secret
        self.uri = 'https://api.kraken.com'
        self.api_version = '0'
        self.session = requests.Session()
        self.response = None
        self._json_options = {}
        return

    def json_options(self, **kwargs):
        self._json_options = kwargs
        return self

    def close(self):
        self.session.close()
        return

    def load_key(self, path):
        with open(path, 'r') as f:
            self.key = f.readline().strip()
            self.secret = f.readline().strip()
        return

    def _query(self, urlpath, data, headers=None, timeout=None):
        if data is None:
            data = {}
        if headers is None:
            headers = {}

        url = self.uri + urlpath

        self.response = self.session.get(
            url, params=data, headers=headers, timeout=timeout
        )

        if self.response.status_code not in (200, 201, 202):
            self.response.raise_for_status()

        return self.response.json(**self._json_options)

    def query_public(self, method, data=None, timeout=None):
        if data is None:
            data = {}

        urlpath = '/' + self.api_version + '/public/' + method

        return self._query(urlpath, data, timeout=timeout)
