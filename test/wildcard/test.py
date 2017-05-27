from ipfs_build import *

build_and_print(IPFSEnvironment({
    'entry': StaticSource(b'an entry'),
    '*_index': IPFSReplaceSource({
        b'my entry': 'entry',
        b'your entry': 'entry',
    }),
}, targets=['*_index']))
