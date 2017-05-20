#!/usr/bin/env python3

from functools import lru_cache
from contextlib import contextmanager
import os
import subprocess
import re
from tempfile import TemporaryDirectory
import json


@contextmanager
def pushed(stack, value):
    stack.append(value)
    yield
    popped = stack.pop()
    assert(popped == value)


class Environment:
    @classmethod
    def from_dict(cls, description):
        return cls(
            sources={
                name: Source.from_dict(source)
                for name, source in description.get('sources', {}).items()
            },
            targets=description.get('targets')
        )

    def __init__(self, sources, targets=None):
        self.sources = sources
        self.targets = targets or self.sources.keys()
        self.build_stack = []

    def product_id(self, source_id):
        if source_id in self.build_stack:
            raise RuntimeError('dependency cycle detected: {}'.format(
                '; '.join(self.build_stack)
            ))
        with pushed(self.build_stack, source_id):
            return self.product_id_unsafe(source_id)

    def product_id_unsafe(self, source_id):
        raise NotImplementedError()

    def build(self):
        return {
            source_id: self.product_id(source_id) for
            source_id in self.targets
        }


class PathBasedIPFSEnvironment(Environment):

    @staticmethod
    def print_result(result):
        print(json.dumps({
            k: v.decode('ASCII') for k, v in result.items()
        }, indent=4, sort_keys=True))

    def __init__(self, sources, *args, **kwargs):
        super().__init__({
            os.path.realpath(key): source
            for key, source in sources.items()
        }, *args, **kwargs)

    def product_id(self, source_id):
        return super().product_id(os.path.realpath(source_id))

    @lru_cache(maxsize=None)
    def product_id_unsafe(self, source_id):
        source = self.sources.get(source_id)

        if os.path.isdir(source_id):
            if source is not None:
                if source.fillers != {}:
                    raise RuntimeError('substitution rules specified in directories are not supported ({})'.format(
                        source_id
                    ))

            # TODO fix
            # this has terrible complexity (number_of_dirs_and_files^2 i guess) but the code is simple, which is nice
            subbuilds = {
                p: self.product_id(os.path.join(source_id, p))
                for p in os.listdir(source_id)
            }
            with TemporaryDirectory() as tempdir:
                for name, product_id in subbuilds.items():
                    self.ipfs_get(product_id, os.path.join(tempdir, name))
                return self.ipfs_add_path(tempdir)

        elif os.path.isfile(source_id):
            if source is not None:
                with open(source_id, 'rb') as file:
                    data = file.read()
                data = source.render(data, self)
                return self.ipfs_add_data(data)
            else:
                return self.ipfs_add_path(source_id)

        else:
            raise RuntimeError('nonexistent source: {}'.format(source_id))

    def build(self):
        return {
            os.path.relpath(source_id): product_id
            for source_id, product_id in super().build().items()
        }

    def ipfs_add_data(self, data):
        return subprocess.run(['ipfs', 'add', '-Q'], input=data, stdout=subprocess.PIPE).stdout.strip()

    def ipfs_add_path(self, path):
        return subprocess.run(['ipfs', 'add', '-Q', '-r', path], stdout=subprocess.PIPE).stdout.strip()

    def ipfs_get(self, hash, dest):
        subprocess.run(['ipfs', 'get', '-o', dest, hash], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Source:
    @classmethod
    def from_dict(cls, description):
        return cls({
            placeholder.encode('UTF-8'): Filler.from_dict(filler)
            for placeholder, filler in description.items()
        })

    def __init__(self, fillers):
        self.fillers = fillers

    def render(self, data, environment):
        d = {
            key: filler.value(environment) for
            key, filler in self.fillers.items()
        }
        pattern = re.compile(b'|'.join([
            re.escape(key) for key in d.keys()
        ]))
        return pattern.sub(lambda x: d[x.group()], data)


class Filler:
    @classmethod
    def from_dict(cls, description):
        return {
            'const': lambda d: ConstantFiller(d['value'].encode('UTF-8')),
            'ref': lambda d: SourceReferenceFiller(d['source']),
        }[description['type']](description)

    def value(self, environment):
        raise NotImplementedError()


class ConstantFiller(Filler):
    def __init__(self, val):
        self.val = val

    def value(self, environment):
        return self.val


class SourceReferenceFiller(Filler):
    def __init__(self, source_id):
        self.source_id = source_id

    def value(self, environment):
        return environment.product_id(self.source_id)


if __name__ == '__main__':
    with open('.ipfs_build.json', 'rt') as f:
        description = json.load(f)
    environment = PathBasedIPFSEnvironment.from_dict(description)
    result = environment.build()
    PathBasedIPFSEnvironment.print_result(result)
