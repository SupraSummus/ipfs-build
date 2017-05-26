from ipfs_build import *

build_and_print(IPFSEnvironment({
    'index': StaticSource(b'abcdefgh'),
}))
