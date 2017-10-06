# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
from sys import maxint

from socorro.lib.util import DotDict
from socorro.processor.support_classifiers import (
    SupportClassificationRule,
    BitguardClassifier,
    OutOfDateClassifier,
)

from socorro.unittest.processor import create_basic_fake_processor
from socorro.unittest.processor.test_breakpad_pipe_to_json import (
    cannonical_json_dump,
)
from socorro.unittest.testbase import TestCase


class TestSupportClassificationRule(TestCase):

    def test_predicate(self):
        rc = DotDict()
        rd = {}
        pc = DotDict()
        pc.classifications = DotDict()
        processor = None

        support_rule = SupportClassificationRule()
        assert support_rule.predicate(rc, rd, pc, processor)

        pc.classifications.support = DotDict()
        assert support_rule.predicate(rc, rd, pc, processor)

    def test_action(self):
        rc = DotDict()
        rd = {}
        pc = DotDict()
        processor = None

        support_rule = SupportClassificationRule()
        assert support_rule.action(rc, rd, pc, processor)

    def test_version(self):
        support_rule = SupportClassificationRule()
        assert support_rule.version() == '0.0'

    def test_add_classification_to_processed_crash(self):
        pc = DotDict()
        pc.classifications = DotDict()

        support_rule = SupportClassificationRule()
        support_rule._add_classification(
            pc,
            'stupid',
            'extra stuff'
        )
        assert 'classifications' in pc
        assert 'support' in pc.classifications
        assert 'stupid' == pc.classifications.support.classification
        assert 'extra stuff' == pc.classifications.support.classification_data
        assert '0.0' == pc.classifications.support.classification_version


class TestBitguardClassfier(TestCase):

    def test_action_success(self):
        jd = copy.deepcopy(cannonical_json_dump)
        jd['modules'].append({'filename': 'bitguard.dll'})
        pc = DotDict()
        pc.json_dump = jd

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}
        rule = BitguardClassifier()
        action_result = rule.action(rc, rd, pc, fake_processor)

        assert action_result
        assert 'classifications' in pc
        assert 'support' in pc.classifications
        assert 'bitguard' == pc.classifications.support.classification

    def test_action_fail(self):
        jd = copy.deepcopy(cannonical_json_dump)
        pc = DotDict()
        pc.json_dump = jd

        fake_processor = create_basic_fake_processor()

        rc = DotDict()
        rd = {}
        rule = BitguardClassifier()
        action_result = rule.action(rc, rd, pc, fake_processor)

        assert not action_result
        assert 'classifications' not in pc


