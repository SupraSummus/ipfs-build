from ipfs_build import *

build_and_print(IPFSEnvironment({
    'index': IPFSReplaceSource({b'cookies': 'strawberries'}),
    'strawberries': StaticSource(b'strawberries'),
}))
