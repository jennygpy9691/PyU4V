# Copyright (c) 2019 Dell Inc. or its subsidiaries.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""test_pyu4v_requests.py."""

import json
import mock
import platform
import requests
import testtools

from PyU4V import rest_requests
from PyU4V.tests.unit_tests import pyu4v_common_data as pcd
from PyU4V.tests.unit_tests import pyu4v_fakes as pf
from PyU4V.utils import constants
from PyU4V.utils import exception


class PyU4VRestRequestsTest(testtools.TestCase):
    """Testing Unisphere REST requests."""

    def setUp(self):
        """Setup."""
        super(PyU4VRestRequestsTest, self).setUp()
        self.data = pcd.CommonData()
        pyu4v_version = constants.PYU4V_VERSION
        python_version = platform.python_version()
        sys_platform = platform.system()
        sys_platform_release = platform.release()
        self.ua_details = (
            'PyU4V/{pv} ({plat}; version {rel}) Python {python}'.format(
                pv=pyu4v_version, plat=sys_platform,
                rel=sys_platform_release, python=python_version))
        self.rest = rest_requests.RestRequests(
            username='smc', password='smc', verify=False,
            base_url='http://10.10.10.10:8443/univmax/restapi',
            interval=1, retries=3, application_type='pyu4v')

    def test_rest_requests_init(self):
        """Test class RestRequests __init__."""
        self.assertEqual(self.rest.username, 'smc')
        self.assertEqual(self.rest.password, 'smc')
        self.assertFalse(self.rest.verify_ssl)
        self.assertEqual(self.rest.base_url,
                         'http://10.10.10.10:8443/univmax/restapi')
        self.assertEqual(self.rest.interval, 1)
        self.assertEqual(self.rest.retries, 3)
        self.assertEqual(self.rest.timeout, 120)
        ref_headers = {'content-type': 'application/json',
                       'accept': 'application/json',
                       'application-type': 'pyu4v',
                       'user-agent': self.ua_details}
        self.assertEqual(self.rest.headers, ref_headers)
        self.assertIsInstance(self.rest.session,
                              type(requests.session()))

    def test_establish_rest_session(self):
        """Test establish REST session."""
        ref_headers = {'content-type': 'application/json',
                       'accept': 'application/json',
                       'application-type': 'pyu4v',
                       'user-agent': self.ua_details}
        self.assertEqual(ref_headers, self.rest.session.headers)
        self.assertEqual('smc', self.rest.session.auth.username)
        self.assertEqual('smc', self.rest.session.auth.password)
        self.assertEqual(False, self.rest.session.verify)

    def test_rest_request(self):
        """Test REST request success."""
        with mock.patch.object(
                self.rest.session, 'request',
                return_value=pf.FakeResponse(
                    200, self.data.server_version)) as mock_request:
            response, sc = self.rest.rest_request('/fake_uri', 'GET')
            mock_request.assert_called_once_with(
                method='GET', timeout=120,
                url='http://10.10.10.10:8443/univmax/restapi/fake_uri')
            self.assertEqual(200, sc)
            self.assertEqual(self.data.server_version, response)

    def test_rest_request_params(self):
        """Test REST request with parameters."""
        with mock.patch.object(
                self.rest.session, 'request',
                return_value=pf.FakeResponse(
                    200, self.data.server_version)) as mock_request:
            request_params = {'param': 'test'}
            response, sc = self.rest.rest_request(
                '/fake_uri', 'GET', params=request_params, timeout=500)
            mock_request.assert_called_once_with(
                method='GET', timeout=500, params=request_params,
                url='http://10.10.10.10:8443/univmax/restapi/fake_uri')
            self.assertEqual(200, sc)
            self.assertEqual(self.data.server_version, response)

    def test_rest_request_object(self):
        """Test REST request with object."""
        with mock.patch.object(
                self.rest.session, 'request',
                return_value=pf.FakeResponse(
                    200, self.data.server_version)) as mock_request:
            request_object = {'param': 'test'}
            response, sc = self.rest.rest_request(
                '/fake_uri', 'GET', request_object=request_object)
            mock_request.assert_called_once_with(
                method='GET', timeout=120,
                data=json.dumps(request_object, sort_keys=True, indent=4),
                url='http://10.10.10.10:8443/univmax/restapi/fake_uri')
            self.assertEqual(200, sc)
            self.assertEqual(self.data.server_version, response)

    def test_rest_request_no_session(self):
        """Test REST requests, no existing session available."""
        with mock.patch.object(
                self.rest, 'establish_rest_session',
                return_value=pf.FakeRequestsSession()) as mck_sesh:
            self.rest.session = None
            __, __ = self.rest.rest_request('/fake_uri', 'GET', timeout=0.1)
            mck_sesh.assert_called_once()

    def test_rest_request_value_error(self):
        """Test REST request value error no response."""
        with mock.patch.object(self.rest.session, 'request',
                               return_value=pf.FakeResponse(500, None)):
            response, sc = self.rest.rest_request('/fake_uri', 'GET')
            self.assertEqual(500, sc)
            self.assertIsNone(response)

    def test_rest_request_value_error_no_status_code(self):
        """Test REST request value error no response or status code."""
        with mock.patch.object(self.rest.session, 'request',
                               return_value=pf.FakeResponse(None, None)):
            response, sc = self.rest.rest_request('/fake_uri', 'GET')
            self.assertIsNone(sc)
            self.assertIsNone(response)

    def test_close_session(self):
        """Test close REST session."""
        with mock.patch.object(self.rest.session, 'close') as mck_close:
            self.rest.close_session()
            mck_close.assert_called_once()

    def test_rest_request_timeout_exception(self):
        """Test REST timeout exception scenario."""
        self.rest.session = pf.FakeRequestsSession()
        sc, msg = self.rest.rest_request('/fake_url', 'TIMEOUT')
        self.assertIsNone(sc)
        self.assertIsNone(msg)

    def test_rest_request_connection_exception(self):
        """Test REST HTTP error exception scenario."""
        self.rest.session = pf.FakeRequestsSession()
        self.assertRaises(requests.exceptions.HTTPError,
                          self.rest.rest_request, '/fake_url', 'HTTPERROR')

    def test_rest_request_ssl_exception(self):
        """Test REST SSL exception scenario."""
        self.rest.session = pf.FakeRequestsSession()
        self.assertRaises(requests.exceptions.SSLError,
                          self.rest.rest_request, '/fake_url', 'SSLERROR')

    def test_rest_request_other_exception(self):
        """Test REST other exception scenario."""
        self.rest.session = pf.FakeRequestsSession()
        self.assertRaises(exception.VolumeBackendAPIException,
                          self.rest.rest_request, '/fake_url', 'EXCEPTION')
