#!/usr/bin/env python3

from functools import lru_cache
from contextlib import contextmanager
import os
import subprocess
import re
from tempfile import TemporaryDirectory
import json
import glob

### general environment ###

@contextmanager
def pushed(stack, value):
    stack.append(value)
    yield
    popped = stack.pop()
    assert(popped == value)

class Environment:

    @classmethod
    def from_dict(cls, d, source_constructors, **kwargs):
        source_types = {
            name: Source.from_dict(source_d, source_constructors=source_constructors, **kwargs)
            for name, source_d in description.get('source_types', {}).items()
        }
        source_constructors['source_type'] = lambda d: source_types[d['name']]

        return cls(
            sources={
                source_id: Source.from_dict(source_d, source_constructors=source_constructors, **kwargs)
                for source_id, source_d in description.get('sources', {}).items()
            },
            targets=description.get('targets', description.get('sources', {}).keys())
        )

    @staticmethod
    def print_result(result):
        print(json.dumps({
            k: v.decode() for k, v in result.items()
        }, indent=4, sort_keys=True))

    def __init__(self, sources, targets=None, **kwargs):
        self.sources = sources
        self.targets = targets or sources.keys()
        self.build_stack = []
        super().__init__(**kwargs)

    @lru_cache(maxsize=None)
    def product_id(self, source_id):
        if source_id in self.build_stack:
            raise RuntimeError('dependency cycle detected: {}'.format(
                '; '.join(self.build_stack)
            ))
        with pushed(self.build_stack, source_id):
            return self.sources[source_id].product_id(self, source_id)

    def build(self):
        return {
            source_id: self.product_id(source_id) for
            source_id in self.targets
        }


class Source:

    @staticmethod
    def from_dict(d, source_constructors, **kwargs):
        dd = d.copy()
        del dd['type']
        return source_constructors[d['type']](dd, **kwargs)

    def product_id(self, environment, source_id):
        raise NotImplementedError()


class StaticSource(Source):
    type = 'static'

    @classmethod
    def from_dict(cls, d, **kwargs):
        return cls(product_id=d['product_id'].encode())

    def __init__(self, product_id, **kwargs):
        self._product_id = product_id
        super().__init__(**kwargs)

    def product_id(self, environment, source_id):
        return self._product_id


### path environment ###

class PathEnvironment(Environment):

    def __init__(self, sources, **kwargs):
        super().__init__(sources={
            os.path.realpath(path): source
            for path, source in sources.items()
        }, **kwargs)

    def default_source_for_file(self):
        raise NotImplementedError()

    def default_source_for_dir(self):
        raise NotImplementedError()

    def product_id(self, source_id):
        source_id = os.path.realpath(source_id)
        if source_id not in self.sources:
            if os.path.isdir(source_id):
                source = self.default_source_for_dir()

            elif os.path.isfile(source_id):
                source = self.default_source_for_file()

            else:
                raise RuntimeError('nonexistent source: {}'.format(source_id))

            self.sources[source_id] = source
        return super().product_id(source_id)

    def build(self):
        return {
            os.path.relpath(source_id): product_id
            for source_id, product_id in super().build().items()
        }

    def read(self, path):
        with open(path, 'rb') as f:
            return f.read()


class WildcardPathEnvironment(PathEnvironment):

    def __init__(self, sources, targets, **kwargs):

        raw_sources = {}
        for wildcard_path, source in sources.items():
            for path in glob.glob(wildcard_path, recursive=True):
                if path in raw_sources:
                    raise RuntimeError('multiple sources for id {}'.format(path))
                raw_sources[path] = source

        raw_targets = []
        for t in targets:
            raw_targets.extend(glob.glob(t))

        super().__init__(sources=raw_sources, targets=raw_targets, **kwargs)


### IPFS environment ###

class IPFSEnvironment(PathEnvironment):

    def default_source_for_file(self):
        return IPFSFileSource()

    def default_source_for_dir(self):
        return IPFSDirSource()

    def ipfs_add_data(self, data):
        return subprocess.run(['ipfs', 'add', '-Q'], input=data, stdout=subprocess.PIPE).stdout.strip()

    def ipfs_add_path(self, path):
        return subprocess.run(['ipfs', 'add', '-Q', '-r', path], stdout=subprocess.PIPE).stdout.strip()

    def ipfs_get(self, hash, dest):
        subprocess.run(['ipfs', 'get', '-o', dest, hash], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class IPFSFileSource:

    def product_id(self, environment, source_id):
        return environment.ipfs_add_path(source_id)


class IPFSDirSource:

    def product_id(self, environment, source_id):
        # TODO fix
        # this has terrible complexity (n^2 i guess) but the code is simple, which is nice
        subbuilds = {
            p: environment.product_id(os.path.join(source_id, p))
            for p in os.listdir(source_id)
        }
        with TemporaryDirectory() as tempdir:
            for name, product_id in subbuilds.items():
                environment.ipfs_get(product_id, os.path.join(tempdir, name))
            return environment.ipfs_add_path(tempdir)


class IPFSDataSource(Source):

    def product_id(self, environment, source_id):
        return environment.ipfs_add_data(self.get_data(environment, source_id))

    def get_data(self, environment):
        raise NotImplementedError()


class IPFSReplaceSource(IPFSDataSource):
    type = 'replace'

    @classmethod
    def from_dict(cls, d, **kwargs):
        return cls(
            replace={
                key.encode(): s
                for key, s in d['replace'].items()
            }
        )

    def __init__(self, replace, **kwargs):
        self.replace = replace
        super().__init__(**kwargs)

    def get_data(self, environment, source_id):
        d = {
            key: environment.product_id(subsource_id) for
            key, subsource_id in self.replace.items()
        }
        pattern = re.compile(b'|'.join([
            re.escape(key) for key in d.keys()
        ]))
        return pattern.sub(lambda x: d[x.group()], environment.read(source_id))


class IPFSRegexpSource(IPFSDataSource):
    type = 'regexp'

    @classmethod
    def from_dict(cls, d, **kwargs):
        return cls(
            pattern=d['pattern'].encode(),
            replacement=d.get('replacement', '{}').encode(),
            source=d.get('source', '{}')
        )

    def __init__(self, pattern, replacement=b'{}', source='{}', **kwargs):
        self.pattern = pattern
        self.replacement = replacement
        self.source = source
        super().__init__(**kwargs)

    def get_data(self, environment, source_id):
        def replace_f(match):
            product_id = environment.product_id(self.source.format(
                *[g.decode() for g in match.groups()],
                **{name: g.decode() for name, g in match.groupdict().items()}
            ))
            return self.replacement.replace(b'{}', product_id)
        return re.compile(self.pattern).sub(replace_f, environment.read(source_id))


source_constructors = {
    StaticSource.type: StaticSource.from_dict,
    IPFSReplaceSource.type: IPFSReplaceSource.from_dict,
    IPFSRegexpSource.type: IPFSRegexpSource.from_dict,
}

def build_and_print(env):
    env.print_result(env.build())

if __name__ == '__main__':
    with open('.ipfs_build.json', 'rt') as f:
        description = json.load(f)
    environment = IPFSEnvironment.from_dict(description, source_constructors=source_constructors)
    build_and_print(environment)
