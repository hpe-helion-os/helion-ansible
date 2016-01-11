#
# (c) Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import jinja2.runtime as jrt


def _split_refs(refs):
    # ["a.b[0][1]", "c"] => ["a", "b[0][1]", c"]
    refs = reduce(lambda acc, i: acc + i.split('.'), refs, [])

    def split_indexes(acc, item):
        # "b[0][1]" => ["b", "0", "1"]
        p = item.partition('[')
        if len(p[1]) == 0:
            return acc + [item]
        return (acc + [p[0]] + p[2][:-1].split(']['))
    refs = reduce(split_indexes, refs, [])

    return refs


def item(root, *refs, **kwargs):
    """Complement to attr."""
    default = kwargs.get('d', jrt.StrictUndefined())
    default = kwargs.get('default', default)

    for ref in _split_refs(refs):
        try:
            if type(root) is list and ref.isdigit():
                ref = int(ref)
            try:
                root = root[ref]
            except KeyError:
                if not ref.isdigit():
                    raise
                root = root[int(ref)]
        except (KeyError, jrt.UndefinedError, IndexError):
            return default
    if isinstance(root, jrt.Undefined):
        return default
    return root


def by_item(array, path, value):
    if isinstance(array, jrt.Undefined):
        return []

    return [x for x in array
            if item(x, path, default=jrt.Undefined) == value]


def test_item():
    data = {'a': {'b': {'c': 111}}}
    assert item(data, 'a', 'b', 'c') is 111
    assert item(data, 'a.b', 'c') is 111
    assert item(data, 'a', 'b.c') is 111
    assert item(data, 'a.b.c') is 111

    assert isinstance(item(data, 'x', 'b'), jrt.Undefined)
    assert item(data, 'x', 'b', default=999) is 999
    assert item(data, 'a', 'x', default=999) is 999
    assert item(data, 'x', d=999) is 999
    assert item(data, 'x', d=None) is None

    data = {'a': [{'b': 111}, [222]]}
    assert item(data, 'a[0].b') is 111
    assert item(data, 'a.0.b') is 111
    assert item(data, 'a.0.1', d=999) is 999
    assert item(data, 'a[1][0]') is 222
    assert item(data, 'a.1.0') is 222
    assert item({'0': 111}, '0') is 111
    assert item({0: 111}, '0') is 111

    undef = jrt.StrictUndefined()
    assert item(undef, d=999) is 999
    assert item(undef, 'x', d=999) is 999
    assert item({'a': undef}, 'a', d=999) is 999


def test_by_item():
    data = [{'con': {'env': 'home'}, 'mount': '/var/lib/rabbitmq'},
            {'con': {'env': 'device'}, 'dev': '/dev/sda1'}]
    assert by_item(data, 'con.env', 'home') == [data[0]]
    assert by_item(data, 'con.env', 'device') == [data[1]]
    assert by_item(data, 'con.env', 'invalid') == []
    assert by_item(data, 'con.invalid', 'invaid') == []


class FilterModule(object):
    def filters(self):
        test_item()
        return {
            'item': item,
            'by_item': by_item
        }


if __name__ == "__main__":
    test_item()
    test_by_item()
