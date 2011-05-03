import urllib

from twisted.internet import reactor, ssl
from twisted.web.client import HTTPClientFactory

from txaws.credentials import AWSCredentials
from txaws.service import AWSServiceEndpoint
from txaws.util import XML

from lae_site import util


class LicenseServiceClient (object):

    __slots__ = ['_creds', '_endpoint']

    def __init__(self, creds, endpoint):

        assert isinstance(creds, AWSCredentials), `creds`
        assert isinstance(endpoint, AWSServiceEndpoint), `creds`

        self._creds = creds
        self._endpoint = endpoint

    def activate_hosted_product(self, activationKey, productToken):
        """
        Reference: http://docs.amazonwebservices.com/AmazonDevPay/latest/DevPayDeveloperGuide/index.html?ActivateHostedProduct.html
        """
        d = self._send_request(
            Action = 'ActivateHostedProduct',
            ActivationKey = activationKey,
            ProductToken = productToken,
            )

        def handle_successful_activation(body):
            doc = util.etree_to_python(XML(body))

            # FIXME: Handle KeyErrors here:
            node = doc[u'ActivateHostedProductResult']
            pid = node[u'PersistentIdentifier']
            usertoken = node[u'UserToken']

            return (pid, usertoken)

        d.addCallback(handle_successful_activation)

        return d

    # Private
    def _send_request(self, **params):
        url = self._build_request_url(params)
        client = HTTPClientFactory(url, method='POST')

        ep = self._endpoint

        if ep.scheme == 'https':
            contextFactory = ssl.ClientContextFactory()
            reactor.connectSSL(ep.host, ep.port, self.client, contextFactory)
        else:
            reactor.connectTCP(ep.host, ep.port, self.client)

        return client.deferred
        
    
    def _build_request_url(self, params):

        util.update_by_keywords_without_overwrite(
            params,
            AWSAccessKey = self._creds.access_key,
            SignatureVersion = 1,
            Timestamp = util.now(),
            Version = '2008-04-28',
            )

        items = self._prep_params( params )
        signature = self._calc_signature( items )

        items.append( ('Signature', signature) )

        querystr = '&'.join( '%s=%s' % (k, v) for (k, v) in items )

        return '%s?%s' % (self._endpoint.get_uri(), querystr)

    @staticmethod
    def _prep_params(params):
        # url encode all item values:
        items = [ (k, urllib.quote(str(params[k]))) for k in params ]

        # Sort case-insensitive:
        items.sort( cmp = lambda a, b: cmp(a.upper(), b.upper()) )

        return items

    def _calc_signature(self, items):
        return self._creds.sign(
            bytes=''.join( (k+v) for (k, v) in items ),
            hash_type='sha1')