class TestOutOfDateClassifier(TestCase):

    def test_predicate(self):
        jd = copy.deepcopy(cannonical_json_dump)
        processed_crash = DotDict()
        processed_crash.json_dump = jd
        raw_crash = DotDict()
        raw_crash.ProductName = 'Firefox'
        raw_crash.Version = '16'
        raw_dumps = {}

        fake_processor = create_basic_fake_processor()
        fake_processor.config.firefox_out_of_date_version = '17'

        classifier = OutOfDateClassifier()
        assert classifier._predicate(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )

        raw_crash.Version = '19'
        assert not classifier._predicate(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )

        raw_crash.Version = '12'
        raw_crash.ProductName = 'NotFireFox'
        assert not classifier._predicate(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )

    def test_normalize_windows_version(self):
        classifier = OutOfDateClassifier()

        assert classifier._normalize_windows_version("5.1.2600 Service Pack 3") == (5, 1, 3)
        assert classifier._normalize_windows_version("5.1.2600") == (5, 1)
        assert classifier._normalize_windows_version("5.1.2600 Dwight Wilma") == (5, 1)
        assert classifier._normalize_windows_version("5") == (5, )

    def test_windows_action(self):
        jd = copy.deepcopy(cannonical_json_dump)
        processed_crash = DotDict()
        processed_crash.json_dump = jd
        raw_crash = DotDict()
        raw_crash.ProductName = 'Firefox'
        raw_crash.Version = '16'
        raw_dumps = {}

        fake_processor = create_basic_fake_processor()

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)
        processed_crash.json_dump['system_info']['os'] = 'Windows NT'
        processed_crash.json_dump['system_info']['os_ver'] = \
            '5.1.2600 Service Pack 2'
        assert classifier._windows_action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'firefox-no-longer-works-some-versions-windows-xp'
        assert processed_crash.classifications.support.classification == expected

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)
        processed_crash.json_dump['system_info']['os'] = 'Windows NT'
        processed_crash.json_dump['system_info']['os_ver'] = \
            '5.0 Service Pack 23'
        assert classifier._windows_action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'firefox-no-longer-works-windows-2000'
        assert processed_crash.classifications.support.classification == expected

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)
        processed_crash.json_dump['system_info']['os'] = 'Windows NT'
        processed_crash.json_dump['system_info']['os_ver'] = \
            '5.1.2600 Service Pack 3'
        assert classifier._windows_action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'update-firefox-latest-version'
        assert processed_crash.classifications.support.classification == expected

    def test_normalize_osx_version(self):
            classifier = OutOfDateClassifier()

            assert classifier._normalize_osx_version("10.4.5") == (10, 4)
            assert classifier._normalize_osx_version("10") == (10,)
            assert classifier._normalize_osx_version("10.dwight") == (10, maxint)

    def test_osx_action(self):
        jd = copy.deepcopy(cannonical_json_dump)
        processed_crash = DotDict()
        processed_crash.json_dump = jd
        raw_crash = DotDict()
        raw_crash.ProductName = 'Firefox'
        raw_crash.Version = '16'
        raw_dumps = {}

        fake_processor = create_basic_fake_processor()

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)
        processed_crash.json_dump['system_info']['os'] = 'Mac OS X'
        processed_crash.json_dump['system_info']['os_ver'] = '10.1'
        processed_crash.json_dump['system_info']['cpu_arch'] = 'ppc'
        assert classifier._osx_action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'firefox-no-longer-works-mac-os-10-4-or-powerpc'
        assert processed_crash.classifications.support.classification == expected

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)
        processed_crash.json_dump['system_info']['os'] = 'Mac OS X'
        processed_crash.json_dump['system_info']['os_ver'] = '10.5'
        processed_crash.json_dump['system_info']['cpu_arch'] = 'ppc'
        assert classifier._osx_action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'firefox-no-longer-works-mac-os-10-4-or-powerpc'
        assert processed_crash.classifications.support.classification == expected

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)
        processed_crash.json_dump['system_info']['os'] = 'Mac OS X'
        processed_crash.json_dump['system_info']['os_ver'] = '10.5'
        processed_crash.json_dump['system_info']['cpu_arch'] = 'x86'
        assert classifier._osx_action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'firefox-no-longer-works-mac-os-x-10-5'
        assert processed_crash.classifications.support.classification == expected

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)
        processed_crash.json_dump['system_info']['os'] = 'Mac OS X'
        processed_crash.json_dump['system_info']['os_ver'] = '10.99'
        assert classifier._osx_action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'update-firefox-latest-version'
        assert processed_crash.classifications.support.classification == expected

    def test_action(self):
        jd = copy.deepcopy(cannonical_json_dump)
        processed_crash = DotDict()
        processed_crash.json_dump = jd
        raw_crash = DotDict()
        raw_crash.ProductName = 'Firefox'
        raw_crash.Version = '16'
        raw_dumps = {}

        fake_processor = create_basic_fake_processor()

        classifier = OutOfDateClassifier()
        classifier.out_of_date_threshold = ('17',)

        processed_crash.json_dump['system_info']['os'] = 'Mac OS X'
        processed_crash.json_dump['system_info']['os_ver'] = '10.1'
        processed_crash.json_dump['system_info']['cpu_arch'] = 'ppc'
        assert classifier._action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'firefox-no-longer-works-mac-os-10-4-or-powerpc'
        assert processed_crash.classifications.support.classification == expected
        processed_crash.json_dump['system_info']['os'] = 'Windows NT'
        processed_crash.json_dump['system_info']['os_ver'] = \
            '5.1.2600 Service Pack 3'
        assert classifier._action(
            raw_crash,
            raw_dumps,
            processed_crash,
            fake_processor
        )
        expected = 'update-firefox-latest-version'
        assert processed_crash.classifications.support.classification == expected
